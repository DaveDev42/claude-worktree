"""Display and information operations for claude-worktree."""

import os
import time
from pathlib import Path

from ..console import get_console
from ..constants import CONFIG_KEY_BASE_BRANCH, CONFIG_KEY_BASE_PATH
from ..exceptions import GitError, InvalidBranchError
from ..git_utils import (
    branch_exists,
    get_config,
    get_current_branch,
    get_repo_root,
    git_command,
    parse_worktrees,
)

console = get_console()


def get_worktree_status(path: str, repo: Path) -> str:
    """
    Determine the status of a worktree.

    Args:
        path: Absolute path to the worktree directory
        repo: Repository root path

    Returns:
        Status string: "stale", "active", "modified", or "clean"
    """
    path_obj = Path(path)

    # Check if directory exists
    if not path_obj.exists():
        return "stale"

    # Check if currently in this worktree
    cwd = str(Path.cwd())
    if cwd.startswith(path):
        return "active"

    # Check for uncommitted changes
    try:
        result = git_command("status", "--porcelain", repo=path_obj, capture=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            return "modified"
    except Exception:
        # If we can't check status, assume clean
        pass

    return "clean"


def list_worktrees() -> None:
    """List all worktrees for the current repository."""
    repo = get_repo_root()
    worktrees = parse_worktrees(repo)

    console.print(f"\n[bold cyan]Worktrees for repository:[/bold cyan] {repo}\n")

    # Calculate maximum branch name length for dynamic column width
    max_branch_len = max((len(branch) for branch, _ in worktrees), default=20)
    # Cap at reasonable maximum but allow for long names
    col_width = min(max(max_branch_len + 2, 35), 60)

    console.print(f"{'BRANCH':<{col_width}} {'STATUS':<10} PATH")
    console.print("-" * (col_width + 50))

    # Status color mapping
    status_colors = {
        "active": "bold green",
        "clean": "green",
        "modified": "yellow",
        "stale": "red",
    }

    for branch, path in worktrees:
        status = get_worktree_status(str(path), repo)
        rel_path = os.path.relpath(str(path), repo)
        color = status_colors.get(status, "white")
        console.print(f"{branch:<{col_width}} [{color}]{status:<10}[/{color}] {rel_path}")

    console.print()


def show_status() -> None:
    """Show status of current worktree and list all worktrees."""
    repo = get_repo_root()

    try:
        branch = get_current_branch(Path.cwd())
        base = get_config(CONFIG_KEY_BASE_BRANCH.format(branch), repo)
        base_path = get_config(CONFIG_KEY_BASE_PATH.format(branch), repo)

        console.print("\n[bold cyan]Current worktree:[/bold cyan]")
        console.print(f"  Feature:  [green]{branch}[/green]")
        console.print(f"  Base:     [green]{base or 'N/A'}[/green]")
        console.print(f"  Base path: [blue]{base_path or 'N/A'}[/blue]\n")
    except (InvalidBranchError, GitError):
        console.print(
            "\n[yellow]Current directory is not a feature worktree "
            "or is the main repository.[/yellow]\n"
        )

    list_worktrees()


def show_tree() -> None:
    """
    Display worktree hierarchy in a visual tree format.

    Shows:
    - Base repository at the root
    - All feature worktrees as branches
    - Status indicators for each worktree
    - Current/active worktree highlighting
    """
    repo = get_repo_root()
    worktrees = parse_worktrees(repo)
    cwd = Path.cwd()

    console.print(f"\n[bold cyan]{repo.name}/[/bold cyan] (base repository)")
    console.print(f"[dim]{repo}[/dim]\n")

    # Separate main repo from feature worktrees
    feature_worktrees = []
    for branch, path in worktrees:
        # Skip main repository
        if path.resolve() == repo.resolve():
            continue
        # Skip detached worktrees
        if branch == "(detached)":
            continue

        branch_name = branch[11:] if branch.startswith("refs/heads/") else branch
        status = get_worktree_status(str(path), repo)
        is_current = str(cwd).startswith(str(path))
        feature_worktrees.append((branch_name, path, status, is_current))

    if not feature_worktrees:
        console.print("[dim]  (no feature worktrees)[/dim]\n")
        return

    # Status icons
    status_icons = {
        "active": "●",  # current worktree
        "clean": "○",  # clean
        "modified": "◉",  # has changes
        "stale": "x",  # directory missing
    }

    # Status colors
    status_colors = {
        "active": "bold green",
        "clean": "green",
        "modified": "yellow",
        "stale": "red",
    }

    # Sort by branch name for consistent display
    feature_worktrees.sort(key=lambda x: x[0])

    # Draw tree
    for i, (branch_name, path, status, is_current) in enumerate(feature_worktrees):
        is_last = i == len(feature_worktrees) - 1
        prefix = "└── " if is_last else "├── "

        # Status icon and color
        icon = status_icons.get(status, "○")
        color = status_colors.get(status, "white")

        # Highlight current worktree
        if is_current:
            branch_display = f"[bold {color}]★ {branch_name}[/bold {color}]"
        else:
            branch_display = f"[{color}]{branch_name}[/{color}]"

        # Show branch with status
        console.print(f"{prefix}[{color}]{icon}[/{color}] {branch_display}")

        # Show path (relative if possible, absolute otherwise)
        try:
            rel_path = path.relative_to(repo.parent)
            path_display = f"../{rel_path}"
        except ValueError:
            path_display = str(path)

        continuation = "    " if is_last else "│   "
        console.print(f"{continuation}[dim]{path_display}[/dim]")

    # Legend
    console.print("\n[bold]Legend:[/bold]")
    console.print(f"  [{status_colors['active']}]●[/{status_colors['active']}] active (current)")
    console.print(f"  [{status_colors['clean']}]○[/{status_colors['clean']}] clean")
    console.print(f"  [{status_colors['modified']}]◉[/{status_colors['modified']}] modified")
    console.print(f"  [{status_colors['stale']}]x[/{status_colors['stale']}] stale")
    console.print("  [bold green]★[/bold green] currently active worktree\n")


def show_stats() -> None:
    """
    Display usage analytics for worktrees.

    Shows:
    - Total worktrees count
    - Active development time per worktree
    - Worktree age statistics
    - Status distribution
    """
    repo = get_repo_root()
    worktrees = parse_worktrees(repo)

    # Collect worktree data
    worktree_data: list[tuple[str, Path, str, float, int]] = []
    for branch, path in worktrees:
        # Skip main repository
        if path.resolve() == repo.resolve():
            continue
        # Skip detached worktrees
        if branch == "(detached)":
            continue

        branch_name = branch[11:] if branch.startswith("refs/heads/") else branch
        status = get_worktree_status(str(path), repo)

        # Get creation time (directory mtime)
        try:
            if path.exists():
                creation_time = path.stat().st_mtime
                age_days = (time.time() - creation_time) / (24 * 3600)

                # Count commits in this worktree
                try:
                    commit_count_result = git_command(
                        "rev-list", "--count", branch_name, repo=path, capture=True, check=False
                    )
                    commit_count = (
                        int(commit_count_result.stdout.strip())
                        if commit_count_result.returncode == 0
                        else 0
                    )
                except Exception:
                    commit_count = 0
            else:
                creation_time = 0.0
                age_days = 0.0
                commit_count = 0

            worktree_data.append((branch_name, path, status, age_days, commit_count))
        except Exception:
            continue

    if not worktree_data:
        console.print("\n[yellow]No feature worktrees found[/yellow]\n")
        return

    console.print("\n[bold cyan]📊 Worktree Statistics[/bold cyan]\n")

    # Overall statistics
    total_count = len(worktree_data)
    status_counts = {"clean": 0, "modified": 0, "active": 0, "stale": 0}
    for _, _, status, _, _ in worktree_data:
        status_counts[status] = status_counts.get(status, 0) + 1

    console.print("[bold]Overview:[/bold]")
    console.print(f"  Total worktrees: {total_count}")
    console.print(
        f"  Status: [green]{status_counts.get('clean', 0)} clean[/green], "
        f"[yellow]{status_counts.get('modified', 0)} modified[/yellow], "
        f"[bold green]{status_counts.get('active', 0)} active[/bold green], "
        f"[red]{status_counts.get('stale', 0)} stale[/red]"
    )
    console.print()

    # Age statistics
    ages = [age for _, _, _, age, _ in worktree_data if age > 0]
    if ages:
        avg_age = sum(ages) / len(ages)
        oldest_age = max(ages)
        newest_age = min(ages)

        console.print("[bold]Age Statistics:[/bold]")
        console.print(f"  Average age: {avg_age:.1f} days")
        console.print(f"  Oldest: {oldest_age:.1f} days")
        console.print(f"  Newest: {newest_age:.1f} days")
        console.print()

    # Commit statistics
    commits = [count for _, _, _, _, count in worktree_data if count > 0]
    if commits:
        total_commits = sum(commits)
        avg_commits = total_commits / len(commits)
        max_commits = max(commits)

        console.print("[bold]Commit Statistics:[/bold]")
        console.print(f"  Total commits across all worktrees: {total_commits}")
        console.print(f"  Average commits per worktree: {avg_commits:.1f}")
        console.print(f"  Most commits in a worktree: {max_commits}")
        console.print()

    # Top worktrees by age
    console.print("[bold]Oldest Worktrees:[/bold]")
    sorted_by_age = sorted(worktree_data, key=lambda x: x[3], reverse=True)[:5]
    for branch_name, _path, status, age_days, _ in sorted_by_age:
        if age_days > 0:
            status_icon = {"clean": "○", "modified": "◉", "active": "●", "stale": "x"}.get(
                status, "○"
            )
            status_color = {
                "clean": "green",
                "modified": "yellow",
                "active": "bold green",
                "stale": "red",
            }.get(status, "white")
            age_str = format_age(age_days)
            console.print(
                f"  [{status_color}]{status_icon}[/{status_color}] {branch_name:<30} {age_str}"
            )
    console.print()

    # Most active worktrees by commit count
    console.print("[bold]Most Active Worktrees (by commits):[/bold]")
    sorted_by_commits = sorted(worktree_data, key=lambda x: x[4], reverse=True)[:5]
    for branch_name, _path, status, _age_days, commit_count in sorted_by_commits:
        if commit_count > 0:
            status_icon = {"clean": "○", "modified": "◉", "active": "●", "stale": "x"}.get(
                status, "○"
            )
            status_color = {
                "clean": "green",
                "modified": "yellow",
                "active": "bold green",
                "stale": "red",
            }.get(status, "white")
            console.print(
                f"  [{status_color}]{status_icon}[/{status_color}] {branch_name:<30} {commit_count} commits"
            )
    console.print()


def format_age(age_days: float) -> str:
    """Format age in days to human-readable string."""
    if age_days < 1:
        hours = int(age_days * 24)
        return f"{hours}h ago" if hours > 0 else "just now"
    elif age_days < 7:
        return f"{int(age_days)}d ago"
    elif age_days < 30:
        weeks = int(age_days / 7)
        return f"{weeks}w ago"
    elif age_days < 365:
        months = int(age_days / 30)
        return f"{months}mo ago"
    else:
        years = int(age_days / 365)
        return f"{years}y ago"


def diff_worktrees(branch1: str, branch2: str, summary: bool = False, files: bool = False) -> None:
    """
    Compare two worktrees or branches.

    Args:
        branch1: First branch name
        branch2: Second branch name
        summary: Show diff statistics only
        files: Show changed files only

    Raises:
        InvalidBranchError: If branches don't exist
        GitError: If git operations fail
    """
    repo = get_repo_root()

    # Verify both branches exist
    if not branch_exists(branch1, repo):
        raise InvalidBranchError(f"Branch '{branch1}' not found")
    if not branch_exists(branch2, repo):
        raise InvalidBranchError(f"Branch '{branch2}' not found")

    console.print("\n[bold cyan]Comparing branches:[/bold cyan]")
    console.print(f"  {branch1} [yellow]...[/yellow] {branch2}\n")

    # Choose diff format based on flags
    if files:
        # Show only changed files
        result = git_command(
            "diff",
            "--name-status",
            branch1,
            branch2,
            repo=repo,
            capture=True,
        )
        console.print("[bold]Changed files:[/bold]\n")
        if result.stdout.strip():
            for line in result.stdout.strip().splitlines():
                # Format: M  file.txt (Modified)
                # Format: A  file.txt (Added)
                # Format: D  file.txt (Deleted)
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    status_char, filename = parts
                    status_color = {
                        "M": "yellow",
                        "A": "green",
                        "D": "red",
                        "R": "cyan",  # Renamed
                        "C": "cyan",  # Copied
                    }.get(status_char[0], "white")
                    status_name = {
                        "M": "Modified",
                        "A": "Added",
                        "D": "Deleted",
                        "R": "Renamed",
                        "C": "Copied",
                    }.get(status_char[0], "Changed")
                    console.print(
                        f"  [{status_color}]{status_char}[/{status_color}]  {filename} ({status_name})"
                    )
        else:
            console.print("  [dim]No differences found[/dim]")
    elif summary:
        # Show diff statistics
        result = git_command(
            "diff",
            "--stat",
            branch1,
            branch2,
            repo=repo,
            capture=True,
        )
        console.print("[bold]Diff summary:[/bold]\n")
        if result.stdout.strip():
            console.print(result.stdout)
        else:
            console.print("  [dim]No differences found[/dim]")
    else:
        # Show full diff
        result = git_command(
            "diff",
            branch1,
            branch2,
            repo=repo,
            capture=True,
        )
        if result.stdout.strip():
            console.print(result.stdout)
        else:
            console.print("[dim]No differences found[/dim]\n")
