"""Automatic detection and sharing of project files across worktrees.

Detects project type (Node.js, Python, Rust, etc.) and automatically symlinks
common directories like node_modules, .venv, target to save disk space and time.
"""

import platform
import subprocess
from pathlib import Path
from typing import TypedDict

from .console import get_console

console = get_console()

# Detect Windows platform
IS_WINDOWS = platform.system() == "Windows"


class SharedFile(TypedDict):
    """Configuration for a file/directory to be shared."""

    path: str  # Relative path from repo root
    method: str  # "symlink" or "copy"


class ProjectTypeConfig(TypedDict):
    """Configuration for a project type."""

    detect: list[str]  # Marker files to detect this project type
    shared: list[SharedFile]  # Files/directories to share


# Project type detection rules and shared files
PROJECT_TYPES: dict[str, ProjectTypeConfig] = {
    "nodejs": {
        "detect": ["package.json"],
        "shared": [
            {"path": "node_modules", "method": "symlink"},
        ],
    },
    "python": {
        "detect": ["pyproject.toml", "requirements.txt", "setup.py"],
        "shared": [
            {"path": ".venv", "method": "symlink"},
            {"path": "venv", "method": "symlink"},
        ],
    },
    "rust": {
        "detect": ["Cargo.toml"],
        "shared": [
            {"path": "target", "method": "symlink"},
        ],
    },
    "go": {
        "detect": ["go.mod"],
        "shared": [
            {"path": "vendor", "method": "symlink"},
        ],
    },
    "php": {
        "detect": ["composer.json"],
        "shared": [
            {"path": "vendor", "method": "symlink"},
        ],
    },
    "ruby": {
        "detect": ["Gemfile"],
        "shared": [
            {"path": "vendor/bundle", "method": "symlink"},
        ],
    },
    "java_maven": {
        "detect": ["pom.xml"],
        "shared": [
            {"path": "target", "method": "symlink"},
        ],
    },
    "java_gradle": {
        "detect": ["build.gradle", "build.gradle.kts"],
        "shared": [
            {"path": "build", "method": "symlink"},
            {"path": ".gradle", "method": "symlink"},
        ],
    },
}


def detect_project_types(repo_path: Path) -> list[str]:
    """Detect project types based on marker files.

    Args:
        repo_path: Path to the repository

    Returns:
        List of detected project type names (e.g., ["nodejs", "python"])
    """
    detected_types = []

    for project_type, config in PROJECT_TYPES.items():
        detect_files = config["detect"]
        # Check if any of the marker files exist
        if any((repo_path / marker).exists() for marker in detect_files):
            detected_types.append(project_type)

    return detected_types


def get_shared_files(repo_path: Path) -> list[SharedFile]:
    """Get list of files/directories to share based on detected project types.

    Args:
        repo_path: Path to the repository

    Returns:
        List of SharedFile configurations
    """
    detected_types = detect_project_types(repo_path)
    shared_files: list[SharedFile] = []

    for project_type in detected_types:
        config = PROJECT_TYPES[project_type]
        shared_files.extend(config["shared"])

    return shared_files


def _create_windows_junction(source: Path, target: Path) -> None:
    """Create a Windows junction point (requires no admin privileges).

    Junction points are similar to symlinks but don't require administrator
    privileges on Windows. They only work for directories.

    Args:
        source: Source directory (absolute path)
        target: Target junction point path (will be created)

    Raises:
        OSError: If junction creation fails
    """
    # mklink /J requires absolute paths
    source_abs = source.resolve()
    target_abs = target.resolve()

    # Use mklink /J to create junction point
    # Note: mklink is a cmd.exe built-in command, so we need shell=True
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(target_abs), str(source_abs)],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise OSError(f"Failed to create junction: {result.stderr.strip()}")


