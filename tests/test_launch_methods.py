"""Tests for terminal launch methods."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from claude_worktree.config import (
    ConfigError,
    get_default_launch_method,
    parse_term_option,
    resolve_launch_alias,
)
from claude_worktree.constants import (
    LAUNCH_METHOD_ALIASES,
    MAX_SESSION_NAME_LENGTH,
    LaunchMethod,
)


class TestLaunchMethodEnum:
    """Test LaunchMethod enum and aliases."""

    def test_all_enum_values_exist(self):
        """Test that all expected enum values exist."""
        expected_methods = [
            "foreground", "detach",
            "iterm-window", "iterm-tab", "iterm-pane-h", "iterm-pane-v",
            "tmux", "tmux-window", "tmux-pane-h", "tmux-pane-v",
            "zellij", "zellij-tab", "zellij-pane-h", "zellij-pane-v",
            "wezterm-window", "wezterm-tab", "wezterm-pane-h", "wezterm-pane-v",
        ]
        for method in expected_methods:
            assert LaunchMethod(method).value == method

    def test_enum_is_string(self):
        """Test that enum values are strings."""
        assert LaunchMethod.FOREGROUND == "foreground"
        assert LaunchMethod.TMUX.value == "tmux"
        # Test string comparison works (str(Enum) inherits from str)
        assert LaunchMethod.FOREGROUND == "foreground"


class TestAliasResolution:
    """Test alias resolution."""

    def test_simple_aliases(self):
        """Test simple alias resolution."""
        assert resolve_launch_alias("fg") == "foreground"
        assert resolve_launch_alias("d") == "detach"

    def test_iterm_aliases(self):
        """Test iTerm aliases."""
        assert resolve_launch_alias("i-w") == "iterm-window"
        assert resolve_launch_alias("i-t") == "iterm-tab"
        assert resolve_launch_alias("i-p-h") == "iterm-pane-h"
        assert resolve_launch_alias("i-p-v") == "iterm-pane-v"

    def test_tmux_aliases(self):
        """Test tmux aliases."""
        assert resolve_launch_alias("t") == "tmux"
        assert resolve_launch_alias("t-w") == "tmux-window"
        assert resolve_launch_alias("t-p-h") == "tmux-pane-h"
        assert resolve_launch_alias("t-p-v") == "tmux-pane-v"

    def test_zellij_aliases(self):
        """Test Zellij aliases."""
        assert resolve_launch_alias("z") == "zellij"
        assert resolve_launch_alias("z-t") == "zellij-tab"
        assert resolve_launch_alias("z-p-h") == "zellij-pane-h"
        assert resolve_launch_alias("z-p-v") == "zellij-pane-v"

    def test_wezterm_aliases(self):
        """Test WezTerm aliases."""
        assert resolve_launch_alias("w-w") == "wezterm-window"
        assert resolve_launch_alias("w-t") == "wezterm-tab"
        assert resolve_launch_alias("w-p-h") == "wezterm-pane-h"
        assert resolve_launch_alias("w-p-v") == "wezterm-pane-v"

    def test_session_name_aliases(self):
        """Test alias resolution with session names."""
        assert resolve_launch_alias("t:mywork") == "tmux:mywork"
        assert resolve_launch_alias("z:dev") == "zellij:dev"
        assert resolve_launch_alias("t:my-session-name") == "tmux:my-session-name"

    def test_no_alias_passthrough(self):
        """Test that non-aliases are passed through."""
        assert resolve_launch_alias("tmux") == "tmux"
        assert resolve_launch_alias("zellij") == "zellij"
        assert resolve_launch_alias("foreground") == "foreground"
        assert resolve_launch_alias("unknown") == "unknown"

    def test_all_aliases_have_valid_targets(self):
        """Test that all aliases map to valid LaunchMethod values."""
        for _alias, full_name in LAUNCH_METHOD_ALIASES.items():
            # Should not raise
            LaunchMethod(full_name)


class TestParseTermOption:
    """Test parse_term_option function."""

    def test_none_returns_default(self):
        """Test that None returns default launch method."""
        with patch("claude_worktree.config.get_default_launch_method") as mock:
            mock.return_value = LaunchMethod.FOREGROUND
            method, session = parse_term_option(None)
            assert method == LaunchMethod.FOREGROUND
            assert session is None

    def test_simple_aliases(self):
        """Test parsing simple aliases."""
        method, session = parse_term_option("i-t")
        assert method == LaunchMethod.ITERM_TAB
        assert session is None

        method, session = parse_term_option("z-p-h")
        assert method == LaunchMethod.ZELLIJ_PANE_H
        assert session is None

    def test_full_names(self):
        """Test parsing full names."""
        method, session = parse_term_option("foreground")
        assert method == LaunchMethod.FOREGROUND
        assert session is None

        method, session = parse_term_option("tmux-window")
        assert method == LaunchMethod.TMUX_WINDOW
        assert session is None

    def test_session_names(self):
        """Test parsing with session names."""
        method, session = parse_term_option("t:mywork")
        assert method == LaunchMethod.TMUX
        assert session == "mywork"

        method, session = parse_term_option("z:dev")
        assert method == LaunchMethod.ZELLIJ
        assert session == "dev"

        method, session = parse_term_option("tmux:my-session")
        assert method == LaunchMethod.TMUX
        assert session == "my-session"

    def test_session_name_length_limit(self):
        """Test session name length validation."""
        long_name = "a" * (MAX_SESSION_NAME_LENGTH + 1)
        with pytest.raises(ConfigError, match="Session name too long"):
            parse_term_option(f"t:{long_name}")

    def test_session_name_at_limit(self):
        """Test session name at exactly the limit."""
        name = "a" * MAX_SESSION_NAME_LENGTH
        method, session = parse_term_option(f"t:{name}")
        assert method == LaunchMethod.TMUX
        assert session == name

    def test_invalid_method(self):
        """Test invalid launch method."""
        with pytest.raises(ConfigError, match="Invalid launch method"):
            parse_term_option("invalid-method")

    def test_session_name_on_unsupported_method(self):
        """Test session name on method that doesn't support it."""
        with pytest.raises(ConfigError, match="Session name not supported"):
            parse_term_option("i-w:mysession")

        with pytest.raises(ConfigError, match="Session name not supported"):
            parse_term_option("wezterm-window:test")


