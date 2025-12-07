"""Tests for .cwshare file setup prompt."""

from pathlib import Path
from unittest.mock import patch

from claude_worktree.cwshare_setup import (
    COMMON_SHARED_FILES,
    create_cwshare_template,
    detect_common_files,
    has_cwshare_file,
    is_cwshare_prompted,
    mark_cwshare_prompted,
    prompt_cwshare_setup,
)


class TestIsCwsharePrompted:
    """Tests for is_cwshare_prompted function."""

    def test_returns_false_when_not_prompted(self, temp_git_repo: Path) -> None:
        """Should return False when cwshare.prompted is not set."""
        assert is_cwshare_prompted(temp_git_repo) is False

    def test_returns_true_when_prompted(self, temp_git_repo: Path) -> None:
        """Should return True when cwshare.prompted is set to true."""
        mark_cwshare_prompted(temp_git_repo)
        assert is_cwshare_prompted(temp_git_repo) is True


class TestMarkCwsharePrompted:
    """Tests for mark_cwshare_prompted function."""

    def test_sets_git_config(self, temp_git_repo: Path) -> None:
        """Should set cwshare.prompted to true in git config."""
        mark_cwshare_prompted(temp_git_repo)

        from claude_worktree.git_utils import get_config

        assert get_config("cwshare.prompted", repo=temp_git_repo) == "true"


class TestHasCwshareFile:
    """Tests for has_cwshare_file function."""

    def test_returns_false_when_no_file(self, temp_git_repo: Path) -> None:
        """Should return False when .cwshare does not exist."""
        assert has_cwshare_file(temp_git_repo) is False

    def test_returns_true_when_file_exists(self, temp_git_repo: Path) -> None:
        """Should return True when .cwshare exists."""
        (temp_git_repo / ".cwshare").write_text("# test")
        assert has_cwshare_file(temp_git_repo) is True


class TestDetectCommonFiles:
    """Tests for detect_common_files function."""

    def test_detects_no_files_in_empty_repo(self, temp_git_repo: Path) -> None:
        """Should return empty list when no common files exist."""
        assert detect_common_files(temp_git_repo) == []

    def test_detects_env_file(self, temp_git_repo: Path) -> None:
        """Should detect .env file."""
        (temp_git_repo / ".env").write_text("SECRET=123")
        detected = detect_common_files(temp_git_repo)
        assert ".env" in detected

    def test_detects_multiple_files(self, temp_git_repo: Path) -> None:
        """Should detect multiple common files."""
        (temp_git_repo / ".env").write_text("SECRET=123")
        (temp_git_repo / ".env.local").write_text("LOCAL=456")
        detected = detect_common_files(temp_git_repo)
        assert ".env" in detected
        assert ".env.local" in detected

    def test_detects_nested_config_files(self, temp_git_repo: Path) -> None:
        """Should detect nested config files like config/local.json."""
        config_dir = temp_git_repo / "config"
        config_dir.mkdir()
        (config_dir / "local.json").write_text('{"key": "value"}')
        detected = detect_common_files(temp_git_repo)
        assert "config/local.json" in detected


class TestCreateCwshareTemplate:
    """Tests for create_cwshare_template function."""

    def test_creates_file(self, temp_git_repo: Path) -> None:
        """Should create .cwshare file."""
        create_cwshare_template(temp_git_repo, [])
        assert (temp_git_repo / ".cwshare").exists()

    def test_includes_header_comment(self, temp_git_repo: Path) -> None:
        """Should include header comments."""
        create_cwshare_template(temp_git_repo, [])
        content = (temp_git_repo / ".cwshare").read_text()
        assert "# .cwshare - Files to copy to new worktrees" in content

    def test_includes_suggested_files_as_comments(self, temp_git_repo: Path) -> None:
        """Should include suggested files as commented lines."""
        create_cwshare_template(temp_git_repo, [".env", ".env.local"])
        content = (temp_git_repo / ".cwshare").read_text()
        assert "# .env" in content
        assert "# .env.local" in content
        # Should NOT include uncommented versions
        lines = content.split("\n")
        assert ".env" not in [line.strip() for line in lines if not line.startswith("#")]

    def test_shows_message_when_no_files_detected(self, temp_git_repo: Path) -> None:
        """Should show helpful message when no files detected."""
        create_cwshare_template(temp_git_repo, [])
        content = (temp_git_repo / ".cwshare").read_text()
        assert "No common files detected" in content


