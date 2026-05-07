import click
import typer

from sufe_cli.client.auth.browser import authenticate_from_config
from sufe_cli.config import (
    APP_DIR,
    AUTH_FILE_PATH,
    AuthConfig,
    AuthMode,
    auth_config_exists,
    load_auth_config,
    save_auth_config,
)
from sufe_cli.errors import AuthConfigMissingError


def _print_welcome_banner() -> None:
    """首次使用的欢迎横幅。"""
    typer.echo("")
    typer.echo("╔══════════════════════════════════════════════════╗")
    typer.echo("║               欢迎首次使用 Sufe CLI                ║")
    typer.echo("╚══════════════════════════════════════════════════╝")
    typer.echo("")


def _print_auth_banner() -> None:
    """通用认证横幅。"""
    typer.echo("")
    typer.echo("╔══════════════════════════════════════════════════╗")
    typer.echo("║                Sufe CLI 认证模块                  ║")
    typer.echo("╚══════════════════════════════════════════════════╝")
    typer.echo("")


def _format_config_preview(config: AuthConfig) -> str:
    """生成配置预览文本（密码脱敏）。"""
    mode_str = config.mode if isinstance(config.mode, str) else config.mode.value
    lines = [f"  登录模式: {mode_str}"]
    if config.username:
        lines.append(f"  学号: {config.username}")
    if config.password:
        masked = "*" * len(config.password)
        lines.append(f"  密码: {masked}")
    return "\n".join(lines)


def _configure_auth(is_first_time: bool) -> AuthConfig:
    """交互式认证配置流程，返回配置对象。"""
    typer.echo("步骤 1/3: 选择登录模式")
    typer.echo("")
    typer.echo("请选择登录方式：")
    typer.echo("")
    typer.echo("  [1] manual  - 打开浏览器窗口手动完成登录")
    typer.echo("  [2] auto    - 使用学号密码自动登录")
    typer.echo("")

    mode_choice = typer.prompt(
        "登录模式 [1/2]",
        default="1",
        type=click.Choice(["1", "2"], case_sensitive=False),
    )
    selected_mode = AuthMode.AUTO if mode_choice == "2" else AuthMode.MANUAL

    typer.echo("")
    typer.echo("步骤 2/3: 配置账号信息")
    typer.echo("")

    username: str | None = None
    password: str | None = None

    if selected_mode == AuthMode.AUTO:
        username = typer.prompt("学号", type=str)

        max_attempts = 3
        for attempt in range(max_attempts):
            password = typer.prompt("密码", type=str, hide_input=True)
            password_confirm = typer.prompt("确认密码", type=str, hide_input=True)
            if password == password_confirm:
                break
            remaining = max_attempts - attempt - 1
            if remaining > 0:
                typer.secho(
                    f"两次输入的密码不一致，还有 {remaining} 次机会，请重新输入。",
                    fg=typer.colors.YELLOW,
                )
            else:
                typer.secho(
                    "密码输入错误次数过多，请重新运行命令。",
                    fg=typer.colors.RED,
                    err=True,
                )
                raise typer.Exit(1)

        if is_first_time:
            typer.echo("")
            typer.secho(
                f"注意：账号密码将保存在 {AUTH_FILE_PATH}",
                fg=typer.colors.YELLOW,
            )

    typer.echo("")
    typer.echo("配置预览：")
    preview_config = AuthConfig(
        mode=selected_mode,
        username=username,
        password=password,
    )
    typer.echo(_format_config_preview(preview_config))
    typer.echo("")

    if not typer.confirm("确认保存？", default=True):
        typer.secho("已取消配置保存。", fg=typer.colors.YELLOW)
        raise typer.Exit(0)

    config = AuthConfig(mode=selected_mode, username=username, password=password)
    save_auth_config(config)
    typer.secho("配置已保存。", fg=typer.colors.GREEN)

    return config


def auth_command() -> None:
    """配置认证信息并完成登录。"""
    config_exists = auth_config_exists()

    if config_exists:
        _print_auth_banner()
        config = load_auth_config()
        typer.echo("检测到已有认证配置：")
        typer.echo(_format_config_preview(config))
        typer.echo("")

        if typer.confirm("是否修改当前配置？", default=False):
            config = _configure_auth(is_first_time=False)
    else:
        _print_welcome_banner()
        typer.echo("未检测到认证配置，需要进行初始化设置。")
        typer.echo("")
        config = _configure_auth(is_first_time=True)

    typer.echo("")
    typer.echo("步骤 3/3: 完成登录")
    typer.echo("")

    if config.mode == AuthMode.AUTO:
        typer.echo("正在使用自动登录...")
    else:
        typer.echo("即将打开浏览器，请在弹出的窗口中完成登录...")

    try:
        ok, info = authenticate_from_config(config)
    except AuthConfigMissingError as e:
        typer.secho(str(e), fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from None

    if not ok:
        typer.secho(f"认证失败：{info}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    typer.secho(f"登录状态已保存到 {APP_DIR / 'state.json'}", fg=typer.colors.GREEN)

    typer.echo("")
    typer.secho("登录成功！运行 `sufe me` 查看当前用户信息。", fg=typer.colors.GREEN)
