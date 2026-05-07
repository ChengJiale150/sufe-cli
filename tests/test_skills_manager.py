import pytest
from pathlib import Path
from sufe_cli import skills_manager
from sufe_cli.errors import SkillInstallError


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_skill_dir(parent: Path, name: str, content: str = "test") -> Path:
    """在 parent 下创建一个简单的 skill 目录."""
    skill_dir = parent / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    return skill_dir


# ---------------------------------------------------------------------------
# list_builtin_skills
# ---------------------------------------------------------------------------


def test_list_builtin_skills_auto_discovery(monkeypatch, tmp_path) -> None:
    """自动发现内置 skills（排序）."""
    builtin = tmp_path / "skills"
    builtin.mkdir()
    _make_skill_dir(builtin, "sufe-canvas")
    _make_skill_dir(builtin, "sufe-base")
    _make_skill_dir(builtin, "sufe-score")

    monkeypatch.setattr(skills_manager, "get_builtin_skills_path", lambda: builtin)

    result = skills_manager.list_builtin_skills()
    assert result == ["sufe-base", "sufe-canvas", "sufe-score"]


def test_list_builtin_skills_empty(monkeypatch, tmp_path) -> None:
    """空目录返回空列表."""
    builtin = tmp_path / "skills"
    builtin.mkdir()
    monkeypatch.setattr(skills_manager, "get_builtin_skills_path", lambda: builtin)
    assert skills_manager.list_builtin_skills() == []


# ---------------------------------------------------------------------------
# get_target_dirs
# ---------------------------------------------------------------------------


def test_get_target_dirs_with_claude(monkeypatch, tmp_path) -> None:
    """~/.claude 存在时包含两个目录."""
    home = tmp_path / "home"
    home.mkdir()
    (home / ".claude").mkdir()
    (home / ".agents").mkdir()

    monkeypatch.setattr(Path, "home", lambda: home)

    dirs = skills_manager.get_target_dirs()
    assert len(dirs) == 2
    assert dirs[0].parts[-2:] == (".agents", "skills")
    assert dirs[1].parts[-2:] == (".claude", "skills")


def test_get_target_dirs_without_claude(monkeypatch, tmp_path) -> None:
    """~/.claude 不存在时只返回 agents 目录."""
    home = tmp_path / "home"
    home.mkdir()
    (home / ".agents").mkdir()

    monkeypatch.setattr(Path, "home", lambda: home)

    dirs = skills_manager.get_target_dirs()
    assert len(dirs) == 1
    assert dirs[0].parts[-2:] == (".agents", "skills")


# ---------------------------------------------------------------------------
# compute_dir_hash
# ---------------------------------------------------------------------------


def test_compute_dir_hash_consistency(tmp_path) -> None:
    """相同内容返回相同哈希."""
    d1 = tmp_path / "a"
    d1.mkdir()
    (d1 / "SKILL.md").write_text("hello", encoding="utf-8")

    d2 = tmp_path / "b"
    d2.mkdir()
    (d2 / "SKILL.md").write_text("hello", encoding="utf-8")

    assert skills_manager.compute_dir_hash(d1) == skills_manager.compute_dir_hash(d2)
    assert skills_manager.compute_dir_hash(d1) != ""


def test_compute_dir_hash_different_content(tmp_path) -> None:
    """不同内容返回不同哈希."""
    d1 = tmp_path / "a"
    d1.mkdir()
    (d1 / "SKILL.md").write_text("hello", encoding="utf-8")

    d2 = tmp_path / "b"
    d2.mkdir()
    (d2 / "SKILL.md").write_text("world", encoding="utf-8")

    assert skills_manager.compute_dir_hash(d1) != skills_manager.compute_dir_hash(d2)


def test_compute_dir_hash_missing(tmp_path) -> None:
    """目录不存在返回空字符串."""
    assert skills_manager.compute_dir_hash(tmp_path / "nonexistent") == ""


# ---------------------------------------------------------------------------
# get_install_plan
# ---------------------------------------------------------------------------


