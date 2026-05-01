import subprocess
import sys

import requests
import typer
from playwright.sync_api import sync_playwright

from . import __version__
from .config import (
    SufeCookies,
    UserProfile,
    load_cookies,
    load_user_profile,
    save_cookies,
    save_user_profile,
    STATE_FILE_PATH,
)
from .commands.lclibrary import app as lclibrary_app
from .commands.score import app as score_app
from .utils.env import check_playwright
from .utils.network import check_cookie_valid
from .utils.token import load_portal_token

app = typer.Typer(help="Sufe CLI - 与上海财经大学网页系统交互的命令行工具")

app.add_typer(lclibrary_app, name="lclibrary")
app.add_typer(score_app, name="score")


def version_callback(value: bool):
    if value:
        typer.echo(f"sufe-cli version: {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True, help="显示版本信息"
    ),
):
    """
    Sufe CLI
    """
    pass


@app.command()
def doctor():
    """检查运行环境：浏览器、Cookie 配置及有效性"""
    has_error = False

    # 1. Playwright 浏览器检查
    typer.echo("正在检查 Playwright 环境...")
    ok, msg = check_playwright()
    if ok:
        typer.secho(f"✅ Playwright Chromium 浏览器已安装（{msg}）", fg=typer.colors.GREEN)
    else:
        typer.secho(f"❌ {msg}", fg=typer.colors.RED)
        typer.secho("请运行 `sufe install` 进行安装。", fg=typer.colors.YELLOW)
        has_error = True

    # 2. Cookie 配置存在性检查
    typer.echo("正在检查 Cookie 配置...")
    cookies = load_cookies()
    if cookies:
        typer.secho("✅ Cookie 配置文件存在", fg=typer.colors.GREEN)
    else:
        typer.secho("❌ Cookie 配置文件不存在或已损坏", fg=typer.colors.RED)
        typer.secho("请运行 `sufe auth` 完成登录并保存 Cookie。", fg=typer.colors.YELLOW)
        has_error = True

    # 3. Cookie 有效性检查
    if cookies:
        typer.echo("正在检查 Cookie 有效性...")
        valid, info = check_cookie_valid()
        if valid:
            typer.secho(f"✅ {info}", fg=typer.colors.GREEN)
        else:
            typer.secho(f"❌ {info}", fg=typer.colors.RED)
            typer.secho("请运行 `sufe auth` 重新登录。", fg=typer.colors.YELLOW)
            has_error = True

    if has_error:
        raise typer.Exit(1)


@app.command()
def install(
    force: bool = typer.Option(False, "--force", help="强制重新安装浏览器"),
):
    """安装所需的 Playwright 浏览器（Chromium）"""
    if not force:
        ok, msg = check_playwright()
        if ok:
            typer.secho(f"✅ Playwright Chromium 浏览器已安装（{msg}），如需重装请使用 --force", fg=typer.colors.GREEN)
            return

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

            # 2. 等待跳转至 portal 并确保页面完全加载
            try:
                page.wait_for_url("**/portal.sufe.edu.cn/main.html*", timeout=300000)
                page.wait_for_load_state("networkidle")
                typer.secho("登录成功，正在获取授权...", fg=typer.colors.GREEN)
            except Exception:
                typer.secho("等待登录完成超时或出现错误，请重试。", fg=typer.colors.RED, err=True)
                raise typer.Exit(1)

            # 3. 跳转到目标获取 Cookie 的地址
            page.goto("https://lclibrary.sufe.edu.cn/ClientWeb/xcus/ic2/Default.aspx")
            page.wait_for_load_state("networkidle")

            # 5. 提取 Cookie
            cookies = context.cookies()
            target_cookies = {}
            for cookie in cookies:
                if cookie["name"] in ["ASP.NET_SessionId", "SF_cookie_154"]:
                    target_cookies[cookie["name"]] = cookie["value"]

            if "ASP.NET_SessionId" not in target_cookies or "SF_cookie_154" not in target_cookies:
                typer.secho("未能获取到完整的授权 Cookie（可能登录状态异常），请重试。", fg=typer.colors.RED, err=True)
                raise typer.Exit(1)

            # 6. 校验并保存
            from .config import LclibraryCookies

            lclibrary_cookies = LclibraryCookies(**target_cookies)
            cookie_model = SufeCookies(lclibrary=lclibrary_cookies)
            save_cookies(cookie_model)

            # 7. 保存完整的 Context State (包含 CAS Cookie)
            STATE_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            context.storage_state(path=str(STATE_FILE_PATH))

            # 8. 从已保存的 state 中提取 token 并获取用户信息
            token_value = load_portal_token()
            if token_value:
                try:
                    resp = requests.get(
                        "https://authx-service.sufe.edu.cn/personal/api/v1/personal/me/user",
                        headers={
                            "User-Agent": (
                                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
                            ),
                            "Accept": "application/json",
                            "x-id-token": token_value,
                        },
                        timeout=30,
                    )
                    if resp.status_code == 200:
                        payload = resp.json()
                        data = payload.get("data", {})
                        attrs = data.get("attributes", {})
                        profile = UserProfile(
                            user_id=attrs.get("userUid", ""),
                            user_name=attrs.get("userName", ""),
                            organization_name=attrs.get("organizationName", ""),
                        )
                        save_user_profile(profile)
                        typer.secho("✅ 用户信息已保存", fg=typer.colors.GREEN)
                except Exception:
                    typer.secho("⚠️ 获取用户信息失败，仅保存 Cookie", fg=typer.colors.YELLOW)
            else:
                typer.secho("⚠️ 未提取到 token，跳过用户信息获取", fg=typer.colors.YELLOW)

            typer.secho("✅ Cookie 获取并保存成功！", fg=typer.colors.GREEN)

            browser.close()
    except Exception as e:
        typer.secho(f"认证过程中出现错误: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command()
def me():
    """显示当前登录用户的基本信息"""
    profile = load_user_profile()
    if profile is None or not profile.user_id:
        typer.secho(
            "未找到用户信息，请先运行 `sufe auth` 完成登录。",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    typer.echo(f"学号: {profile.user_id}")
    typer.echo(f"姓名: {profile.user_name}")
    typer.echo(f"学院: {profile.organization_name}")
