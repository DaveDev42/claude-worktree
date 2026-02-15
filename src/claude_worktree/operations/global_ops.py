"""Global worktree management operations.

Business logic for cross-repository worktree commands (`cw -g`).
"""

from pathlib import Path

from ..console import get_console
from ..constants import CONFIG_KEY_INTENDED_BRANCH
from ..git_utils import get_config, normalize_branch_name, parse_worktrees
from ..registry import (
    get_all_registered_repos,
    prune_registry,
    register_repo,
    scan_for_repos,
)
from .display import STATUS_COLORS, format_age, get_worktree_status

console = get_console()


def global_list_worktrees() -> None:
    """List worktrees across all registered repositories."""
    # Auto-prune stale entries before listing
    removed = prune_registry()
    if removed:
        console.print(f"\n[dim]Auto-pruned {len(removed)} stale registry entry(s)[/dim]")

    repos = get_all_registered_repos()

    if not repos:
        console.print(
            "\n[yellow]No repositories registered.[/yellow]\n"
            "Use [cyan]cw -g scan[/cyan] to discover repositories,\n"
            "or run [cyan]cw new[/cyan] in a repository to auto-register it.\n"
        )
        return

    console.print("\n[bold cyan]Global Worktree Overview[/bold cyan]\n")

    total_worktrees = 0
    total_repos = 0
    status_counts: dict[str, int] = {}

    for name, repo_path in sorted(repos, key=lambda x: x[0]):
        if not repo_path.exists():
            console.print(
                f"[bold]{name}[/bold] [dim]({repo_path})[/dim]"
            )
            console.print("  [red]Repository not found[/red]\n")
            continue

        try:
            worktrees = parse_worktrees(repo_path)
        except Exception:
            console.print(
                f"[bold]{name}[/bold] [dim]({repo_path})[/dim]"
            )
            console.print("  [red]Failed to read worktrees[/red]\n")
            continue

        # Filter to feature worktrees only
        feature_worktrees: list[tuple[str, str, Path, str]] = []
        for branch, path in worktrees:
            if path.resolve() == repo_path.resolve():
                continue
            if branch == "(detached)":
                continue

            branch_name = normalize_branch_name(branch)
            status = get_worktree_status(str(path), repo_path)

            # Check intended branch for mismatch detection
            intended = get_config(
                CONFIG_KEY_INTENDED_BRANCH.format(branch_name), repo_path
            )
            display_name = intended if intended else branch_name
            feature_worktrees.append((display_name, branch_name, path, status))

            # Update status counts
            status_counts[status] = status_counts.get(status, 0) + 1
            total_worktrees += 1

        if not feature_worktrees:
            # Only show repos that have feature worktrees
            continue

        total_repos += 1

        console.print(
            f"[bold]{name}[/bold] [dim]({repo_path})[/dim]"
        )

        import os
        import time

        for display_name, branch_name, path, status in sorted(
            feature_worktrees, key=lambda x: x[0]
        ):
            color = STATUS_COLORS.get(status, "white")

            # Mismatch indicator
            mismatch = ""
            if display_name != branch_name:
                mismatch = " (⚠️)"

            # Get age
            age_str = ""
            try:
                if path.exists():
                    mtime = path.stat().st_mtime
                    age_days = (time.time() - mtime) / (24 * 3600)
                    age_str = f" ({format_age(age_days)})"
            except OSError:
                pass

            # Relative path
            try:
                rel_path = os.path.relpath(str(path), repo_path)
            except ValueError:
                rel_path = str(path)

            console.print(
                f"  [{color}]{status:<10}[/{color}] "
                f"{display_name}{mismatch}{age_str} [dim]{rel_path}[/dim]"
            )

        console.print()

    # Summary
    if total_worktrees > 0:
        console.print("[bold]Summary:[/bold]")
        console.print(
            f"  {total_repos} repo(s), {total_worktrees} worktree(s)"
        )

        parts: list[str] = []
        for status_name in ("clean", "modified", "active", "stale"):
            count = status_counts.get(status_name, 0)
            if count > 0:
                color = STATUS_COLORS.get(status_name, "white")
                parts.append(f"[{color}]{count} {status_name}[/{color}]")

        if parts:
            console.print(f"  Status: {', '.join(parts)}")

        console.print()
    elif total_repos == 0:
        console.print(
            "[yellow]No repositories with active worktrees found.[/yellow]\n"
        )


def global_scan(base_dir: Path | None = None) -> None:
    """Scan filesystem for repositories with worktrees and register them.

    Args:
        base_dir: Directory to scan from. Defaults to home directory.
    """
    scan_dir = base_dir or Path.home()
    console.print(
        f"\n[bold cyan]Scanning for repositories...[/bold cyan]\n"
        f"  Directory: [blue]{scan_dir}[/blue]\n"
    )

    found = scan_for_repos(base_dir=base_dir)

    if not found:
        console.print("[yellow]No repositories with worktrees found.[/yellow]\n")
        return

    console.print(f"[bold green]*[/bold green] Found {len(found)} repository(s):\n")

    for repo_path in sorted(found):
        console.print(f"  [green]+[/green] {repo_path.name} [dim]({repo_path})[/dim]")
        register_repo(repo_path)

    console.print(
        f"\n[bold green]*[/bold green] Registered {len(found)} repository(s)\n"
        f"Use [cyan]cw -g list[/cyan] to see all worktrees.\n"
    )


def global_prune() -> None:
    """Remove stale entries from the global registry."""
    console.print("\n[bold cyan]Pruning registry...[/bold cyan]\n")

    removed = prune_registry()

    if not removed:
        console.print("[bold green]*[/bold green] Registry is clean, nothing to prune.\n")
        return

    console.print(f"[bold green]*[/bold green] Removed {len(removed)} stale entry(s):\n")
    for path in removed:
        console.print(f"  [red]-[/red] {path}")

    console.print()
