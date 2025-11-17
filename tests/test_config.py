"""Tests for config module."""

import json
from pathlib import Path

import pytest

from claude_worktree.config import (
    AI_TOOL_MERGE_PRESETS,
    AI_TOOL_PRESETS,
    AI_TOOL_RESUME_PRESETS,
    DEFAULT_CONFIG,
    ConfigError,
    add_copy_file,
    get_ai_tool_command,
    get_ai_tool_merge_command,
    get_ai_tool_resume_command,
    get_config_path,
    get_copy_files,
    list_copy_files,
    list_presets,
    load_config,
    remove_copy_file,
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

    # Mock HOME (Unix) and USERPROFILE (Windows) to use temp directory
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    # Also ensure no CW_AI_TOOL is set
    monkeypatch.delenv("CW_AI_TOOL", raising=False)

    return config_dir


def test_get_config_path(tmp_path: Path, monkeypatch) -> None:
    """Test getting config file path."""
    # Mock both HOME (Unix) and USERPROFILE (Windows)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

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
        "claude-yolo",
        "codex",
        "codex-yolo",
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


def test_claude_preset_commands() -> None:
    """Test that Claude presets generate correct commands."""
    # Test basic claude
    assert AI_TOOL_PRESETS["claude"] == ["claude"]

    # Test claude-yolo (with --dangerously-skip-permissions flag)
    assert AI_TOOL_PRESETS["claude-yolo"] == ["claude", "--dangerously-skip-permissions"]


def test_codex_preset_commands() -> None:
    """Test that Codex presets generate correct commands."""
    # Test basic codex
    assert AI_TOOL_PRESETS["codex"] == ["codex"]

    # Test codex-yolo (with --dangerously-bypass-approvals-and-sandbox flag)
    assert AI_TOOL_PRESETS["codex-yolo"] == [
        "codex",
        "--dangerously-bypass-approvals-and-sandbox",
    ]


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

    # Test happy-yolo (with --yolo flag for dangerously skip permissions)
    assert AI_TOOL_PRESETS["happy-yolo"] == ["happy", "--yolo"]


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
    assert cmd == ["happy", "--yolo"]


def test_get_ai_tool_resume_command_default(temp_config_dir: Path) -> None:
    """Test getting resume command with default AI tool."""
    cmd = get_ai_tool_resume_command()
    assert cmd == ["claude", "--continue"]


def test_get_ai_tool_resume_command_preset(temp_config_dir: Path) -> None:
    """Test getting resume command from preset."""
    import copy as copy_module

    config = copy_module.deepcopy(DEFAULT_CONFIG)
    config["ai_tool"]["command"] = "happy-codex"
    config["ai_tool"]["args"] = []
    save_config(config)

    cmd = get_ai_tool_resume_command()
    assert cmd == ["happy", "codex", "--permission-mode", "bypassPermissions", "--continue"]


def test_get_ai_tool_resume_command_no_tool(temp_config_dir: Path) -> None:
    """Test getting resume command when no AI tool configured."""
    import copy as copy_module

    config = copy_module.deepcopy(DEFAULT_CONFIG)
    config["ai_tool"]["command"] = "no-op"
    save_config(config)

    cmd = get_ai_tool_resume_command()
    assert cmd == []


def test_get_ai_tool_resume_command_env_override(temp_config_dir: Path, monkeypatch) -> None:
    """Test resume command respects environment variable override."""
    # Set config to use claude
    import copy as copy_module

    config = copy_module.deepcopy(DEFAULT_CONFIG)
    config["ai_tool"]["command"] = "claude"
    save_config(config)

    # Override with environment variable
    monkeypatch.setenv("CW_AI_TOOL", "happy --backend codex")

    cmd = get_ai_tool_resume_command()
    assert cmd == ["happy", "--backend", "codex", "--resume"]


def test_get_ai_tool_resume_command_codex(temp_config_dir: Path) -> None:
    """Test getting resume command for codex preset (uses subcommand syntax)."""
    import copy as copy_module

    config = copy_module.deepcopy(DEFAULT_CONFIG)
    config["ai_tool"]["command"] = "codex"
    config["ai_tool"]["args"] = []
    save_config(config)

    cmd = get_ai_tool_resume_command()
    # Codex uses "codex resume --last" instead of "codex --resume"
    assert cmd == ["codex", "resume", "--last"]


def test_get_ai_tool_resume_command_codex_yolo(temp_config_dir: Path) -> None:
    """Test getting resume command for codex-yolo preset."""
    import copy as copy_module

    config = copy_module.deepcopy(DEFAULT_CONFIG)
    config["ai_tool"]["command"] = "codex-yolo"
    config["ai_tool"]["args"] = []
    save_config(config)

    cmd = get_ai_tool_resume_command()
    assert cmd == ["codex", "resume", "--dangerously-bypass-approvals-and-sandbox", "--last"]


def test_get_ai_tool_resume_command_codex_with_extra_args(temp_config_dir: Path) -> None:
    """Test getting resume command for codex with additional args."""
    import copy as copy_module

    config = copy_module.deepcopy(DEFAULT_CONFIG)
    config["ai_tool"]["command"] = "codex"
    config["ai_tool"]["args"] = ["--model", "o3"]
    save_config(config)

    cmd = get_ai_tool_resume_command()
    # Extra args should be appended
    assert cmd == ["codex", "resume", "--last", "--model", "o3"]


def test_ai_tool_resume_presets_defined() -> None:
    """Test that resume presets are defined for tools that need special syntax."""
    # Claude uses --continue flag instead of --resume
    assert "claude" in AI_TOOL_RESUME_PRESETS
    assert "claude-yolo" in AI_TOOL_RESUME_PRESETS

    # Happy uses --continue flag (inherits from Claude Code)
    assert "happy" in AI_TOOL_RESUME_PRESETS
    assert "happy-codex" in AI_TOOL_RESUME_PRESETS
    assert "happy-yolo" in AI_TOOL_RESUME_PRESETS

    # Codex uses subcommand syntax
    assert "codex" in AI_TOOL_RESUME_PRESETS
    assert "codex-yolo" in AI_TOOL_RESUME_PRESETS


def test_default_config_has_shell_completion() -> None:
    """Test that DEFAULT_CONFIG includes shell_completion fields."""
    assert "shell_completion" in DEFAULT_CONFIG
    assert "prompted" in DEFAULT_CONFIG["shell_completion"]
    assert "installed" in DEFAULT_CONFIG["shell_completion"]
    assert DEFAULT_CONFIG["shell_completion"]["prompted"] is False
    assert DEFAULT_CONFIG["shell_completion"]["installed"] is False


def test_shell_completion_tracking(temp_config_dir: Path) -> None:
    """Test tracking shell completion setup status."""
    import copy as copy_module

    # Initial state: not prompted
    config = load_config()
    assert config["shell_completion"]["prompted"] is False
    assert config["shell_completion"]["installed"] is False

    # Mark as prompted and installed
    config = copy_module.deepcopy(config)
    config["shell_completion"]["prompted"] = True
    config["shell_completion"]["installed"] = True
    save_config(config)

    # Verify persistence
    loaded = load_config()
    assert loaded["shell_completion"]["prompted"] is True
    assert loaded["shell_completion"]["installed"] is True


def test_shell_completion_tracking_declined(temp_config_dir: Path) -> None:
    """Test tracking when user declines shell completion setup."""
    import copy as copy_module

    # User was prompted but declined
    config = load_config()
    config = copy_module.deepcopy(config)
    config["shell_completion"]["prompted"] = True
    config["shell_completion"]["installed"] = False
    save_config(config)

    # Verify persistence
    loaded = load_config()
    assert loaded["shell_completion"]["prompted"] is True
    assert loaded["shell_completion"]["installed"] is False


def test_get_ai_tool_merge_command_claude(temp_config_dir: Path) -> None:
    """Test getting merge command for claude preset."""
    import copy as copy_module

    config = copy_module.deepcopy(DEFAULT_CONFIG)
    config["ai_tool"]["command"] = "claude"
    config["ai_tool"]["args"] = []
    save_config(config)

    prompt = "Resolve conflicts in test.txt"
    cmd = get_ai_tool_merge_command(prompt)
    # Should include --print and --tools=default flags for non-interactive execution
    assert cmd == ["claude", "--print", "--tools=default", prompt]


def test_get_ai_tool_merge_command_claude_yolo(temp_config_dir: Path) -> None:
    """Test getting merge command for claude-yolo preset."""
    import copy as copy_module

    config = copy_module.deepcopy(DEFAULT_CONFIG)
    config["ai_tool"]["command"] = "claude-yolo"
    config["ai_tool"]["args"] = []
    save_config(config)

    prompt = "Resolve conflicts"
    cmd = get_ai_tool_merge_command(prompt)
    # Should include base command + merge flags + prompt
    assert cmd == [
        "claude",
        "--dangerously-skip-permissions",
        "--print",
        "--tools=default",
        prompt,
    ]


def test_get_ai_tool_merge_command_codex(temp_config_dir: Path) -> None:
    """Test getting merge command for codex preset."""
    import copy as copy_module

    config = copy_module.deepcopy(DEFAULT_CONFIG)
    config["ai_tool"]["command"] = "codex"
    config["ai_tool"]["args"] = []
    save_config(config)

    prompt = "Fix merge conflicts"
    cmd = get_ai_tool_merge_command(prompt)
    # Should use --non-interactive flag for codex
    assert cmd == ["codex", "--non-interactive", prompt]


def test_get_ai_tool_merge_command_with_extra_args(temp_config_dir: Path) -> None:
    """Test getting merge command with additional args."""
    import copy as copy_module

    config = copy_module.deepcopy(DEFAULT_CONFIG)
    config["ai_tool"]["command"] = "claude"
    config["ai_tool"]["args"] = ["--verbose"]
    save_config(config)

    prompt = "Resolve conflicts"
    cmd = get_ai_tool_merge_command(prompt)
    # Extra args should be inserted between base and merge flags
    assert cmd == ["claude", "--verbose", "--print", "--tools=default", prompt]


def test_get_ai_tool_merge_command_env_override(temp_config_dir: Path, monkeypatch) -> None:
    """Test merge command respects environment variable override."""
    import copy as copy_module

    config = copy_module.deepcopy(DEFAULT_CONFIG)
    config["ai_tool"]["command"] = "claude"
    save_config(config)

    # Override with environment variable
    monkeypatch.setenv("CW_AI_TOOL", "custom-tool --flag")

    prompt = "Resolve conflicts"
    cmd = get_ai_tool_merge_command(prompt)
    # Environment override: use base command + prompt
    assert cmd == ["custom-tool", "--flag", prompt]


def test_get_ai_tool_merge_command_no_tool(temp_config_dir: Path) -> None:
    """Test getting merge command when no AI tool configured."""
    import copy as copy_module

    config = copy_module.deepcopy(DEFAULT_CONFIG)
    config["ai_tool"]["command"] = "no-op"
    save_config(config)

    prompt = "Resolve conflicts"
    cmd = get_ai_tool_merge_command(prompt)
    assert cmd == []


def test_ai_tool_merge_presets_defined() -> None:
    """Test that merge presets are defined for supported tools."""
    # Claude presets should have merge configurations
    assert "claude" in AI_TOOL_MERGE_PRESETS
    assert "claude-yolo" in AI_TOOL_MERGE_PRESETS

    # Happy presets
    assert "happy" in AI_TOOL_MERGE_PRESETS
    assert "happy-codex" in AI_TOOL_MERGE_PRESETS
    assert "happy-yolo" in AI_TOOL_MERGE_PRESETS

    # Codex presets
    assert "codex" in AI_TOOL_MERGE_PRESETS
    assert "codex-yolo" in AI_TOOL_MERGE_PRESETS

    # Verify structure
    for _preset, config in AI_TOOL_MERGE_PRESETS.items():
        assert "flags" in config
        assert "prompt_position" in config
        assert isinstance(config["flags"], list)
        assert config["prompt_position"] in ["end", 0, 1, 2, 3]  # Valid positions


def test_get_ai_tool_merge_command_happy_yolo(temp_config_dir: Path) -> None:
    """Test getting merge command for happy-yolo preset."""
    import copy as copy_module

    config = copy_module.deepcopy(DEFAULT_CONFIG)
    config["ai_tool"]["command"] = "happy-yolo"
    config["ai_tool"]["args"] = []
    save_config(config)

    prompt = "Resolve conflicts"
    cmd = get_ai_tool_merge_command(prompt)
    # Should include happy --yolo + merge flags
    assert cmd == ["happy", "--yolo", "--print", "--tools=default", prompt]


# Copy files configuration tests


def test_get_copy_files_default(temp_config_dir: Path) -> None:
    """Test getting copy files with default configuration."""
    copy_files = get_copy_files()
    assert copy_files == []


def test_add_copy_file(temp_config_dir: Path) -> None:
    """Test adding a file to copy list."""
    add_copy_file(".env")
    copy_files = get_copy_files()
    assert ".env" in copy_files


def test_add_copy_file_no_duplicates(temp_config_dir: Path) -> None:
    """Test that adding the same file twice doesn't create duplicates."""
    add_copy_file(".env")
    add_copy_file(".env")
    copy_files = get_copy_files()
    assert copy_files.count(".env") == 1


def test_add_multiple_copy_files(temp_config_dir: Path) -> None:
    """Test adding multiple files to copy list."""
    add_copy_file(".env")
    add_copy_file(".env.local")
    add_copy_file("config/local.json")

    copy_files = get_copy_files()
    assert ".env" in copy_files
    assert ".env.local" in copy_files
    assert "config/local.json" in copy_files
    assert len(copy_files) == 3


def test_remove_copy_file(temp_config_dir: Path) -> None:
    """Test removing a file from copy list."""
    add_copy_file(".env")
    add_copy_file(".env.local")

    removed = remove_copy_file(".env")
    assert removed is True

    copy_files = get_copy_files()
    assert ".env" not in copy_files
    assert ".env.local" in copy_files


def test_remove_copy_file_not_in_list(temp_config_dir: Path) -> None:
    """Test removing a file that's not in the copy list."""
    add_copy_file(".env")

    removed = remove_copy_file(".env.local")
    assert removed is False

    copy_files = get_copy_files()
    assert ".env" in copy_files


def test_list_copy_files_empty(temp_config_dir: Path) -> None:
    """Test listing copy files when list is empty."""
    output = list_copy_files()
    assert "No files configured" in output
    assert "cw config copy-files add" in output


def test_list_copy_files_with_files(temp_config_dir: Path) -> None:
    """Test listing copy files when files are configured."""
    add_copy_file(".env")
    add_copy_file(".env.local")

    output = list_copy_files()
    assert "Files to copy to new worktrees:" in output
    assert ".env" in output
    assert ".env.local" in output


def test_copy_files_persist_after_reload(temp_config_dir: Path) -> None:
    """Test that copy files configuration persists after reload."""
    add_copy_file(".env")
    add_copy_file(".env.local")

    # Reload config
    config = load_config()
    copy_files = config["worktree"]["copy_files"]
    assert ".env" in copy_files
    assert ".env.local" in copy_files
