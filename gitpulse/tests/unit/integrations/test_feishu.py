from __future__ import annotations

import base64
import hashlib
import hmac
import json

import httpx
import pytest

from gitpulse.config import FeishuConfig
from gitpulse.exceptions import FeishuWebhookError
from gitpulse.integrations.feishu_client import FeishuClient, FeishuWebhookValidator
from gitpulse.integrations.feishu_response import FeishuResponseParser
from gitpulse.integrations.feishu_signer import FeishuSigner


class FixedClock:
    def now_timestamp(self) -> int:
        return 1599360473


class NoSleep:
    def sleep(self, seconds: float) -> None:
        return None


def test_feishu_signer_uses_official_algorithm() -> None:
    secret = "test-secret"
    signature = FeishuSigner(secret, FixedClock()).generate()
    expected = base64.b64encode(
        hmac.new(f"1599360473\n{secret}".encode(), digestmod=hashlib.sha256).digest()
    ).decode("utf-8")

    assert signature.timestamp == "1599360473"
    assert signature.sign == expected


def test_webhook_validator_allows_only_feishu_https_v2() -> None:
    validator = FeishuWebhookValidator()

    validator.validate("https://open.feishu.cn/open-apis/bot/v2/hook/abcd")

    with pytest.raises(FeishuWebhookError):
        validator.validate("http://open.feishu.cn/open-apis/bot/v2/hook/abcd")
    with pytest.raises(FeishuWebhookError):
        validator.validate("https://example.com/open-apis/bot/v2/hook/abcd")


def test_feishu_response_parser_checks_business_code() -> None:
    parser = FeishuResponseParser()

    ok = parser.parse(http_status=200, data={"code": 0, "msg": "success"}, headers={"X-Request-Id": "req"})
    bad = parser.parse(http_status=200, data={"code": 9499, "msg": "Bad Request"})

    assert ok.success is True
    assert ok.request_id == "req"
    assert bad.success is False


def test_feishu_client_adds_signature_and_parses_success() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content.decode("utf-8")))
        return httpx.Response(200, json={"code": 0, "msg": "success"})

    client = FeishuClient(
        "https://open.feishu.cn/open-apis/bot/v2/hook/abcd",
        FeishuConfig(max_retries=0),
        signer=FeishuSigner("test-secret", FixedClock()),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleeper=NoSleep(),
    )

    response = client.send_text("hello")

    assert response.success is True
    assert seen["timestamp"] == "1599360473"
    assert seen["msg_type"] == "text"
