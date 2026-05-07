"""Agent Skills 发现、校验与安装管理."""

import hashlib
from pathlib import Path

import importlib.resources


from .errors import SkillInstallError


def get_builtin_skills_path() -> Path:
    """定位内置 skills/ 目录（支持正常安装与可编辑模式）."""
    # 1) 正常安装 / wheel 路径
    pkg = importlib.resources.files("sufe_cli")
    wheel_path = Path(str(pkg)) / "skills"
    if wheel_path.exists():
        return wheel_path

    # 2) 可编辑模式回退：从本文件向上追溯到项目根目录
    # __file__  -> src/sufe_cli/skills_manager.py
    # parents[1] -> src/
    # parents[2] -> 项目根目录
    editable_path = Path(__file__).resolve().parents[2] / "skills"
    if editable_path.exists():
        return editable_path

    msg = f"内置 skills 目录不存在（尝试: {wheel_path}, {editable_path}）"
    raise SkillInstallError(msg)


def list_builtin_skills() -> list[str]:
    """扫描内置 skills/ 目录，自动发现所有 skill 子目录（按名称排序）."""
    skills_path = get_builtin_skills_path()
    skills = [p.name for p in skills_path.iterdir() if p.is_dir() and not p.name.startswith(".")]
    return sorted(skills)


def get_target_dirs() -> list[Path]:
    """
    返回目标目录列表.
    - ~/.agents/skills（始终包含）
    - ~/.claude/skills（仅当 ~/.claude 存在时包含）
    """
    dirs: list[Path] = [Path.home() / ".agents" / "skills"]
    claude_dir = Path.home() / ".claude"
    if claude_dir.exists():
        dirs.append(claude_dir / "skills")
    return dirs


def compute_dir_hash(path: Path) -> str:
    """递归计算目录内容的 sha256 哈希；目录不存在返回空字符串."""
    if not path.exists():
        return ""

    hasher = hashlib.sha256()
    files_list: list[Path] = []

    for item in sorted(path.rglob("*")):
        if item.is_file():
            files_list.append(item)

    for file_path in files_list:
        rel_path = file_path.relative_to(path).as_posix()
        hasher.update(rel_path.encode("utf-8"))
        hasher.update(file_path.read_bytes())

    return hasher.hexdigest()


def get_install_plan() -> list[tuple[Path, str, bool]]:
    """
    返回安装计划列表，每项为 (target_dir, skill_name, will_overwrite).
    will_overwrite = True 表示目标已存在但哈希不一致.
    不包含已存在且哈希一致的项.
    """
    builtin_path = get_builtin_skills_path()
    skill_names = list_builtin_skills()
    target_dirs = get_target_dirs()

    plan: list[tuple[Path, str, bool]] = []
    for target_dir in target_dirs:
        for skill_name in skill_names:
            builtin_skill = builtin_path / skill_name
            target_skill = target_dir / skill_name

            builtin_hash = compute_dir_hash(builtin_skill)
            target_hash = compute_dir_hash(target_skill)

            if target_hash == builtin_hash and target_hash != "":
                continue  # 已存在且一致，跳过

            will_overwrite = target_skill.exists()
            plan.append((target_dir, skill_name, will_overwrite))

    return plan


def execute_install(plan: list[tuple[Path, str, bool]]) -> None:
    """执行复制操作；任一失败抛 SkillInstallError."""
    builtin_path = get_builtin_skills_path()

    for target_dir, skill_name, _ in plan:
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            dst = target_dir / skill_name
            if dst.exists():
                import shutil

                shutil.rmtree(dst)
            import shutil

            shutil.copytree(builtin_path / skill_name, dst)
        except Exception as exc:  # noqa: BLE001
            msg = f"安装 skill '{skill_name}' 到 {target_dir} 失败: {exc}"
            raise SkillInstallError(msg) from exc
