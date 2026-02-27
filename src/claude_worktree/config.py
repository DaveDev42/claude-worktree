"""Configuration management for claude-worktree.

Supports multiple AI coding assistants with customizable commands.
Configuration is stored in ~/.config/claude-worktree/config.json.
"""

import copy
import json
import os
from pathlib import Path
from typing import Any

from .constants import LAUNCH_METHOD_ALIASES, MAX_SESSION_NAME_LENGTH, LaunchMethod
from .exceptions import ClaudeWorktreeError


class ConfigError(ClaudeWorktreeError):
    """Raised when configuration operations fail."""

    pass


# Predefined AI tool presets
AI_TOOL_PRESETS = {
    # No AI tool (no operation)
    "no-op": [],
    # Claude Code
    "claude": ["claude"],
    "claude-yolo": ["claude", "--dangerously-skip-permissions"],
    # Claude Code with Remote Control (local terminal + phone/tablet/browser access)
    "claude-remote": ["claude", "/remote-control"],
    "claude-yolo-remote": ["claude", "--dangerously-skip-permissions", "/remote-control"],
    # Codex
    "codex": ["codex"],
    "codex-yolo": ["codex", "--dangerously-bypass-approvals-and-sandbox"],
}

# Predefined resume commands for AI tools that use different resume syntax
# If a preset is not listed here, the default behavior is to append "--resume" flag
AI_TOOL_RESUME_PRESETS = {
    # Claude uses --continue flag instead of --resume
    "claude": ["claude", "--continue"],
    "claude-yolo": ["claude", "--dangerously-skip-permissions", "--continue"],
    # Claude remote: --continue resumes session, /remote-control activates remote access
    "claude-remote": ["claude", "--continue", "/remote-control"],
    "claude-yolo-remote": ["claude", "--dangerously-skip-permissions", "--continue", "/remote-control"],
    # Codex uses subcommand syntax: "codex resume [OPTIONS]" instead of "codex [OPTIONS] --resume"
    "codex": ["codex", "resume", "--last"],
    "codex-yolo": ["codex", "resume", "--dangerously-bypass-approvals-and-sandbox", "--last"],
}

# Predefined merge commands for AI tools used during automated conflict resolution
# These commands are used when --ai-merge flag is passed to merge/sync commands
# Format: {"preset_name": {"flags": [...], "prompt_position": "end"}}
# - flags: Additional flags to add for non-interactive merge mode
# - prompt_position: Where to insert the prompt ("end" or position index)
AI_TOOL_MERGE_PRESETS = {
    # Claude Code: Use --print mode for non-interactive execution
    # Note: Use --tools=default syntax to avoid positional arg confusion
    "claude": {
        "flags": ["--print", "--tools=default"],
        "prompt_position": "end",
    },
    "claude-yolo": {
        "flags": ["--print", "--tools=default"],
        "prompt_position": "end",
    },
    # Claude remote: merge uses --print mode, /remote-control prompt must be stripped
    "claude-remote": {
        "base_override": ["claude"],
        "flags": ["--print", "--tools=default"],
        "prompt_position": "end",
    },
    "claude-yolo-remote": {
        "base_override": ["claude", "--dangerously-skip-permissions"],
        "flags": ["--print", "--tools=default"],
        "prompt_position": "end",
    },
    # Codex: Use non-interactive mode
    "codex": {
        "flags": ["--non-interactive"],
        "prompt_position": "end",
    },
    "codex-yolo": {
        "flags": ["--non-interactive"],
        "prompt_position": "end",
    },
}


# Claude-based preset names (derived from AI_TOOL_PRESETS to stay in sync automatically)
CLAUDE_PRESET_NAMES = {k for k, v in AI_TOOL_PRESETS.items() if v and v[0] == "claude"}


DEFAULT_CONFIG = {
    "ai_tool": {
        "command": "claude",  # Command name or preset name (safe default without dangerous permissions)
        "args": [],  # Additional arguments
    },
    "launch": {
        "method": None,  # bg, iterm, tmux, or None
        "tmux_session_prefix": "cw",
    },
    "git": {
        "default_base_branch": "main",
    },
    "update": {
        "auto_check": True,  # Automatically check for updates daily
    },
    "shell_completion": {
        "prompted": False,  # Whether user has been prompted to install completion
        "installed": False,  # Whether completion is installed (user's response)
    },
    "slash_commands": {
        "prompted": False,  # Whether user has been prompted to install slash commands
        "installed": False,  # Whether slash commands are installed (user's response)
    },
    # Note: hooks are stored per-repository in .claude-worktree/hooks.json
    # not in this global config file
}


