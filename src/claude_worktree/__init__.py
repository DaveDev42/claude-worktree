"""Claude Worktree - CLI tool integrating git worktree with Claude Code."""

from importlib.metadata import version

try:
    __version__ = version("claude-worktree")
except Exception:
    # Fallback for development/editable installs
    __version__ = "0.0.0.dev"

__author__ = "Dave"
__license__ = "BSD-3-Clause"

from .cli import app
from .exceptions import (
    ClaudeWorktreeError,
    GitError,
    InvalidBranchError,
    MergeError,
    RebaseError,
    WorktreeNotFoundError,
)

__all__ = [
    "__version__",
    "__author__",
    "__license__",
    "app",
    "ClaudeWorktreeError",
    "GitError",
    "InvalidBranchError",
    "MergeError",
    "RebaseError",
    "WorktreeNotFoundError",
]
