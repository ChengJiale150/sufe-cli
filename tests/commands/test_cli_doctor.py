from typing import Any

import pytest
from typer.testing import CliRunner

from sufe_cli.cli import app

runner = CliRunner()


def _setup_mocks(
    monkeypatch: pytest.MonkeyPatch,
    *,
    playwright_ok: bool = True,
    portal_state_valid: bool = False,
) -> None:
    """统一设置 doctor 命令所需的 mock"""

    def mock_check_playwright() -> tuple[bool, str]:
        if playwright_ok:
            return True, "/path/to/chromium"
        return False, "Playwright Chromium 浏览器未安装"

    monkeypatch.setattr("sufe_cli.cli.check_playwright", mock_check_playwright)

    def mock_ensure_portal_state(state_path: Any = None) -> bool:
        return portal_state_valid

    monkeypatch.setattr("sufe_cli.cli.ensure_portal_state", mock_ensure_portal_state)


# ---------------------------------------------------------------------------
# 正常情况
# ---------------------------------------------------------------------------


def test_doctor_all_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    """所有检查通过"""
    _setup_mocks(monkeypatch, portal_state_valid=True)

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "Playwright Chromium 浏览器已安装" in result.output
    assert "门户登录状态有效" in result.output


# ---------------------------------------------------------------------------
# 门户状态无效
# ---------------------------------------------------------------------------


def test_doctor_portal_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    """门户登录状态无效"""
    _setup_mocks(monkeypatch, portal_state_valid=False)

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "门户登录状态无效" in result.output
    assert "请运行 `sufe auth` 重新登录。" in result.output


# ---------------------------------------------------------------------------
# Playwright 缺失
# ---------------------------------------------------------------------------


def test_doctor_playwright_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """浏览器未安装 → 提示安装，同时检查认证状态"""
    _setup_mocks(
        monkeypatch,
        playwright_ok=False,
        portal_state_valid=True,
    )

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "Playwright Chromium 浏览器未安装" in result.output
    assert "请运行 `sufe install` 进行安装" in result.output
    assert "门户登录状态有效" in result.output