def get_config_path() -> Path:
    """Get the path to the configuration file.

    Returns:
        Path to config file: ~/.config/claude-worktree/config.json
    """
    config_dir = Path.home() / ".config" / "claude-worktree"
    return config_dir / "config.json"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries.

    Args:
        base: Base dictionary
        override: Dictionary with overriding values

    Returns:
        Merged dictionary (deep copy to avoid mutations)
    """
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_config() -> dict[str, Any]:
    """Load configuration from file.

    Returns:
        Configuration dictionary. Returns DEFAULT_CONFIG if file doesn't exist.
    """
    config_path = get_config_path()

    if not config_path.exists():
        return copy.deepcopy(DEFAULT_CONFIG)

    try:
        with open(config_path) as f:
            config = json.load(f)

        # Deep merge with defaults to ensure all keys exist
        merged = _deep_merge(DEFAULT_CONFIG, config)
        return merged

    except (OSError, json.JSONDecodeError) as e:
        raise ConfigError(f"Failed to load config from {config_path}: {e}")


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to file.

    Args:
        config: Configuration dictionary to save
    """
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
    except OSError as e:
        raise ConfigError(f"Failed to save config to {config_path}: {e}")


def get_ai_tool_command() -> list[str]:
    """Get the AI tool command to execute.

    Priority order:
    1. Environment variable CW_AI_TOOL
    2. Configuration file
    3. Default ("claude")

    Returns:
        List of command parts (e.g., ["claude"] or ["codex", "--model", "o3"])
        Empty list [] means no AI tool should be launched.
    """
    # Check environment variable first
    env_tool = os.environ.get("CW_AI_TOOL")
    if env_tool is not None:
        # Empty string means no AI tool
        if not env_tool.strip():
            return []
        return env_tool.split()

    # Load from config
    config = load_config()
    command: str = config["ai_tool"]["command"]
    args: list[str] = config["ai_tool"]["args"]

    # Check if it's a preset
    if command in AI_TOOL_PRESETS:
        base_cmd: list[str] = AI_TOOL_PRESETS[command].copy()
        return base_cmd + args

    # Empty command means no AI tool
    if not command.strip():
        return []

    # Otherwise, use as custom command
    return [command] + args


def get_ai_tool_resume_command() -> list[str]:
    """Get the AI tool command to execute when resuming a session.

    For presets with custom resume syntax (like codex), uses AI_TOOL_RESUME_PRESETS.
    Otherwise, appends --resume flag to the regular command.

    Returns:
        List of command parts for resuming a session
        Empty list [] means no AI tool should be launched.
    """
    # Check environment variable first - use default --resume behavior
    env_tool = os.environ.get("CW_AI_TOOL")
    if env_tool is not None:
        if not env_tool.strip():
            return []
        # Environment override: append --resume flag
        return env_tool.split() + ["--resume"]

    # Load from config
    config = load_config()
    command: str = config["ai_tool"]["command"]
    args: list[str] = config["ai_tool"]["args"]

    # Empty command means no AI tool
    if not command.strip():
        return []

    # Check if preset has a custom resume command
    if command in AI_TOOL_RESUME_PRESETS:
        resume_cmd: list[str] = AI_TOOL_RESUME_PRESETS[command].copy()
        return resume_cmd + args

    # Check if it's a regular preset
    if command in AI_TOOL_PRESETS:
        base_cmd: list[str] = AI_TOOL_PRESETS[command].copy()
        if not base_cmd:  # no-op preset
            return []
        return base_cmd + args + ["--resume"]

    # Custom command: append --resume flag
    return [command] + args + ["--resume"]


