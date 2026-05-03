from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import requests

from sufe_cli.config import STATE_FILE_PATH
from sufe_cli.errors import AuthExpiredError, RequestFailedError
from sufe_cli.runtime import CliContext, debug_log, get_cli_context

from .auth.browser import recover_portal_state, refresh_domain_state
from .state import extract_cookies_for_domain

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
)

AUTH_EXPIRED_MESSAGE = "认证配置缺失或登录状态已过期，请先运行 `sufe auth` 完成配置"
REFRESH_FAILED_MESSAGE = "静默刷新失败，请先运行 `sufe auth` 完成配置"
RETRY_REJECTED_MESSAGE = "重试依然被拒绝，请先运行 `sufe auth` 完成配置"


def get_default_headers(
    *,
    accept: str = "application/json, text/javascript, */*; q=0.01",
    referer: str | None = None,
    requested_with: str | None = None,
) -> dict[str, str]:
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": accept,
    }
    if referer is not None:
        headers["Referer"] = referer
    if requested_with is not None:
        headers["X-Requested-With"] = requested_with
    return headers


@dataclass(frozen=True)
class DomainSessionSpec:
    host: str
    entry_url: str
    cookie_names: tuple[str, ...]
    debug_label: str


def read_domain_cookies(spec: DomainSessionSpec, state_path: Path | None = None) -> dict[str, str]:
    cookies = extract_cookies_for_domain(spec.host, spec.cookie_names, state_path)
    if all(name in cookies for name in spec.cookie_names):
        return cookies
    return {}


def refresh_domain_cookies(spec: DomainSessionSpec, state_path: Path = STATE_FILE_PATH) -> bool:
    if refresh_domain_state(spec.entry_url, state_path=state_path) and read_domain_cookies(spec, state_path):
        return True
    return (
        recover_portal_state(state_path=state_path)
        and refresh_domain_state(spec.entry_url, state_path=state_path)
        and bool(read_domain_cookies(spec, state_path))
    )


def ensure_domain_cookies(spec: DomainSessionSpec, state_path: Path | None = None) -> dict[str, str]:
    actual_path = STATE_FILE_PATH if state_path is None else state_path
    cookies = read_domain_cookies(spec, actual_path)
    if cookies:
        return cookies
    if not refresh_domain_cookies(spec, state_path=actual_path):
        raise AuthExpiredError(AUTH_EXPIRED_MESSAGE)
    cookies = read_domain_cookies(spec, actual_path)
    if not cookies:
        raise AuthExpiredError(AUTH_EXPIRED_MESSAGE)
    return cookies


def refresh_domain_cookies_or_raise(spec: DomainSessionSpec, state_path: Path | None = None) -> dict[str, str]:
    actual_path = STATE_FILE_PATH if state_path is None else state_path
    if not refresh_domain_cookies(spec, state_path=actual_path):
        raise AuthExpiredError(REFRESH_FAILED_MESSAGE)
    cookies = read_domain_cookies(spec, actual_path)
    if not cookies:
        raise AuthExpiredError(REFRESH_FAILED_MESSAGE)
    return cookies


def request_with_refresh(
    spec: DomainSessionSpec,
    request: Callable[[dict[str, str]], requests.Response],
    is_login_timeout: Callable[[requests.Response], bool],
    *,
    context: CliContext | None = None,
    debug_message: str | None = None,
    request_error_message: str = "请求失败",
    retry_error_message: str = "重试请求失败",
) -> requests.Response:
    cli_context = get_cli_context(context)

    try:
        response = request(ensure_domain_cookies(spec))
    except requests.RequestException as e:
        raise RequestFailedError(f"{request_error_message}: {e}") from e

    if not is_login_timeout(response):
        return response

    debug_log(debug_message or f"检测到{spec.debug_label}会话过期，正在后台尝试静默刷新...", cli_context)
    cookies = refresh_domain_cookies_or_raise(spec)

    try:
        response = request(cookies)
    except requests.RequestException as e:
        raise RequestFailedError(f"{retry_error_message}: {e}") from e

    if is_login_timeout(response):
        raise AuthExpiredError(RETRY_REJECTED_MESSAGE)
    return response