class TestGetDefaultLaunchMethod:
    """Test get_default_launch_method function."""

    def test_env_override(self):
        """Test environment variable overrides config."""
        with patch.dict(os.environ, {"CW_LAUNCH_METHOD": "i-t"}):
            with patch("claude_worktree.config.load_config") as mock_config:
                mock_config.return_value = {"launch": {"method": "d"}}
                method = get_default_launch_method()
                assert method == LaunchMethod.ITERM_TAB

    def test_config_default(self):
        """Test config file default."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove CW_LAUNCH_METHOD if present
            os.environ.pop("CW_LAUNCH_METHOD", None)
            with patch("claude_worktree.config.load_config") as mock_config:
                mock_config.return_value = {"launch": {"method": "z-p-h"}}
                method = get_default_launch_method()
                assert method == LaunchMethod.ZELLIJ_PANE_H

    def test_fallback_foreground(self):
        """Test fallback to foreground."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("CW_LAUNCH_METHOD", None)
            with patch("claude_worktree.config.load_config") as mock_config:
                mock_config.return_value = {}
                method = get_default_launch_method()
                assert method == LaunchMethod.FOREGROUND

    def test_invalid_env_value_falls_through(self):
        """Test that invalid env value falls through to config."""
        with patch.dict(os.environ, {"CW_LAUNCH_METHOD": "invalid"}):
            with patch("claude_worktree.config.load_config") as mock_config:
                mock_config.return_value = {"launch": {"method": "d"}}
                method = get_default_launch_method()
                assert method == LaunchMethod.DETACH


