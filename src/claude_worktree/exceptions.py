"""Custom exception classes for claude-worktree."""


class ClaudeWorktreeError(Exception):
    """Base exception for all claude-worktree errors."""

    pass


class GitError(ClaudeWorktreeError):
    """Raised when a git operation fails."""

    pass


class WorktreeNotFoundError(ClaudeWorktreeError):
    """Raised when a worktree cannot be found."""

    pass


class InvalidBranchError(ClaudeWorktreeError):
    """Raised when a branch is invalid or in an unexpected state."""

    pass


class MergeError(ClaudeWorktreeError):
    """Raised when a merge operation fails."""

    pass


class RebaseError(ClaudeWorktreeError):
    """Raised when a rebase operation fails."""

    pass
