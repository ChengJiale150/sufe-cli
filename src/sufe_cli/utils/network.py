import requests
import typer
from typing import Dict, Any
from playwright.sync_api import sync_playwright

from ..config import STATE_FILE_PATH, SufeCookies, LclibraryCookies, save_cookies, load_cookies


def check_cookie_valid() -> tuple[bool, str]:
    """检查本地 Cookie 是否存在且未过期。返回 (是否有效, 状态信息)。"""
    cookies = load_cookies()
    if not cookies:
        return False, "Cookie 配置文件不存在或已损坏"

    try:
        req_cookies = {
            "ASP.NET_SessionId": cookies.lclibrary.asp_net_session_id,
            "SF_cookie_154": cookies.lclibrary.sf_cookie_154,
        }
        response = requests.get(
            "https://portal.sufe.edu.cn/main.html",
            cookies=req_cookies,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
                )
            },
            allow_redirects=True,
            timeout=10,
        )
    except requests.RequestException as e:
        return False, f"网络请求异常：{e}"

    if "login.sufe.edu.cn" in response.url:
        return False, "Cookie 已过期（被重定向到登录页面）"
    if response.status_code != 200:
        return False, f"Portal 返回非预期状态码：{response.status_code}"

    return True, "Cookie 配置有效"


def get_default_headers() -> Dict[str, str]:
    """返回通用的网络请求伪装头"""
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Referer": "https://lclibrary.sufe.edu.cn/ClientWeb/xcus/ic2/Default.aspx",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    }


def refresh_cookies_silently() -> bool:
    """
    静默刷新 Cookie
    使用已保存的 storage_state 在后台启动浏览器进行重定向登录。
    返回是否刷新成功。
    """
    if not STATE_FILE_PATH.exists():
        return False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=str(STATE_FILE_PATH))
            page = context.new_page()

            # 访问目标页面，期望通过 CAS cookie 自动完成重定向
            page.goto("https://lclibrary.sufe.edu.cn/ClientWeb/xcus/ic2/Default.aspx")
            page.wait_for_load_state("networkidle")

            # 如果依然在登录页，说明 CAS 凭证也过期了
            if "login.sufe.edu.cn" in page.url:
                browser.close()
                return False

            # 提取新 Cookie
            cookies = context.cookies()
            target_cookies = {}
            for cookie in cookies:
                if cookie["name"] in ["ASP.NET_SessionId", "SF_cookie_154"]:
                    target_cookies[cookie["name"]] = cookie["value"]

            if "ASP.NET_SessionId" not in target_cookies or "SF_cookie_154" not in target_cookies:
                browser.close()
                return False

            # 保存新的 Cookie 和状态
            lclibrary_cookies = LclibraryCookies(**target_cookies)
            cookie_model = SufeCookies(lclibrary=lclibrary_cookies)
            save_cookies(cookie_model)
            context.storage_state(path=str(STATE_FILE_PATH))

            browser.close()
            return True
    except Exception:
        return False


def is_login_timeout(response: requests.Response) -> bool:
    """判定响应是否代表登录已超时"""
    if "login.sufe.edu.cn" in response.url:
        return True
    if response.status_code not in (200, 302, 304):
        return True
    try:
        # 有些接口可能返回 200，但 JSON 里提示未登录
        data = response.json()
        if "登录超时" in str(data.get("msg", "")):
            return True
    except Exception:
        pass
    return False


def sufe_get(url: str, headers: Dict[str, str] | None = None, timeout: int = 30, **kwargs: Any) -> requests.Response:
    """
    带静默刷新机制的 GET 请求包装。
    会自动读取本地 Cookie 注入请求。
    如果发现过期，则尝试刷新，若刷新成功会重新发起请求。
    如果最终还是失败，将直接使用 typer 抛出错误退出。
    """

    def _do_request():
        cookies = load_cookies()
        if not cookies:
            typer.secho("未找到 Cookie 文件或文件损坏，请先运行 `sufe auth`", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)

        req_cookies = {
            "ASP.NET_SessionId": cookies.lclibrary.asp_net_session_id,
            "SF_cookie_154": cookies.lclibrary.sf_cookie_154,
        }

        actual_headers = headers if headers is not None else get_default_headers()

        return requests.get(url, cookies=req_cookies, headers=actual_headers, timeout=timeout, **kwargs)

    try:
        response = _do_request()
    except requests.RequestException as e:
        typer.secho(f"请求失败: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    if is_login_timeout(response):
        typer.secho("检测到会话过期，正在后台尝试静默刷新...", fg=typer.colors.YELLOW)
        if refresh_cookies_silently():
            typer.secho("静默刷新成功！重新执行请求...", fg=typer.colors.GREEN)
            try:
                response = _do_request()
            except requests.RequestException as e:
                typer.secho(f"重试请求失败: {e}", fg=typer.colors.RED, err=True)
                raise typer.Exit(1)

            if is_login_timeout(response):
                typer.secho("重试依然被拒绝，请手动运行 `sufe auth` 重新登录", fg=typer.colors.RED, err=True)
                raise typer.Exit(1)
        else:
            typer.secho(
                "静默刷新失败（统一身份认证可能也已过期），请手动运行 `sufe auth` 重新登录",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(1)

    return response