def get_ai_tool_merge_command(prompt: str) -> list[str]:
    """Get the AI tool command to execute for automated conflict resolution.

    For presets with custom merge configuration, uses AI_TOOL_MERGE_PRESETS.
    Otherwise, returns the base command with prompt appended.

    Args:
        prompt: The prompt to send to the AI tool for conflict resolution

    Returns:
        List of command parts for merge/conflict resolution
        Empty list [] means no AI tool should be launched.
    """
    # Check environment variable first
    env_tool = os.environ.get("CW_AI_TOOL")
    if env_tool is not None:
        if not env_tool.strip():
            return []
        # Environment override: use base command + prompt
        return env_tool.split() + [prompt]

    # Load from config
    config = load_config()
    command: str = config["ai_tool"]["command"]
    args: list[str] = config["ai_tool"]["args"]

    # Empty command means no AI tool
    if not command.strip():
        return []

    # Check if preset has a custom merge command configuration
    if command in AI_TOOL_MERGE_PRESETS:
        merge_config = AI_TOOL_MERGE_PRESETS[command]
        flags = list(merge_config.get("flags", []))
        prompt_position = merge_config.get("prompt_position", "end")

        # Get base command (use base_override to strip interactive-only args
        # like /remote-control that don't work with --print mode)
        base_override = merge_config.get("base_override")
        if base_override is not None:
            base_cmd: list[str] = list(base_override)
        else:
            base_cmd = AI_TOOL_PRESETS.get(command, [command]).copy()

        # Build command: base + args + flags + prompt
        cmd_parts = base_cmd + args + flags

        # Insert prompt at specified position
        if prompt_position == "end":
            cmd_parts.append(prompt)
        elif isinstance(prompt_position, int):
            # Insert at specific index (for tools that need prompt in middle)
            cmd_parts.insert(prompt_position, prompt)
        else:
            # Fallback: append to end if invalid position
            cmd_parts.append(prompt)

        return cmd_parts

    # Check if it's a regular preset without merge config
    if command in AI_TOOL_PRESETS:
        base_cmd = AI_TOOL_PRESETS[command].copy()
        if not base_cmd:  # no-op preset
            return []
        return base_cmd + args + [prompt]

    # Custom command: just append prompt
    return [command] + args + [prompt]


def is_claude_tool() -> bool:
    """Check if the currently configured AI tool is Claude-based.

    Checks environment variable CW_AI_TOOL first, then config preset name.

    Returns:
        True if the AI tool is a Claude variant, False otherwise
    """
    env_tool = os.environ.get("CW_AI_TOOL")
    if env_tool is not None:
        # Check if the first word of the command is "claude"
        first_word = env_tool.strip().split()[0] if env_tool.strip() else ""
        return first_word == "claude"

    config = load_config()
    command: str = config["ai_tool"]["command"]
    return command in CLAUDE_PRESET_NAMES


def set_ai_tool(tool: str, args: list[str] | None = None) -> None:
    """Set the AI tool command in configuration.

    Args:
        tool: Tool name (preset or custom command)
        args: Additional arguments to pass to the tool
    """
    config = load_config()
    config["ai_tool"]["command"] = tool
    config["ai_tool"]["args"] = args or []
    save_config(config)


def use_preset(preset_name: str) -> None:
    """Use a predefined AI tool preset.

    Args:
        preset_name: Name of the preset (e.g., "claude", "codex")

    Raises:
        ConfigError: If preset doesn't exist
    """
    if preset_name not in AI_TOOL_PRESETS:
        available = ", ".join(AI_TOOL_PRESETS.keys())
        raise ConfigError(f"Unknown preset: {preset_name}. Available: {available}")

    set_ai_tool(preset_name)


def reset_config() -> None:
    """Reset configuration to defaults."""
    save_config(copy.deepcopy(DEFAULT_CONFIG))


def set_config_value(key_path: str, value: Any) -> None:
    """Set a configuration value by dot-separated key path.

    Args:
        key_path: Dot-separated path (e.g., "git.default_base_branch")
        value: Value to set (auto-converts "true"/"false" strings to booleans)
    """
    config = load_config()
    keys = key_path.split(".")

    # Convert string boolean values to actual booleans
    if isinstance(value, str):
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False

    # Navigate to the parent dict
    current = config
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]

    # Set the value
    current[keys[-1]] = value
    save_config(config)


def show_config() -> str:
    """Get a formatted string representation of the current configuration.

    Returns:
        Formatted configuration string
    """
    config = load_config()

    lines = ["Current configuration:", ""]
    lines.append(f"  AI Tool: {config['ai_tool']['command']}")

    if config["ai_tool"]["args"]:
        lines.append(f"    Args: {' '.join(config['ai_tool']['args'])}")

    # Show actual command that will be executed
    cmd = get_ai_tool_command()
    lines.append(f"    Effective command: {' '.join(cmd)}")
    lines.append("")

    if config["launch"]["method"]:
        lines.append(f"  Launch method: {config['launch']['method']}")
    else:
        lines.append("  Launch method: foreground (default)")

    lines.append(f"  Default base branch: {config['git']['default_base_branch']}")
    lines.append("")

    lines.append(f"Config file: {get_config_path()}")

    return "\n".join(lines)


