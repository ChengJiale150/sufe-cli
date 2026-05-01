from typing import Any

import requests
import typer

from .browser import recover_portal_state, refresh_lclibrary_state
from .state import extract_cookies_for_domain

LCLIBRARY_DOMAIN = "lclibrary.sufe.edu.cn"
LCLIBRARY_COOKIE_NAMES = ("ASP.NET_SessionId", "SF_cookie_154")


def get_default_headers() -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        ),
        "Referer": "https://lclibrary.sufe.edu.cn/ClientWeb/xcus/ic2/Default.aspx",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    }


def get_lclibrary_cookies() -> dict[str, str]:
    cookies = extract_cookies_for_domain(LCLIBRARY_DOMAIN, LCLIBRARY_COOKIE_NAMES)
    if all(name in cookies for name in LCLIBRARY_COOKIE_NAMES):
        return cookies
    return {}


def refresh_lclibrary_cookies() -> bool:
    if refresh_lclibrary_state() and get_lclibrary_cookies():
        return True
    if recover_portal_state() and refresh_lclibrary_state() and get_lclibrary_cookies():
        return True
    return False


def is_login_timeout(response: requests.Response) -> bool:
    if "login.sufe.edu.cn" in response.url:
        return True
    if response.status_code not in (200, 302, 304):
        return True
    try:
        data = response.json()
        if isinstance(data, dict) and "msg" in data:
            return "登录超时" in str(data.get("msg", ""))
    except Exception:
        return False

    return False


def sufe_get(url: str, headers: dict[str, str] | None = None, timeout: int = 30, **kwargs: Any) -> requests.Response:
    def _do_request() -> requests.Response:
        cookies = get_lclibrary_cookies()
        if not cookies:
            if not refresh_lclibrary_cookies():
                typer.secho("登录状态已过期，请运行 `sufe auth` 重新登录", fg=typer.colors.RED, err=True)
                raise typer.Exit(1)
            cookies = get_lclibrary_cookies()

        actual_headers = headers if headers is not None else get_default_headers()
        return requests.get(url, cookies=cookies, headers=actual_headers, timeout=timeout, **kwargs)

    try:
        response = _do_request()
    except requests.RequestException as e:
        typer.secho(f"请求失败: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    if not is_login_timeout(response):
        return response

    typer.secho("检测到会话过期，正在后台尝试静默刷新...", fg=typer.colors.YELLOW)
    if not refresh_lclibrary_cookies():
        typer.secho("静默刷新失败，请运行 `sufe auth` 重新登录", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    try:
        response = _do_request()
    except requests.RequestException as e:
        typer.secho(f"重试请求失败: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    if is_login_timeout(response):
        typer.secho("重试依然被拒绝，请运行 `sufe auth` 重新登录", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    return response
