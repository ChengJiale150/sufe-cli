from typing import Any

import pytest
from typer.testing import CliRunner

from sufe_cli.cli import app
from sufe_cli.config import AuthConfig, AuthMode

runner = CliRunner()


def _setup_auth_mocks(
    monkeypatch: pytest.MonkeyPatch,
    *,
    auth_config_exists: bool = False,
    authenticate_ok: bool = True,
) -> None:
    """统一设置 auth 命令所需的 mock"""

    def mock_auth_config_exists(path: Any = None) -> bool:
        return auth_config_exists

    monkeypatch.setattr("sufe_cli.cli.auth_config_exists", mock_auth_config_exists)

    def mock_authenticate_from_config(config: AuthConfig, state_path: Any = None) -> tuple[bool, str]:
        if authenticate_ok:
            return True, "https://portal.sufe.edu.cn/main.html"
        return False, "模拟认证失败"

    monkeypatch.setattr("sufe_cli.cli.authenticate_from_config", mock_authenticate_from_config)


# ---------------------------------------------------------------------------
# 首次配置（auth.json 不存在）
# ---------------------------------------------------------------------------


def test_auth_first_time_manual_mode(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """首次使用，选择 manual 模式"""
    _setup_auth_mocks(monkeypatch, auth_config_exists=False)

    saved_config = None

    def mock_save_auth_config(config: AuthConfig, path=None) -> None:
        nonlocal saved_config
        saved_config = config

    monkeypatch.setattr("sufe_cli.cli.save_auth_config", mock_save_auth_config)

    result = runner.invoke(app, ["auth"], input="manual\n")
    assert result.exit_code == 0
    assert "未检测到 auth.json，首次使用需要配置登录方式：" in result.output
    assert "配置已保存。" in result.output
    assert "登录状态已保存到 state.json" in result.output
    assert saved_config is not None
    assert saved_config.mode == AuthMode.MANUAL


def test_auth_first_time_auto_mode(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """首次使用，选择 auto 模式并输入账号密码"""
    _setup_auth_mocks(monkeypatch, auth_config_exists=False)

    result = runner.invoke(app, ["auth"], input="auto\n20230001\npassword123\n")
    assert result.exit_code == 0
    assert "未检测到 auth.json，首次使用需要配置登录方式：" in result.output
    assert "配置已保存。" in result.output
    assert "正在使用 auth.json 中的账号密码自动登录..." in result.output
    assert "登录状态已保存到 state.json" in result.output


def test_auth_first_time_invalid_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """首次使用，输入无效模式"""
    _setup_auth_mocks(monkeypatch, auth_config_exists=False)

    result = runner.invoke(app, ["auth"], input="invalid\n")
    assert result.exit_code == 1
    assert "无效的模式：invalid，请输入 manual 或 auto" in result.output


# ---------------------------------------------------------------------------
# 已有配置（auth.json 存在）
# ---------------------------------------------------------------------------


def test_auth_existing_config_skip_interactive(monkeypatch: pytest.MonkeyPatch) -> None:
    """已有配置，直接登录，跳过交互"""
    _setup_auth_mocks(monkeypatch, auth_config_exists=True)

    result = runner.invoke(app, ["auth"])
    assert result.exit_code == 0
    assert "未检测到 auth.json" not in result.output
    assert "登录状态已保存到 state.json" in result.output


# ---------------------------------------------------------------------------
# 强制交互模式（--interactive）
# ---------------------------------------------------------------------------


def test_auth_interactive_force_reconfig(monkeypatch: pytest.MonkeyPatch) -> None:
    """使用 --interactive 强制重新配置为 auto 模式"""
    _setup_auth_mocks(monkeypatch, auth_config_exists=True)

    result = runner.invoke(app, ["auth", "--interactive"], input="auto\n20230001\npassword123\n")
    assert result.exit_code == 0
    assert "进入交互配置模式：" in result.output
    assert "配置已保存。" in result.output


def test_auth_interactive_switch_to_manual(monkeypatch: pytest.MonkeyPatch) -> None:
    """使用 --interactive 强制重新配置为 manual 模式"""
    _setup_auth_mocks(monkeypatch, auth_config_exists=True)

    result = runner.invoke(app, ["auth", "--interactive"], input="manual\n")
    assert result.exit_code == 0
    assert "进入交互配置模式：" in result.output
    assert "配置已保存。" in result.output


# ---------------------------------------------------------------------------
# 认证失败
# ---------------------------------------------------------------------------


def test_auth_authenticate_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """认证过程失败"""
    _setup_auth_mocks(monkeypatch, auth_config_exists=True, authenticate_ok=False)

    result = runner.invoke(app, ["auth"])
    assert result.exit_code == 1
    assert "认证失败：模拟认证失败" in result.output
