import tempfile
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from sufe_cli.cli import app

runner = CliRunner()


def _setup_mocks(
    monkeypatch: pytest.MonkeyPatch,
    *,
    playwright_ok: bool = True,
    auth_config_exists: bool = True,
    portal_state_valid: bool = False,
    skills_ok: bool = True,
    skills_error: bool = False,
) -> None:
    """统一设置 doctor 命令所需的 mock"""

    def mock_check_playwright() -> tuple[bool, str]:
        if playwright_ok:
            return True, "/path/to/chromium"
        return False, "Playwright Chromium 浏览器未安装"

    monkeypatch.setattr("sufe_cli.cli.check_playwright", mock_check_playwright)

    def mock_auth_config_exists(path: Any = None) -> bool:
        return auth_config_exists

    monkeypatch.setattr("sufe_cli.cli.auth_config_exists", mock_auth_config_exists)

    def mock_ensure_portal_state(state_path: Any = None) -> bool:
        return portal_state_valid

    monkeypatch.setattr("sufe_cli.cli.ensure_portal_state", mock_ensure_portal_state)

    if skills_error:
        from sufe_cli.errors import SkillInstallError

        monkeypatch.setattr(
            "sufe_cli.skills_manager.get_builtin_skills_path",
            lambda: (_ for _ in ()).throw(SkillInstallError("missing")),
        )
    elif skills_ok:
        import sufe_cli.skills_manager as sm

        tmp_dir = Path(tempfile.mkdtemp())
        agents_skills = tmp_dir / "agents" / "skills"
        agents_skills.mkdir(parents=True)
        (agents_skills / "sufe-base").mkdir()
        (agents_skills / "sufe-base" / "SKILL.md").write_text("test", encoding="utf-8")

        def mock_builtin() -> Path:
            return Path("/fake/builtin")

        def mock_list() -> list[str]:
            return ["sufe-base"]

        def mock_dirs() -> list[Path]:
            return [agents_skills]

        def mock_hash(path: Any) -> str:
            return "same"

        monkeypatch.setattr(sm, "get_builtin_skills_path", mock_builtin)
        monkeypatch.setattr(sm, "list_builtin_skills", mock_list)
        monkeypatch.setattr(sm, "get_target_dirs", mock_dirs)
        monkeypatch.setattr(sm, "compute_dir_hash", mock_hash)
    else:
        # skills_ok=False: 需要让目标目录存在但哈希不一致
        import sufe_cli.skills_manager as sm

        tmp_dir = Path(tempfile.mkdtemp())
        agents_skills = tmp_dir / "agents" / "skills"
        agents_skills.mkdir(parents=True)
        (agents_skills / "sufe-base").mkdir()
        (agents_skills / "sufe-base" / "SKILL.md").write_text("old", encoding="utf-8")

        def mock_dirs() -> list[Path]:
            return [agents_skills]

        monkeypatch.setattr(sm, "get_target_dirs", mock_dirs)


# ---------------------------------------------------------------------------
# 正常情况
# ---------------------------------------------------------------------------


def test_doctor_all_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    """所有检查通过"""
    _setup_mocks(monkeypatch, portal_state_valid=True)

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "Playwright Chromium 浏览器已安装" in result.output
    assert "认证配置文件 auth.json 已存在" in result.output
    assert "门户登录状态有效" in result.output


# ---------------------------------------------------------------------------
# 认证配置缺失
# ---------------------------------------------------------------------------


def test_doctor_auth_config_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """认证配置文件缺失"""
    _setup_mocks(monkeypatch, auth_config_exists=False, portal_state_valid=True)

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "认证配置文件 auth.json 不存在" in result.output
    assert "请运行 `sufe auth` 进行配置。" in result.output


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


# ---------------------------------------------------------------------------
# Skills 检查
# ---------------------------------------------------------------------------


def test_doctor_skills_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """agents skills 缺失 → 报错"""
    _setup_mocks(monkeypatch, portal_state_valid=True, skills_ok=False)

    import sufe_cli.skills_manager as sm

    def mock_builtin() -> Path:
        return Path("/fake/builtin")

    def mock_list() -> list[str]:
        return ["sufe-base"]

    def mock_dirs() -> list[Path]:
        return [Path("~/.agents/skills")]

    def mock_hash(path: Any) -> str:
        if "agents" in str(path):
            return ""  # 缺失
        return "same"

    monkeypatch.setattr(sm, "get_builtin_skills_path", mock_builtin)
    monkeypatch.setattr(sm, "list_builtin_skills", mock_list)
    monkeypatch.setattr(sm, "get_target_dirs", mock_dirs)
    monkeypatch.setattr(sm, "compute_dir_hash", mock_hash)

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "sufe-base 未安装" in result.output


def test_doctor_skills_builtin_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """内置 skills 读取失败 → 报错"""
    _setup_mocks(monkeypatch, portal_state_valid=True, skills_error=True)

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "内置 Skills 读取失败" in result.output
