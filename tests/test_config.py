"""Tests for config module."""

import json
from pathlib import Path

import pytest

from claude_worktree.config import (
    AI_TOOL_PRESETS,
    DEFAULT_CONFIG,
    ConfigError,
    get_ai_tool_command,
    get_config_path,
    get_config_value,
    list_presets,
    load_config,
    reset_config,
    save_config,
    set_ai_tool,
    set_config_value,
    show_config,
    use_preset,
)


@pytest.fixture
def temp_config_dir(tmp_path: Path, monkeypatch) -> Path:
    """Create a temporary config directory for testing."""
    config_dir = tmp_path / ".config" / "claude-worktree"
    config_dir.mkdir(parents=True)

    # Mock HOME environment to use temp directory
    monkeypatch.setenv("HOME", str(tmp_path))

    # Also ensure no CW_AI_TOOL is set
    monkeypatch.delenv("CW_AI_TOOL", raising=False)

    return config_dir


def test_get_config_path(tmp_path: Path, monkeypatch) -> None:
    """Test getting config file path."""
    monkeypatch.setenv("HOME", str(tmp_path))

    # Real implementation (without mocking)
    from claude_worktree.config import get_config_path as real_get_config_path

    expected = tmp_path / ".config" / "claude-worktree" / "config.json"
    assert real_get_config_path() == expected


def test_load_config_no_file(temp_config_dir: Path) -> None:
    """Test loading config when file doesn't exist returns defaults."""
    config = load_config()
    assert config == DEFAULT_CONFIG


def test_save_and_load_config(temp_config_dir: Path) -> None:
    """Test saving and loading configuration."""
    test_config = {
        "ai_tool": {
            "command": "codex",
            "args": ["--verbose"],
        },
        "launch": {
            "method": "bg",
            "tmux_session_prefix": "cw",
        },
        "git": {
            "default_base_branch": "develop",
        },
    }

    save_config(test_config)

    # Verify file was created
    config_path = get_config_path()
    assert config_path.exists()

    # Load and verify
    loaded = load_config()
    assert loaded["ai_tool"]["command"] == "codex"
    assert loaded["ai_tool"]["args"] == ["--verbose"]
    assert loaded["launch"]["method"] == "bg"
    assert loaded["git"]["default_base_branch"] == "develop"


def test_save_config_creates_directory(tmp_path: Path, monkeypatch) -> None:
    """Test that save_config creates parent directory if needed."""
    config_dir = tmp_path / ".config" / "claude-worktree"

    def mock_get_config_path() -> Path:
        return config_dir / "config.json"

    monkeypatch.setattr("claude_worktree.config.get_config_path", mock_get_config_path)

    # Directory shouldn't exist yet
    assert not config_dir.exists()

    save_config(DEFAULT_CONFIG)

    # Should have created directory and file
    assert config_dir.exists()
    assert (config_dir / "config.json").exists()


def test_get_ai_tool_command_default(temp_config_dir: Path) -> None:
    """Test getting default AI tool command."""
    cmd = get_ai_tool_command()
    assert cmd == ["claude"]


def test_get_ai_tool_command_custom(temp_config_dir: Path) -> None:
    """Test getting custom AI tool command."""
    import copy as copy_module

    config = copy_module.deepcopy(DEFAULT_CONFIG)
    config["ai_tool"]["command"] = "happy"
    config["ai_tool"]["args"] = ["--backend", "claude"]
    save_config(config)

    cmd = get_ai_tool_command()
    assert cmd == ["happy", "--backend", "claude"]


def test_get_ai_tool_command_preset(temp_config_dir: Path) -> None:
    """Test getting AI tool command from preset."""
    import copy as copy_module

    config = copy_module.deepcopy(DEFAULT_CONFIG)
    config["ai_tool"]["command"] = "happy-codex"
    config["ai_tool"]["args"] = []
    save_config(config)

    cmd = get_ai_tool_command()
    assert cmd == ["happy", "codex", "--permission-mode", "bypassPermissions"]


def test_get_ai_tool_command_preset_with_extra_args(temp_config_dir: Path) -> None:
    """Test getting AI tool command from preset with additional args."""
    import copy as copy_module

    config = copy_module.deepcopy(DEFAULT_CONFIG)
    config["ai_tool"]["command"] = "claude"
    config["ai_tool"]["args"] = ["--verbose"]
    save_config(config)

    cmd = get_ai_tool_command()
    expected = AI_TOOL_PRESETS["claude"] + ["--verbose"]
    assert cmd == expected


def test_get_ai_tool_command_env_override(temp_config_dir: Path, monkeypatch) -> None:
    """Test environment variable overrides config file."""
    # Set config to use claude
    import copy as copy_module

    config = copy_module.deepcopy(DEFAULT_CONFIG)
    config["ai_tool"]["command"] = "claude"
    save_config(config)

    # Override with environment variable
    monkeypatch.setenv("CW_AI_TOOL", "happy --backend codex")

    cmd = get_ai_tool_command()
    assert cmd == ["happy", "--backend", "codex"]


def test_set_ai_tool(temp_config_dir: Path) -> None:
    """Test setting AI tool."""
    set_ai_tool("codex", ["--api-key", "test"])

    config = load_config()
    assert config["ai_tool"]["command"] == "codex"
    assert config["ai_tool"]["args"] == ["--api-key", "test"]


def test_set_ai_tool_no_args(temp_config_dir: Path) -> None:
    """Test setting AI tool without args."""
    set_ai_tool("happy")

    config = load_config()
    assert config["ai_tool"]["command"] == "happy"
    assert config["ai_tool"]["args"] == []


