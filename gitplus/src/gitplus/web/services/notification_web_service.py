"""Web orchestration for Feishu weekly notifications."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone

from gitplus.config import FeishuConfig, load_secret_value
from gitplus.exceptions import (
    FeishuError,
    RepositoryOperationError,
)
from gitplus.integrations.feishu_client import FeishuClient, FeishuWebhookClient
from gitplus.models.diff import DiffCollection, DiffSource, FileChangeStatus, FileDiff
from gitplus.models.feishu import FeishuSendResponse
from gitplus.models.notification import NotificationPayload, NotificationRecord
from gitplus.models.weekly import WeeklyReport, WeeklyReportItem
from gitplus.notifications.idempotency import NotificationIdempotencyService
from gitplus.notifications.preview import NotificationPreview
from gitplus.notifications.renderer import FeishuNotificationRenderer
from gitplus.services.security_service import SecurityService
from gitplus.storage.database import Database
from gitplus.storage.serializers import IdGenerator
from gitplus.storage.unit_of_work import UnitOfWork
from gitplus.web.schemas.notification import (
    NotificationPreviewRequest,
    NotificationRetryRequest,
    NotificationSendRequest,
    NotificationTestRequest,
)
from gitplus.web.services.repository_context_service import RepositoryContextService
from gitplus.web.services.repository_web_service import RepositoryWebError


class NotificationWebService:
    """Coordinate Web notification flows without exposing Feishu secrets."""

    def __init__(
        self,
        database: Database,
        repository_context: RepositoryContextService,
        config: FeishuConfig,
        *,
        security_service: SecurityService | None = None,
        renderer: FeishuNotificationRenderer | None = None,
        id_generator: IdGenerator | None = None,
        client_factory=None,  # type: ignore[no-untyped-def]
    ) -> None:
        self.database = database
        self.repository_context = repository_context
        self.config = config
        self.security_service = security_service or SecurityService()
        self.renderer = renderer or FeishuNotificationRenderer()
        self.id_generator = id_generator or IdGenerator()
        self.client_factory = client_factory

    def config_status(self) -> dict[str, object]:
        target = self._target()
        issues = self._config_issues()
        return {
            "enabled": self.config.enabled,
            "mode": self.config.mode,
            "valid": self.config.enabled and not issues,
            "message_type": self.config.message_type,
            "target": self._mask(target),
            "target_digest": self._target_digest(),
            "receive_id_type": self.config.receive_id_type
            if self.config.mode == "app"
            else None,
            "has_webhook": bool(self.config.webhook),
            "has_secret": bool(self.config.secret),
            "has_app_id": bool(self.config.app_id or os.getenv(self.config.app_id_env)),
            "has_app_secret": bool(self._app_secret()),
            "issues": issues,
        }

    def test(self, payload: NotificationTestRequest) -> dict[str, object]:
        self._require_config()
        if not payload.confirmed:
            raise RepositoryWebError(
                "notification_confirmation_required",
                "发送测试消息需要明确确认。",
                409,
            )
        try:
            response = self._client().test_connection(send_message=True)
        except FeishuError as exc:
            raise RepositoryWebError("feishu_test_failed", str(exc), 422) from exc
        return {"response": self._response_payload(response)}

    def preview(self, payload: NotificationPreviewRequest) -> dict[str, object]:
        self._require_config()
        report = self._owned_report(payload.report_id)
        self._validate_report(report)
        rendered = self._render(report, payload.message_type)
        self._scan(rendered)
        duplicate = self._duplicate(rendered)
        return {
            "report": self._report_summary(report),
            "message_type": rendered.message_type,
            "preview": NotificationPreview().render(rendered, self.config),
            "payload": rendered.payload,
            "byte_size": rendered.byte_size,
            "truncated": rendered.truncated,
            "removed_sections": rendered.removed_sections,
            "target": self._mask(self._target()),
            "target_digest": self._target_digest(),
            "duplicate": duplicate,
        }

    def send(self, payload: NotificationSendRequest) -> dict[str, object]:
        self._require_config()
        if not payload.confirmed:
            raise RepositoryWebError(
                "notification_confirmation_required",
                "发送正式周报需要明确确认。",
                409,
            )
        report = self._owned_report(payload.report_id)
        rendered = self._render(report, payload.message_type)
        return self._send_report(
            report,
            rendered,
            allow_duplicate=payload.allow_duplicate,
            retry_record=None,
        )

    def list_records(
        self, *, status: str | None, page: int, page_size: int
    ) -> dict[str, object]:
        with UnitOfWork(self.database) as uow:
            records = uow.notifications.list(
                status=status,
                channel="feishu",
                limit=page_size + 1,
                offset=(page - 1) * page_size,
            )
        has_next = len(records) > page_size
        return {
            "items": [self._record_payload(record) for record in records[:page_size]],
            "page": page,
            "page_size": page_size,
            "has_next": has_next,
        }

    def get_record(self, notification_id: str) -> dict[str, object]:
        with UnitOfWork(self.database) as uow:
            record = uow.notifications.get_by_id(notification_id)
        if not record:
            raise RepositoryWebError("notification_not_found", "未找到发送记录。", 404)
        return {"record": self._record_payload(record)}

    def retry(
        self, notification_id: str, payload: NotificationRetryRequest
    ) -> dict[str, object]:
        self._require_config()
        if not payload.confirmed:
            raise RepositoryWebError(
                "notification_confirmation_required",
                "重试发送需要明确确认。",
                409,
            )
        with UnitOfWork(self.database) as uow:
            record = uow.notifications.get_by_id(notification_id)
        if not record:
            raise RepositoryWebError("notification_not_found", "未找到发送记录。", 404)
        if record.status not in {"failed", "unknown"}:
            raise RepositoryWebError(
                "notification_retry_invalid",
                "只有失败或未知状态的记录可以重试。",
                409,
            )
        report = self._owned_report(record.report_id)
        rendered = self._render(report, record.message_type)
        return self._send_report(
            report,
            rendered,
            allow_duplicate=payload.allow_duplicate or record.forced,
            retry_record=record,
        )

    def confirmed_reports(self, *, limit: int = 50) -> list[dict[str, object]]:
        repository = self.repository_context.ensure_record()
        with UnitOfWork(self.database) as uow:
            reports = uow.weekly_reports.list(
                repository_id=repository.id,
                statuses=["confirmed"],
                limit=limit,
            )
        return [self._report_summary(report) for report in reports]

    def _send_report(
        self,
        report: WeeklyReport,
        rendered: NotificationPayload,
        *,
        allow_duplicate: bool,
        retry_record: NotificationRecord | None,
    ) -> dict[str, object]:
        self._validate_report(report)
        self._scan(rendered)
        duplicate = self._duplicate(rendered)
        if duplicate["is_duplicate"] and not allow_duplicate:
            record = self._create_record(
                report, rendered, status="duplicate_blocked", forced=False
            )
            return {
                "record": self._record_payload(record),
                "duplicate": duplicate,
                "message": "该版本周报已发送到相同目标。",
            }
        if retry_record:
            with UnitOfWork(self.database) as uow:
                record = uow.notifications.update_status(
                    retry_record.id,
                    status="sending",
                    attempt_count=retry_record.attempt_count + 1,
                )
        else:
            record = self._create_record(
                report,
                rendered,
                status="sending",
                forced=allow_duplicate,
                attempt_count=1,
            )
        try:
            response = self._client().send_payload(rendered.payload)
        except FeishuError as exc:
            with UnitOfWork(self.database) as uow:
                failed = uow.notifications.update_status(
                    record.id,
                    status="failed",
                    error_type=exc.__class__.__name__,
                    error_message=str(exc)[:300],
                )
            return {"record": self._record_payload(failed), "ok": False}
        message_id = self._message_id(response)
        with UnitOfWork(self.database) as uow:
            sent = uow.notifications.update_status(
                record.id,
                status="sent" if response.success else "failed",
                http_status=response.http_status,
                response_code=str(response.code) if response.code is not None else None,
                response_message=response.message,
                request_id=response.request_id,
                feishu_message_id=message_id,
                sent_at=datetime.now(timezone.utc) if response.success else None,
            )
            if response.success and report.status == "confirmed":
                updated = report.model_copy(
                    update={
                        "status": "sent",
                        "updated_at": datetime.now(timezone.utc),
                    }
                )
                try:
                    uow.weekly_reports.update(updated, expected_version=report.version)
                except RepositoryOperationError:
                    pass
        return {
            "record": self._record_payload(sent),
            "response": self._response_payload(response),
            "ok": response.success,
        }

    def _create_record(
        self,
        report: WeeklyReport,
        payload: NotificationPayload,
        *,
        status: str,
        forced: bool,
        attempt_count: int = 0,
    ) -> NotificationRecord:
        now = datetime.now(timezone.utc)
        record = NotificationRecord(
            id=self.id_generator.new_notification_id(),
            report_id=report.id,
            report_version=report.version,
            channel="feishu",
            provider_mode=self.config.mode,
            message_type=payload.message_type,
            status=status,  # type: ignore[arg-type]
            content_hash=payload.content_hash,
            target_digest=self._target_digest(),
            payload_summary=payload.text_preview[:500],
            byte_size=payload.byte_size,
            truncated=payload.truncated,
            removed_sections=payload.removed_sections,
            attempt_count=attempt_count,
            forced=forced,
            created_at=now,
            updated_at=now,
        )
        with UnitOfWork(self.database) as uow:
            return uow.notifications.create(record)

    def _render(self, report: WeeklyReport, message_type: str) -> NotificationPayload:
        config = self.config.model_copy(update={"message_type": message_type})
        payload = self.renderer.render(report, config)
        content_hash = self.renderer.fingerprint.generate(
            report_id=report.id,
            report_version=report.version,
            channel="feishu",
            message_type=payload.message_type,
            normalized_payload=payload.payload,
            target_digest=self._target_digest(),
        )
        return payload.model_copy(update={"content_hash": content_hash})

    def _duplicate(self, payload: NotificationPayload) -> dict[str, object]:
        with UnitOfWork(self.database) as uow:
            records = uow.notifications.find_sent_by_fingerprint(
                payload.content_hash,
                target_digest=self._target_digest(),
                statuses=["sent", "unknown"],
            )
        return {
            "is_duplicate": bool(records),
            "record_ids": [record.id for record in records],
            "message": "该版本周报已发送到相同目标。" if records else "",
        }

    def _owned_report(self, report_id: str) -> WeeklyReport:
        repository = self.repository_context.ensure_record()
        with UnitOfWork(self.database) as uow:
            report = uow.weekly_reports.get_by_id_for_repository(
                report_id, repository.id
            )
        if not report:
            raise RepositoryWebError("weekly_not_found", "未找到周报。", 404)
        return report

    def _validate_report(self, report: WeeklyReport) -> None:
        if report.status not in {"confirmed", "sent"}:
            raise RepositoryWebError(
                "weekly_state_invalid",
                "只有已确认或已发送周报可以发送到飞书。",
                422,
            )
        if report.source_coverage < 1:
            raise RepositoryWebError(
                "weekly_sources_incomplete",
                "周报来源覆盖率不足，不能发送。",
                422,
            )
        for item in self._items(report):
            if item.confidence == "low":
                raise RepositoryWebError(
                    "weekly_low_confidence", "低可信内容不能发送。", 422
                )
            if item.confidence == "medium" and not item.confirmed_by_user:
                raise RepositoryWebError(
                    "weekly_confirmation_required",
                    "仍有中可信工作项需要用户确认。",
                    422,
                )

    def _scan(self, payload: NotificationPayload) -> None:
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
            raise RepositoryWebError(
                "notification_sensitive_content",
                "飞书通知内容包含高风险敏感信息，已阻止发送。",
                422,
            )
        if payload.byte_size > self.config.max_json_bytes:
            raise RepositoryWebError(
                "notification_too_large",
                "飞书消息超过配置的 JSON 字节上限。",
                422,
            )

    def _client(self) -> FeishuClient | FeishuWebhookClient:
        if self.config.mode == "webhook":
            if not self.config.webhook:
                raise RepositoryWebError(
                    "feishu_config_invalid", "未配置飞书 Webhook。", 422
                )
            if self.client_factory:
                return self.client_factory("webhook", self.config)
            return FeishuWebhookClient(
                self.config.webhook,
                self.config,
                secret=self.config.secret,
            )
        app_id = self.config.app_id or os.getenv(self.config.app_id_env)
        app_secret = self._app_secret()
        receive_id = self._target()
        if not app_id or not app_secret or not receive_id:
            raise RepositoryWebError(
                "feishu_config_invalid", "飞书应用机器人配置不完整。", 422
            )
        if self.client_factory:
            return self.client_factory(app_id, app_secret, receive_id, self.config)
        return FeishuClient(app_id, app_secret, receive_id, self.config)

    def _require_config(self) -> None:
        issues = self._config_issues()
        if not self.config.enabled or issues:
            raise RepositoryWebError(
                "feishu_config_invalid",
                "飞书配置未启用或不完整。",
                422,
            )

    def _config_issues(self) -> list[str]:
        issues: list[str] = []
        if self.config.mode == "webhook":
            if not self.config.webhook:
                issues.append("缺少 feishu.webhook")
        else:
            if not (self.config.app_id or os.getenv(self.config.app_id_env)):
                issues.append("缺少 feishu.app_id")
            if not self._app_secret():
                issues.append("缺少 feishu.app_secret")
            if not self._target():
                issues.append("缺少 feishu.receive_id")
        return issues

    def _app_secret(self) -> str | None:
        return (
            self.config.app_secret
            or os.getenv(self.config.app_secret_env)
            or load_secret_value("feishu.app_secret")
        )

    def _target(self) -> str | None:
        if self.config.mode == "webhook":
            return self.config.webhook
        return self.config.receive_id or os.getenv(self.config.receive_id_env)

    def _target_digest(self) -> str:
        return NotificationIdempotencyService.target_digest(
            mode=self.config.mode,
            target=self._target() or "",
            receive_id_type=self.config.receive_id_type,
        )

    def _mask(self, value: str | None) -> str | None:
        if not value:
            return None
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]
        visible = value[-6:] if len(value) > 6 else value
        return f"***{visible} ({digest})"

    def _items(self, report: WeeklyReport) -> list[WeeklyReportItem]:
        items: list[WeeklyReportItem] = []
        for topic in report.completed:
            items.extend(topic.items)
        for section in [report.debugging, report.testing, report.risks, report.next_week]:
            items.extend(section)
        return items

    def _message_id(self, response: FeishuSendResponse) -> str | None:
        message_id = response.raw_metadata.get("message_id")
        return message_id if isinstance(message_id, str) else None

    def _response_payload(self, response: FeishuSendResponse) -> dict[str, object]:
        return {
            "success": response.success,
            "http_status": response.http_status,
            "code": response.code,
            "message": response.message,
            "request_id": response.request_id,
            "message_id": self._message_id(response),
        }

    def _record_payload(self, record: NotificationRecord) -> dict[str, object]:
        return record.model_dump(mode="json")

    def _report_summary(self, report: WeeklyReport) -> dict[str, object]:
        return {
            "id": report.id,
            "title": report.title,
            "status": report.status,
            "version": report.version,
            "date_from": report.date_range.date_from.isoformat(),
            "date_to": report.date_range.date_to.isoformat(),
            "source_coverage": report.source_coverage,
        }