class TestLauncherFunctions:
    """Test individual launcher functions with mocks."""

    @patch("subprocess.run")
    @patch("sys.platform", "darwin")
    def test_iterm_pane_horizontal(self, mock_run):
        """Test iTerm horizontal pane split."""
        from claude_worktree.operations.ai_tools import _launch_iterm_pane

        path = Path("/test/worktree")
        command = "claude --resume"

        _launch_iterm_pane(path, command, "claude", horizontal=True)

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        # Check that the script contains "horizontally"
        assert "horizontally" in call_args[0][0][2]

    @patch("subprocess.run")
    @patch("sys.platform", "darwin")
    def test_iterm_pane_vertical(self, mock_run):
        """Test iTerm vertical pane split."""
        from claude_worktree.operations.ai_tools import _launch_iterm_pane

        path = Path("/test/worktree")
        command = "claude --resume"

        _launch_iterm_pane(path, command, "claude", horizontal=False)

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "vertically" in call_args[0][0][2]

    @patch("sys.platform", "linux")
    def test_iterm_pane_non_macos(self):
        """Test iTerm pane fails on non-macOS."""
        from claude_worktree.exceptions import GitError
        from claude_worktree.operations.ai_tools import _launch_iterm_pane

        with pytest.raises(GitError, match="only works on macOS"):
            _launch_iterm_pane(Path("/test"), "command", "claude")

    @patch("claude_worktree.operations.ai_tools.has_command", return_value=True)
    @patch("subprocess.run")
    def test_tmux_session(self, mock_run, mock_has_command):
        """Test tmux new session creation."""
        from claude_worktree.operations.ai_tools import _launch_tmux_session

        path = Path("/test/worktree")
        command = "claude --resume"
        session_name = "test-session"

        _launch_tmux_session(path, command, "claude", session_name)

        # Should call: new-session, send-keys, attach-session
        assert mock_run.call_count == 3
        calls = mock_run.call_args_list

        # new-session
        new_session_args = calls[0][0][0]
        assert "new-session" in new_session_args
        assert "-s" in new_session_args
        assert session_name in new_session_args

        # send-keys
        send_keys_args = calls[1][0][0]
        assert "send-keys" in send_keys_args
        assert command in send_keys_args

        # attach-session
        attach_args = calls[2][0][0]
        assert "attach-session" in attach_args

    @patch.dict(os.environ, {"TMUX": "/tmp/tmux-1000/default,1,0"})
    @patch("subprocess.run")
    def test_tmux_window(self, mock_run):
        """Test tmux new window creation."""
        from claude_worktree.operations.ai_tools import _launch_tmux_window

        path = Path("/test/worktree")
        command = "claude --resume"

        _launch_tmux_window(path, command, "claude")

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "new-window" in call_args
        assert "-c" in call_args

    @patch.dict(os.environ, {}, clear=True)
    def test_tmux_window_not_in_session(self):
        """Test tmux window fails outside session."""
        os.environ.pop("TMUX", None)
        from claude_worktree.exceptions import GitError
        from claude_worktree.operations.ai_tools import _launch_tmux_window

        with pytest.raises(GitError, match="requires running inside a tmux session"):
            _launch_tmux_window(Path("/test"), "command", "claude")

    @patch.dict(os.environ, {"TMUX": "/tmp/tmux-1000/default,1,0"})
    @patch("subprocess.run")
    def test_tmux_pane_horizontal(self, mock_run):
        """Test tmux horizontal pane split."""
        from claude_worktree.operations.ai_tools import _launch_tmux_pane

        path = Path("/test/worktree")
        command = "claude --resume"

        _launch_tmux_pane(path, command, "claude", horizontal=True)

        call_args = mock_run.call_args[0][0]
        assert "split-window" in call_args
        assert "-h" in call_args

    @patch.dict(os.environ, {"TMUX": "/tmp/tmux-1000/default,1,0"})
    @patch("subprocess.run")
    def test_tmux_pane_vertical(self, mock_run):
        """Test tmux vertical pane split."""
        from claude_worktree.operations.ai_tools import _launch_tmux_pane

        path = Path("/test/worktree")
        command = "claude --resume"

        _launch_tmux_pane(path, command, "claude", horizontal=False)

        call_args = mock_run.call_args[0][0]
        assert "split-window" in call_args
        assert "-v" in call_args

    @patch("claude_worktree.operations.ai_tools.has_command", return_value=True)
    @patch("subprocess.run")
    def test_zellij_session(self, mock_run, mock_has_command):
        """Test Zellij new session creation."""
        from claude_worktree.operations.ai_tools import _launch_zellij_session

        path = Path("/test/worktree")
        command = "claude --resume"
        session_name = "test-session"

        _launch_zellij_session(path, command, "claude", session_name)

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "zellij" in call_args
        assert "-s" in call_args
        assert session_name in call_args
        assert mock_run.call_args[1]["cwd"] == path

    @patch.dict(os.environ, {"ZELLIJ": "0"})
    @patch("subprocess.run")
    def test_zellij_tab(self, mock_run):
        """Test Zellij new tab creation."""
        from claude_worktree.operations.ai_tools import _launch_zellij_tab

        path = Path("/test/worktree")
        command = "claude --resume"

        _launch_zellij_tab(path, command, "claude")

        call_args = mock_run.call_args[0][0]
        assert "zellij" in call_args
        assert "action" in call_args
        assert "new-tab" in call_args
        assert "--cwd" in call_args

    @patch.dict(os.environ, {}, clear=True)
    def test_zellij_tab_not_in_session(self):
        """Test Zellij tab fails outside session."""
        os.environ.pop("ZELLIJ", None)
        from claude_worktree.exceptions import GitError
        from claude_worktree.operations.ai_tools import _launch_zellij_tab

        with pytest.raises(GitError, match="requires running inside a Zellij session"):
            _launch_zellij_tab(Path("/test"), "command", "claude")

    @patch.dict(os.environ, {"ZELLIJ": "0"})
    @patch("subprocess.run")
    def test_zellij_pane_horizontal(self, mock_run):
        """Test Zellij horizontal pane split."""
        from claude_worktree.operations.ai_tools import _launch_zellij_pane

        path = Path("/test/worktree")
        command = "claude --resume"

        _launch_zellij_pane(path, command, "claude", horizontal=True)

        call_args = mock_run.call_args[0][0]
        assert "new-pane" in call_args
        assert "-d" in call_args
        assert "right" in call_args

    @patch.dict(os.environ, {"ZELLIJ": "0"})
    @patch("subprocess.run")
    def test_zellij_pane_vertical(self, mock_run):
        """Test Zellij vertical pane split."""
        from claude_worktree.operations.ai_tools import _launch_zellij_pane

        path = Path("/test/worktree")
        command = "claude --resume"

        _launch_zellij_pane(path, command, "claude", horizontal=False)

        call_args = mock_run.call_args[0][0]
        assert "new-pane" in call_args
        assert "-d" in call_args
        assert "down" in call_args

    @patch("claude_worktree.operations.ai_tools.has_command", return_value=True)
    @patch("subprocess.run")
    def test_wezterm_window(self, mock_run, mock_has_command):
        """Test WezTerm new window creation."""
        from claude_worktree.operations.ai_tools import _launch_wezterm_window

        path = Path("/test/worktree")
        command = "claude --resume"

        _launch_wezterm_window(path, command, "claude")

        call_args = mock_run.call_args[0][0]
        assert "wezterm" in call_args
        assert "cli" in call_args
        assert "spawn" in call_args
        assert "--new-window" in call_args
        assert "--cwd" in call_args

    @patch("claude_worktree.operations.ai_tools.has_command", return_value=True)
    @patch("subprocess.run")
    def test_wezterm_tab(self, mock_run, mock_has_command):
        """Test WezTerm new tab creation."""
        from claude_worktree.operations.ai_tools import _launch_wezterm_tab

        path = Path("/test/worktree")
        command = "claude --resume"

        _launch_wezterm_tab(path, command, "claude")

        call_args = mock_run.call_args[0][0]
        assert "wezterm" in call_args
        assert "spawn" in call_args
        assert "--cwd" in call_args

    @patch("claude_worktree.operations.ai_tools.has_command", return_value=True)
    @patch("subprocess.run")
    def test_wezterm_pane_horizontal(self, mock_run, mock_has_command):
        """Test WezTerm horizontal pane split."""
        from claude_worktree.operations.ai_tools import _launch_wezterm_pane

        path = Path("/test/worktree")
        command = "claude --resume"

        _launch_wezterm_pane(path, command, "claude", horizontal=True)

        call_args = mock_run.call_args[0][0]
        assert "split-pane" in call_args
        assert "--horizontal" in call_args

    @patch("claude_worktree.operations.ai_tools.has_command", return_value=True)
    @patch("subprocess.run")
    def test_wezterm_pane_vertical(self, mock_run, mock_has_command):
        """Test WezTerm vertical pane split."""
        from claude_worktree.operations.ai_tools import _launch_wezterm_pane

        path = Path("/test/worktree")
        command = "claude --resume"

        _launch_wezterm_pane(path, command, "claude", horizontal=False)

        call_args = mock_run.call_args[0][0]
        assert "split-pane" in call_args
        assert "--bottom" in call_args