def test_get_install_plan_all_new(monkeypatch, tmp_path) -> None:
    """目标目录为空，所有 skills 都需要安装."""
    builtin = tmp_path / "builtin" / "skills"
    builtin.mkdir(parents=True)
    _make_skill_dir(builtin, "sufe-base")

    home = tmp_path / "home"
    home.mkdir()
    (home / ".agents").mkdir()
    (home / ".claude").mkdir()

    monkeypatch.setattr(skills_manager, "get_builtin_skills_path", lambda: builtin)
    monkeypatch.setattr(Path, "home", lambda: home)

    plan = skills_manager.get_install_plan()
    assert len(plan) == 2  # agents + claude
    for target_dir, skill_name, will_overwrite in plan:
        assert skill_name == "sufe-base"
        assert not will_overwrite


def test_get_install_plan_up_to_date(monkeypatch, tmp_path) -> None:
    """目标已存在且一致，计划为空."""
    builtin = tmp_path / "builtin" / "skills"
    builtin.mkdir(parents=True)
    _make_skill_dir(builtin, "sufe-base", "content")

    home = tmp_path / "home"
    home.mkdir()
    agents_skills = home / ".agents" / "skills"
    agents_skills.mkdir(parents=True)
    _make_skill_dir(agents_skills, "sufe-base", "content")

    monkeypatch.setattr(skills_manager, "get_builtin_skills_path", lambda: builtin)
    monkeypatch.setattr(Path, "home", lambda: home)

    plan = skills_manager.get_install_plan()
    assert plan == []


def test_get_install_plan_overwrite(monkeypatch, tmp_path) -> None:
    """目标存在但内容不同，标记为覆盖."""
    builtin = tmp_path / "builtin" / "skills"
    builtin.mkdir(parents=True)
    _make_skill_dir(builtin, "sufe-base", "new content")

    home = tmp_path / "home"
    home.mkdir()
    agents_skills = home / ".agents" / "skills"
    agents_skills.mkdir(parents=True)
    _make_skill_dir(agents_skills, "sufe-base", "old content")

    monkeypatch.setattr(skills_manager, "get_builtin_skills_path", lambda: builtin)
    monkeypatch.setattr(Path, "home", lambda: home)

    plan = skills_manager.get_install_plan()
    assert len(plan) == 1
    _, _, will_overwrite = plan[0]
    assert will_overwrite


# ---------------------------------------------------------------------------
# execute_install
# ---------------------------------------------------------------------------


def test_execute_install_success(monkeypatch, tmp_path) -> None:
    """正常复制 skill 到目标目录."""
    builtin = tmp_path / "builtin" / "skills"
    builtin.mkdir(parents=True)
    _make_skill_dir(builtin, "sufe-base", "hello")

    target = tmp_path / "target"

    monkeypatch.setattr(skills_manager, "get_builtin_skills_path", lambda: builtin)

    plan = [(target, "sufe-base", False)]
    skills_manager.execute_install(plan)

    assert (target / "sufe-base" / "SKILL.md").read_text() == "hello"


def test_execute_install_overwrite(monkeypatch, tmp_path) -> None:
    """覆盖已存在的 skill."""
    builtin = tmp_path / "builtin" / "skills"
    builtin.mkdir(parents=True)
    _make_skill_dir(builtin, "sufe-base", "new")

    target = tmp_path / "target"
    target.mkdir()
    old_skill = target / "sufe-base"
    old_skill.mkdir()
    (old_skill / "SKILL.md").write_text("old", encoding="utf-8")
    (old_skill / "extra.txt").write_text("extra", encoding="utf-8")

    monkeypatch.setattr(skills_manager, "get_builtin_skills_path", lambda: builtin)

    plan = [(target, "sufe-base", True)]
    skills_manager.execute_install(plan)

    assert (target / "sufe-base" / "SKILL.md").read_text() == "new"
    assert not (target / "sufe-base" / "extra.txt").exists()


def test_execute_install_failure(monkeypatch, tmp_path) -> None:
    """复制失败时抛出 SkillInstallError."""
    builtin = tmp_path / "builtin" / "skills"
    builtin.mkdir(parents=True)
    # 不创建 sufe-base 目录，让它找不到源

    target = tmp_path / "target"

    monkeypatch.setattr(skills_manager, "get_builtin_skills_path", lambda: builtin)

    plan = [(target, "sufe-base", False)]
    with pytest.raises(SkillInstallError):
        skills_manager.execute_install(plan)