def list_presets() -> str:
    """Get a formatted string listing all available presets.

    Returns:
        Formatted presets list
    """
    lines = ["Available AI tool presets:", ""]

    for name, cmd in AI_TOOL_PRESETS.items():
        lines.append(f"  {name:20} -> {' '.join(cmd)}")

    return "\n".join(lines)


# =============================================================================
# Launch Method Configuration
# =============================================================================


def resolve_launch_alias(value: str) -> str:
    """Resolve launch method alias to full name.

    Handles both simple aliases and session name syntax:
    - "t" -> "tmux"
    - "t:mywork" -> "tmux:mywork"
    - "z-p-h" -> "zellij-pane-h"

    Args:
        value: Alias or full name, optionally with session suffix

    Returns:
        Resolved full name, preserving any session suffix
    """
    import warnings

    # Deprecated aliases
    _DEPRECATED_ALIASES: dict[str, str] = {
        "bg": "detach",
        "background": "detach",
    }

    # Handle session name suffix (e.g., "t:mysession" -> "tmux:mysession")
    if ":" in value:
        prefix, suffix = value.split(":", 1)
        if prefix in _DEPRECATED_ALIASES:
            warnings.warn(
                f"'{prefix}' is deprecated. Use '{_DEPRECATED_ALIASES[prefix]}' instead.",
                DeprecationWarning,
                stacklevel=3,
            )
            prefix = _DEPRECATED_ALIASES[prefix]
        resolved_prefix = LAUNCH_METHOD_ALIASES.get(prefix, prefix)
        return f"{resolved_prefix}:{suffix}"

    if value in _DEPRECATED_ALIASES:
        new_value = _DEPRECATED_ALIASES[value]
        warnings.warn(
            f"'{value}' is deprecated. Use '{new_value}' instead.",
            DeprecationWarning,
            stacklevel=3,
        )
        return new_value

    return LAUNCH_METHOD_ALIASES.get(value, value)


def parse_term_option(term_value: str | None) -> tuple[LaunchMethod, str | None]:
    """Parse --term option value.

    Args:
        term_value: The value passed to --term option

    Returns:
        Tuple of (LaunchMethod, optional_session_name)

    Raises:
        ConfigError: If the launch method is invalid or session name is too long

    Examples:
        "i-t" -> (LaunchMethod.ITERM_TAB, None)
        "z" -> (LaunchMethod.ZELLIJ, None)
        "t:mywork" -> (LaunchMethod.TMUX, "mywork")
        "z:dev" -> (LaunchMethod.ZELLIJ, "dev")
    """
    if term_value is None:
        return get_default_launch_method(), None

    resolved = resolve_launch_alias(term_value)

    # Handle session name for tmux/zellij
    if ":" in resolved:
        method_str, session_name = resolved.split(":", 1)
        try:
            method = LaunchMethod(method_str)
            # Only tmux and zellij support session names
            if method in (LaunchMethod.TMUX, LaunchMethod.ZELLIJ):
                # Validate session name length
                if len(session_name) > MAX_SESSION_NAME_LENGTH:
                    raise ConfigError(
                        f"Session name too long (max {MAX_SESSION_NAME_LENGTH} chars): {session_name}"
                    )
                return method, session_name
            else:
                raise ConfigError(f"Session name not supported for {method_str}")
        except ValueError:
            raise ConfigError(f"Invalid launch method: {method_str}")

    try:
        return LaunchMethod(resolved), None
    except ValueError:
        raise ConfigError(f"Invalid launch method: {term_value}")


def get_default_launch_method() -> LaunchMethod:
    """Get default launch method from config or environment.

    Priority order:
    1. Environment variable CW_LAUNCH_METHOD
    2. Configuration file (launch.method)
    3. Default (FOREGROUND)

    Returns:
        Default LaunchMethod
    """
    # 1. Environment variable
    env_val = os.environ.get("CW_LAUNCH_METHOD")
    if env_val:
        resolved = resolve_launch_alias(env_val)
        try:
            return LaunchMethod(resolved)
        except ValueError:
            pass  # Invalid value, fall through to config

    # 2. Config file
    config = load_config()
    method = config.get("launch", {}).get("method")
    if method:
        resolved = resolve_launch_alias(method)
        try:
            return LaunchMethod(resolved)
        except ValueError:
            pass  # Invalid value, fall through to default

    return LaunchMethod.FOREGROUND
