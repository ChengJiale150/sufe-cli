"""Bump version in src/sufe_cli/__init__.py and create a git tag."""

import re
import subprocess
import sys
from pathlib import Path


def bump_version(type_arg: str) -> None:
    version_file = Path(__file__).parent.parent / "src" / "sufe_cli" / "__init__.py"

    content = version_file.read_text()

    match = re.search(r'__version__ = "(\d+)\.(\d+)\.(\d+)"', content)
    if not match:
        print("❌ Could not parse version")
        sys.exit(1)

    major, minor, patch = map(int, match.groups())

    if type_arg == "major":
        major += 1
        minor = 0
        patch = 0
    elif type_arg == "minor":
        minor += 1
        patch = 0
    elif type_arg == "patch":
        patch += 1
    else:
        print(f"❌ Invalid type: {type_arg}. Use patch, minor, or major.")
        sys.exit(1)

    new_version = f"{major}.{minor}.{patch}"

    new_content = re.sub(r'__version__ = "[\d.]+"', f'__version__ = "{new_version}"', content)
    version_file.write_text(new_content)

    print(f"✅ Version updated to {new_version}")

    # Git operations
    subprocess.run(["git", "add", str(version_file)], check=True)
    subprocess.run(["git", "commit", "-m", f"chore: bump version to {new_version}"], check=True)
    subprocess.run(["git", "tag", f"v{new_version}"], check=True)
    subprocess.run(["git", "push"], check=True)
    subprocess.run(["git", "push", "--tags"], check=True)

    print(f"✅ Git tag v{new_version} created and pushed")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_version.py <patch|minor|major>")
        sys.exit(1)
    bump_version(sys.argv[1])
