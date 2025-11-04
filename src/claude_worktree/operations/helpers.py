"""Helper functions shared across operations modules."""

from pathlib import Path

from ..constants import CONFIG_KEY_BASE_BRANCH, CONFIG_KEY_BASE_PATH
from ..exceptions import GitError, InvalidBranchError, WorktreeNotFoundError
from ..git_utils import (
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

    Args:
        branch: Feature branch name
        repo: Worktree repository path

    Returns:
        tuple[str, Path]: (base_branch_name, base_repo_path)

    Raises:
        GitError: If metadata is missing or invalid

    Example:
        >>> base_branch, base_path = get_worktree_metadata("fix-auth", Path("/path/to/worktree"))
        >>> print(f"Created from: {base_branch}")
        Created from: main
    """
    base_branch = get_config(CONFIG_KEY_BASE_BRANCH.format(branch), repo)
    base_path_str = get_config(CONFIG_KEY_BASE_PATH.format(branch), repo)

    if not base_branch or not base_path_str:
        raise GitError(
            f"Missing metadata for branch '{branch}'. Was this worktree created with 'cw new'?"
        )

    base_path = Path(base_path_str)
    return base_branch, base_path
