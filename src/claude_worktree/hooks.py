"""Hook execution system for claude-worktree.

Hooks allow users to run custom commands at lifecycle events
(worktree creation, deletion, merge, PR, etc.).

Hooks are stored per-repository in .claude-worktree/hooks.json
"""

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from .console import get_console
from .exceptions import ClaudeWorktreeError


class HookError(ClaudeWorktreeError):
    """Raised when a hook execution fails."""

    pass


# Valid hook events
HOOK_EVENTS = [
    "worktree.pre_create",
    "worktree.post_create",
    "worktree.pre_delete",
    "worktree.post_delete",
    "merge.pre",
    "merge.post",
    "pr.pre",
    "pr.post",
    "resume.pre",
    "resume.post",
    "sync.pre",
    "sync.post",
]

# Local config file name (stored in repository root)
LOCAL_CONFIG_FILE = ".cwconfig.json"


def get_repo_root_for_hooks(start_path: Path | None = None) -> Path | None:
    """Find the git repository root from start_path or current directory.

    Args:
        start_path: Starting path to search from (default: current directory)

    Returns:
        Path to repository root, or None if not in a git repository
    """
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent

    # Check root directory too
    if (current / ".git").exists():
        return current

    return None


def get_hooks_file_path(repo_root: Path | None = None) -> Path | None:
    """Get the path to the local configuration file.

    Args:
        repo_root: Repository root path (auto-detected if not provided)

    Returns:
        Path to .cwconfig.json, or None if not in a repository
    """
    if repo_root is None:
        repo_root = get_repo_root_for_hooks()

    if repo_root is None:
        return None

    return repo_root / LOCAL_CONFIG_FILE


