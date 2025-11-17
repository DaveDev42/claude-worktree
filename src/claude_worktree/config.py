"""Configuration management for claude-worktree.

Supports multiple AI coding assistants with customizable commands.
Configuration is stored in ~/.config/claude-worktree/config.json.
"""

import copy
import json
import os
from pathlib import Path
from typing import Any

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
    # Codex
    "codex": ["codex"],
    "codex-yolo": ["codex", "--dangerously-bypass-approvals-and-sandbox"],
    # Happy (mobile-enabled Claude Code)
    "happy": ["happy"],
    "happy-codex": ["happy", "codex", "--permission-mode", "bypassPermissions"],
    "happy-yolo": ["happy", "--yolo"],
}

# Predefined resume commands for AI tools that use different resume syntax
# If a preset is not listed here, the default behavior is to append "--resume" flag
AI_TOOL_RESUME_PRESETS = {
    # Claude uses --continue flag instead of --resume
    "claude": ["claude", "--continue"],
    "claude-yolo": ["claude", "--dangerously-skip-permissions", "--continue"],
    # Happy uses --continue flag (inherits from Claude Code)
    "happy": ["happy", "--continue"],
    "happy-codex": ["happy", "codex", "--permission-mode", "bypassPermissions", "--continue"],
    "happy-yolo": ["happy", "--yolo", "--continue"],
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
    # Happy: Use --yolo mode for automated conflict resolution
    "happy": {
        "flags": ["--print", "--tools=default"],
        "prompt_position": "end",
    },
    "happy-codex": {
        "flags": ["--print", "--tools=default"],
        "prompt_position": "end",
    },
    "happy-yolo": {
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
    "worktree": {
        "auto_share_files": True,  # Automatically symlink shared files (node_modules, .venv, etc.)
        "copy_files": [],  # Additional files to copy (e.g., [".env", ".env.local", "config.json"])
    },
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
        List of command parts (e.g., ["claude"] or ["happy", "--backend", "claude"])
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

        # Get base command from preset
        base_cmd: list[str] = AI_TOOL_PRESETS.get(command, [command]).copy()

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
        preset_name: Name of the preset (e.g., "claude", "happy-claude")

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


def get_copy_files() -> list[str]:
    """Get list of files to copy to new worktrees.

    Returns:
        List of file paths to copy
    """
    config = load_config()
    worktree_config = config.get("worktree", {})
    copy_files: list[str] = worktree_config.get("copy_files", [])
    return copy_files


def add_copy_file(file_path: str) -> None:
    """Add a file to the copy_files list.

    Args:
        file_path: Relative path to file (e.g., ".env", "config/local.json")
    """
    config = load_config()
    copy_files = config.get("worktree", {}).get("copy_files", [])

    if file_path not in copy_files:
        copy_files.append(file_path)
        if "worktree" not in config:
            config["worktree"] = {}
        config["worktree"]["copy_files"] = copy_files
        save_config(config)


def remove_copy_file(file_path: str) -> bool:
    """Remove a file from the copy_files list.

    Args:
        file_path: Relative path to file

    Returns:
        True if file was removed, False if it wasn't in the list
    """
    config = load_config()
    copy_files = config.get("worktree", {}).get("copy_files", [])

    if file_path in copy_files:
        copy_files.remove(file_path)
        config["worktree"]["copy_files"] = copy_files
        save_config(config)
        return True

    return False


def list_copy_files() -> str:
    """Get a formatted string listing all files configured to be copied.

    Returns:
        Formatted copy files list
    """
    copy_files = get_copy_files()

    if not copy_files:
        return (
            "No files configured to be copied.\n\nAdd files with: cw config copy-files add <file>"
        )

    lines = ["Files to copy to new worktrees:", ""]
    for file_path in copy_files:
        lines.append(f"  • {file_path}")

    return "\n".join(lines)
