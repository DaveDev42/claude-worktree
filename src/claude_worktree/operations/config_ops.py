"""Configuration operations for claude-worktree."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..console import get_console
from ..constants import CONFIG_KEY_BASE_BRANCH, CONFIG_KEY_BASE_PATH
from ..exceptions import GitError, InvalidBranchError, RebaseError
from ..git_utils import (
    branch_exists,
    get_config,
    get_repo_root,
    git_command,
    parse_worktrees,
    set_config,
)

console = get_console()


def change_base_branch(
    new_base: str,
    target: str | None = None,
    interactive: bool = False,
    dry_run: bool = False,
) -> None:
    """
    Change the base branch for a worktree and rebase onto it.

    Args:
        new_base: New base branch name
        target: Branch name of worktree (optional, defaults to current directory)
        interactive: Use interactive rebase
        dry_run: Preview changes without executing

    Raises:
        WorktreeNotFoundError: If worktree not found
        InvalidBranchError: If base branch is invalid
        RebaseError: If rebase fails
        GitError: If git operations fail
    """
    from .helpers import resolve_worktree_target

    # Resolve worktree target to (path, branch, repo)
    worktree_path, feature_branch, repo = resolve_worktree_target(target)

    # Get current base branch metadata
    current_base = get_config(CONFIG_KEY_BASE_BRANCH.format(feature_branch), repo)
    if not current_base:
        raise GitError(
            f"No base branch metadata found for '{feature_branch}'. "
            "Was this worktree created with 'cw new'?"
        )

    # Verify new base branch exists
    if not branch_exists(new_base, repo):
        raise InvalidBranchError(f"Base branch '{new_base}' not found")

    console.print("\n[bold cyan]Changing base branch:[/bold cyan]")
    console.print(f"  Worktree:    [green]{feature_branch}[/green]")
    console.print(f"  Current base: [yellow]{current_base}[/yellow]")
    console.print(f"  New base:     [green]{new_base}[/green]")
    console.print(f"  Path:         [blue]{worktree_path}[/blue]\n")

    # Dry-run mode: preview operations without executing
    if dry_run:
        console.print("[bold yellow]DRY RUN MODE - No changes will be made[/bold yellow]\n")
        console.print("[bold]The following operations would be performed:[/bold]\n")
        console.print("  1. [cyan]Fetch[/cyan] updates from remote")
        console.print(f"  2. [cyan]Rebase[/cyan] {feature_branch} onto {new_base}")
        console.print(
            f"  3. [cyan]Update[/cyan] base branch metadata: {current_base} -> {new_base}"
        )
        console.print("\n[dim]Run without --dry-run to execute these operations.[/dim]\n")
        return

    # Fetch from remote
    console.print("[yellow]Fetching updates from remote...[/yellow]")
    fetch_result = git_command("fetch", "--all", "--prune", repo=repo, check=False)

    # Determine rebase target (prefer origin/new_base if available)
    rebase_target = new_base
    if fetch_result.returncode == 0:
        # Check if origin/new_base exists
        check_result = git_command(
            "rev-parse",
            "--verify",
            f"origin/{new_base}",
            repo=worktree_path,
            check=False,
            capture=True,
        )
        if check_result.returncode == 0:
            rebase_target = f"origin/{new_base}"

    console.print(f"[yellow]Rebasing {feature_branch} onto {rebase_target}...[/yellow]")

    # Build rebase command
    rebase_args = ["rebase"]
    if interactive:
        rebase_args.append("--interactive")
    rebase_args.append(rebase_target)

    try:
        git_command(*rebase_args, repo=worktree_path)
    except GitError:
        # Rebase failed - check if there are conflicts
        conflicts_result = git_command(
            "diff", "--name-only", "--diff-filter=U", repo=worktree_path, capture=True, check=False
        )
        conflicted_files = (
            conflicts_result.stdout.strip().splitlines() if conflicts_result.returncode == 0 else []
        )

        # Abort the rebase
        git_command("rebase", "--abort", repo=worktree_path, check=False)
        error_msg = f"Rebase failed. Please resolve conflicts manually:\n  cd {worktree_path}\n  git rebase {rebase_target}"
        if conflicted_files:
            error_msg += f"\n\nConflicted files ({len(conflicted_files)}):"
            for file in conflicted_files:
                error_msg += f"\n  • {file}"
            error_msg += (
                "\n\nAfter resolving conflicts, run 'cw change-base' again to update metadata."
            )
        raise RebaseError(error_msg)

    console.print("[bold green]*[/bold green] Rebase successful\n")

    # Update base branch metadata
    console.print("[yellow]Updating base branch metadata...[/yellow]")
    set_config(CONFIG_KEY_BASE_BRANCH.format(feature_branch), new_base, repo=repo)
    console.print("[bold green]*[/bold green] Base branch metadata updated\n")

    console.print(f"[bold green]* Base branch changed to '{new_base}'![/bold green]\n")


def export_config(output_file: Path | None = None) -> None:
    """
    Export worktree configuration and metadata to a file.

    Args:
        output_file: Path to export file (default: cw-export-<timestamp>.json)

    Raises:
        GitError: If git operations fail
    """
    from ..config import load_config
    from .display import get_worktree_status

    repo = get_repo_root()

    # Collect export data
    export_data: dict[str, Any] = {
        "export_version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "repository": str(repo),
        "config": load_config(),
        "worktrees": [],
    }

    # Collect worktree metadata
    for branch, path in parse_worktrees(repo):
        # Skip main repository
        if path.resolve() == repo.resolve():
            continue
        # Skip detached worktrees
        if branch == "(detached)":
            continue

        branch_name = branch[11:] if branch.startswith("refs/heads/") else branch

        # Get metadata for this worktree
        base_branch = get_config(CONFIG_KEY_BASE_BRANCH.format(branch_name), repo)
        base_path = get_config(CONFIG_KEY_BASE_PATH.format(branch_name), repo)

        worktree_info = {
            "branch": branch_name,
            "base_branch": base_branch,
            "base_path": base_path,
            "path": str(path),
            "status": get_worktree_status(str(path), repo),
        }

        export_data["worktrees"].append(worktree_info)

    # Determine output file
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_file = Path(f"cw-export-{timestamp}.json")

    # Write export file
    console.print(f"\n[yellow]Exporting configuration to:[/yellow] {output_file}")
    try:
        with open(output_file, "w") as f:
            json.dump(export_data, f, indent=2)
        console.print("[bold green]*[/bold green] Export complete!\n")
        console.print("[bold]Exported:[/bold]")
        console.print(f"  • {len(export_data['worktrees'])} worktree(s)")
        console.print("  • Configuration settings")
        console.print(
            "\n[dim]Transfer this file to another machine and use 'cw import' to restore.[/dim]\n"
        )
    except OSError as e:
        raise GitError(f"Failed to write export file: {e}")


def import_config(import_file: Path, apply: bool = False) -> None:
    """
    Import worktree configuration and metadata from a file.

    Args:
        import_file: Path to import file
        apply: Apply imported configuration (default: preview only)

    Raises:
        GitError: If import fails
    """
    from ..config import save_config

    if not import_file.exists():
        raise GitError(f"Import file not found: {import_file}")

    # Load import data
    console.print(f"\n[yellow]Loading import file:[/yellow] {import_file}\n")
    try:
        with open(import_file) as f:
            import_data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise GitError(f"Failed to read import file: {e}")

    # Validate format
    if "export_version" not in import_data:
        raise GitError("Invalid export file format")

    # Show import preview
    console.print("[bold cyan]Import Preview:[/bold cyan]\n")
    console.print(f"[bold]Exported from:[/bold] {import_data.get('repository', 'unknown')}")
    console.print(f"[bold]Exported at:[/bold] {import_data.get('exported_at', 'unknown')}")
    console.print(f"[bold]Worktrees:[/bold] {len(import_data.get('worktrees', []))}\n")

    if import_data.get("worktrees"):
        console.print("[bold]Worktrees to import:[/bold]")
        for wt in import_data["worktrees"]:
            console.print(f"  • {wt.get('branch', 'unknown')}")
            console.print(f"    Base: {wt.get('base_branch', 'unknown')}")
            console.print(f"    Original path: {wt.get('path', 'unknown')}")
            console.print()

    if not apply:
        console.print(
            "[bold yellow]Preview mode:[/bold yellow] No changes made. "
            "Use --apply to import configuration.\n"
        )
        return

    # Apply import
    console.print("[bold yellow]Applying import...[/bold yellow]\n")

    repo = get_repo_root()
    imported_count = 0

    # Import global configuration
    if "config" in import_data and import_data["config"]:
        console.print("[yellow]Importing global configuration...[/yellow]")
        try:
            save_config(import_data["config"])
            console.print("[bold green]*[/bold green] Configuration imported\n")
        except Exception as e:
            console.print(f"[yellow]![/yellow] Configuration import failed: {e}\n")

    # Import worktree metadata
    console.print("[yellow]Importing worktree metadata...[/yellow]\n")
    for wt in import_data.get("worktrees", []):
        branch = wt.get("branch")
        base_branch = wt.get("base_branch")

        if not branch or not base_branch:
            console.print("[yellow]![/yellow] Skipping invalid worktree entry\n")
            continue

        # Check if branch exists locally
        if not branch_exists(branch, repo):
            console.print(
                f"[yellow]![/yellow] Branch '{branch}' not found locally. "
                f"Create it with 'cw new {branch} --base {base_branch}'"
            )
            continue

        # Set metadata for this branch
        try:
            set_config(CONFIG_KEY_BASE_BRANCH.format(branch), base_branch, repo=repo)
            set_config(CONFIG_KEY_BASE_PATH.format(branch), str(repo), repo=repo)
            console.print(f"[bold green]*[/bold green] Imported metadata for: {branch}")
            imported_count += 1
        except Exception as e:
            console.print(f"[yellow]![/yellow] Failed to import {branch}: {e}")

    console.print(
        f"\n[bold green]* Import complete! Imported {imported_count} worktree(s)[/bold green]\n"
    )
    console.print(
        "[dim]Note: This only imports metadata. "
        "Create actual worktrees with 'cw new' if they don't exist.[/dim]\n"
    )