class TestLaunchAIToolIntegration:
    """Test launch_ai_tool function with --term option."""

    @patch("claude_worktree.operations.ai_tools._launch_iterm_pane")
    @patch("claude_worktree.operations.ai_tools.has_command", return_value=True)
    @patch("claude_worktree.operations.ai_tools.get_ai_tool_command", return_value=["claude"])
    def test_launch_iterm_pane_alias(self, mock_cmd, mock_has, mock_launch):
        """Test launch with iTerm pane alias."""
        from claude_worktree.operations.ai_tools import launch_ai_tool

        path = Path("/test/worktree")
        launch_ai_tool(path, term="i-p-h")

        mock_launch.assert_called_once()
        # Check horizontal=True
        assert mock_launch.call_args[1]["horizontal"] is True

    @patch("claude_worktree.operations.ai_tools._launch_tmux_session")
    @patch("claude_worktree.operations.ai_tools.has_command", return_value=True)
    @patch("claude_worktree.operations.ai_tools.get_ai_tool_command", return_value=["claude"])
    def test_launch_tmux_with_session_name(self, mock_cmd, mock_has, mock_launch):
        """Test launch tmux with custom session name."""
        from claude_worktree.operations.ai_tools import launch_ai_tool

        path = Path("/test/worktree")
        launch_ai_tool(path, term="t:mywork")

        mock_launch.assert_called_once()
        # Check session_name is passed
        assert mock_launch.call_args[0][3] == "mywork"

    @patch("claude_worktree.operations.ai_tools._run_detached")
    @patch("claude_worktree.operations.ai_tools.has_command", return_value=True)
    @patch("claude_worktree.operations.ai_tools.get_ai_tool_command", return_value=["claude"])
    def test_deprecated_bg_param(self, mock_cmd, mock_has, mock_run):
        """Test deprecated --bg parameter shows warning."""
        from claude_worktree.operations.ai_tools import launch_ai_tool

        with pytest.warns(DeprecationWarning, match="--bg is deprecated. Use --term detach instead"):
            launch_ai_tool(Path("/test"), bg=True)

        mock_run.assert_called_once()

    @patch("claude_worktree.operations.ai_tools._launch_iterm_window")
    @patch("claude_worktree.operations.ai_tools.has_command", return_value=True)
    @patch("claude_worktree.operations.ai_tools.get_ai_tool_command", return_value=["claude"])
    def test_deprecated_iterm_param(self, mock_cmd, mock_has, mock_launch):
        """Test deprecated --iterm parameter shows warning."""
        from claude_worktree.operations.ai_tools import launch_ai_tool

        with pytest.warns(DeprecationWarning, match="--iterm is deprecated"):
            launch_ai_tool(Path("/test"), iterm=True)

        mock_launch.assert_called_once()

    @patch("claude_worktree.operations.ai_tools._launch_iterm_tab")
    @patch("claude_worktree.operations.ai_tools.has_command", return_value=True)
    @patch("claude_worktree.operations.ai_tools.get_ai_tool_command", return_value=["claude"])
    def test_deprecated_iterm_tab_param(self, mock_cmd, mock_has, mock_launch):
        """Test deprecated --iterm-tab parameter shows warning."""
        from claude_worktree.operations.ai_tools import launch_ai_tool

        with pytest.warns(DeprecationWarning, match="--iterm-tab is deprecated"):
            launch_ai_tool(Path("/test"), iterm_tab=True)

        mock_launch.assert_called_once()

    @patch("claude_worktree.operations.ai_tools._launch_tmux_session")
    @patch("claude_worktree.operations.ai_tools.has_command", return_value=True)
    @patch("claude_worktree.operations.ai_tools.get_ai_tool_command", return_value=["claude"])
    def test_deprecated_tmux_session_param(self, mock_cmd, mock_has, mock_launch):
        """Test deprecated --tmux parameter shows warning."""
        from claude_worktree.operations.ai_tools import launch_ai_tool

        with pytest.warns(DeprecationWarning, match="--tmux is deprecated"):
            launch_ai_tool(Path("/test"), tmux_session="mysession")

        mock_launch.assert_called_once()
        # Check session name is passed
        assert mock_launch.call_args[0][3] == "mysession"


