"""Backup and restore operations for claude-worktree."""

import json
import subprocess
from datetime import datetime
from pathlib import Path

from ..console import get_console
from ..constants import CONFIG_KEY_BASE_BRANCH, CONFIG_KEY_BASE_PATH, default_worktree_path
from ..exceptions import GitError
from ..git_utils import get_config, get_repo_root, git_command, parse_worktrees, set_config

console = get_console()


def get_backups_dir() -> Path:
    """
    Get the backups directory path.

    Returns:
        Path to ~/.config/claude-worktree/backups/
    """
    from ..config import get_config_path

    config_dir = get_config_path().parent
    backups_dir = config_dir / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    return backups_dir


def backup_worktree(
    branch: str | None = None,
    output: Path | None = None,
    all_worktrees: bool = False,
) -> None:
    """
    Create backup of worktree(s) using git bundle.

    Args:
        branch: Branch name to backup (None = current worktree)
        output: Custom output directory for backups
        all_worktrees: Backup all worktrees

    Raises:
        WorktreeNotFoundError: If worktree not found
        GitError: If backup fails
    """
    from .helpers import resolve_worktree_target

    repo = get_repo_root()

    # Determine which worktrees to backup
    branches_to_backup: list[tuple[str, Path]] = []

    if all_worktrees:
        # Backup all worktrees
        for br, path in parse_worktrees(repo):
            if path.resolve() == repo.resolve() or br == "(detached)":
                continue
            branch_name = br[11:] if br.startswith("refs/heads/") else br
            branches_to_backup.append((branch_name, path))
    elif branch or not all_worktrees:
        # Backup specific branch or current worktree
        worktree_path, branch_name, _ = resolve_worktree_target(branch)
        branches_to_backup.append((branch_name, worktree_path))

    # Determine output directory
    if output:
        backups_root = output
    else:
        backups_root = get_backups_dir()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_count = 0

    console.print("\n[bold cyan]Creating backup(s)...[/bold cyan]\n")

    for branch_name, worktree_path in branches_to_backup:
        # Create backup directory for this branch
        branch_backup_dir = backups_root / branch_name / timestamp
        branch_backup_dir.mkdir(parents=True, exist_ok=True)

        bundle_file = branch_backup_dir / "bundle.git"
        metadata_file = branch_backup_dir / "metadata.json"

        console.print(f"[yellow]Backing up:[/yellow] [bold]{branch_name}[/bold]")

        try:
            # Create git bundle (includes full history)
            git_command(
                "bundle",
                "create",
                str(bundle_file),
                "--all",
                repo=worktree_path,
            )

            # Get metadata
            base_branch = get_config(CONFIG_KEY_BASE_BRANCH.format(branch_name), repo)
            base_path = get_config(CONFIG_KEY_BASE_PATH.format(branch_name), repo)

            # Check for uncommitted changes
            status_result = git_command("status", "--porcelain", repo=worktree_path, capture=True)
            has_changes = bool(status_result.stdout.strip())

            # Create stash for uncommitted changes if they exist
            stash_file = None
            if has_changes:
                console.print("  [dim]Found uncommitted changes, creating stash...[/dim]")
                stash_file = branch_backup_dir / "stash.patch"
                diff_result = git_command("diff", "HEAD", repo=worktree_path, capture=True)
                stash_file.write_text(diff_result.stdout)

            # Save metadata
            metadata = {
                "branch": branch_name,
                "base_branch": base_branch,
                "base_path": base_path,
                "worktree_path": str(worktree_path),
                "backed_up_at": datetime.now().isoformat(),
                "has_uncommitted_changes": has_changes,
                "bundle_file": str(bundle_file),
                "stash_file": str(stash_file) if stash_file else None,
            }

            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)

            console.print(f"  [green]*[/green] Backup saved to: {branch_backup_dir}")
            backup_count += 1

        except GitError as e:
            console.print(f"  [red]x[/red] Backup failed: {e}")
            continue

    console.print(
        f"\n[bold green]* Backup complete! Created {backup_count} backup(s)[/bold green]\n"
    )
    console.print(f"[dim]Backups saved in: {backups_root}[/dim]\n")


