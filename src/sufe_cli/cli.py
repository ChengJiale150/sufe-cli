import subprocess
import sys

import typer

from . import __version__
from .client.auth_config import AuthMode, load_auth_config
from .client.browser import authenticate_from_config, check_playwright, ensure_portal_state
from .client.portal import fetch_user_profile
from .client.state import load_portal_token
from .commands import config_app, lclibrary_app, score_app
from .config import STATE_FILE_PATH

app = typer.Typer(help="Sufe CLI - 与上海财经大学网页系统交互的命令行工具")

app.add_typer(config_app, name="config")
app.add_typer(lclibrary_app, name="lclibrary")
app.add_typer(score_app, name="score")


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"sufe-cli version: {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True, help="显示版本信息"
    ),
) -> None:
    """Sufe CLI"""


@app.command()
def doctor() -> None:
    """检查运行环境：浏览器与门户登录状态"""
    has_error = False

    typer.echo("正在检查 Playwright 环境...")
    ok, msg = check_playwright()
    if ok:
        typer.secho(f"Playwright Chromium 浏览器已安装（{msg}）", fg=typer.colors.GREEN)
    else:
        typer.secho(msg, fg=typer.colors.RED)
        typer.secho("请运行 `sufe install` 进行安装。", fg=typer.colors.YELLOW)
        has_error = True

    typer.echo("正在检查门户登录状态...")
    if not STATE_FILE_PATH.exists():
        typer.secho("未找到登录状态文件 state.json", fg=typer.colors.RED)
        typer.secho("请运行 `sufe auth` 完成登录。", fg=typer.colors.YELLOW)
        has_error = True
    elif load_portal_token() is None:
        typer.secho("state.json 中未找到门户 token", fg=typer.colors.RED)
        typer.secho("请运行 `sufe auth` 重新登录。", fg=typer.colors.YELLOW)
        has_error = True
    else:
        profile = None
        try:
            profile = fetch_user_profile()
        except Exception as e:
            typer.secho(f"门户状态检查失败：{e}", fg=typer.colors.RED)
            has_error = True
        if profile is not None and profile.user_id:
            typer.secho(f"门户登录状态有效：{profile.user_name} ({profile.user_id})", fg=typer.colors.GREEN)
        elif not has_error:
            typer.secho("门户登录状态无效，请运行 `sufe auth` 重新登录。", fg=typer.colors.RED)
            has_error = True

    if has_error:
        raise typer.Exit(1)


@app.command()
def install(
    force: bool = typer.Option(False, "--force", help="强制重新安装浏览器"),
) -> None:
    """安装所需的 Playwright 浏览器（Chromium）"""
    if not force:
        ok, msg = check_playwright()
        if ok:
            typer.secho(f"Playwright Chromium 浏览器已安装（{msg}），如需重装请使用 --force", fg=typer.colors.GREEN)
            return

    typer.echo("正在安装 Playwright Chromium 浏览器，这可能需要一些时间...")
    try:
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        typer.secho("浏览器安装完成！", fg=typer.colors.GREEN)
    except subprocess.CalledProcessError as e:
        typer.secho(f"安装失败：{e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)


@app.command()
def auth() -> None:
    """根据 auth.json 配置完成登录并保存门户状态"""
    config = load_auth_config()
    if config.mode == AuthMode.AUTO:
        typer.echo("正在使用 auth.json 中的账号密码自动登录...")
    else:
        typer.echo("即将打开浏览器，请在弹出的窗口中完成登录...")

    try:
        ok, info = authenticate_from_config(config)
    except ValueError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    if not ok:
        typer.secho(f"认证失败：{info}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    typer.secho("登录状态已保存到 state.json", fg=typer.colors.GREEN)


@app.command()
def me() -> None:
    """显示当前登录用户的基本信息"""
    try:
        profile = fetch_user_profile()
    except Exception:
        profile = None

    if profile is None or not profile.user_id:
        if ensure_portal_state():
            try:
                profile = fetch_user_profile()
            except Exception:
                profile = None

    if profile is None or not profile.user_id:
        typer.secho(
            "未获取到用户信息，请先运行 `sufe auth` 完成登录。",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    typer.echo(f"学号: {profile.user_id}")
    typer.echo(f"姓名: {profile.user_name}")
    typer.echo(f"学院: {profile.organization_name}")
