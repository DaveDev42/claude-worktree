"""Claude Worktree - CLI tool integrating git worktree with Claude Code."""

__version__ = "0.1.2"
__author__ = "Dave"
__license__ = "MIT"

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
