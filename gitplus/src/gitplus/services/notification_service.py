"""Notification business service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

from gitplus.config import FeishuConfig, load_secret_value
from gitplus.exceptions import (
    DuplicateNotificationError,
    FeishuError,
    FeishuTimeoutError,
    NotificationConfigurationError,
    NotificationConfirmationError,
    NotificationSecurityError,
    NotificationValidationError,
    RecordNotFoundError,
)
from gitplus.integrations.feishu_client import FeishuClient, FeishuWebhookClient
from gitplus.models.diff import DiffCollection, DiffSource, FileChangeStatus, FileDiff
from gitplus.models.feishu import FeishuSendResponse
from gitplus.models.notification import (
    EligibilityIssue,
    NotificationPayload,
    NotificationRecord,
)
from gitplus.models.weekly import WeeklyReport, WeeklyReportItem
from gitplus.notifications.idempotency import NotificationIdempotencyService
from gitplus.notifications.preview import NotificationPreview
from gitplus.notifications.renderer import FeishuNotificationRenderer
from gitplus.services.security_service import SecurityService
from gitplus.storage.database import Database
from gitplus.storage.serializers import IdGenerator
from gitplus.storage.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class NotificationSendResult:
    record: NotificationRecord
    payload: NotificationPayload
    response: FeishuSendResponse | None = None
    preview: str | None = None


class WeeklyNotificationEligibility:
    """Validate whether a weekly report can be sent."""

    def validate(self, report: WeeklyReport) -> list[EligibilityIssue]:
        issues: list[EligibilityIssue] = []
        if report.status != "confirmed":
            issues.append(
                EligibilityIssue(
                    code="not_confirmed", message="当前周报尚未确认，不能发送到飞书。"
                )
            )
        if report.source_coverage < 1:
            issues.append(
                EligibilityIssue(
                    code="source_coverage", message="周报来源覆盖率不足 100%。"
                )
            )
        if report.status == "archived":
            issues.append(
                EligibilityIssue(code="archived", message="已归档周报不能发送。")
            )
        if not report.content_markdown.strip():
            issues.append(
                EligibilityIssue(
                    code="empty_content", message="周报 Markdown 内容为空。"
                )
            )
        for item in self._items(report):
            if item.needs_confirmation or (
                item.confidence == "medium" and not item.confirmed_by_user
            ):
                issues.append(
                    EligibilityIssue(
                        code="needs_confirmation", message="周报仍有待确认内容。"
                    )
                )
            if item.confidence == "low":
                issues.append(
                    EligibilityIssue(
                        code="low_confidence", message="周报包含低可信内容。"
                    )
                )
        return issues

    def _items(self, report: WeeklyReport) -> list[WeeklyReportItem]:
        items: list[WeeklyReportItem] = []
        for topic in report.completed:
            items.extend(topic.items)
        for section in [
            report.debugging,
            report.testing,
            report.risks,
            report.next_week,
        ]:
            items.extend(section)
        return items


class NotificationService:
    """Coordinate weekly report delivery to Feishu."""

    def __init__(
        self,
        database: Database,
        *,
        feishu_config: FeishuConfig | None = None,
        renderer: FeishuNotificationRenderer | None = None,
        security_service: SecurityService | None = None,
        id_generator: IdGenerator | None = None,
        eligibility: WeeklyNotificationEligibility | None = None,
        app_secret: str | None = None,
        client_factory=None,  # type: ignore[no-untyped-def]
    ) -> None:
        self.database = database
        self.config = feishu_config or FeishuConfig()
        self.renderer = renderer or FeishuNotificationRenderer()
        self.security_service = security_service or SecurityService()
        self.id_generator = id_generator or IdGenerator()
        self.eligibility = eligibility or WeeklyNotificationEligibility()
        self.app_secret = app_secret
        self.client_factory = client_factory

    def preview_weekly(self, report_id: str) -> tuple[NotificationPayload, str]:
        report = self._get_report(report_id)
        self._validate_report(report)
        payload = self.renderer.render(report, self.config)
        payload = self._with_target_fingerprint(report, payload)
        self._scan_payload(payload)
        return payload, NotificationPreview().render(payload, self.config)

    def send_weekly(
        self,
        report_id: str,
        *,
        confirmed: bool = False,
        force: bool = False,
        dry_run: bool = False,
    ) -> NotificationSendResult:
        report = self._get_report(report_id)
        self._validate_report(report)
        payload = self.renderer.render(report, self.config)
        payload = self._with_target_fingerprint(report, payload)
        self._scan_payload(payload)
        preview = NotificationPreview().render(payload, self.config)
        duplicate = NotificationIdempotencyService(self.database).check(
            payload,
            channel="feishu",
            window_hours=self.config.duplicate_window_hours,
        )
        current = datetime.now(timezone.utc)
        target_digest = self._target_digest()
        record = NotificationRecord(
            id=self.id_generator.new_notification_id(),
            report_id=report.id,
            report_version=report.version,
            channel="feishu",
            provider_mode=self.config.mode,
            message_type=payload.message_type,
            status="pending",
            content_hash=payload.content_hash,
            target_digest=target_digest,
            payload_summary=payload.text_preview[:500],
            byte_size=payload.byte_size,
            truncated=payload.truncated,
            removed_sections=payload.removed_sections,
            forced=force,
            created_at=current,
            updated_at=current,
        )
        with UnitOfWork(self.database) as uow:
            record = uow.notifications.create(record)
            if (
                duplicate.is_duplicate
                and not force
                and not self.config.allow_duplicate_send
            ):
                record = uow.notifications.update_status(
                    record.id, status="duplicate_blocked"
                )
            else:
                record = uow.notifications.update_status(record.id, status="previewed")
        if record.status == "duplicate_blocked":
            raise DuplicateNotificationError(duplicate.reason or "检测到重复发送。")
        if dry_run:
            return NotificationSendResult(
                record=record, payload=payload, preview=preview
            )
        if self.config.require_confirmation and not confirmed:
            with UnitOfWork(self.database) as uow:
                uow.notifications.update_status(record.id, status="cancelled")
            raise NotificationConfirmationError("发送飞书通知需要用户明确确认。")
        client = self._client()
        with UnitOfWork(self.database) as uow:
            record = uow.notifications.update_status(record.id, status="confirmed")
            record = uow.notifications.update_status(
                record.id, status="sending", attempt_count=1
            )
        try:
            response = client.send_payload(payload.payload)
        except FeishuTimeoutError as exc:
            return self._mark_unknown(record.id, exc, payload, preview)
        except FeishuError as exc:
            return self._mark_failed(record.id, exc, payload, preview)
        if response.success:
            with UnitOfWork(self.database) as uow:
                sent = uow.notifications.update_status(
                    record.id,
                    status="sent",
                    attempt_count=self.config.max_retries + 1,
                    http_status=response.http_status,
                    response_code=str(response.code)
                    if response.code is not None
                    else None,
                    response_message=response.message,
                    request_id=response.request_id,
                    feishu_message_id=self._message_id(response),
                    sent_at=datetime.now(timezone.utc),
                )
            return NotificationSendResult(
                record=sent, payload=payload, response=response, preview=preview
            )
        return self._mark_failed(
            record.id,
            FeishuError(response.message or "飞书业务响应失败。"),
            payload,
            preview,
        )

    def test_feishu_connection(self, *, confirmed: bool = False) -> FeishuSendResponse:
        if self.config.require_confirmation and not confirmed:
            raise NotificationConfirmationError("测试飞书连接需要用户明确确认。")
        if not self.config.test_message_enabled:
            raise NotificationConfigurationError("飞书测试消息已被配置关闭。")
        return self._client().test_connection(send_message=True)

    def _get_report(self, report_id: str) -> WeeklyReport:
        with UnitOfWork(self.database) as uow:
            report = uow.weekly_reports.get_by_id(report_id)
        if not report:
            raise RecordNotFoundError(f"未找到周报：{report_id}")
        return report

    def _validate_report(self, report: WeeklyReport) -> None:
        issues = self.eligibility.validate(report)
        if issues:
            raise NotificationValidationError(
                "；".join(issue.message for issue in issues)
            )

    def _scan_payload(self, payload: NotificationPayload) -> None:
        text = payload.text_preview + "\n" + str(payload.payload)
        collection = DiffCollection(
            source=DiffSource.STAGED,
            files=[
                FileDiff.with_extension(
                    new_path="feishu-notification.txt",
                    status=FileChangeStatus.MODIFIED,
                    patch=text,
                )
            ],
        )
        result = self.security_service.process_diff(collection)
        if result.summary.high or result.summary.critical:
            raise NotificationSecurityError(
                "飞书通知内容包含高风险敏感信息，已阻止发送。"
            )

    def _client(self) -> FeishuClient | FeishuWebhookClient:
        if self.config.mode == "webhook":
            webhook = self.config.webhook
            if not webhook:
                raise NotificationConfigurationError("未配置飞书 Webhook。")
            return FeishuWebhookClient(
                webhook,
                self.config,
                secret=self.config.secret,
            )
        app_id = self.config.app_id or os.getenv(self.config.app_id_env)
        if not app_id:
            raise NotificationConfigurationError(
                f"未配置飞书应用 App ID。请配置 feishu.app_id 或环境变量：{self.config.app_id_env}"
            )
        app_secret = (
            self.app_secret
            or os.getenv(self.config.app_secret_env)
            or self.config.app_secret
            or load_secret_value("feishu.app_secret")
        )
        if not app_secret:
            raise NotificationConfigurationError(
                f"未配置飞书应用 App Secret。请使用本地 Secret 文件或环境变量：{self.config.app_secret_env}"
            )
        receive_id = self.config.receive_id or os.getenv(self.config.receive_id_env)
        if not receive_id:
            raise NotificationConfigurationError(
                f"未配置飞书消息接收目标。请配置 feishu.receive_id 或环境变量：{self.config.receive_id_env}"
            )
        if self.client_factory:
            return self.client_factory(app_id, app_secret, receive_id, self.config)
        return FeishuClient(app_id, app_secret, receive_id, self.config)

    def _target_digest(self) -> str:
        target = self.config.webhook if self.config.mode == "webhook" else self.config.receive_id
        return NotificationIdempotencyService.target_digest(
            mode=self.config.mode,
            target=target or "",
            receive_id_type=self.config.receive_id_type,
        )

    def _with_target_fingerprint(
        self, report: WeeklyReport, payload: NotificationPayload
    ) -> NotificationPayload:
        content_hash = self.renderer.fingerprint.generate(
            report_id=report.id,
            report_version=report.version,
            channel="feishu",
            message_type=payload.message_type,
            normalized_payload=payload.payload,
            target_digest=self._target_digest(),
        )
        return payload.model_copy(update={"content_hash": content_hash})

    def _message_id(self, response: FeishuSendResponse) -> str | None:
        message_id = response.raw_metadata.get("message_id")
        return message_id if isinstance(message_id, str) else None

    def _mark_failed(
        self,
        record_id: str,
        exc: Exception,
        payload: NotificationPayload,
        preview: str,
    ) -> NotificationSendResult:
        with UnitOfWork(self.database) as uow:
            record = uow.notifications.update_status(
                record_id,
                status="failed",
                error_type=exc.__class__.__name__,
                error_message=str(exc)[:300],
            )
        return NotificationSendResult(record=record, payload=payload, preview=preview)

    def _mark_unknown(
        self,
        record_id: str,
        exc: Exception,
        payload: NotificationPayload,
        preview: str,
    ) -> NotificationSendResult:
        with UnitOfWork(self.database) as uow:
            record = uow.notifications.update_status(
                record_id,
                status="unknown",
                error_type=exc.__class__.__name__,
                error_message=str(exc)[:300],
            )
        return NotificationSendResult(record=record, payload=payload, preview=preview)
