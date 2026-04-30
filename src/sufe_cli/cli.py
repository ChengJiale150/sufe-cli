import os
import sys
import subprocess
import typer
from typing import Optional
from playwright.sync_api import sync_playwright

from . import __version__
from .config import SufeCookies, save_cookies, STATE_FILE_PATH
from .commands.lclibrary import app as lclibrary_app

app = typer.Typer(help="Sufe CLI - 与上海财经大学网页系统交互的命令行工具")

app.add_typer(lclibrary_app, name="lclibrary")


def version_callback(value: bool):
    if value:
        typer.echo(f"sufe-cli version: {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True, help="显示版本信息"
    ),
):
    """
    Sufe CLI
    """
    pass


@app.command()
def doctor():
    """检查 Playwright 浏览器（Chromium）是否已安装"""
    typer.echo("正在检查 Playwright 环境...")
    try:
        with sync_playwright() as p:
            executable_path = p.chromium.executable_path
            if os.path.exists(executable_path):
                typer.secho("✅ Playwright Chromium 浏览器已安装，环境正常。", fg=typer.colors.GREEN)
            else:
                typer.secho(
                    f"❌ 找不到 Playwright Chromium 浏览器（预期路径：{executable_path}）。", fg=typer.colors.RED
                )
                typer.secho("请运行 `sufe install` 进行安装。", fg=typer.colors.YELLOW)
    except Exception as e:
        typer.secho(f"检查失败：{e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command()
def install():
    """安装所需的 Playwright 浏览器（Chromium）"""
    typer.echo("正在安装 Playwright Chromium 浏览器，这可能需要一些时间...")
    try:
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        typer.secho("✅ 浏览器安装完成！", fg=typer.colors.GREEN)
    except subprocess.CalledProcessError as e:
        typer.secho(f"❌ 安装失败：{e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command()
def auth():
    """引导用户登录，获取授权 Cookie 并保存"""
    typer.echo("即将打开浏览器，请在弹出的窗口中完成登录...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            # 1. 引导登录
            page.goto("https://login.sufe.edu.cn/login/")
            typer.secho("请在浏览器中登录您的账户，最长等待时间为 5 分钟...", fg=typer.colors.CYAN)

            # 2. 等待跳转至 portal
            try:
                page.wait_for_url("**/portal.sufe.edu.cn/main.html*", timeout=300000)
                typer.secho("登录成功，正在获取授权...", fg=typer.colors.GREEN)
            except Exception:
                typer.secho("等待登录完成超时或出现错误，请重试。", fg=typer.colors.RED, err=True)
                raise typer.Exit(1)

            # 3. 跳转到目标获取 Cookie 的地址
            page.goto("https://lclibrary.sufe.edu.cn/ClientWeb/xcus/ic2/Default.aspx")
            page.wait_for_load_state("networkidle")

            # 4. 提取 Cookie
            cookies = context.cookies()
            target_cookies = {}
            for cookie in cookies:
                if cookie["name"] in ["ASP.NET_SessionId", "SF_cookie_154"]:
                    target_cookies[cookie["name"]] = cookie["value"]

            if "ASP.NET_SessionId" not in target_cookies or "SF_cookie_154" not in target_cookies:
                typer.secho("未能获取到完整的授权 Cookie（可能登录状态异常），请重试。", fg=typer.colors.RED, err=True)
                raise typer.Exit(1)

            # 5. 校验并保存
            from .config import LclibraryCookies

            lclibrary_cookies = LclibraryCookies(**target_cookies)
            cookie_model = SufeCookies(lclibrary=lclibrary_cookies)
            save_cookies(cookie_model)

            # 6. 保存完整的 Context State (包含 CAS Cookie)
            STATE_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            context.storage_state(path=str(STATE_FILE_PATH))

            typer.secho("✅ Cookie 获取并保存成功！", fg=typer.colors.GREEN)

            browser.close()
    except Exception as e:
        typer.secho(f"认证过程中出现错误: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
