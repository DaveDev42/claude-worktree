"""Constants and default values for claude-worktree."""

from pathlib import Path

# Git config keys for metadata storage
CONFIG_KEY_BASE_BRANCH = "branch.{}.worktreeBase"
CONFIG_KEY_BASE_PATH = "worktree.{}.basePath"

# Default Claude CLI command
DEFAULT_CLAUDE_COMMAND = "claude --dangerously-skip-permissions"

# Minimum required Git version
MIN_GIT_VERSION = "2.31"


def default_worktree_path(repo_path: Path, branch_name: str) -> Path:
    """
    Generate default worktree path based on new naming convention.

    New format: ../<repo>-<branch>
    Example: /Users/dave/myproject -> /Users/dave/myproject-fix-auth

    Args:
        repo_path: Path to the repository root
        branch_name: Name of the feature branch

    Returns:
        Default worktree path
    """
    repo_path = repo_path.resolve()
    return repo_path.parent / f"{repo_path.name}-{branch_name}"
