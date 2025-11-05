"""Diagnostic operations for claude-worktree."""

import subprocess
from pathlib import Path

from packaging.version import parse

from ..console import get_console
from ..constants import CONFIG_KEY_BASE_BRANCH
from ..git_utils import get_config, get_repo_root, git_command, parse_worktrees

console = get_console()


def doctor() -> None:
    """
    Perform health check on all worktrees.

    Checks:
    - Git version compatibility
    - Worktree accessibility
    - Uncommitted changes
    - Worktrees behind base branch
    - Existing merge conflicts
    - Cleanup recommendations
    """
    from .display import get_worktree_status

    repo = get_repo_root()
    console.print("\n[bold cyan]🏥 claude-worktree Health Check[/bold cyan]\n")

    issues_found = 0
    warnings_found = 0

    # 1. Check Git version
    console.print("[bold]1. Checking Git version...[/bold]")
    try:
        result = subprocess.run(
            ["git", "--version"], capture_output=True, text=True, check=True, timeout=5
        )
        version_output = result.stdout.strip()
        # Extract version number (e.g., "git version 2.39.0" or "git version 2.50.1 (Apple Git-155)")
        # Take the third word which is always the version number
        parts = version_output.split()
        if len(parts) >= 3:
            version_str = parts[2]
        else:
            version_str = parts[-1]
        git_version = parse(version_str)
        min_version = parse("2.31.0")

        if git_version >= min_version:
            console.print(f"   [green]*[/green] Git version {version_str} (minimum: 2.31.0)")
        else:
            console.print(f"   [red]x[/red] Git version {version_str} is too old (minimum: 2.31.0)")
            issues_found += 1
    except Exception as e:
        console.print(f"   [red]x[/red] Could not detect Git version: {e}")
        issues_found += 1

    console.print()

    # 2. Check all worktrees
    console.print("[bold]2. Checking worktree accessibility...[/bold]")
    worktrees: list[tuple[str, Path, str]] = []
    stale_count = 0
    for branch, path in parse_worktrees(repo):
        # Skip main repository
        if path.resolve() == repo.resolve():
            continue
        if branch == "(detached)":
            continue

        branch_name = branch[11:] if branch.startswith("refs/heads/") else branch
        status = get_worktree_status(str(path), repo)
        worktrees.append((branch_name, path, status))

        if status == "stale":
            stale_count += 1
            console.print(f"   [red]x[/red] {branch_name}: Stale (directory missing)")
            issues_found += 1

    if stale_count == 0:
        console.print(f"   [green]*[/green] All {len(worktrees)} worktrees are accessible")
    else:
        console.print(
            f"   [yellow]![/yellow] {stale_count} stale worktree(s) found (use 'cw prune')"
        )

    console.print()

    # 3. Check for uncommitted changes
    console.print("[bold]3. Checking for uncommitted changes...[/bold]")
    dirty_worktrees: list[tuple[str, Path]] = []
    for branch_name, path, status in worktrees:
        if status in ["modified", "active"]:
            # Check if there are actual uncommitted changes
            try:
                diff_result = git_command(
                    "status",
                    "--porcelain",
                    repo=path,
                    capture=True,
                    check=False,
                )
                if diff_result.returncode == 0 and diff_result.stdout.strip():
                    dirty_worktrees.append((branch_name, path))
            except Exception:
                pass

    if dirty_worktrees:
        console.print(
            f"   [yellow]![/yellow] {len(dirty_worktrees)} worktree(s) with uncommitted changes:"
        )
        for branch_name, _path in dirty_worktrees:
            console.print(f"      • {branch_name}")
        warnings_found += 1
    else:
        console.print("   [green]*[/green] No uncommitted changes")

    console.print()

    # 4. Check if worktrees are behind base branch
    console.print("[bold]4. Checking if worktrees are behind base branch...[/bold]")
    behind_worktrees: list[tuple[str, str, str]] = []
    for branch_name, path, status in worktrees:
        if status == "stale":
            continue

        # Get base branch metadata
        base_branch = get_config(CONFIG_KEY_BASE_BRANCH.format(branch_name), repo)
        if not base_branch:
            continue

        try:
            # Fetch to get latest remote refs
            git_command("fetch", "--all", "--prune", repo=path, check=False)

            # Check if branch is behind origin/base
            merge_base_result = git_command(
                "merge-base",
                branch_name,
                f"origin/{base_branch}",
                repo=path,
                capture=True,
                check=False,
            )
            if merge_base_result.returncode != 0:
                continue

            merge_base = merge_base_result.stdout.strip()

            # Get current commit of base branch
            base_commit_result = git_command(
                "rev-parse",
                f"origin/{base_branch}",
                repo=path,
                capture=True,
                check=False,
            )
            if base_commit_result.returncode != 0:
                continue

            base_commit = base_commit_result.stdout.strip()

            # If merge base != base commit, then we're behind
            if merge_base != base_commit:
                # Count commits behind
                behind_count_result = git_command(
                    "rev-list",
                    "--count",
                    f"{branch_name}..origin/{base_branch}",
                    repo=path,
                    capture=True,
                    check=False,
                )
                if behind_count_result.returncode == 0:
                    behind_count = behind_count_result.stdout.strip()
                    behind_worktrees.append((branch_name, base_branch, behind_count))
        except Exception:
            pass

    if behind_worktrees:
        console.print(
            f"   [yellow]![/yellow] {len(behind_worktrees)} worktree(s) behind base branch:"
        )
        for branch_name, base_branch, count in behind_worktrees:
            console.print(f"      • {branch_name}: {count} commit(s) behind {base_branch}")
        console.print("   [dim]Tip: Use 'cw sync --all' to update all worktrees[/dim]")
        warnings_found += 1
    else:
        console.print("   [green]*[/green] All worktrees are up-to-date with base")

    console.print()

    # 5. Check for existing merge conflicts
    console.print("[bold]5. Checking for merge conflicts...[/bold]")
    conflicted_worktrees: list[tuple[str, list[str]]] = []
    for branch_name, path, status in worktrees:
        if status == "stale":
            continue

        try:
            # Check for unmerged files (conflicts)
            conflicts_result = git_command(
                "diff",
                "--name-only",
                "--diff-filter=U",
                repo=path,
                capture=True,
                check=False,
            )
            if conflicts_result.returncode == 0 and conflicts_result.stdout.strip():
                conflicted_files = conflicts_result.stdout.strip().splitlines()
                conflicted_worktrees.append((branch_name, conflicted_files))
        except Exception:
            pass

    if conflicted_worktrees:
        console.print(
            f"   [red]x[/red] {len(conflicted_worktrees)} worktree(s) with merge conflicts:"
        )
        for branch_name, files in conflicted_worktrees:
            console.print(f"      • {branch_name}: {len(files)} conflicted file(s)")
        console.print("   [dim]Tip: Use 'cw finish --ai-merge' for AI-assisted resolution[/dim]")
        issues_found += 1
    else:
        console.print("   [green]*[/green] No merge conflicts detected")

    console.print()

    # Summary
    console.print("[bold cyan]Summary:[/bold cyan]")
    if issues_found == 0 and warnings_found == 0:
        console.print("[bold green]* Everything looks healthy![/bold green]\n")
    else:
        if issues_found > 0:
            console.print(f"[bold red]x {issues_found} issue(s) found[/bold red]")
        if warnings_found > 0:
            console.print(f"[bold yellow]! {warnings_found} warning(s) found[/bold yellow]")
        console.print()

    # Recommendations
    if stale_count > 0:
        console.print("[bold]Recommendations:[/bold]")
        console.print("  • Run [cyan]cw prune[/cyan] to clean up stale worktrees")
    if behind_worktrees:
        if not stale_count:
            console.print("[bold]Recommendations:[/bold]")
        console.print("  • Run [cyan]cw sync --all[/cyan] to update all worktrees")
    if conflicted_worktrees:
        if not stale_count and not behind_worktrees:
            console.print("[bold]Recommendations:[/bold]")
        console.print("  • Resolve conflicts in conflicted worktrees")
        console.print("  • Use [cyan]cw finish --ai-merge[/cyan] for AI assistance")

    if stale_count > 0 or behind_worktrees or conflicted_worktrees:
        console.print()
