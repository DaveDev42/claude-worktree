"""Constants and default values for claude-worktree."""

import re
from enum import StrEnum
from pathlib import Path


class LaunchMethod(StrEnum):
    """Terminal launch methods for AI tool execution."""

    FOREGROUND = "foreground"
    DETACH = "detach"
    # iTerm (macOS)
    ITERM_WINDOW = "iterm-window"
    ITERM_TAB = "iterm-tab"
    ITERM_PANE_H = "iterm-pane-h"
    ITERM_PANE_V = "iterm-pane-v"
    # tmux
    TMUX = "tmux"
    TMUX_WINDOW = "tmux-window"
    TMUX_PANE_H = "tmux-pane-h"
    TMUX_PANE_V = "tmux-pane-v"
    # Zellij
    ZELLIJ = "zellij"
    ZELLIJ_TAB = "zellij-tab"
    ZELLIJ_PANE_H = "zellij-pane-h"
    ZELLIJ_PANE_V = "zellij-pane-v"
    # WezTerm
    WEZTERM_WINDOW = "wezterm-window"
    WEZTERM_TAB = "wezterm-tab"
    WEZTERM_PANE_H = "wezterm-pane-h"
    WEZTERM_PANE_V = "wezterm-pane-v"


# Alias mapping for launch methods
# First letter: i=iTerm, t=tmux, z=Zellij, w=WezTerm
# Second: w=window, t=tab, p=pane
# For panes: h=horizontal, v=vertical
LAUNCH_METHOD_ALIASES: dict[str, str] = {
    "fg": "foreground",
    "d": "detach",
    # iTerm
    "i-w": "iterm-window",
    "i-t": "iterm-tab",
    "i-p-h": "iterm-pane-h",
    "i-p-v": "iterm-pane-v",
    # tmux
    "t": "tmux",
    "t-w": "tmux-window",
    "t-p-h": "tmux-pane-h",
    "t-p-v": "tmux-pane-v",
    # Zellij
    "z": "zellij",
    "z-t": "zellij-tab",
    "z-p-h": "zellij-pane-h",
    "z-p-v": "zellij-pane-v",
    # WezTerm
    "w-w": "wezterm-window",
    "w-t": "wezterm-tab",
    "w-p-h": "wezterm-pane-h",
    "w-p-v": "wezterm-pane-v",
}

# Maximum session name length for tmux/zellij compatibility
# Zellij uses Unix sockets which have a ~108 byte path limit
MAX_SESSION_NAME_LENGTH = 50

# Git config keys for metadata storage
CONFIG_KEY_BASE_BRANCH = "branch.{}.worktreeBase"
CONFIG_KEY_BASE_PATH = "worktree.{}.basePath"
CONFIG_KEY_INTENDED_BRANCH = "worktree.{}.intendedBranch"


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
