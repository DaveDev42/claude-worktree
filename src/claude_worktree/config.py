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
    # Codex
    "codex": ["codex"],
    # Happy (mobile-enabled Claude Code)
    "happy": ["happy"],
    "happy-codex": ["happy", "codex", "--permission-mode", "bypassPermissions"],
    "happy-yolo": ["happy", "--permission-mode", "bypassPermissions"],
}


DEFAULT_CONFIG = {
    "ai_tool": {
        "command": "claude",  # Command name or preset name
        "args": [],  # Additional arguments
    },
    "launch": {
        "method": None,  # bg, iterm, tmux, or None
        "tmux_session_prefix": "cw",
    },
    "git": {
        "default_base_branch": "main",
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
    if env_tool:
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


def get_config_value(key_path: str) -> Any:
    """Get a configuration value by dot-separated key path.

    Args:
        key_path: Dot-separated path (e.g., "ai_tool.command")

    Returns:
        Configuration value

    Raises:
        ConfigError: If key path doesn't exist
    """
    config = load_config()
    keys = key_path.split(".")

    value = config
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            raise ConfigError(f"Configuration key not found: {key_path}")
        value = value[key]

    return value


def set_config_value(key_path: str, value: Any) -> None:
    """Set a configuration value by dot-separated key path.

    Args:
        key_path: Dot-separated path (e.g., "git.default_base_branch")
        value: Value to set
    """
    config = load_config()
    keys = key_path.split(".")

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
        lines.append(f"  {name:20} → {' '.join(cmd)}")

    return "\n".join(lines)
