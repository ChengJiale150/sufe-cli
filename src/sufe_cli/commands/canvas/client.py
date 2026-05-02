import re
from typing import Any, Literal

import requests

from sufe_cli.client.http import DEFAULT_USER_AGENT, get_default_headers
from sufe_cli.client.session import (
    DomainSessionSpec,
    RETRY_REJECTED_MESSAGE,
    ensure_domain_cookies,
    read_domain_cookies,
    refresh_domain_cookies,
    refresh_domain_cookies_or_raise,
    request_with_refresh,
)
from sufe_cli.client.state import extract_cookies_for_domain
from sufe_cli.errors import AuthExpiredError, RequestFailedError
from sufe_cli.runtime import CliContext, debug_log, get_cli_context

CANVAS_BASE = "https://canvas.shufe.edu.cn"
CANVAS_COOKIE_NAMES = ("_normandy_session",)
CANVAS_SESSION = DomainSessionSpec(
    host="canvas.shufe.edu.cn",
    entry_url=f"{CANVAS_BASE}/",
    cookie_names=CANVAS_COOKIE_NAMES,
    debug_label="Canvas ",
)


def get_canvas_cookies() -> dict[str, str]:
    return read_domain_cookies(CANVAS_SESSION)


def get_canvas_csrf_token() -> str | None:
    cookies = extract_cookies_for_domain("canvas.shufe.edu.cn", ("_csrf_token",))
    return cookies.get("_csrf_token")


def refresh_canvas_cookies() -> bool:
    return refresh_domain_cookies(CANVAS_SESSION)


def is_canvas_login_timeout(response: requests.Response) -> bool:
    if "login.sufe.edu.cn" in response.url:
        return True
    if response.status_code in (401, 403):
        return True
    try:
        data = response.json()
    except Exception:
        return False
    return isinstance(data, dict) and "errors" in data


def fetch_canvas_auth_token(
    page_url: str | None = None, context: CliContext | None = None
) -> tuple[dict[str, str], str]:
    cli_context = get_cli_context(context)
    cookies = ensure_domain_cookies(CANVAS_SESSION)

    target_url = page_url or f"{CANVAS_BASE}/"
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        response = requests.get(target_url, cookies=cookies, headers=headers, timeout=cli_context.timeout)
    except requests.RequestException as e:
        raise RequestFailedError(f"获取 Canvas 认证 Token 失败: {e}") from e

    if is_canvas_login_timeout(response):
        debug_log("检测到 Canvas 会话过期，正在后台尝试静默刷新...", cli_context)
        cookies = refresh_domain_cookies_or_raise(CANVAS_SESSION)
        try:
            response = requests.get(target_url, cookies=cookies, headers=headers, timeout=cli_context.timeout)
        except requests.RequestException as e:
            raise RequestFailedError(f"重试获取 Canvas 认证 Token 失败: {e}") from e

    cookies.update(response.cookies.get_dict())
    tokens = re.findall(r'name="authenticity_token" value="([^"]+)"', response.text)
    return cookies, tokens[0] if tokens else ""


def _canvas_request(
    method: Literal["get", "post"],
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    stream: bool = False,
    use_auth_token: bool = False,
    page_url: str | None = None,
    context: CliContext | None = None,
    **kwargs: Any,
) -> requests.Response:
    cli_context = get_cli_context(context)
    actual_timeout = timeout if timeout != 30 else cli_context.timeout

    def do_request(cookies_dict: dict[str, str], auth_token: str = "") -> requests.Response:
        actual_headers = headers if headers is not None else get_default_headers()
        if auth_token:
            actual_headers = {**actual_headers, "X-CSRF-Token": auth_token}
        request = requests.post if method == "post" else requests.get
        return request(
            url, cookies=cookies_dict, headers=actual_headers, timeout=actual_timeout, stream=stream, **kwargs
        )

    if not use_auth_token:
        return request_with_refresh(
            CANVAS_SESSION,
            lambda cookies: do_request(cookies),
            is_canvas_login_timeout,
            context=cli_context,
            debug_message="检测到 Canvas 会话过期，正在后台尝试静默刷新...",
        )

    cookies, auth_token = fetch_canvas_auth_token(page_url=page_url, context=cli_context)

    try:
        response = do_request(cookies, auth_token)
    except requests.RequestException as e:
        raise RequestFailedError(f"请求失败: {e}") from e

    if not is_canvas_login_timeout(response):
        return response

    debug_log("检测到 Canvas 会话过期，正在后台尝试静默刷新...", cli_context)
    refresh_domain_cookies_or_raise(CANVAS_SESSION)
    cookies, auth_token = fetch_canvas_auth_token(page_url=page_url, context=cli_context)

    try:
        response = do_request(cookies, auth_token)
    except requests.RequestException as e:
        raise RequestFailedError(f"重试请求失败: {e}") from e

    if is_canvas_login_timeout(response):
        raise AuthExpiredError(RETRY_REJECTED_MESSAGE)
    return response


def sufe_get_canvas(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    stream: bool = False,
    context: CliContext | None = None,
    **kwargs: Any,
) -> requests.Response:
    return _canvas_request("get", url, headers=headers, timeout=timeout, stream=stream, context=context, **kwargs)


def sufe_post_canvas(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    use_auth_token: bool = False,
    page_url: str | None = None,
    context: CliContext | None = None,
    **kwargs: Any,
) -> requests.Response:
    return _canvas_request(
        "post",
        url,
        headers=headers,
        timeout=timeout,
        use_auth_token=use_auth_token,
        page_url=page_url,
        context=context,
        **kwargs,
    )