class TestSessionNameGeneration:
    """Test session name generation."""

    @patch("claude_worktree.operations.ai_tools.load_config")
    def test_generate_session_name_default_prefix(self, mock_config):
        """Test session name with default prefix."""
        from claude_worktree.operations.ai_tools import _generate_session_name

        mock_config.return_value = {"launch": {"session_prefix": "cw"}}
        path = Path("/home/user/project-feature")

        name = _generate_session_name(path)
        assert name == "cw-project-feature"

    @patch("claude_worktree.operations.ai_tools.load_config")
    def test_generate_session_name_custom_prefix(self, mock_config):
        """Test session name with custom prefix."""
        from claude_worktree.operations.ai_tools import _generate_session_name

        mock_config.return_value = {"launch": {"session_prefix": "myproject"}}
        path = Path("/home/user/project-feature")

        name = _generate_session_name(path)
        assert name == "myproject-project-feature"

    @patch("claude_worktree.operations.ai_tools.load_config")
    def test_generate_session_name_truncation(self, mock_config):
        """Test session name is truncated if too long."""
        from claude_worktree.operations.ai_tools import _generate_session_name

        mock_config.return_value = {"launch": {"session_prefix": "cw"}}
        # Create a very long path name
        long_name = "a" * 100
        path = Path(f"/home/user/{long_name}")

        name = _generate_session_name(path)
        assert len(name) <= MAX_SESSION_NAME_LENGTH
        assert name.startswith("cw-")


