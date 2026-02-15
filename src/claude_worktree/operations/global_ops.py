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
from .display import (
    _MIN_TABLE_WIDTH,
    STATUS_COLORS,
    _get_terminal_width,
    format_age,
    get_worktree_status,
)

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

    import os
    import time

    total_repos = 0
    status_counts: dict[str, int] = {}
    # Collect all rows: (repo_name, worktree_id, current_branch, status, age_str, rel_path)
    rows: list[tuple[str, str, str, str, str, str]] = []

    for name, repo_path in sorted(repos, key=lambda x: x[0]):
        if not repo_path.exists():
            console.print(
                f"[yellow]⚠ {name}[/yellow] [dim]({repo_path})[/dim] — "
                "[red]repository not found[/red]"
            )
            continue

        try:
            worktrees = parse_worktrees(repo_path)
        except Exception:
            console.print(
                f"[yellow]⚠ {name}[/yellow] [dim]({repo_path})[/dim] — "
                "[red]failed to read worktrees[/red]"
            )
            continue

        has_feature = False
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
            worktree_id = intended if intended else branch_name

            # Compute age
            age_str = ""
            try:
                if path.exists():
                    mtime = path.stat().st_mtime
                    age_days = (time.time() - mtime) / (24 * 3600)
                    age_str = format_age(age_days)
            except OSError:
                pass

            # Relative path
            try:
                rel_path = os.path.relpath(str(path), repo_path)
            except ValueError:
                rel_path = str(path)

            rows.append((name, worktree_id, branch_name, status, age_str, rel_path))
            status_counts[status] = status_counts.get(status, 0) + 1
            has_feature = True

        if has_feature:
            total_repos += 1

    if not rows:
        console.print(
            "[yellow]No repositories with active worktrees found.[/yellow]\n"
        )
        return

    # Choose layout based on terminal width
    # Global table has an extra REPO column, so needs more space
    term_width = _get_terminal_width()
    if term_width >= _MIN_TABLE_WIDTH + 25:
        _global_print_table(rows)
    else:
        _global_print_compact(rows)

    # Summary footer
    total_worktrees = len(rows)
    summary_parts: list[str] = []
    for status_name in ("clean", "modified", "active", "stale"):
        count = status_counts.get(status_name, 0)
        if count > 0:
            color = STATUS_COLORS.get(status_name, "white")
            summary_parts.append(f"[{color}]{count} {status_name}[/{color}]")

    summary = f"\n{total_repos} repo(s), {total_worktrees} worktree(s)"
    if summary_parts:
        summary += f" — {', '.join(summary_parts)}"
    console.print(summary)
    console.print()


def _global_print_table(
    rows: list[tuple[str, str, str, str, str, str]],
) -> None:
    """Print global worktree rows as a wide table."""
    max_repo_len = max(len(r) for r, _, _, _, _, _ in rows)
    max_wt_len = max(len(wt) for _, wt, _, _, _, _ in rows)
    max_br_len = max(len(br) for _, _, br, _, _, _ in rows)
    repo_col = min(max(max_repo_len + 2, 12), 25)
    wt_col = min(max(max_wt_len + 2, 20), 35)
    br_col = min(max(max_br_len + 2, 20), 35)

    console.print(
        f"{'REPO':<{repo_col}} {'WORKTREE':<{wt_col}} {'CURRENT BRANCH':<{br_col}} "
        f"{'STATUS':<10} {'AGE':<12} PATH"
    )
    console.print("─" * (repo_col + wt_col + br_col + 82))

    for repo_name, worktree_id, current_branch, status, age_str, rel_path in rows:
        color = STATUS_COLORS.get(status, "white")

        if worktree_id != current_branch:
            branch_display = f"[yellow]{current_branch} (⚠️)[/yellow]"
        else:
            branch_display = current_branch

        console.print(
            f"{repo_name:<{repo_col}} {worktree_id:<{wt_col}} {branch_display:<{br_col}} "
            f"[{color}]{status:<10}[/{color}] {age_str:<12} {rel_path}"
        )


def _global_print_compact(
    rows: list[tuple[str, str, str, str, str, str]],
) -> None:
    """Print global worktree rows in compact format for narrow terminals."""
    current_repo = ""
    for repo_name, worktree_id, current_branch, status, age_str, rel_path in rows:
        if repo_name != current_repo:
            if current_repo:
                console.print()  # blank line between repos
            console.print(f"[bold]{repo_name}[/bold]")
            current_repo = repo_name

        color = STATUS_COLORS.get(status, "white")
        age_part = f"  {age_str}" if age_str else ""

        console.print(
            f"  [bold]{worktree_id}[/bold]  [{color}]{status}[/{color}]{age_part}"
        )

        details: list[str] = []
        if worktree_id != current_branch:
            details.append(f"branch: [yellow]{current_branch} (⚠️)[/yellow]")
        details.append(f"path: {rel_path}")
        console.print(f"    {' · '.join(details)}")


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
