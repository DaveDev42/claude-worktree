"""Constants and default values for claude-worktree."""

import re
from pathlib import Path

# Git config keys for metadata storage
CONFIG_KEY_BASE_BRANCH = "branch.{}.worktreeBase"
CONFIG_KEY_BASE_PATH = "worktree.{}.basePath"

# Default Claude CLI command
DEFAULT_CLAUDE_COMMAND = "claude --dangerously-skip-permissions"

# Minimum required Git version
MIN_GIT_VERSION = "2.31"


def sanitize_branch_name(branch_name: str) -> str:
    """
    Convert branch name to safe directory name.

    Handles branch names with slashes (feat/auth), special characters,
    and other filesystem-unsafe characters.

    Strategy:
    1. Replace forward slashes with hyphens (feat/auth -> feat-auth)
    2. Replace other unsafe characters with hyphens
    3. Collapse multiple consecutive hyphens
    4. Strip leading/trailing hyphens
    5. Ensure result is not empty

    Examples:
        feat/auth -> feat-auth
        bugfix/issue-123 -> bugfix-issue-123
        feature/user@login -> feature-user-login
        hotfix/v2.0 -> hotfix-v2.0

    Args:
        branch_name: Git branch name

    Returns:
        Sanitized directory-safe name
    """
    # Characters that are unsafe for directory names across platforms
    # Windows: < > : " / \ | ? *
    # Unix: / (and null byte)
    # Shell-problematic: # @ & ; $ ` ! ~
    # We'll be conservative and replace most special chars
    unsafe_chars = r'[/<>:"|?*\\#@&;$`!~%^()[\]{}=+]+'

    # Replace unsafe characters with hyphen
    safe_name = re.sub(unsafe_chars, "-", branch_name)

    # Replace whitespace and control characters with hyphen
    safe_name = re.sub(r"\s+", "-", safe_name)

    # Collapse multiple consecutive hyphens
    safe_name = re.sub(r"-+", "-", safe_name)

    # Strip leading/trailing hyphens
    safe_name = safe_name.strip("-")

    # Fallback if result is empty
    if not safe_name:
        safe_name = "worktree"

    return safe_name


def default_worktree_path(repo_path: Path, branch_name: str) -> Path:
    """
    Generate default worktree path based on new naming convention.

    New format: ../<repo>-<branch>
    Example: /Users/dave/myproject -> /Users/dave/myproject-fix-auth

    Handles branch names with slashes and special characters:
        feat/auth -> myproject-feat-auth
        bugfix/issue-123 -> myproject-bugfix-issue-123

    Args:
        repo_path: Path to the repository root
        branch_name: Name of the feature branch

    Returns:
        Default worktree path
    """
    repo_path = repo_path.resolve()
    safe_branch = sanitize_branch_name(branch_name)
    return repo_path.parent / f"{repo_path.name}-{safe_branch}"
