from typing import Any

import pytest

from sufe_cli.client import network as session
from sufe_cli.commands.lclibrary import client
from sufe_cli.errors import AuthExpiredError
from sufe_cli.runtime import CliContext


class DummyResponse:
    def __init__(self, *, url: str = "https://lclibrary.sufe.edu.cn/api", status_code: int = 200) -> None:
        self.url = url
        self.status_code = status_code

    def json(self) -> dict[str, str]:
        return {"msg": "ok"}


def test_sufe_get_uses_existing_lclibrary_cookies(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        session, "ensure_domain_cookies", lambda spec: {"ASP.NET_SessionId": "s", "SF_cookie_154": "sf"}
    )

    def fake_get(*args: Any, **kwargs: Any) -> DummyResponse:
        calls.append(kwargs)
        return DummyResponse()

    monkeypatch.setattr(client.requests, "get", fake_get)

    response = client.sufe_get("https://lclibrary.sufe.edu.cn/api")

    assert response.status_code == 200
    assert calls[0]["cookies"] == {"ASP.NET_SessionId": "s", "SF_cookie_154": "sf"}


def test_sufe_get_retries_once_after_login_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    responses = [
        DummyResponse(url="https://login.sufe.edu.cn/login/"),
        DummyResponse(url="https://lclibrary.sufe.edu.cn/api"),
    ]

    monkeypatch.setattr(session, "ensure_domain_cookies", lambda spec: {"ASP.NET_SessionId": "old"})
    monkeypatch.setattr(session, "refresh_domain_cookies_or_raise", lambda spec: {"ASP.NET_SessionId": "new"})

    def fake_get(*args: Any, **kwargs: Any) -> DummyResponse:
        calls.append(kwargs)
        return responses.pop(0)

    monkeypatch.setattr(client.requests, "get", fake_get)

    response = client.sufe_get("https://lclibrary.sufe.edu.cn/api")

    assert response.url == "https://lclibrary.sufe.edu.cn/api"
    assert [call["cookies"] for call in calls] == [{"ASP.NET_SessionId": "old"}, {"ASP.NET_SessionId": "new"}]


def test_sufe_get_uses_context_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        session, "ensure_domain_cookies", lambda spec: {"ASP.NET_SessionId": "s", "SF_cookie_154": "sf"}
    )

    def fake_get(*args: Any, **kwargs: Any) -> DummyResponse:
        calls.append(kwargs)
        return DummyResponse()

    monkeypatch.setattr(client.requests, "get", fake_get)

    client.sufe_get("https://lclibrary.sufe.edu.cn/api", context=CliContext(timeout=9))

    assert calls[0]["timeout"] == 9


def test_sufe_get_raises_auth_error_after_failed_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_auth_error(spec) -> dict[str, str]:
        raise AuthExpiredError("expired")

    monkeypatch.setattr(session, "ensure_domain_cookies", raise_auth_error)

    with pytest.raises(AuthExpiredError):
        client.sufe_get("https://lclibrary.sufe.edu.cn/api")
