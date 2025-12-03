"""File sharing for worktrees via .cwshare configuration.

Reads .cwshare file from repository root and copies specified files
to new worktrees during creation.
"""

import shutil
from pathlib import Path

from .console import get_console

console = get_console()


def parse_cwshare(repo_path: Path) -> list[str]:
    """Parse .cwshare file and return list of paths to share.

    The .cwshare file format:
    - One file/directory path per line
    - Lines starting with # are comments
    - Empty lines are ignored

    Args:
        repo_path: Path to the repository

    Returns:
        List of relative paths to share
    """
    cwshare_path = repo_path / ".cwshare"
    if not cwshare_path.exists():
        return []

    paths = []
    for line in cwshare_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            paths.append(line)
    return paths


def share_files(source_repo: Path, target_worktree: Path) -> None:
    """Copy files specified in .cwshare to target worktree.

    Reads the .cwshare file from source_repo and copies each specified
    file or directory to the target worktree.

    Args:
        source_repo: Source repository path (base worktree)
        target_worktree: Target worktree path (newly created)
    """
    paths = parse_cwshare(source_repo)

    if not paths:
        return

    console.print("\n[bold cyan]Copying shared files:[/bold cyan]")

    for rel_path in paths:
        source = source_repo / rel_path
        target = target_worktree / rel_path

        # Skip if source doesn't exist
        if not source.exists():
            continue

        # Skip if target already exists
        if target.exists():
            continue

        try:
            if source.is_dir():
                shutil.copytree(source, target, symlinks=True)
            else:
                # Ensure parent directory exists
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            console.print(f"  [green]✓[/green] Copied: {rel_path}")
        except OSError as e:
            # Non-fatal: warn but continue
            console.print(f"  [yellow]![/yellow] Failed: {rel_path}: {e}")

    console.print()
