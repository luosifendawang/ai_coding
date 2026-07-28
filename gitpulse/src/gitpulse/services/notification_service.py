"""Notification business service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

from gitpulse.config import FeishuConfig
from gitpulse.exceptions import (
    DuplicateNotificationError,
    FeishuError,
    FeishuSignatureError,
    FeishuTimeoutError,
    NotificationConfigurationError,
    NotificationConfirmationError,
    NotificationSecurityError,
    NotificationValidationError,
    RecordNotFoundError,
)
from gitpulse.integrations.feishu_client import FeishuClient
from gitpulse.integrations.feishu_signer import FeishuSigner
from gitpulse.models.diff import DiffCollection, DiffSource, FileChangeStatus, FileDiff
from gitpulse.models.feishu import FeishuSendResponse
from gitpulse.models.notification import (
    EligibilityIssue,
    NotificationPayload,
    NotificationRecord,
)
from gitpulse.models.weekly import WeeklyReport, WeeklyReportItem
from gitpulse.notifications.idempotency import NotificationIdempotencyService
from gitpulse.notifications.preview import NotificationPreview
from gitpulse.notifications.renderer import FeishuNotificationRenderer
from gitpulse.services.security_service import SecurityService
from gitpulse.storage.database import Database
from gitpulse.storage.serializers import IdGenerator
from gitpulse.storage.unit_of_work import UnitOfWork


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
            issues.append(EligibilityIssue(code="not_confirmed", message="当前周报尚未确认，不能发送到飞书。"))
        if report.source_coverage < 1:
            issues.append(EligibilityIssue(code="source_coverage", message="周报来源覆盖率不足 100%。"))
        if report.status == "archived":
            issues.append(EligibilityIssue(code="archived", message="已归档周报不能发送。"))
        if not report.content_markdown.strip():
            issues.append(EligibilityIssue(code="empty_content", message="周报 Markdown 内容为空。"))
        for item in self._items(report):
            if item.needs_confirmation or (item.confidence == "medium" and not item.confirmed_by_user):
                issues.append(EligibilityIssue(code="needs_confirmation", message="周报仍有待确认内容。"))
            if item.confidence == "low":
                issues.append(EligibilityIssue(code="low_confidence", message="周报包含低可信内容。"))
        return issues

    def _items(self, report: WeeklyReport) -> list[WeeklyReportItem]:
        items: list[WeeklyReportItem] = []
        for topic in report.completed:
            items.extend(topic.items)
        for section in [report.debugging, report.testing, report.risks, report.next_week]:
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
        client_factory=None,  # type: ignore[no-untyped-def]
    ) -> None:
        self.database = database
        self.config = feishu_config or FeishuConfig()
        self.renderer = renderer or FeishuNotificationRenderer()
        self.security_service = security_service or SecurityService()
        self.id_generator = id_generator or IdGenerator()
        self.eligibility = eligibility or WeeklyNotificationEligibility()
        self.client_factory = client_factory

    def preview_weekly(self, report_id: str) -> tuple[NotificationPayload, str]:
        report = self._get_report(report_id)
        self._validate_report(report)
        payload = self.renderer.render(report, self.config)
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
        self._scan_payload(payload)
        preview = NotificationPreview().render(payload, self.config)
        duplicate = NotificationIdempotencyService(self.database).check(
            payload,
            channel="feishu",
            window_hours=self.config.duplicate_window_hours,
        )
        current = datetime.now(timezone.utc)
        record = NotificationRecord(
            id=self.id_generator.new_notification_id(),
            report_id=report.id,
            channel="feishu",
            message_type=payload.message_type,
            status="pending",
            content_hash=payload.content_hash,
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
            if duplicate.is_duplicate and not force and not self.config.allow_duplicate_send:
                record = uow.notifications.update_status(record.id, status="duplicate_blocked")
            else:
                record = uow.notifications.update_status(record.id, status="previewed")
        if record.status == "duplicate_blocked":
            raise DuplicateNotificationError(duplicate.reason or "检测到重复发送。")
        if dry_run:
            return NotificationSendResult(record=record, payload=payload, preview=preview)
        if self.config.require_confirmation and not confirmed:
            with UnitOfWork(self.database) as uow:
                uow.notifications.update_status(record.id, status="cancelled")
            raise NotificationConfirmationError("发送飞书通知需要用户明确确认。")
        client = self._client()
        with UnitOfWork(self.database) as uow:
            record = uow.notifications.update_status(record.id, status="confirmed")
            record = uow.notifications.update_status(record.id, status="sending", attempt_count=1)
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
                    response_code=str(response.code) if response.code is not None else None,
                    response_message=response.message,
                    request_id=response.request_id,
                    sent_at=datetime.now(timezone.utc),
                )
            return NotificationSendResult(record=sent, payload=payload, response=response, preview=preview)
        return self._mark_failed(record.id, FeishuError(response.message or "飞书业务响应失败。"), payload, preview)

    def test_feishu_connection(self, *, confirmed: bool = False) -> FeishuSendResponse:
        if self.config.require_confirmation and not confirmed:
            raise NotificationConfirmationError("测试飞书连接需要用户明确确认。")
        if not self.config.test_message_enabled:
            raise NotificationConfigurationError("飞书测试消息已被配置关闭。")
        return self._client().test_connection()

    def _get_report(self, report_id: str) -> WeeklyReport:
        with UnitOfWork(self.database) as uow:
            report = uow.weekly_reports.get_by_id(report_id)
        if not report:
            raise RecordNotFoundError(f"未找到周报：{report_id}")
        return report

    def _validate_report(self, report: WeeklyReport) -> None:
        issues = self.eligibility.validate(report)
        if issues:
            raise NotificationValidationError("；".join(issue.message for issue in issues))

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
            raise NotificationSecurityError("飞书通知内容包含高风险敏感信息，已阻止发送。")

    def _client(self) -> FeishuClient:
        webhook = os.getenv(self.config.webhook_env)
        if not webhook:
            raise NotificationConfigurationError(f"未配置飞书机器人 Webhook。请设置环境变量：{self.config.webhook_env}")
        secret = os.getenv(self.config.secret_env)
        if self.config.signature_required and not secret:
            raise FeishuSignatureError("飞书机器人启用了签名校验，但本地未配置 Secret。")
        signer = FeishuSigner(secret) if secret else None
        if self.client_factory:
            return self.client_factory(webhook, self.config, signer)
        return FeishuClient(webhook, self.config, signer=signer)

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
