import json
from typing import Any

import requests

from sufe_cli.client.network import (
    DomainSessionSpec,
    get_default_headers,
    read_domain_cookies,
    refresh_domain_cookies,
    request_with_refresh,
)
from sufe_cli.runtime import CliContext, get_cli_context

LCLIBRARY_BASE = "https://lclibrary.sufe.edu.cn"
LCLIBRARY_HOME_URL = f"{LCLIBRARY_BASE}/ClientWeb/xcus/ic2/Default.aspx"
LCLIBRARY_COOKIE_NAMES = ("ASP.NET_SessionId", "SF_cookie_154")
LCLIBRARY_SESSION = DomainSessionSpec(
    host="lclibrary.sufe.edu.cn",
    entry_url=LCLIBRARY_HOME_URL,
    cookie_names=LCLIBRARY_COOKIE_NAMES,
    debug_label="",
)


def get_lclibrary_headers() -> dict[str, str]:
    return get_default_headers(referer=LCLIBRARY_HOME_URL, requested_with="XMLHttpRequest")


def get_lclibrary_cookies() -> dict[str, str]:
    return read_domain_cookies(LCLIBRARY_SESSION)


def refresh_lclibrary_cookies() -> bool:
    return refresh_domain_cookies(LCLIBRARY_SESSION)


def is_login_timeout(response: requests.Response) -> bool:
    if "login.sufe.edu.cn" in response.url:
        return True
    if response.status_code not in (200, 302, 304):
        return True
    try:
        data = response.json()
    except (json.JSONDecodeError, TypeError):
        return False
    return isinstance(data, dict) and "登录超时" in str(data.get("msg", ""))


def sufe_get(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    context: CliContext | None = None,
    **kwargs: Any,
) -> requests.Response:
    cli_context = get_cli_context(context)
    actual_timeout = timeout if timeout != 30 else cli_context.timeout

    def do_request(cookies: dict[str, str]) -> requests.Response:
        actual_headers = headers if headers is not None else get_lclibrary_headers()
        return requests.get(url, cookies=cookies, headers=actual_headers, timeout=actual_timeout, **kwargs)

    return request_with_refresh(
        LCLIBRARY_SESSION,
        do_request,
        is_login_timeout,
        context=cli_context,
        debug_message="检测到会话过期，正在后台尝试静默刷新...",
    )
