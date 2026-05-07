from typing import Any
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sufe_cli.cli import app
from sufe_cli.errors import SkillInstallError

runner = CliRunner()


def _setup_install_mocks(
    monkeypatch: pytest.MonkeyPatch,
    *,
    playwright_ok: bool = True,
    plan: list[tuple[Path, str, bool]] | None = None,
    skills_error: bool = False,
) -> None:
    """统一设置 install 命令所需的 mock"""

    def mock_check_playwright() -> tuple[bool, str]:
        if playwright_ok:
            return True, "/path/to/chromium"
        return False, "未安装"

    monkeypatch.setattr("sufe_cli.cli.check_playwright", mock_check_playwright)

    import sufe_cli.skills_manager as sm

    if skills_error:
        monkeypatch.setattr(
            sm,
            "get_install_plan",
            lambda: (_ for _ in ()).throw(SkillInstallError("bad")),
        )
    else:
        monkeypatch.setattr(sm, "get_install_plan", lambda: plan or [])

    monkeypatch.setattr(sm, "execute_install", lambda p: None)


# ---------------------------------------------------------------------------
# 无需更新
# ---------------------------------------------------------------------------


def test_install_all_up_to_date(monkeypatch: pytest.MonkeyPatch) -> None:
    """浏览器和 skills 都无需更新"""
    _setup_install_mocks(monkeypatch, playwright_ok=True, plan=[])

    result = runner.invoke(app, ["install"])
    assert result.exit_code == 0
    assert "Playwright Chromium 已安装" in result.output
    assert "Agent Skills 已是最新" in result.output


# ---------------------------------------------------------------------------
# 需要安装
# ---------------------------------------------------------------------------


def test_install_new_skills_confirm(monkeypatch: pytest.MonkeyPatch) -> None:
    """全新安装 skills，用户确认"""
    plan = [(Path("~/.agents/skills"), "sufe-base", False)]
    _setup_install_mocks(monkeypatch, plan=plan)

    result = runner.invoke(app, ["install"], input="Y\n")
    assert result.exit_code == 0
    assert "sufe-base" in result.output
    assert "Agent Skills 安装完成" in result.output


def test_install_new_skills_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    """全新安装 skills，用户取消"""
    plan = [(Path("~/.agents/skills"), "sufe-base", False)]
    _setup_install_mocks(monkeypatch, plan=plan)

    result = runner.invoke(app, ["install"], input="n\n")
    assert result.exit_code == 0
    assert "已取消" in result.output


def test_install_with_overwrite(monkeypatch: pytest.MonkeyPatch) -> None:
    """存在过期 skill，显示覆盖提示"""
    plan = [(Path("~/.agents/skills"), "sufe-base", True)]
    _setup_install_mocks(monkeypatch, plan=plan)

    result = runner.invoke(app, ["install"], input="Y\n")
    assert result.exit_code == 0
    assert "1 个已存在，将被覆盖" in result.output
    assert "Agent Skills 安装完成" in result.output


# ---------------------------------------------------------------------------
# 错误处理
# ---------------------------------------------------------------------------


def test_install_skills_check_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """skills 检查失败"""
    _setup_install_mocks(monkeypatch, skills_error=True)

    result = runner.invoke(app, ["install"])
    assert result.exit_code == 1
    assert "Skills 检查失败" in result.output


def test_install_skills_execute_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """skills 执行安装失败"""
    import sufe_cli.skills_manager as sm

    plan = [(Path("~/.agents/skills"), "sufe-base", False)]

    def mock_plan() -> list[tuple[Path, str, bool]]:
        return plan

    def mock_execute(p: Any) -> None:
        raise SkillInstallError("copy failed")

    _setup_install_mocks(monkeypatch, plan=plan)
    monkeypatch.setattr(sm, "get_install_plan", mock_plan)
    monkeypatch.setattr(sm, "execute_install", mock_execute)

    result = runner.invoke(app, ["install"], input="Y\n")
    assert result.exit_code == 1
    assert "Skills 安装失败" in result.output


# ---------------------------------------------------------------------------
# Playwright 安装
# ---------------------------------------------------------------------------


def test_install_playwright_needed(monkeypatch: pytest.MonkeyPatch) -> None:
    """需要安装浏览器"""
    import subprocess

    _setup_install_mocks(monkeypatch, playwright_ok=False, plan=[])
    monkeypatch.setattr(subprocess, "check_call", lambda cmd, **kwargs: None)

    result = runner.invoke(app, ["install"])
    assert result.exit_code == 0
    assert "正在安装 Playwright Chromium 浏览器" in result.output
