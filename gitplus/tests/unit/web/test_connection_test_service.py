from pathlib import Path

from gitplus.ai.provider import LLMProvider
from gitplus.config import AIConfig, FeishuConfig, StorageConfig
from gitplus.models.ai import AIRequest, AIResponse
from gitplus.models.feishu import FeishuSendResponse
from gitplus.web.services.connection_test_service import ConnectionTestService


class HealthyProvider(LLMProvider):
    name = "healthy"

    @property
    def is_local(self) -> bool:
        return True

    def generate(self, request: AIRequest) -> AIResponse:
        assert "Git Diff" not in request.messages[0].content
        return AIResponse(content='{"status":"ok"}')

    def health_check(self) -> bool:
        return True


class FailingProvider(HealthyProvider):
    def generate(self, request: AIRequest) -> AIResponse:
        raise RuntimeError("raw-provider-detail")


def test_ai_connection_uses_minimal_request() -> None:
    service = ConnectionTestService(provider_factory=lambda _config: HealthyProvider())

    result = service.test_ai(AIConfig(), None)

    assert result["success"] is True
    assert result["message"] == "连接成功"


def test_ai_connection_does_not_return_raw_provider_error() -> None:
    service = ConnectionTestService(provider_factory=lambda _config: FailingProvider())

    result = service.test_ai(AIConfig(), None)

    assert result["success"] is False
    assert result["message"] == "AI Provider 连接失败"
    assert "raw-provider-detail" not in str(result)


def test_feishu_connection_authenticates_without_sending() -> None:
    class FakeFeishuClient:
        def test_connection(self, *, send_message: bool = False):
            assert send_message is False
            return FeishuSendResponse(
                success=True, http_status=200, code=0, message="success"
            )

    service = ConnectionTestService(
        feishu_client_factory=lambda *_args: FakeFeishuClient()
    )
    result = service.test_feishu(
        FeishuConfig(app_id="cli_testapp1234"),
        "test-app-secret",
    )

    assert result["success"] is True


def test_storage_paths_are_writable(tmp_path: Path) -> None:
    result = ConnectionTestService().test_storage(
        StorageConfig(database=Path("data/gitplus.db"), report_dir=Path("reports")),
        tmp_path,
    )

    assert result["success"] is True
    assert (tmp_path / "data" / "gitplus.db").exists()
    assert (tmp_path / "reports").is_dir()
