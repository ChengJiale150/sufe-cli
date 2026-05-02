import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from sufe_cli.cli import app
from sufe_cli.config import AuthConfig, AuthMode

runner = CliRunner()


class DummyProfile:
    def __init__(self, user_id: str = "20230001", user_name: str = "张三", organization_name: str = "经济学院") -> None:
        self.user_id = user_id
        self.user_name = user_name
        self.organization_name = organization_name


def _setup_mocks(
    monkeypatch: pytest.MonkeyPatch,
    playwright_ok: bool = True,
    state_exists: bool = False,
    token_valid: bool = False,
    profile: DummyProfile | None = None,
    auth_mode: AuthMode = AuthMode.MANUAL,
    auth_ok: bool = False,
    auth_error: str | None = None,
) -> None:
    """统一设置 doctor 命令所需的 mock"""

    def mock_check_playwright() -> tuple[bool, str]:
        if playwright_ok:
            return True, "/path/to/chromium"
        return False, "Playwright Chromium 浏览器未安装"

    monkeypatch.setattr("sufe_cli.cli.check_playwright", mock_check_playwright)

    # mock STATE_FILE_PATH
    fake_state_path = Path("/tmp/fake_state.json")
    monkeypatch.setattr("sufe_cli.cli.STATE_FILE_PATH", fake_state_path)

    if state_exists:
        fake_state_path.write_text(
            json.dumps(
                {
                    "origins": [
                        {
                            "origin": "https://portal.sufe.edu.cn",
                            "localStorage": [
                                {
                                    "name": "vuex",
                                    "value": json.dumps({"user": {"token": "valid-token-123"}}),
                                }
                            ],
                        }
                    ],
                    "cookies": [],
                }
            ),
            encoding="utf-8",
        )
    elif fake_state_path.exists():
        fake_state_path.unlink()

    def mock_load_portal_token(path: Any = None) -> str | None:
        return "valid-token-123" if token_valid else None

    monkeypatch.setattr("sufe_cli.cli.load_portal_token", mock_load_portal_token)

    def mock_fetch_user_profile(timeout: int = 30) -> DummyProfile | None:
        return profile

    monkeypatch.setattr("sufe_cli.cli.fetch_user_profile", mock_fetch_user_profile)

    def mock_load_auth_config() -> AuthConfig:
        if auth_mode == AuthMode.AUTO:
            return AuthConfig(mode=AuthMode.AUTO, username="20230001", password="secret")
        return AuthConfig(mode=AuthMode.MANUAL)

    monkeypatch.setattr("sufe_cli.cli.load_auth_config", mock_load_auth_config)

    def mock_authenticate_from_config(config: AuthConfig, state_path: Any = None) -> tuple[bool, str]:
        if auth_ok:
            # 模拟成功登录后创建 state 文件
            fake_state_path.write_text(
                json.dumps(
                    {
                        "origins": [
                            {
                                "origin": "https://portal.sufe.edu.cn",
                                "localStorage": [
                                    {
                                        "name": "vuex",
                                        "value": json.dumps({"user": {"token": "valid-token-123"}}),
                                    }
                                ],
                            }
                        ],
                        "cookies": [],
                    }
                ),
                encoding="utf-8",
            )
            # 同时让后续 token 检查通过
            monkeypatch.setattr("sufe_cli.cli.load_portal_token", lambda path=None: "valid-token-123")
            return True, "https://portal.sufe.edu.cn/main.html"
        if auth_error:
            raise ValueError(auth_error)
        return False, "用户名或密码错误"

    monkeypatch.setattr("sufe_cli.cli.authenticate_from_config", mock_authenticate_from_config)


# ---------------------------------------------------------------------------
# 正常情况
# ---------------------------------------------------------------------------


def test_doctor_all_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    """所有检查通过"""
    _setup_mocks(
        monkeypatch,
        state_exists=True,
        token_valid=True,
        profile=DummyProfile(),
    )

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "Playwright Chromium 浏览器已安装" in result.output
    assert "门户登录状态有效：张三 (20230001)" in result.output


# ---------------------------------------------------------------------------
# 自动修复成功
# ---------------------------------------------------------------------------


def test_doctor_auto_fix_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """认证失效 + AUTO 模式 → 自动修复成功"""
    _setup_mocks(
        monkeypatch,
        state_exists=False,
        auth_mode=AuthMode.AUTO,
        auth_ok=True,
        profile=DummyProfile(),
    )

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "检测到自动登录模式，正在尝试自动修复认证状态..." in result.output
    assert "自动修复成功，认证状态已恢复" in result.output


# ---------------------------------------------------------------------------
# 自动修复失败
# ---------------------------------------------------------------------------


def test_doctor_auto_fix_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """认证失效 + AUTO 模式 → 自动修复失败"""
    _setup_mocks(
        monkeypatch,
        state_exists=False,
        auth_mode=AuthMode.AUTO,
        auth_ok=False,
    )

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "自动修复失败：用户名或密码错误" in result.output
    assert "请运行 `sufe auth` 重新登录。" in result.output


def test_doctor_auto_fix_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """认证失效 + AUTO 模式 → 自动修复抛出 ValueError"""
    _setup_mocks(
        monkeypatch,
        state_exists=False,
        auth_mode=AuthMode.AUTO,
        auth_error="自动登录配置缺少密码",
    )

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "自动修复失败：自动登录配置缺少密码" in result.output
    assert "请运行 `sufe auth` 重新登录。" in result.output


# ---------------------------------------------------------------------------
# 手动模式不自动修复
# ---------------------------------------------------------------------------


def test_doctor_manual_mode_no_auto_fix(monkeypatch: pytest.MonkeyPatch) -> None:
    """认证失效 + MANUAL 模式 → 不自动修复，提示用户"""
    _setup_mocks(
        monkeypatch,
        state_exists=False,
        auth_mode=AuthMode.MANUAL,
    )

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "未找到登录状态文件 state.json" in result.output
    assert "请运行 `sufe auth` 完成登录。" in result.output
    assert "自动修复" not in result.output


# ---------------------------------------------------------------------------
# 非 retryable 错误
# ---------------------------------------------------------------------------


def test_doctor_non_retryable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """认证检查抛出异常（非 retryable）→ 不尝试自动修复"""

    def mock_fetch_user_profile_with_error(timeout: int = 30) -> None:
        raise RuntimeError("网络连接失败")

    _setup_mocks(
        monkeypatch,
        state_exists=True,
        token_valid=True,
        auth_mode=AuthMode.AUTO,
    )
    monkeypatch.setattr("sufe_cli.cli.fetch_user_profile", mock_fetch_user_profile_with_error)

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "门户状态检查失败：网络连接失败" in result.output
    assert "自动修复" not in result.output


# ---------------------------------------------------------------------------
# Playwright 缺失
# ---------------------------------------------------------------------------


def test_doctor_playwright_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """浏览器未安装 → 提示安装，同时检查认证状态"""
    _setup_mocks(
        monkeypatch,
        playwright_ok=False,
        state_exists=True,
        token_valid=True,
        profile=DummyProfile(),
    )

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "Playwright Chromium 浏览器未安装" in result.output
    assert "请运行 `sufe install` 进行安装" in result.output
    assert "门户登录状态有效" in result.output