class TestSmartContinueDetection:
    """Test smart --continue auto-detection in launch_ai_tool."""

    @patch("claude_worktree.operations.ai_tools._run_command_in_shell")
    @patch("claude_worktree.operations.ai_tools.has_command", return_value=True)
    @patch("claude_worktree.operations.ai_tools.is_claude_tool", return_value=True)
    @patch(
        "claude_worktree.operations.ai_tools.get_ai_tool_resume_command",
        return_value=["claude", "--continue"],
    )
    @patch(
        "claude_worktree.operations.ai_tools.get_ai_tool_command",
        return_value=["claude"],
    )
    @patch("claude_worktree.session_manager.claude_native_session_exists", return_value=True)
    def test_launch_uses_continue_when_native_session_exists(
        self, mock_native, mock_cmd, mock_resume_cmd, mock_is_claude, mock_has, mock_run
    ):
        """Test that launch_ai_tool adds --continue when native session exists."""
        from claude_worktree.operations.ai_tools import launch_ai_tool

        path = Path("/test/worktree")
        launch_ai_tool(path)

        # Should use resume command (--continue), not regular command
        mock_resume_cmd.assert_called_once()
        mock_cmd.assert_not_called()
        mock_run.assert_called_once()
        # Verify the command string contains --continue
        cmd_str = mock_run.call_args[0][0]
        assert "--continue" in cmd_str

    @patch("claude_worktree.operations.ai_tools._run_command_in_shell")
    @patch("claude_worktree.operations.ai_tools.has_command", return_value=True)
    @patch("claude_worktree.operations.ai_tools.is_claude_tool", return_value=True)
    @patch(
        "claude_worktree.operations.ai_tools.get_ai_tool_resume_command",
        return_value=["claude", "--continue"],
    )
    @patch(
        "claude_worktree.operations.ai_tools.get_ai_tool_command",
        return_value=["claude"],
    )
    @patch("claude_worktree.session_manager.claude_native_session_exists", return_value=False)
    def test_launch_skips_continue_when_no_native_session(
        self, mock_native, mock_cmd, mock_resume_cmd, mock_is_claude, mock_has, mock_run
    ):
        """Test that launch_ai_tool uses regular command when no session exists."""
        from claude_worktree.operations.ai_tools import launch_ai_tool

        path = Path("/test/worktree")
        launch_ai_tool(path)

        # Should use regular command, not resume
        mock_cmd.assert_called_once()
        mock_resume_cmd.assert_not_called()
        mock_run.assert_called_once()
        cmd_str = mock_run.call_args[0][0]
        assert "--continue" not in cmd_str

    @patch("claude_worktree.operations.ai_tools._run_command_in_shell")
    @patch("claude_worktree.operations.ai_tools.has_command", return_value=True)
    @patch("claude_worktree.operations.ai_tools.is_claude_tool", return_value=False)
    @patch(
        "claude_worktree.operations.ai_tools.get_ai_tool_command",
        return_value=["codex"],
    )
    def test_launch_skips_continue_for_non_claude_tool(
        self, mock_cmd, mock_is_claude, mock_has, mock_run
    ):
        """Test that smart --continue is skipped for non-Claude tools."""
        from claude_worktree.operations.ai_tools import launch_ai_tool

        path = Path("/test/worktree")
        launch_ai_tool(path)

        # Should use regular command without checking native sessions
        mock_cmd.assert_called_once()
        mock_run.assert_called_once()

    @patch("claude_worktree.operations.ai_tools._run_command_in_shell")
    @patch("claude_worktree.operations.ai_tools.has_command", return_value=True)
    @patch("claude_worktree.operations.ai_tools.is_claude_tool", return_value=True)
    @patch(
        "claude_worktree.operations.ai_tools.get_ai_tool_resume_command",
        return_value=["claude", "--continue"],
    )
    def test_launch_resume_flag_bypasses_smart_continue(
        self, mock_resume_cmd, mock_is_claude, mock_has, mock_run
    ):
        """Test that explicit resume=True bypasses smart --continue detection."""
        from claude_worktree.operations.ai_tools import launch_ai_tool

        path = Path("/test/worktree")
        # resume=True should go directly to resume command, no native session check
        launch_ai_tool(path, resume=True)

        mock_resume_cmd.assert_called_once()
        # is_claude_tool should not be consulted when resume=True
        mock_is_claude.assert_not_called()
