import os

from playwright.sync_api import sync_playwright


def check_playwright() -> tuple[bool, str]:
    """检查 Playwright Chromium 是否已安装。返回 (是否成功, 可执行文件路径或错误信息)。"""
    try:
        with sync_playwright() as p:
            executable_path = p.chromium.executable_path
            if os.path.exists(executable_path):
                return True, executable_path
            return False, f"找不到 Playwright Chromium 浏览器（预期路径：{executable_path}）"
    except Exception as e:
        return False, f"检查失败：{e}"