def share_files(source_repo: Path, target_worktree: Path) -> None:
    """Share files/directories from source repository to target worktree.

    Creates symlinks for specified files/directories if they exist in the source.
    Also copies additional files specified in configuration (e.g., .env files).
    Automatically adds symlinked paths to .git/info/exclude to prevent git tracking.

    Args:
        source_repo: Source repository path (base worktree)
        target_worktree: Target worktree path (newly created)
    """
    shared_files = get_shared_files(source_repo)

    # Get additional files to copy from configuration
    from .config import get_copy_files

    copy_files = get_copy_files()

    # Add copy files to the list
    for file_path in copy_files:
        shared_files.append({"path": file_path, "method": "copy"})

    if not shared_files:
        return

    console.print("\n[bold cyan]Sharing files:[/bold cyan]")

    symlinked_paths = []  # Track symlinked paths to add to git exclude

    for shared_file in shared_files:
        rel_path = shared_file["path"]
        method = shared_file["method"]

        source_path = source_repo / rel_path
        target_path = target_worktree / rel_path

        # Skip if source doesn't exist
        if not source_path.exists():
            continue

        # Skip if target already exists
        if target_path.exists():
            continue

        try:
            if method == "symlink":
                # Create symlink (with Windows-specific handling)
                if IS_WINDOWS and source_path.is_dir():
                    # On Windows, try junction points first (no admin required)
                    try:
                        _create_windows_junction(source_path, target_path)
                        console.print(f"  [green]✓[/green] Junction: {rel_path}")
                        symlinked_paths.append(rel_path)
                    except OSError:
                        # Fall back to directory symlink (may require admin)
                        try:
                            target_path.symlink_to(source_path, target_is_directory=True)
                            console.print(f"  [green]✓[/green] Symlinked: {rel_path}")
                            symlinked_paths.append(rel_path)
                        except OSError as symlink_error:
                            # If both junction and symlink fail, raise the symlink error
                            raise symlink_error
                else:
                    # Unix/Linux or file symlink
                    target_path.symlink_to(source_path)
                    console.print(f"  [green]✓[/green] Symlinked: {rel_path}")
                    symlinked_paths.append(rel_path)
            elif method == "copy":
                # Copy file/directory
                import shutil

                if source_path.is_dir():
                    shutil.copytree(source_path, target_path, symlinks=True)
                else:
                    # Ensure parent directory exists
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, target_path)
                console.print(f"  [green]✓[/green] Copied: {rel_path}")
        except OSError as e:
            # Non-fatal: warn but continue
            console.print(f"  [yellow]![/yellow] Failed to share {rel_path}: {e}")

    # Add symlinked paths to .git/info/exclude to prevent git tracking
    if symlinked_paths:
        _add_to_git_exclude(target_worktree, symlinked_paths)

    console.print()


def _add_to_git_exclude(worktree_path: Path, paths: list[str]) -> None:
    """Add paths to .git/info/exclude to prevent git from tracking them.

    Args:
        worktree_path: Path to the worktree
        paths: List of relative paths to exclude
    """
    try:
        # In worktrees, .git is a file containing "gitdir: <path>"
        # We need to find the actual git directory
        git_file = worktree_path / ".git"

        if git_file.is_file():
            # Read gitdir path from .git file
            git_content = git_file.read_text().strip()
            if git_content.startswith("gitdir: "):
                git_dir = Path(git_content[8:])  # Remove "gitdir: " prefix
            else:
                return
        elif git_file.is_dir():
            # Main repository (not a worktree)
            git_dir = git_file
        else:
            return

        exclude_file = git_dir / "info" / "exclude"

        # Ensure directory exists
        exclude_file.parent.mkdir(parents=True, exist_ok=True)

        # Read existing content
        existing_lines = []
        if exclude_file.exists():
            existing_lines = exclude_file.read_text().splitlines()

        # Check which paths need to be added
        new_lines = []
        marker = "# claude-worktree auto-shared files"
        has_marker = marker in existing_lines

        for path in paths:
            if path not in existing_lines:
                new_lines.append(path)

        # Add new paths if needed
        if new_lines:
            with exclude_file.open("a") as f:
                if not has_marker:
                    f.write(f"\n{marker}\n")
                for path in new_lines:
                    f.write(f"{path}\n")

    except OSError:
        # Non-fatal: just skip if we can't update exclude file
        pass
