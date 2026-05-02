from typing import Any

import requests
import typer

from .browser import recover_portal_state, refresh_domain_state, refresh_lclibrary_state
from .state import extract_cookies_for_domain

LCLIBRARY_DOMAIN = "lclibrary.sufe.edu.cn"
LCLIBRARY_COOKIE_NAMES = ("ASP.NET_SessionId", "SF_cookie_154")

CANVAS_DOMAIN = "canvas.shufe.edu.cn"
CANVAS_COOKIE_NAMES = ("_normandy_session",)


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


def is_canvas_login_timeout(response: requests.Response) -> bool:
    if "login.sufe.edu.cn" in response.url:
        return True
    if response.status_code in (401, 403):
        return True
    try:
        data = response.json()
        if isinstance(data, dict) and "errors" in data:
            return True
    except Exception:
        pass
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


def get_canvas_cookies() -> dict[str, str]:
    cookies = extract_cookies_for_domain(CANVAS_DOMAIN, CANVAS_COOKIE_NAMES)
    if all(name in cookies for name in CANVAS_COOKIE_NAMES):
        return cookies
    return {}


def get_canvas_csrf_token() -> str | None:
    """从 state.json 中获取 Canvas 的 CSRF Token"""
    cookies = extract_cookies_for_domain(CANVAS_DOMAIN, ("_csrf_token",))
    return cookies.get("_csrf_token")


def fetch_canvas_auth_token(page_url: str | None = None) -> tuple[dict[str, str], str]:
    """访问 Canvas 页面获取最新的 cookies 和 authenticity_token

    Args:
        page_url: 要访问的 Canvas 页面 URL，用于提取 authenticity_token。
                  如果为 None，则使用 Canvas 首页。

    返回: (更新后的 cookies 字典, authenticity_token)
    """
    cookies = get_canvas_cookies()
    if not cookies:
        if not refresh_canvas_cookies():
            typer.secho("登录状态已过期，请运行 `sufe auth` 重新登录", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)
        cookies = get_canvas_cookies()

    target_url = page_url if page_url else "https://canvas.shufe.edu.cn/"
    headers = {
        "User-Agent": get_default_headers()["User-Agent"],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        response = requests.get(target_url, cookies=cookies, headers=headers, timeout=30)
    except requests.RequestException as e:
        typer.secho(f"获取 Canvas 认证 Token 失败: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    if is_canvas_login_timeout(response):
        typer.secho("检测到 Canvas 会话过期，正在后台尝试静默刷新...", fg=typer.colors.YELLOW)
        if not refresh_canvas_cookies():
            typer.secho("静默刷新失败，请运行 `sufe auth` 重新登录", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)
        cookies = get_canvas_cookies()
        try:
            response = requests.get(target_url, cookies=cookies, headers=headers, timeout=30)
        except requests.RequestException as e:
            typer.secho(f"重试获取 Canvas 认证 Token 失败: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)

    # 更新 cookies
    cookies.update(response.cookies.get_dict())

    # 提取 authenticity_token
    import re

    tokens = re.findall(r'name="authenticity_token" value="([^"]+)"', response.text)
    auth_token = tokens[0] if tokens else ""

    return cookies, auth_token


def refresh_canvas_cookies() -> bool:
    canvas_home = "https://canvas.shufe.edu.cn/"
    if refresh_domain_state(canvas_home) and get_canvas_cookies():
        return True
    if recover_portal_state() and refresh_domain_state(canvas_home) and get_canvas_cookies():
        return True
    return False


def _canvas_request(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    stream: bool = False,
    use_auth_token: bool = False,
    page_url: str | None = None,
    **kwargs: Any,
) -> requests.Response:
    """发送 Canvas API 请求

    Args:
        use_auth_token: 是否自动获取并附加 CSRF Token（POST 请求需要）
        page_url: 用于提取 authenticity_token 的 Canvas 页面 URL
    """

    def _do_request(cookies_dict: dict[str, str], auth_token: str = "") -> requests.Response:
        actual_headers = headers if headers is not None else get_default_headers()
        if auth_token:
            actual_headers = {**actual_headers, "X-CSRF-Token": auth_token}

        if method == "post":
            return requests.post(
                url, cookies=cookies_dict, headers=actual_headers, timeout=timeout, stream=stream, **kwargs
            )
        elif method == "get":
            return requests.get(
                url, cookies=cookies_dict, headers=actual_headers, timeout=timeout, stream=stream, **kwargs
            )
        else:
            msg = f"不支持的 HTTP 方法: {method}"
            raise ValueError(msg)

    if use_auth_token:
        cookies, auth_token = fetch_canvas_auth_token(page_url=page_url)
    else:
        cookies = get_canvas_cookies()
        auth_token = ""
        if not cookies:
            if not refresh_canvas_cookies():
                typer.secho("登录状态已过期，请运行 `sufe auth` 重新登录", fg=typer.colors.RED, err=True)
                raise typer.Exit(1)
            cookies = get_canvas_cookies()

    try:
        response = _do_request(cookies, auth_token)
    except requests.RequestException as e:
        typer.secho(f"请求失败: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    if not is_canvas_login_timeout(response):
        return response

    typer.secho("检测到 Canvas 会话过期，正在后台尝试静默刷新...", fg=typer.colors.YELLOW)
    if not refresh_canvas_cookies():
        typer.secho("静默刷新失败，请运行 `sufe auth` 重新登录", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    if use_auth_token:
        cookies, auth_token = fetch_canvas_auth_token()
    else:
        cookies = get_canvas_cookies()

    try:
        response = _do_request(cookies, auth_token)
    except requests.RequestException as e:
        typer.secho(f"重试请求失败: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    if is_canvas_login_timeout(response):
        typer.secho("重试依然被拒绝，请运行 `sufe auth` 重新登录", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    return response


def sufe_get_canvas(
    url: str, headers: dict[str, str] | None = None, timeout: int = 30, stream: bool = False, **kwargs: Any
) -> requests.Response:
    return _canvas_request("get", url, headers=headers, timeout=timeout, stream=stream, **kwargs)


def sufe_post_canvas(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    use_auth_token: bool = False,
    page_url: str | None = None,
    **kwargs: Any,
) -> requests.Response:
    return _canvas_request(
        "post", url, headers=headers, timeout=timeout, use_auth_token=use_auth_token, page_url=page_url, **kwargs
    )
