"""Helper utilities shared across claude-worktree operations."""

from pathlib import Path

from .constants import CONFIG_KEY_BASE_BRANCH, CONFIG_KEY_BASE_PATH
from .exceptions import GitError
from .git_utils import get_config


def get_worktree_metadata(branch: str, repo: Path) -> tuple[str, Path]:
    """
    Get worktree metadata (base branch and base repository path).

    This helper function retrieves the stored metadata for a worktree,
    including the base branch it was created from and the path to the
    base repository.

    If metadata is missing (e.g., branch created manually without 'cw new'),
    it will attempt to infer:
    - base_path: Main repository path from git worktree list
    - base_branch: Common default branches (main, master, develop) or first worktree branch

    Args:
        branch: Feature branch name
        repo: Worktree repository path

    Returns:
        tuple[str, Path]: (base_branch_name, base_repo_path)

    Raises:
        GitError: If metadata cannot be retrieved or inferred

    Example:
        >>> base_branch, base_path = get_worktree_metadata("fix-auth", Path("/path/to/worktree"))
        >>> print(f"Created from: {base_branch}")
        Created from: main
    """
    from .console import get_console
    from .git_utils import branch_exists, parse_worktrees

    base_branch = get_config(CONFIG_KEY_BASE_BRANCH.format(branch), repo)
    base_path_str = get_config(CONFIG_KEY_BASE_PATH.format(branch), repo)

    # If metadata exists, use it
    if base_branch and base_path_str:
        base_path = Path(base_path_str)
        return base_branch, base_path

    # Metadata missing - try to infer
    console = get_console()
    console.print(f"\n[yellow]! Metadata missing for branch '{branch}'[/yellow]")
    console.print("[dim]Attempting to infer metadata automatically...[/dim]\n")

    # Step 1: Infer base_path (main repository)
    # Find the main repository by getting the first worktree (which is always the main repo)
    inferred_base_path: Path | None = None
    try:
        worktrees = parse_worktrees(repo)
        if worktrees:
            # The first worktree is always the main repository
            inferred_base_path = worktrees[0][1]
    except Exception:
        pass

    if not inferred_base_path:
        raise GitError(
            f"Cannot infer base repository path for branch '{branch}'. "
            f"Please use 'cw new' to create worktrees."
        )

    # Step 2: Infer base_branch
    # Try common default branch names in order: main, master, develop
    inferred_base_branch: str | None = None
    for candidate in ["main", "master", "develop"]:
        if branch_exists(candidate, inferred_base_path):
            inferred_base_branch = candidate
            break

    # If no common branch found, use the branch of the first worktree (main repo)
    if not inferred_base_branch:
        if worktrees and worktrees[0][0] != "(detached)":
            first_branch = worktrees[0][0]
            # Normalize branch name (remove refs/heads/ prefix)
            inferred_base_branch = (
                first_branch[11:] if first_branch.startswith("refs/heads/") else first_branch
            )

    if not inferred_base_branch:
        raise GitError(
            f"Cannot infer base branch for '{branch}'. "
            f"Please specify manually or use 'cw new' to create worktrees."
        )

    console.print(f"  [dim]Inferred base branch: [cyan]{inferred_base_branch}[/cyan][/dim]")
    console.print(f"  [dim]Inferred base path: [blue]{inferred_base_path}[/blue][/dim]")
    console.print("\n[dim]Tip: Use 'cw new' to create worktrees with proper metadata.[/dim]\n")

    return inferred_base_branch, inferred_base_path


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
