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

    monkeypatch.setattr("sufe_cli.commands.auth.auth_config_exists", mock_auth_config_exists)

    def mock_load_auth_config(path: Any = None) -> AuthConfig:
        return AuthConfig(mode=AuthMode.AUTO, username="20230001", password="oldpass")

    monkeypatch.setattr("sufe_cli.commands.auth.load_auth_config", mock_load_auth_config)

    def mock_authenticate_from_config(config: AuthConfig, state_path: Any = None) -> tuple[bool, str]:
        if authenticate_ok:
            return True, "https://portal.sufe.edu.cn/main.html"
        return False, "模拟认证失败"

    monkeypatch.setattr(
        "sufe_cli.commands.auth.authenticate_from_config",
        mock_authenticate_from_config,
    )

    class MockProfile:
        user_id = "20230001"
        user_name = "测试用户"
        organization_name = "测试学院"

    def mock_ensure_user_profile(timeout: int = 30) -> MockProfile:
        return MockProfile()

    monkeypatch.setattr("sufe_cli.cli.ensure_user_profile", mock_ensure_user_profile)


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

    monkeypatch.setattr("sufe_cli.commands.auth.save_auth_config", mock_save_auth_config)

    # 输入: 1(manual) -> Y(确认)
    result = runner.invoke(app, ["auth"], input="1\nY\n")
    assert result.exit_code == 0
    assert "欢迎首次使用 Sufe CLI" in result.output
    assert "配置已保存。" in result.output
    assert "登录状态已保存到" in result.output
    assert "登录成功！运行 `sufe me`" in result.output
    assert saved_config is not None
    assert saved_config.mode == AuthMode.MANUAL


def test_auth_first_time_auto_mode(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """首次使用，选择 auto 模式并输入账号密码"""
    _setup_auth_mocks(monkeypatch, auth_config_exists=False)

    saved_config = None

    def mock_save_auth_config(config: AuthConfig, path=None) -> None:
        nonlocal saved_config
        saved_config = config

    monkeypatch.setattr("sufe_cli.commands.auth.save_auth_config", mock_save_auth_config)

    # 输入: 2(auto) -> 学号 -> 密码 -> 确认密码 -> Y(确认)
    result = runner.invoke(app, ["auth"], input="2\n20230001\npassword123\npassword123\nY\n")
    assert result.exit_code == 0
    assert "欢迎首次使用 Sufe CLI" in result.output
    assert "配置已保存。" in result.output
    assert "正在使用自动登录..." in result.output
    assert "登录状态已保存到" in result.output
    assert "登录成功！运行 `sufe me`" in result.output
    assert saved_config is not None
    assert saved_config.mode == AuthMode.AUTO
    assert saved_config.username == "20230001"
    assert saved_config.password == "password123"


def test_auth_first_time_password_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """首次使用，auto 模式密码两次输入不一致"""
    _setup_auth_mocks(monkeypatch, auth_config_exists=False)

    # 输入: 2(auto) -> 学号 -> 密码1 -> 密码2(不一致) -> 密码3 -> 密码4(不一致) -> 密码5 -> 密码6(不一致)
    result = runner.invoke(
        app,
        ["auth"],
        input="2\n20230001\npass1\npass2\npass3\npass4\npass5\npass6\n",
    )
    assert result.exit_code == 1
    assert "密码输入错误次数过多" in result.output


def test_auth_first_time_cancel_save(monkeypatch: pytest.MonkeyPatch) -> None:
    """首次使用，预览配置后取消保存"""
    _setup_auth_mocks(monkeypatch, auth_config_exists=False)

    # 输入: 1(manual) -> n(取消)
    result = runner.invoke(app, ["auth"], input="1\nn\n")
    assert result.exit_code == 0
    assert "已取消配置保存。" in result.output


# ---------------------------------------------------------------------------
# 已有配置（auth.json 存在）
# ---------------------------------------------------------------------------


def test_auth_existing_config_skip_reconfig(monkeypatch: pytest.MonkeyPatch) -> None:
    """已有配置，不修改直接登录"""
    _setup_auth_mocks(monkeypatch, auth_config_exists=True)

    # 直接回车（默认不修改）
    result = runner.invoke(app, ["auth"], input="\n")
    assert result.exit_code == 0
    assert "Sufe CLI 认证模块" in result.output
    assert "检测到已有认证配置" in result.output
    assert "是否修改当前配置？" in result.output
    assert "登录状态已保存到" in result.output
    assert "登录成功！运行 `sufe me`" in result.output


def test_auth_existing_config_reconfig_manual(monkeypatch: pytest.MonkeyPatch) -> None:
    """已有配置，选择修改并切换为 manual 模式"""
    _setup_auth_mocks(monkeypatch, auth_config_exists=True)

    saved_config = None

    def mock_save_auth_config(config: AuthConfig, path=None) -> None:
        nonlocal saved_config
        saved_config = config

    monkeypatch.setattr("sufe_cli.commands.auth.save_auth_config", mock_save_auth_config)

    # 输入: y(修改) -> 1(manual) -> Y(确认)
    result = runner.invoke(app, ["auth"], input="y\n1\nY\n")
    assert result.exit_code == 0
    assert "配置已保存。" in result.output
    assert saved_config is not None
    assert saved_config.mode == AuthMode.MANUAL


# ---------------------------------------------------------------------------
# 认证失败
# ---------------------------------------------------------------------------


def test_auth_authenticate_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """认证过程失败"""
    _setup_auth_mocks(monkeypatch, auth_config_exists=True, authenticate_ok=False)

    result = runner.invoke(app, ["auth"], input="\n")
    assert result.exit_code == 1
    assert "认证失败：模拟认证失败" in result.output
