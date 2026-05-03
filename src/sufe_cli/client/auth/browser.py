import os
from pathlib import Path

from playwright.sync_api import sync_playwright

from sufe_cli.config import STATE_FILE_PATH

from ...config import AuthConfig, AuthMode, load_auth_config, require_auto_credentials
from .auto_login import LOGIN_DOMAIN, LOGIN_URL, attempt_login

PORTAL_URL = "https://portal.sufe.edu.cn/main.html"


class BrowserAuthError(RuntimeError):
    pass


def check_playwright() -> tuple[bool, str]:
    try:
        with sync_playwright() as p:
            executable_path = p.chromium.executable_path
            if os.path.exists(executable_path):
                return True, executable_path
            return False, f"找不到 Playwright Chromium 浏览器（预期路径：{executable_path}）"
    except Exception as e:
        return False, f"检查失败：{e}"


def authenticate_from_config(config: AuthConfig | None = None, state_path: Path = STATE_FILE_PATH) -> tuple[bool, str]:
    actual_config = load_auth_config() if config is None else config
    if actual_config.mode == AuthMode.AUTO:
        return authenticate_auto(actual_config, state_path=state_path)
    return authenticate_manual(state_path=state_path)


def authenticate_auto(config: AuthConfig, state_path: Path = STATE_FILE_PATH) -> tuple[bool, str]:
    username, password = require_auto_credentials(config)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    return attempt_login(username, password, headless=True, storage_state_path=str(state_path))


def authenticate_manual(state_path: Path = STATE_FILE_PATH) -> tuple[bool, str]:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto(LOGIN_URL)
            try:
                page.wait_for_url("**/portal.sufe.edu.cn/main.html*", timeout=300000)
                page.wait_for_load_state("networkidle")
            except Exception:
                return False, "等待登录完成超时或出现错误，请重试"
            context.storage_state(path=str(state_path))
            return True, page.url
        finally:
            browser.close()


def recover_portal_state(state_path: Path = STATE_FILE_PATH) -> bool:
    config = load_auth_config()
    if config.mode != AuthMode.AUTO:
        return False
    try:
        ok, _ = authenticate_auto(config, state_path=state_path)
    except ValueError:
        return False
    return ok


def refresh_domain_state(url: str, state_path: Path = STATE_FILE_PATH) -> bool:
    if not state_path.exists():
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(state_path))
        page = context.new_page()
        try:
            page.goto(url)
            page.wait_for_load_state("networkidle")
            if LOGIN_DOMAIN in page.url:
                return False
            context.storage_state(path=str(state_path))
            return True
        except Exception:
            return False
        finally:
            browser.close()


def ensure_portal_state(state_path: Path = STATE_FILE_PATH) -> bool:
    if refresh_domain_state(PORTAL_URL, state_path=state_path):
        return True
    return recover_portal_state(state_path=state_path)


def fetch_page_with_state(url: str, state_path: Path = STATE_FILE_PATH) -> str:
    if not ensure_portal_state(state_path=state_path):
        msg = "认证配置缺失或登录状态已过期，请先运行 `sufe auth` 完成配置"
        raise BrowserAuthError(msg)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(state_path))
        page = context.new_page()
        try:
            page.goto(url)
            page.wait_for_load_state("networkidle")
            if LOGIN_DOMAIN in page.url:
                if not recover_portal_state(state_path=state_path):
                    msg = "认证配置缺失或登录状态已过期，请先运行 `sufe auth` 完成配置"
                    raise BrowserAuthError(msg)
                context = browser.new_context(storage_state=str(state_path))
                page = context.new_page()
                page.goto(url)
                page.wait_for_load_state("networkidle")
                if LOGIN_DOMAIN in page.url:
                    msg = "认证配置缺失或登录状态已过期，请先运行 `sufe auth` 完成配置"
                    raise BrowserAuthError(msg)
            context.storage_state(path=str(state_path))
            return page.content()
        finally:
            browser.close()
