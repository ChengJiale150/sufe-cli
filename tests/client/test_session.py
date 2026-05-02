from typing import Any

import pytest
import requests

from sufe_cli.client import network as session
from sufe_cli.errors import AuthExpiredError


SPEC = session.DomainSessionSpec(
    host="example.sufe.edu.cn",
    entry_url="https://example.sufe.edu.cn/",
    cookie_names=("sid",),
    debug_label="测试",
)


def response_with_url(url: str = "https://example.sufe.edu.cn/api") -> requests.Response:
    response = requests.Response()
    response.url = url
    return response


def test_refresh_domain_cookies_recovers_portal_before_retrying_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_refresh_domain_state(url: str, **kwargs: Any) -> bool:
        calls.append(f"domain:{url}")
        return len(calls) == 3

    def fake_recover_portal_state(**kwargs: Any) -> bool:
        calls.append("portal")
        return True

    monkeypatch.setattr(session, "refresh_domain_state", fake_refresh_domain_state)
    monkeypatch.setattr(session, "recover_portal_state", fake_recover_portal_state)
    monkeypatch.setattr(session, "extract_cookies_for_domain", lambda *args, **kwargs: {"sid": "fresh"})

    assert session.refresh_domain_cookies(SPEC) is True
    assert calls == ["domain:https://example.sufe.edu.cn/", "portal", "domain:https://example.sufe.edu.cn/"]


def test_request_with_refresh_retries_once_with_refreshed_cookies(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, str]] = []
    responses = [
        response_with_url("https://login.sufe.edu.cn/login/"),
        response_with_url("https://example.sufe.edu.cn/api"),
    ]

    monkeypatch.setattr(session, "ensure_domain_cookies", lambda spec: {"sid": "old"})
    monkeypatch.setattr(session, "refresh_domain_cookies_or_raise", lambda spec: {"sid": "new"})

    def fake_request(cookies: dict[str, str]) -> requests.Response:
        calls.append(cookies)
        return responses.pop(0)

    response = session.request_with_refresh(
        SPEC,
        fake_request,
        lambda response: "login.sufe.edu.cn" in response.url,
    )

    assert response.url == "https://example.sufe.edu.cn/api"
    assert calls == [{"sid": "old"}, {"sid": "new"}]


def test_request_with_refresh_raises_when_domain_refresh_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_auth_error(spec) -> dict[str, str]:
        raise AuthExpiredError("expired")

    monkeypatch.setattr(session, "ensure_domain_cookies", raise_auth_error)

    with pytest.raises(AuthExpiredError):
        session.request_with_refresh(SPEC, lambda cookies: response_with_url(), lambda response: False)
