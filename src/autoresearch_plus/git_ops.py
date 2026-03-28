from __future__ import annotations

import subprocess
from pathlib import Path


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def current_branch(root: Path) -> str:
    return _git(root, "rev-parse", "--abbrev-ref", "HEAD") or "nogit"


def current_commit(root: Path) -> str:
    return _git(root, "rev-parse", "--short", "HEAD") or "nogit"


def is_dirty(root: Path) -> bool:
    return bool(_git(root, "status", "--porcelain"))


def commit_paths(root: Path, paths: list[Path], message: str) -> str:
    rel_paths = [str(path.relative_to(root)) for path in paths]
    subprocess.run(["git", "-C", str(root), "add", *rel_paths], check=False, capture_output=True, text=True)
    result = subprocess.run(
        ["git", "-C", str(root), "commit", "-m", message],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return current_commit(root)
    return current_commit(root)


def commit_target(root: Path, target_file: Path, message: str) -> str:
    return commit_paths(root, [target_file], message)