class TestPromptCwshareSetup:
    """Tests for prompt_cwshare_setup function."""

    def test_skips_when_not_in_git_repo(self, tmp_path: Path, monkeypatch) -> None:
        """Should skip silently when not in a git repository."""
        monkeypatch.chdir(tmp_path)

        # Should not raise an exception
        prompt_cwshare_setup()

    def test_skips_in_non_interactive_mode(self, temp_git_repo: Path, monkeypatch) -> None:
        """Should skip in non-interactive environments."""
        monkeypatch.setenv("CI", "true")

        prompt_cwshare_setup()

        # Should not have been prompted
        assert is_cwshare_prompted(temp_git_repo) is False

    def test_skips_when_cwshare_exists(self, temp_git_repo: Path, monkeypatch) -> None:
        """Should skip when .cwshare already exists."""
        # Create .cwshare file
        (temp_git_repo / ".cwshare").write_text("# existing")

        with patch("claude_worktree.cwshare_setup.is_non_interactive", return_value=False):
            prompt_cwshare_setup()

        # Should be marked as prompted
        assert is_cwshare_prompted(temp_git_repo) is True

    def test_skips_when_already_prompted(self, temp_git_repo: Path, monkeypatch) -> None:
        """Should skip when already prompted for this repo."""
        # Mark as prompted
        mark_cwshare_prompted(temp_git_repo)

        # Mock confirm to verify it's not called
        with patch("claude_worktree.cwshare_setup.is_non_interactive", return_value=False):
            with patch("claude_worktree.cwshare_setup.typer.confirm") as mock_confirm:
                prompt_cwshare_setup()
                mock_confirm.assert_not_called()

    def test_marks_prompted_on_accept(self, temp_git_repo: Path) -> None:
        """Should mark as prompted when user accepts."""
        with patch("claude_worktree.cwshare_setup.is_non_interactive", return_value=False):
            with patch("claude_worktree.cwshare_setup.typer.confirm", return_value=True):
                prompt_cwshare_setup()

        assert is_cwshare_prompted(temp_git_repo) is True
        assert has_cwshare_file(temp_git_repo) is True

    def test_marks_prompted_on_decline(self, temp_git_repo: Path) -> None:
        """Should mark as prompted when user declines."""
        with patch("claude_worktree.cwshare_setup.is_non_interactive", return_value=False):
            with patch("claude_worktree.cwshare_setup.typer.confirm", return_value=False):
                prompt_cwshare_setup()

        assert is_cwshare_prompted(temp_git_repo) is True
        assert has_cwshare_file(temp_git_repo) is False

    def test_marks_prompted_on_keyboard_interrupt(self, temp_git_repo: Path) -> None:
        """Should mark as prompted when user cancels with Ctrl+C."""
        with patch("claude_worktree.cwshare_setup.is_non_interactive", return_value=False):
            with patch(
                "claude_worktree.cwshare_setup.typer.confirm", side_effect=KeyboardInterrupt
            ):
                prompt_cwshare_setup()

        assert is_cwshare_prompted(temp_git_repo) is True
        assert has_cwshare_file(temp_git_repo) is False

    def test_creates_template_with_detected_files(self, temp_git_repo: Path) -> None:
        """Should create template with detected files when user accepts."""
        # Create some common files
        (temp_git_repo / ".env").write_text("SECRET=123")
        (temp_git_repo / ".env.local").write_text("LOCAL=456")

        with patch("claude_worktree.cwshare_setup.is_non_interactive", return_value=False):
            with patch("claude_worktree.cwshare_setup.typer.confirm", return_value=True):
                prompt_cwshare_setup()

        content = (temp_git_repo / ".cwshare").read_text()
        assert "# .env" in content
        assert "# .env.local" in content


class TestCommonSharedFiles:
    """Tests for COMMON_SHARED_FILES constant."""

    def test_includes_env_files(self) -> None:
        """Should include common .env files."""
        assert ".env" in COMMON_SHARED_FILES
        assert ".env.local" in COMMON_SHARED_FILES

    def test_includes_config_files(self) -> None:
        """Should include common config files."""
        assert "config/local.json" in COMMON_SHARED_FILES
        assert "config/local.yaml" in COMMON_SHARED_FILES
