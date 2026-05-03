import subprocess
import sys
from typing import Annotated

import typer

from . import __version__
from .client.auth.browser import check_playwright, ensure_portal_state
from .client.portal import ensure_user_profile
from .commands import canvas_app, lclibrary_app, score_app
from .commands.auth import auth_command
from .config import auth_config_exists
from .errors import AuthExpiredError
from .runtime import CliContext, set_cli_context

DebugOption = Annotated[bool, typer.Option("--debug/--no-debug", help="显示调试诊断信息")]
TimeoutOption = Annotated[int, typer.Option("--timeout", min=1, help="请求超时时间（秒）")]
ForceOption = Annotated[bool, typer.Option("--force", help="强制重新安装浏览器")]

app = typer.Typer(help="Sufe CLI - 与上海财经大学网页系统交互的命令行工具")

app.add_typer(canvas_app, name="canvas")
app.add_typer(lclibrary_app, name="lclibrary")
app.add_typer(score_app, name="score")


@app.command()
def auth() -> None:
    """配置认证信息并完成登录"""
    auth_command()


@app.command()
def me() -> None:
    """显示当前登录用户的基本信息"""
    try:
        profile = ensure_user_profile()
    except AuthExpiredError:
        typer.secho(
            "未获取到用户信息，请先运行 `sufe auth` 完成登录。",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1) from None

    typer.echo(f"学号: {profile.user_id}")
    typer.echo(f"姓名: {profile.user_name}")
    typer.echo(f"学院: {profile.organization_name}")


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"sufe-cli version: {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[
        bool | None,
        typer.Option("--version", "-v", callback=version_callback, is_eager=True, help="显示版本信息"),
    ] = None,
    timeout: TimeoutOption = 30,
    debug: DebugOption = False,
) -> None:
    """Sufe CLI"""
    cli_context = CliContext(timeout=timeout, debug=debug)
    ctx.obj = cli_context
    set_cli_context(cli_context)


@app.command()
def doctor() -> None:
    """检查运行环境：浏览器、认证配置与门户登录状态"""
    has_error = False

    typer.echo("正在检查 Playwright 环境...")
    ok, msg = check_playwright()
    if ok:
        typer.secho(f"Playwright Chromium 浏览器已安装（{msg}）", fg=typer.colors.GREEN)
    else:
        typer.secho(msg, fg=typer.colors.RED)
        typer.secho("请运行 `sufe install` 进行安装。", fg=typer.colors.YELLOW)
        has_error = True

    typer.echo("正在检查认证配置...")
    if auth_config_exists():
        typer.secho("认证配置文件 auth.json 已存在", fg=typer.colors.GREEN)
    else:
        typer.secho("认证配置文件 auth.json 不存在", fg=typer.colors.RED)
        typer.secho("请运行 `sufe auth` 进行配置。", fg=typer.colors.YELLOW)
        has_error = True

    typer.echo("正在检查门户登录状态...")
    if ensure_portal_state():
        typer.secho("门户登录状态有效", fg=typer.colors.GREEN)
    else:
        typer.secho("门户登录状态无效", fg=typer.colors.RED)
        typer.secho("请运行 `sufe auth` 重新登录。", fg=typer.colors.YELLOW)
        has_error = True

    if has_error:
        raise typer.Exit(1)


@app.command()
def install(
    force: ForceOption = False,
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