def list_backups(branch: str | None = None) -> None:
    """
    List available backups.

    Args:
        branch: Filter by branch name (None = all branches)
    """
    backups_dir = get_backups_dir()

    if not backups_dir.exists() or not any(backups_dir.iterdir()):
        console.print("\n[yellow]No backups found[/yellow]\n")
        return

    console.print("\n[bold cyan]Available Backups:[/bold cyan]\n")

    # Collect all backups
    backups: list[tuple[str, str, dict]] = []  # (branch, timestamp, metadata)

    for branch_dir in sorted(backups_dir.iterdir()):
        if not branch_dir.is_dir():
            continue

        branch_name = branch_dir.name

        # Filter by branch if specified
        if branch and branch_name != branch:
            continue

        # Find all timestamp directories
        for timestamp_dir in sorted(branch_dir.iterdir(), reverse=True):
            if not timestamp_dir.is_dir():
                continue

            metadata_file = timestamp_dir / "metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file) as f:
                        metadata = json.load(f)
                    backups.append((branch_name, timestamp_dir.name, metadata))
                except (OSError, json.JSONDecodeError):
                    continue

    if not backups:
        console.print(
            f"[yellow]No backups found{' for branch: ' + branch if branch else ''}[/yellow]\n"
        )
        return

    # Group by branch
    from collections import defaultdict

    backups_by_branch: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for branch_name, timestamp, metadata in backups:
        backups_by_branch[branch_name].append((timestamp, metadata))

    # Display backups
    for branch_name, branch_backups in sorted(backups_by_branch.items()):
        console.print(f"[bold green]{branch_name}[/bold green]:")
        for timestamp, metadata in branch_backups:
            backed_up_at = metadata.get("backed_up_at", "unknown")
            has_changes = metadata.get("has_uncommitted_changes", False)
            changes_indicator = (
                " [yellow](with uncommitted changes)[/yellow]" if has_changes else ""
            )
            console.print(f"  • {timestamp} - {backed_up_at}{changes_indicator}")
        console.print()


def restore_worktree(
    branch: str,
    backup_id: str | None = None,
    path: Path | None = None,
) -> None:
    """
    Restore worktree from backup.

    Args:
        branch: Branch name to restore
        backup_id: Timestamp of backup to restore (None = latest)
        path: Custom path for restored worktree (None = default)

    Raises:
        GitError: If restore fails
    """
    backups_dir = get_backups_dir()
    branch_backup_dir = backups_dir / branch

    if not branch_backup_dir.exists():
        raise GitError(f"No backups found for branch '{branch}'")

    # Find backup to restore
    if backup_id:
        backup_dir = branch_backup_dir / backup_id
        if not backup_dir.exists():
            raise GitError(f"Backup '{backup_id}' not found for branch '{branch}'")
    else:
        # Use latest backup
        backups = sorted(
            [d for d in branch_backup_dir.iterdir() if d.is_dir()],
            reverse=True,
        )
        if not backups:
            raise GitError(f"No backups found for branch '{branch}'")
        backup_dir = backups[0]
        backup_id = backup_dir.name

    metadata_file = backup_dir / "metadata.json"
    bundle_file = backup_dir / "bundle.git"

    if not metadata_file.exists() or not bundle_file.exists():
        raise GitError("Invalid backup: missing metadata or bundle file")

    # Load metadata
    try:
        with open(metadata_file) as f:
            metadata = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise GitError(f"Failed to read backup metadata: {e}")

    console.print("\n[bold cyan]Restoring from backup:[/bold cyan]")
    console.print(f"  Branch: [green]{branch}[/green]")
    console.print(f"  Backup ID: [yellow]{backup_id}[/yellow]")
    console.print(f"  Backed up at: {metadata.get('backed_up_at', 'unknown')}\n")

    repo = get_repo_root()

    # Determine worktree path
    if path is None:
        worktree_path = default_worktree_path(repo, branch)
    else:
        worktree_path = path.resolve()

    if worktree_path.exists():
        raise GitError(
            f"Worktree path already exists: {worktree_path}\n"
            f"Remove it first or specify a different path with --path"
        )

    try:
        # Create worktree directory
        worktree_path.parent.mkdir(parents=True, exist_ok=True)

        # Clone from bundle
        console.print(f"[yellow]Restoring worktree to:[/yellow] {worktree_path}")
        git_command("clone", str(bundle_file), str(worktree_path), repo=repo.parent)

        # Checkout the branch
        git_command("checkout", branch, repo=worktree_path, check=False)

        # Restore metadata
        base_branch = metadata.get("base_branch")
        if base_branch:
            set_config(CONFIG_KEY_BASE_BRANCH.format(branch), base_branch, repo=repo)
            set_config(CONFIG_KEY_BASE_PATH.format(branch), str(repo), repo=repo)

        # Restore uncommitted changes if they exist
        # Use backup_dir/stash.patch instead of relying on absolute path from metadata
        # This ensures cross-platform compatibility (Windows temp paths may not persist)
        stash_file = backup_dir / "stash.patch"
        if stash_file.exists():
            console.print("  [dim]Restoring uncommitted changes...[/dim]")
            patch_content = stash_file.read_text()
            # Apply patch
            result = subprocess.run(
                ["git", "apply", "--whitespace=fix"],
                input=patch_content,
                text=True,
                cwd=worktree_path,
                capture_output=True,
            )
            if result.returncode != 0:
                console.print(
                    f"  [yellow]![/yellow] Failed to restore uncommitted changes: {result.stderr}"
                )

        console.print("[bold green]*[/bold green] Restore complete!")
        console.print(f"  Worktree path: {worktree_path}\n")

    except Exception as e:
        # Cleanup on failure
        if worktree_path.exists():
            import shutil

            shutil.rmtree(worktree_path, ignore_errors=True)
        raise GitError(f"Restore failed: {e}")
