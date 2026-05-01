from typing import Any

import pytest

from sufe_cli.client import http


class DummyResponse:
    def __init__(self, *, url: str = "https://lclibrary.sufe.edu.cn/api", status_code: int = 200) -> None:
        self.url = url
        self.status_code = status_code

    def json(self) -> dict[str, str]:
        return {"msg": "ok"}


def test_sufe_get_uses_existing_lclibrary_cookies(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(http, "get_lclibrary_cookies", lambda: {"ASP.NET_SessionId": "s", "SF_cookie_154": "sf"})
    monkeypatch.setattr(http, "refresh_lclibrary_cookies", lambda: False)

    def fake_get(*args: Any, **kwargs: Any) -> DummyResponse:
        calls.append(kwargs)
        return DummyResponse()

    monkeypatch.setattr(http.requests, "get", fake_get)

    response = http.sufe_get("https://lclibrary.sufe.edu.cn/api")

    assert response.status_code == 200
    assert calls[0]["cookies"] == {"ASP.NET_SessionId": "s", "SF_cookie_154": "sf"}


def test_sufe_get_refreshes_when_cookies_are_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    cookie_states = [{}, {"ASP.NET_SessionId": "s", "SF_cookie_154": "sf"}]
    refreshed = False

    def fake_cookies() -> dict[str, str]:
        return cookie_states.pop(0) if cookie_states else {"ASP.NET_SessionId": "s", "SF_cookie_154": "sf"}

    def fake_refresh() -> bool:
        nonlocal refreshed
        refreshed = True
        return True

    monkeypatch.setattr(http, "get_lclibrary_cookies", fake_cookies)
    monkeypatch.setattr(http, "refresh_lclibrary_cookies", fake_refresh)
    monkeypatch.setattr(http.requests, "get", lambda *args, **kwargs: DummyResponse())

    http.sufe_get("https://lclibrary.sufe.edu.cn/api")

    assert refreshed is True


def test_sufe_get_retries_once_after_login_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        DummyResponse(url="https://login.sufe.edu.cn/login/"),
        DummyResponse(url="https://lclibrary.sufe.edu.cn/api"),
    ]
    refresh_count = 0

    def fake_refresh() -> bool:
        nonlocal refresh_count
        refresh_count += 1
        return True

    monkeypatch.setattr(http, "get_lclibrary_cookies", lambda: {"ASP.NET_SessionId": "s", "SF_cookie_154": "sf"})
    monkeypatch.setattr(http, "refresh_lclibrary_cookies", fake_refresh)
    monkeypatch.setattr(http.requests, "get", lambda *args, **kwargs: responses.pop(0))

    response = http.sufe_get("https://lclibrary.sufe.edu.cn/api")

    assert response.url == "https://lclibrary.sufe.edu.cn/api"
    assert refresh_count == 1
