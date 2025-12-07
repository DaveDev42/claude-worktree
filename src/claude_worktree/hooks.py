"""Hook execution system for claude-worktree.

Hooks allow users to run custom commands at lifecycle events
(worktree creation, deletion, merge, PR, etc.).
"""

import hashlib
import os
import subprocess
from pathlib import Path
from typing import Any

from .config import load_config, save_config
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


def generate_hook_id(command: str) -> str:
    """Generate a unique ID for a hook based on command hash.

    Args:
        command: The hook command

    Returns:
        A short unique identifier like "hook-a1b2c3d4"
    """
    return f"hook-{hashlib.md5(command.encode()).hexdigest()[:8]}"


def get_hooks(event: str) -> list[dict[str, Any]]:
    """Get all hooks for a specific event.

    Args:
        event: Hook event name (e.g., "worktree.post_create")

    Returns:
        List of hook configurations for the event
    """
    config = load_config()
    hooks: dict[str, list[dict[str, Any]]] = config.get("hooks", {})
    return hooks.get(event, [])


def add_hook(
    event: str,
    command: str,
    hook_id: str | None = None,
    description: str | None = None,
) -> str:
    """Add a new hook for an event.

    Args:
        event: Hook event name
        command: Shell command to execute
        hook_id: Custom identifier (auto-generated if not provided)
        description: Human-readable description

    Returns:
        The hook ID (generated or provided)

    Raises:
        HookError: If event is invalid or hook ID already exists
    """
    if event not in HOOK_EVENTS:
        raise HookError(f"Invalid hook event: {event}. Valid events: {', '.join(HOOK_EVENTS)}")

    config = load_config()
    if "hooks" not in config:
        config["hooks"] = {}
    if event not in config["hooks"]:
        config["hooks"][event] = []

    # Generate ID if not provided
    if not hook_id:
        hook_id = generate_hook_id(command)

    # Check for duplicate ID
    for hook in config["hooks"][event]:
        if hook["id"] == hook_id:
            raise HookError(f"Hook with ID '{hook_id}' already exists for event '{event}'")

    hook_entry = {
        "id": hook_id,
        "command": command,
        "enabled": True,
        "description": description or "",
    }

    config["hooks"][event].append(hook_entry)
    save_config(config)
    return hook_id


def remove_hook(event: str, hook_id: str) -> None:
    """Remove a hook by event and ID.

    Args:
        event: Hook event name
        hook_id: Hook identifier to remove

    Raises:
        HookError: If hook is not found
    """
    config = load_config()
    hooks = config.get("hooks", {}).get(event, [])

    original_len = len(hooks)
    config["hooks"][event] = [h for h in hooks if h["id"] != hook_id]

    if len(config["hooks"][event]) == original_len:
        raise HookError(f"Hook '{hook_id}' not found for event '{event}'")

    save_config(config)


def set_hook_enabled(event: str, hook_id: str, enabled: bool) -> None:
    """Enable or disable a hook.

    Args:
        event: Hook event name
        hook_id: Hook identifier
        enabled: True to enable, False to disable

    Raises:
        HookError: If hook is not found
    """
    config = load_config()
    hooks = config.get("hooks", {}).get(event, [])

    found = False
    for hook in hooks:
        if hook["id"] == hook_id:
            hook["enabled"] = enabled
            found = True
            break

    if not found:
        raise HookError(f"Hook '{hook_id}' not found for event '{event}'")

    save_config(config)


def run_hooks(
    event: str,
    context: dict[str, str],
    cwd: Path | None = None,
) -> bool:
    """Run all enabled hooks for an event.

    Args:
        event: Hook event name
        context: Dictionary of context variables (passed as CW_* env vars)
        cwd: Working directory for hook execution

    Returns:
        True if all hooks succeeded, False if any failed

    Raises:
        HookError: If a pre-hook fails (aborts the operation)
    """
    console = get_console()
    hooks = get_hooks(event)

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