def load_hooks_config(repo_root: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    """Load hooks configuration from the repository.

    Args:
        repo_root: Repository root path (auto-detected if not provided)

    Returns:
        Dictionary of hooks by event name
    """
    hooks_file = get_hooks_file_path(repo_root)

    if hooks_file is None or not hooks_file.exists():
        return {}

    try:
        with open(hooks_file) as f:
            data = json.load(f)
            hooks_data: dict[str, list[dict[str, Any]]] = data.get("hooks", {})
            return hooks_data
    except (OSError, json.JSONDecodeError):
        return {}


def save_hooks_config(
    hooks: dict[str, list[dict[str, Any]]], repo_root: Path | None = None
) -> None:
    """Save hooks configuration to the repository.

    Args:
        hooks: Dictionary of hooks by event name
        repo_root: Repository root path (auto-detected if not provided)

    Raises:
        HookError: If not in a repository or cannot save
    """
    if repo_root is None:
        repo_root = get_repo_root_for_hooks()

    # Check if repo_root is actually a git repository
    if repo_root is None or not (repo_root / ".git").exists():
        raise HookError("Not in a git repository. Hooks must be configured within a repository.")

    config_file = repo_root / LOCAL_CONFIG_FILE

    try:
        with open(config_file, "w") as f:
            json.dump({"hooks": hooks}, f, indent=2)
    except OSError as e:
        raise HookError(f"Failed to save hooks config: {e}")


def generate_hook_id(command: str) -> str:
    """Generate a unique ID for a hook based on command hash.

    Args:
        command: The hook command

    Returns:
        A short unique identifier like "hook-a1b2c3d4"
    """
    return f"hook-{hashlib.md5(command.encode()).hexdigest()[:8]}"


def get_hooks(event: str, repo_root: Path | None = None) -> list[dict[str, Any]]:
    """Get all hooks for a specific event.

    Args:
        event: Hook event name (e.g., "worktree.post_create")
        repo_root: Repository root path (auto-detected if not provided)

    Returns:
        List of hook configurations for the event
    """
    hooks = load_hooks_config(repo_root)
    return hooks.get(event, [])


def add_hook(
    event: str,
    command: str,
    hook_id: str | None = None,
    description: str | None = None,
    repo_root: Path | None = None,
) -> str:
    """Add a new hook for an event.

    Args:
        event: Hook event name
        command: Shell command to execute
        hook_id: Custom identifier (auto-generated if not provided)
        description: Human-readable description
        repo_root: Repository root path (auto-detected if not provided)

    Returns:
        The hook ID (generated or provided)

    Raises:
        HookError: If event is invalid or hook ID already exists
    """
    if event not in HOOK_EVENTS:
        raise HookError(f"Invalid hook event: {event}. Valid events: {', '.join(HOOK_EVENTS)}")

    hooks = load_hooks_config(repo_root)
    if event not in hooks:
        hooks[event] = []

    # Generate ID if not provided
    if not hook_id:
        hook_id = generate_hook_id(command)

    # Check for duplicate ID
    for hook in hooks[event]:
        if hook["id"] == hook_id:
            raise HookError(f"Hook with ID '{hook_id}' already exists for event '{event}'")

    hook_entry = {
        "id": hook_id,
        "command": command,
        "enabled": True,
        "description": description or "",
    }

    hooks[event].append(hook_entry)
    save_hooks_config(hooks, repo_root)
    return hook_id


def remove_hook(event: str, hook_id: str, repo_root: Path | None = None) -> None:
    """Remove a hook by event and ID.

    Args:
        event: Hook event name
        hook_id: Hook identifier to remove
        repo_root: Repository root path (auto-detected if not provided)

    Raises:
        HookError: If hook is not found
    """
    hooks = load_hooks_config(repo_root)
    event_hooks = hooks.get(event, [])

    original_len = len(event_hooks)
    hooks[event] = [h for h in event_hooks if h["id"] != hook_id]

    if len(hooks[event]) == original_len:
        raise HookError(f"Hook '{hook_id}' not found for event '{event}'")

    save_hooks_config(hooks, repo_root)


def set_hook_enabled(
    event: str, hook_id: str, enabled: bool, repo_root: Path | None = None
) -> None:
    """Enable or disable a hook.

    Args:
        event: Hook event name
        hook_id: Hook identifier
        enabled: True to enable, False to disable
        repo_root: Repository root path (auto-detected if not provided)

    Raises:
        HookError: If hook is not found
    """
    hooks = load_hooks_config(repo_root)
    event_hooks = hooks.get(event, [])

    found = False
    for hook in event_hooks:
        if hook["id"] == hook_id:
            hook["enabled"] = enabled
            found = True
            break

    if not found:
        raise HookError(f"Hook '{hook_id}' not found for event '{event}'")

    save_hooks_config(hooks, repo_root)


def run_hooks(
    event: str,
    context: dict[str, str],
    cwd: Path | None = None,
    repo_root: Path | None = None,
) -> bool:
    """Run all enabled hooks for an event.

    Args:
        event: Hook event name
        context: Dictionary of context variables (passed as CW_* env vars)
        cwd: Working directory for hook execution
        repo_root: Repository root path (auto-detected if not provided)

    Returns:
        True if all hooks succeeded, False if any failed

    Raises:
        HookError: If a pre-hook fails (aborts the operation)
    """
    console = get_console()
    hooks = get_hooks(event, repo_root)

    if not hooks:
        return True

    enabled_hooks = [h for h in hooks if h.get("enabled", True)]
    if not enabled_hooks:
        return True

    # Determine if this is a pre-hook (can abort operation)
    is_pre_hook = ".pre" in event or event.endswith(".pre_create") or event.endswith(".pre_delete")

    console.print(f"[dim]Running {len(enabled_hooks)} hook(s) for {event}...[/dim]")

    # Build environment with context
    env = os.environ.copy()
    for key, value in context.items():
        env[f"CW_{key.upper()}"] = str(value)

    all_succeeded = True

    for hook in enabled_hooks:
        hook_id = hook["id"]
        command = hook["command"]
        description = hook.get("description", "")

        desc_suffix = f" ({description})" if description else ""
        console.print(f"  [cyan]Running:[/cyan] {hook_id}{desc_suffix}")

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(cwd) if cwd else None,
                env=env,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                all_succeeded = False
                console.print(
                    f"  [bold red]✗[/bold red] Hook '{hook_id}' failed "
                    f"(exit code {result.returncode})"
                )
                if result.stderr:
                    # Show stderr on failure
                    for line in result.stderr.strip().splitlines()[:5]:
                        console.print(f"    [dim]{line}[/dim]")

                if is_pre_hook:
                    raise HookError(
                        f"Pre-hook '{hook_id}' failed with exit code {result.returncode}. "
                        f"Operation aborted."
                    )
            else:
                console.print(f"  [bold green]✓[/bold green] Hook '{hook_id}' completed")

        except subprocess.SubprocessError as e:
            all_succeeded = False
            console.print(f"  [bold red]✗[/bold red] Hook '{hook_id}' failed: {e}")

            if is_pre_hook:
                raise HookError(f"Pre-hook '{hook_id}' failed to execute: {e}")

    if not all_succeeded and not is_pre_hook:
        console.print("[yellow]Warning: Some post-hooks failed. See output above.[/yellow]")

    return all_succeeded
