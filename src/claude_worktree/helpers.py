"""Helper utilities shared across claude-worktree operations."""

from pathlib import Path

from .constants import CONFIG_KEY_BASE_BRANCH, CONFIG_KEY_BASE_PATH
from .exceptions import GitError, InvalidBranchError, WorktreeNotFoundError
from .git_utils import (
    find_worktree_by_branch,
    get_config,
    get_current_branch,
    get_repo_root,
    normalize_branch_name,
)


def resolve_worktree_target(target: str | None) -> tuple[Path, str, Path]:
    """
    Resolve worktree target (branch name or None) to (worktree_path, branch_name, worktree_repo).

    This is a helper function that encapsulates the common pattern used across multiple
    commands to locate and identify a worktree based on a branch name or current directory.

    Args:
        target: Branch name or None (uses current directory if None)

    Returns:
        tuple[Path, str, Path]: (worktree_path, branch_name, worktree_repo)
            - worktree_path: Path to the worktree directory
            - branch_name: Simple branch name (without refs/heads/ prefix)
            - worktree_repo: Git repository root of the worktree

    Raises:
        WorktreeNotFoundError: If worktree not found for specified branch
        InvalidBranchError: If current branch cannot be determined
        GitError: If not in a git repository
    """
    if target:
        # Target branch specified - find its worktree path
        repo = get_repo_root()
        worktree_path_result = find_worktree_by_branch(repo, target)
        if not worktree_path_result:
            worktree_path_result = find_worktree_by_branch(repo, f"refs/heads/{target}")
        if not worktree_path_result:
            raise WorktreeNotFoundError(
                f"No worktree found for branch '{target}'. "
                f"Use 'cw list' to see available worktrees."
            )
        worktree_path = worktree_path_result
        # Normalize branch name: remove refs/heads/ prefix if present
        branch_name = normalize_branch_name(target)
        # Get repo root from the worktree we found
        worktree_repo = get_repo_root(worktree_path)
    else:
        # No target specified - use current directory
        worktree_path = Path.cwd()
        try:
            branch_name = get_current_branch(worktree_path)
        except InvalidBranchError:
            raise InvalidBranchError("Cannot determine current branch")
        # Get repo root from current directory
        worktree_repo = get_repo_root()

    return worktree_path, branch_name, worktree_repo


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
