import json
from typing import Annotated

import typer

from sufe_cli.config import AuthConfig, AuthMode, load_auth_config, save_auth_config

app = typer.Typer(help="SUFE CLI 配置命令")


@app.command(name="set")
def set_config(
    mode: Annotated[AuthMode, typer.Option("--mode", help="登录模式：manual 或 auto")],
    username: Annotated[str | None, typer.Option("--username", "-u", help="自动登录学号")] = None,
    password: Annotated[str | None, typer.Option("--password", "-p", help="自动登录密码")] = None,
) -> None:
    """设置登录模式与自动登录账号密码。"""
    if mode == AuthMode.MANUAL:
        save_auth_config(AuthConfig(mode=AuthMode.MANUAL))
        typer.secho("已设置为手动登录模式", fg=typer.colors.GREEN)
        return

    actual_username = username or typer.prompt("学号")
    actual_password = password or typer.prompt("密码")
    save_auth_config(AuthConfig(mode=AuthMode.AUTO, username=actual_username, password=actual_password))
    typer.secho("已设置为自动登录模式", fg=typer.colors.GREEN)


@app.command(name="show")
def show_config() -> None:
    """显示当前登录配置。"""
    config = load_auth_config()
    typer.echo(json.dumps(config.model_dump(exclude_none=True), ensure_ascii=False, indent=2))
