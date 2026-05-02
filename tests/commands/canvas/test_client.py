from typing import Any

import pytest

from sufe_cli.client import session
from sufe_cli.commands.canvas import client
from sufe_cli.errors import AuthExpiredError
from sufe_cli.runtime import CliContext


class DummyCookies:
    def get_dict(self) -> dict[str, str]:
        return {"fresh": "cookie"}


class DummyResponse:
    def __init__(
        self,
        *,
        url: str = "https://canvas.shufe.edu.cn/",
        status_code: int = 200,
        text: str = "",
        data: dict | None = None,
    ) -> None:
        self.url = url
        self.status_code = status_code
        self.text = text
        self._data = data or {}
        self.cookies = DummyCookies()

    def json(self) -> dict:
        return self._data


def test_fetch_canvas_auth_token_extracts_token_and_response_cookies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client, "ensure_domain_cookies", lambda spec: {"_normandy_session": "s"})
    monkeypatch.setattr(
        client.requests,
        "get",
        lambda *args, **kwargs: DummyResponse(text='<input name="authenticity_token" value="token-123">'),
    )

    cookies, token = client.fetch_canvas_auth_token()

    assert cookies == {"_normandy_session": "s", "fresh": "cookie"}
    assert token == "token-123"


def test_canvas_request_refreshes_and_retries_on_login_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    responses = [
        DummyResponse(url="https://login.sufe.edu.cn/login/"),
        DummyResponse(url="https://canvas.shufe.edu.cn/api"),
    ]

    monkeypatch.setattr(session, "ensure_domain_cookies", lambda spec: {"_normandy_session": "old"})
    monkeypatch.setattr(session, "refresh_domain_cookies_or_raise", lambda spec: {"_normandy_session": "new"})

    def fake_get(*args: Any, **kwargs: Any) -> DummyResponse:
        calls.append(kwargs)
        return responses.pop(0)

    monkeypatch.setattr(client.requests, "get", fake_get)

    response = client.sufe_get_canvas("https://canvas.shufe.edu.cn/api")

    assert response.url == "https://canvas.shufe.edu.cn/api"
    assert [call["cookies"] for call in calls] == [{"_normandy_session": "old"}, {"_normandy_session": "new"}]


def test_canvas_post_adds_auth_token_header(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        client,
        "fetch_canvas_auth_token",
        lambda page_url=None, context=None: ({"_normandy_session": "s"}, "csrf"),
    )

    def fake_post(*args: Any, **kwargs: Any) -> DummyResponse:
        calls.append(kwargs)
        return DummyResponse()

    monkeypatch.setattr(client.requests, "post", fake_post)

    client.sufe_post_canvas("https://canvas.shufe.edu.cn/api", use_auth_token=True)

    assert calls[0]["headers"]["X-CSRF-Token"] == "csrf"


def test_canvas_request_uses_context_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(session, "ensure_domain_cookies", lambda spec: {"_normandy_session": "s"})

    def fake_get(*args: Any, **kwargs: Any) -> DummyResponse:
        calls.append(kwargs)
        return DummyResponse()

    monkeypatch.setattr(client.requests, "get", fake_get)

    client.sufe_get_canvas("https://canvas.shufe.edu.cn/api", context=CliContext(timeout=7))

    assert calls[0]["timeout"] == 7


def test_canvas_request_raises_auth_error_after_failed_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_auth_error(spec) -> dict[str, str]:
        raise AuthExpiredError("expired")

    monkeypatch.setattr(session, "ensure_domain_cookies", raise_auth_error)

    with pytest.raises(AuthExpiredError):
        client.sufe_get_canvas("https://canvas.shufe.edu.cn/api")
