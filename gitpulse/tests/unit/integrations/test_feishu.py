from __future__ import annotations

import json

import httpx
import pytest

from gitpulse.config import FeishuConfig
from gitpulse.exceptions import FeishuAuthenticationError, FeishuRequestError
from gitpulse.integrations.feishu_client import FeishuClient
from gitpulse.integrations.feishu_response import FeishuResponseParser


class NoSleep:
    def sleep(self, seconds: float) -> None:
        return None


def test_feishu_response_parser_checks_business_code() -> None:
    parser = FeishuResponseParser()

    ok = parser.parse(
        http_status=200,
        data={"code": 0, "msg": "success"},
        headers={"X-Request-Id": "req"},
    )
    bad = parser.parse(http_status=200, data={"code": 9499, "msg": "Bad Request"})

    assert ok.success is True
    assert ok.request_id == "req"
    assert bad.success is False


def test_feishu_client_authenticates_and_sends_as_application_bot() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/tenant_access_token/internal/"):
            assert json.loads(request.content) == {
                "app_id": "cli_testapp1234",
                "app_secret": "test-app-secret",
            }
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "tenant_access_token": "tenant-token",
                    "expire": 7200,
                },
            )
        assert request.url.path == "/open-apis/im/v1/messages"
        assert request.url.params["receive_id_type"] == "chat_id"
        assert request.headers["Authorization"] == "Bearer tenant-token"
        body = json.loads(request.content)
        assert body["receive_id"] == "oc_test_chat"
        assert body["msg_type"] == "text"
        assert json.loads(body["content"]) == {"text": "hello"}
        return httpx.Response(
            200,
            json={"code": 0, "msg": "success"},
            headers={"X-Request-Id": "req"},
        )

    client = FeishuClient(
        "cli_testapp1234",
        "test-app-secret",
        "oc_test_chat",
        FeishuConfig(max_retries=0),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleeper=NoSleep(),
    )

    first = client.send_text("hello")
    second = client.send_text("hello")

    assert first.success is True
    assert second.success is True
    assert (
        len(
            [
                request
                for request in requests
                if request.url.path.endswith("/tenant_access_token/internal/")
            ]
        )
        == 1
    )


def test_feishu_client_reports_invalid_application_credentials() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 10003, "msg": "invalid app"})

    client = FeishuClient(
        "cli_testapp1234",
        "wrong-secret",
        None,
        FeishuConfig(max_retries=0),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(FeishuAuthenticationError):
        client.authenticate()


def test_feishu_client_requires_receive_target_before_send() -> None:
    client = FeishuClient(
        "cli_testapp1234",
        "test-app-secret",
        None,
        FeishuConfig(max_retries=0),
    )

    with pytest.raises(FeishuRequestError):
        client.send_text("hello")
