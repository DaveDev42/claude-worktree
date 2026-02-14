"""Global repository registry for cross-repo worktree management.

Tracks repositories that use claude-worktree so they can be managed
globally with `cw -g` commands. Registry is stored at
~/.config/claude-worktree/registry.json.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .git_utils import git_command

REGISTRY_VERSION = 1

# Directories to skip during filesystem scan
SCAN_SKIP_DIRS = frozenset({
    "node_modules",
    ".cache",
    ".npm",
    ".yarn",
    "__pycache__",
    ".venv",
    "venv",
    ".tox",
    ".nox",
    ".eggs",
    "dist",
    "build",
    ".git",
    "Library",
    ".Trash",
    ".local",
    "Applications",
    ".cargo",
    ".rustup",
    ".pyenv",
    ".nvm",
    ".rbenv",
    ".goenv",
    ".volta",
    "site-packages",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "coverage",
    ".next",
    ".nuxt",
    ".output",
    ".turbo",
})


def get_registry_path() -> Path:
    """Get the path to the global registry file.

    Returns:
        Path to registry file: ~/.config/claude-worktree/registry.json
    """
    config_dir = Path.home() / ".config" / "claude-worktree"
    return config_dir / "registry.json"


def load_registry() -> dict[str, Any]:
    """Load the global registry from disk.

    Returns:
        Registry dictionary with 'version' and 'repositories' keys.
        Returns empty registry if file doesn't exist.
    """
    registry_path = get_registry_path()

    if not registry_path.exists():
        return {"version": REGISTRY_VERSION, "repositories": {}}

    try:
        with open(registry_path) as f:
            data: dict[str, Any] = json.load(f)

        # Ensure required keys exist
        if "version" not in data:
            data["version"] = REGISTRY_VERSION
        if "repositories" not in data:
            data["repositories"] = {}

        return data
    except (OSError, json.JSONDecodeError):
        return {"version": REGISTRY_VERSION, "repositories": {}}


def save_registry(registry: dict[str, Any]) -> None:
    """Save the global registry to disk.

    Args:
        registry: Registry dictionary to save.
    """
    registry_path = get_registry_path()
    registry_path.parent.mkdir(parents=True, exist_ok=True)

    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=2)


def register_repo(repo_path: Path) -> None:
    """Register a repository in the global registry.

    If the repository is already registered, updates last_seen timestamp.

    Args:
        repo_path: Absolute path to the repository root.
    """
    registry = load_registry()
    repo_key = str(repo_path.resolve())
    now = datetime.now(UTC).isoformat()

    if repo_key in registry["repositories"]:
        registry["repositories"][repo_key]["last_seen"] = now
    else:
        registry["repositories"][repo_key] = {
            "name": repo_path.name,
            "registered_at": now,
            "last_seen": now,
        }

    save_registry(registry)


def update_last_seen(repo_path: Path) -> None:
    """Update the last_seen timestamp for a registered repository.

    No-op if the repository is not registered.

    Args:
        repo_path: Absolute path to the repository root.
    """
    registry = load_registry()
    repo_key = str(repo_path.resolve())

    if repo_key in registry["repositories"]:
        registry["repositories"][repo_key]["last_seen"] = (
            datetime.now(UTC).isoformat()
        )
        save_registry(registry)


def prune_registry() -> list[str]:
    """Remove registry entries for repositories that no longer exist.

    Returns:
        List of removed repository paths.
    """
    registry = load_registry()
    removed: list[str] = []

    for repo_path in list(registry["repositories"]):
        path = Path(repo_path)
        # Check if directory exists and is still a git repo
        if not path.exists() or not (path / ".git").exists():
            del registry["repositories"][repo_path]
            removed.append(repo_path)

    if removed:
        save_registry(registry)

    return removed


def _is_git_repo(path: Path) -> bool:
    """Check if a path is a git repository root (not a worktree).

    Args:
        path: Directory path to check.

    Returns:
        True if path is a main git repository root.
    """
    git_path = path / ".git"
    # Main repo has .git as a directory; worktrees have .git as a file
    return git_path.is_dir()


def _has_worktrees(repo_path: Path) -> bool:
    """Check if a git repository has any worktrees beyond the main one.

    Args:
        repo_path: Path to git repository.

    Returns:
        True if repository has additional worktrees.
    """
    try:
        result = git_command(
            "worktree", "list", "--porcelain",
            repo=repo_path, capture=True, check=False,
        )
        if result.returncode != 0:
            return False

        # Count worktree entries
        worktree_count = sum(
            1 for line in result.stdout.strip().splitlines()
            if line.startswith("worktree ")
        )
        return worktree_count > 1
    except Exception:
        return False


def scan_for_repos(base_dir: Path | None = None, max_depth: int = 5) -> list[Path]:
    """Scan filesystem for git repositories with worktrees.

    Args:
        base_dir: Directory to start scanning from. Defaults to home directory.
        max_depth: Maximum directory depth to scan.

    Returns:
        List of paths to git repositories that have worktrees.
    """
    if base_dir is None:
        base_dir = Path.home()

    base_dir = base_dir.resolve()
    found_repos: list[Path] = []

    def _scan(current: Path, depth: int) -> None:
        if depth > max_depth:
            return

        try:
            entries = sorted(current.iterdir())
        except (PermissionError, OSError):
            return

        for entry in entries:
            if not entry.is_dir():
                continue

            # Skip hidden dirs (except .git which we check) and known skip dirs
            if entry.name.startswith(".") or entry.name in SCAN_SKIP_DIRS:
                continue

            if _is_git_repo(entry) and _has_worktrees(entry):
                found_repos.append(entry)
                # Don't recurse into git repos
                continue

            _scan(entry, depth + 1)

    _scan(base_dir, 0)
    return found_repos


def get_all_registered_repos() -> list[tuple[str, Path]]:
    """Get all registered repositories.

    Returns:
        List of (name, path) tuples for all registered repositories.
    """
    registry = load_registry()
    result: list[tuple[str, Path]] = []

    for repo_path_str, info in registry["repositories"].items():
        result.append((info["name"], Path(repo_path_str)))

    return result
