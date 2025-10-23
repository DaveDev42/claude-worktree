"""AI session management for claude-worktree.

Handles backup and restoration of AI coding assistant sessions across worktrees.
Supports Claude Code, Codex, Happy, and custom AI tools.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from .exceptions import ClaudeWorktreeError


class SessionError(ClaudeWorktreeError):
    """Raised when session operations fail."""

    pass


def get_sessions_dir() -> Path:
    """Get the base sessions directory.

    Returns:
        Path to sessions directory: ~/.config/claude-worktree/sessions/
    """
    sessions_dir = Path.home() / ".config" / "claude-worktree" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return sessions_dir


def get_session_dir(branch_name: str) -> Path:
    """Get the session directory for a specific branch.

    Args:
        branch_name: Name of the feature branch

    Returns:
        Path to session directory for the branch
    """
    sessions_dir = get_sessions_dir()
    # Sanitize branch name for directory (remove refs/heads/ prefix if present)
    if branch_name.startswith("refs/heads/"):
        branch_name = branch_name[11:]

    # Replace slashes and special chars with hyphens for directory safety
    from .constants import sanitize_branch_name

    safe_branch = sanitize_branch_name(branch_name)
    session_dir = sessions_dir / safe_branch
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def session_exists(branch_name: str) -> bool:
    """Check if a session exists for the given branch.

    Args:
        branch_name: Name of the feature branch

    Returns:
        True if session data exists, False otherwise
    """
    session_dir = get_session_dir(branch_name)
    metadata_file = session_dir / "metadata.json"
    return metadata_file.exists()


def save_session_metadata(branch_name: str, ai_tool: str, worktree_path: str) -> None:
    """Save session metadata for a branch.

    Args:
        branch_name: Name of the feature branch
        ai_tool: Name of the AI tool (e.g., "claude", "codex", "happy")
        worktree_path: Path to the worktree directory
    """
    session_dir = get_session_dir(branch_name)
    metadata_file = session_dir / "metadata.json"

    metadata = {
        "branch": branch_name,
        "ai_tool": ai_tool,
        "worktree_path": str(worktree_path),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    # If metadata exists, preserve created_at
    if metadata_file.exists():
        try:
            with open(metadata_file) as f:
                existing = json.load(f)
                metadata["created_at"] = existing.get("created_at", metadata["created_at"])
        except (OSError, json.JSONDecodeError):
            pass  # Use new created_at if loading fails

    try:
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)
    except OSError as e:
        raise SessionError(f"Failed to save session metadata: {e}")


def load_session_metadata(branch_name: str) -> dict[str, Any] | None:
    """Load session metadata for a branch.

    Args:
        branch_name: Name of the feature branch

    Returns:
        Session metadata dictionary or None if not found
    """
    session_dir = get_session_dir(branch_name)
    metadata_file = session_dir / "metadata.json"

    if not metadata_file.exists():
        return None

    try:
        with open(metadata_file) as f:
            metadata: dict[str, Any] = json.load(f)
            return metadata
    except (OSError, json.JSONDecodeError) as e:
        raise SessionError(f"Failed to load session metadata: {e}")


def get_claude_session_file(branch_name: str) -> Path:
    """Get the path to Claude Code session file for a branch.

    Claude Code stores sessions in ~/.claude/sessions/<session-id>.json
    We'll manage our own simplified session data for restoration.

    Args:
        branch_name: Name of the feature branch

    Returns:
        Path to claude session file
    """
    session_dir = get_session_dir(branch_name)
    return session_dir / "claude-session.json"


def save_claude_session(branch_name: str, session_data: dict[str, Any]) -> None:
    """Save Claude Code session data.

    Args:
        branch_name: Name of the feature branch
        session_data: Session data to save
    """
    session_file = get_claude_session_file(branch_name)

    try:
        with open(session_file, "w") as f:
            json.dump(session_data, f, indent=2)
    except OSError as e:
        raise SessionError(f"Failed to save Claude session: {e}")


def load_claude_session(branch_name: str) -> dict[str, Any] | None:
    """Load Claude Code session data.

    Args:
        branch_name: Name of the feature branch

    Returns:
        Session data dictionary or None if not found
    """
    session_file = get_claude_session_file(branch_name)

    if not session_file.exists():
        return None

    try:
        with open(session_file) as f:
            data: dict[str, Any] = json.load(f)
            return data
    except (OSError, json.JSONDecodeError) as e:
        raise SessionError(f"Failed to load Claude session: {e}")


def delete_session(branch_name: str) -> None:
    """Delete all session data for a branch.

    Args:
        branch_name: Name of the feature branch
    """
    session_dir = get_session_dir(branch_name)

    if session_dir.exists():
        try:
            shutil.rmtree(session_dir)
        except OSError as e:
            raise SessionError(f"Failed to delete session: {e}")


def list_sessions() -> list[dict[str, Any]]:
    """List all saved sessions.

    Returns:
        List of session metadata dictionaries
    """
    sessions_dir = get_sessions_dir()
    sessions: list[dict[str, Any]] = []

    if not sessions_dir.exists():
        return sessions

    for session_dir in sessions_dir.iterdir():
        if session_dir.is_dir():
            metadata_file = session_dir / "metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file) as f:
                        metadata: dict[str, Any] = json.load(f)
                        sessions.append(metadata)
                except (OSError, json.JSONDecodeError):
                    # Skip corrupted metadata
                    continue

    return sessions


def get_context_file(branch_name: str) -> Path:
    """Get the path to context file for a branch.

    The context file stores additional context about the work being done,
    which can help the AI tool understand what was being worked on.

    Args:
        branch_name: Name of the feature branch

    Returns:
        Path to context file
    """
    session_dir = get_session_dir(branch_name)
    return session_dir / "context.txt"


def save_context(branch_name: str, context: str) -> None:
    """Save context information for a branch.

    Args:
        branch_name: Name of the feature branch
        context: Context description to save
    """
    context_file = get_context_file(branch_name)

    try:
        with open(context_file, "w") as f:
            f.write(context)
    except OSError as e:
        raise SessionError(f"Failed to save context: {e}")


def load_context(branch_name: str) -> str | None:
    """Load context information for a branch.

    Args:
        branch_name: Name of the feature branch

    Returns:
        Context string or None if not found
    """
    context_file = get_context_file(branch_name)

    if not context_file.exists():
        return None

    try:
        with open(context_file) as f:
            return f.read()
    except OSError as e:
        raise SessionError(f"Failed to load context: {e}")