def test_use_preset(temp_config_dir: Path) -> None:
    """Test using a preset."""
    use_preset("happy")

    config = load_config()
    assert config["ai_tool"]["command"] == "happy"
    assert config["ai_tool"]["args"] == []


def test_use_preset_invalid(temp_config_dir: Path) -> None:
    """Test error when using invalid preset."""
    with pytest.raises(ConfigError, match="Unknown preset"):
        use_preset("invalid-preset")


def test_reset_config(temp_config_dir: Path) -> None:
    """Test resetting config to defaults."""
    # Modify config
    set_ai_tool("codex", ["--verbose"])
    set_config_value("git.default_base_branch", "develop")

    # Verify changes
    config = load_config()
    assert config["ai_tool"]["command"] == "codex"
    assert config["git"]["default_base_branch"] == "develop"

    # Reset
    reset_config()

    # Verify reset to defaults
    config = load_config()
    assert config == DEFAULT_CONFIG


def test_get_config_value(temp_config_dir: Path) -> None:
    """Test getting config value by key path."""
    import copy as copy_module

    config = copy_module.deepcopy(DEFAULT_CONFIG)
    config["ai_tool"]["command"] = "happy"
    save_config(config)

    value = get_config_value("ai_tool.command")
    assert value == "happy"


def test_get_config_value_nested(temp_config_dir: Path) -> None:
    """Test getting nested config value."""
    value = get_config_value("git.default_base_branch")
    assert value == "main"


def test_get_config_value_invalid_key(temp_config_dir: Path) -> None:
    """Test error when getting invalid config key."""
    with pytest.raises(ConfigError, match="Configuration key not found"):
        get_config_value("invalid.key.path")


def test_set_config_value(temp_config_dir: Path) -> None:
    """Test setting config value by key path."""
    set_config_value("git.default_base_branch", "develop")

    config = load_config()
    assert config["git"]["default_base_branch"] == "develop"


def test_set_config_value_creates_nested(temp_config_dir: Path) -> None:
    """Test setting config value creates nested structure."""
    set_config_value("new.nested.key", "value")

    config = load_config()
    assert config["new"]["nested"]["key"] == "value"


def test_show_config(temp_config_dir: Path) -> None:
    """Test showing config as formatted string."""
    # Ensure config file doesn't exist, then reset to defaults
    config_path = get_config_path()
    if config_path.exists():
        config_path.unlink()

    reset_config()

    output = show_config()

    # Should contain key information
    assert "AI Tool: claude" in output
    assert "Effective command: claude" in output
    assert "Default base branch: main" in output
    assert "Config file:" in output


def test_show_config_with_args(temp_config_dir: Path) -> None:
    """Test showing config with additional args."""
    set_ai_tool("happy", ["--backend", "claude", "--verbose"])

    output = show_config()

    assert "AI Tool: happy" in output
    assert "Args: --backend claude --verbose" in output


def test_list_presets() -> None:
    """Test listing available presets."""
    output = list_presets()

    # Should contain preset names and commands
    assert "Available AI tool presets:" in output
    for name, cmd in AI_TOOL_PRESETS.items():
        assert name in output
        assert " ".join(cmd) in output


def test_config_file_invalid_json(temp_config_dir: Path, monkeypatch) -> None:
    """Test error when config file contains invalid JSON."""
    config_path = get_config_path()
    config_path.write_text("{ invalid json }")

    with pytest.raises(ConfigError, match="Failed to load config"):
        load_config()


def test_config_merges_with_defaults(temp_config_dir: Path) -> None:
    """Test that partial config is merged with defaults."""
    # Ensure clean state
    config_path = get_config_path()
    if config_path.exists():
        config_path.unlink()

    # Save partial config (missing some keys)
    partial_config = {
        "ai_tool": {
            "command": "codex",
        },
    }

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(partial_config, f)

    # Load should merge with defaults
    config = load_config()

    # Should have custom value
    assert config["ai_tool"]["command"] == "codex"

    # Should have default values for missing keys
    assert "launch" in config
    assert "git" in config
    assert config["git"]["default_base_branch"] == "main"


def test_ai_tool_presets_defined() -> None:
    """Test that expected presets are defined."""
    expected_presets = [
        "no-op",
        "claude",
        "codex",
        "happy",
        "happy-codex",
        "happy-yolo",
    ]

    for preset in expected_presets:
        assert preset in AI_TOOL_PRESETS
        assert isinstance(AI_TOOL_PRESETS[preset], list)
        # no-op preset can be empty
        if preset != "no-op":
            assert len(AI_TOOL_PRESETS[preset]) > 0


def test_happy_preset_commands() -> None:
    """Test that Happy presets generate correct commands."""
    # Test basic happy (Claude Code mode)
    assert AI_TOOL_PRESETS["happy"] == ["happy"]

    # Test happy-codex (Codex mode with bypass permissions)
    assert AI_TOOL_PRESETS["happy-codex"] == [
        "happy",
        "codex",
        "--permission-mode",
        "bypassPermissions",
    ]

    # Test happy-yolo (with bypass permissions)
    assert AI_TOOL_PRESETS["happy-yolo"] == ["happy", "--permission-mode", "bypassPermissions"]


def test_use_happy_presets(temp_config_dir: Path) -> None:
    """Test using Happy presets."""
    # Test happy preset
    use_preset("happy")
    cmd = get_ai_tool_command()
    assert cmd == ["happy"]

    # Test happy-codex preset
    use_preset("happy-codex")
    cmd = get_ai_tool_command()
    assert cmd == ["happy", "codex", "--permission-mode", "bypassPermissions"]

    # Test happy-yolo preset
    use_preset("happy-yolo")
    cmd = get_ai_tool_command()
    assert cmd == ["happy", "--permission-mode", "bypassPermissions"]
