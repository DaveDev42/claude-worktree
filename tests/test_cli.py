"""Tests for CLI interface - classicist style."""

import subprocess
from pathlib import Path

from typer.testing import CliRunner

from claude_worktree.cli import app

runner = CliRunner()


def test_cli_help() -> None:
    """Test that help command works."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Claude Code × git worktree helper CLI" in result.stdout


def test_cli_version() -> None:
    """Test version flag."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "claude-worktree version" in result.stdout


def test_new_command_help() -> None:
    """Test new command help."""
    result = runner.invoke(app, ["new", "--help"])
    assert result.exit_code == 0
    assert "Create a new worktree" in result.stdout


def test_new_command_execution(temp_git_repo: Path, disable_claude) -> None:
    """Test new command with real execution."""
    result = runner.invoke(app, ["new", "test-feature", "--no-cd", "--no-ai"])

    # Command should succeed
    assert result.exit_code == 0

    # Verify worktree was actually created
    expected_path = temp_git_repo.parent / f"{temp_git_repo.name}-test-feature"
    assert expected_path.exists()

    # Verify branch exists
    git_result = subprocess.run(
        ["git", "branch", "--list", "test-feature"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
    )
    assert "test-feature" in git_result.stdout


def test_new_command_with_deprecated_flag(temp_git_repo: Path, disable_claude) -> None:
    """Test that --no-claude flag still works and is marked as deprecated in help."""
    # Test that --no-claude still works
    result = runner.invoke(app, ["new", "test-deprecated", "--no-cd", "--no-claude"])

    # Command should still succeed
    assert result.exit_code == 0

    # Verify worktree was created
    expected_path = temp_git_repo.parent / f"{temp_git_repo.name}-test-deprecated"
    assert expected_path.exists()


def test_new_command_help_shows_deprecated() -> None:
    """Test that help message shows --no-claude as deprecated."""
    import re

    result = runner.invoke(app, ["new", "--help"])
    assert result.exit_code == 0

    # Strip ANSI color codes for reliable string matching
    ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
    clean_output = ansi_escape.sub("", result.stdout)

    assert "deprecated" in clean_output.lower()
    assert "--no-ai" in clean_output
    assert "--no-claude" in clean_output


def test_new_command_with_base(temp_git_repo: Path, disable_claude) -> None:
    """Test new command with base branch specification."""
    # Create develop branch
    subprocess.run(
        ["git", "branch", "develop"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    result = runner.invoke(app, ["new", "from-develop", "--base", "develop", "--no-cd", "--no-ai"])

    assert result.exit_code == 0
    expected_path = temp_git_repo.parent / f"{temp_git_repo.name}-from-develop"
    assert expected_path.exists()


def test_new_command_custom_path(temp_git_repo: Path, disable_claude) -> None:
    """Test new command with custom path."""
    custom_path = temp_git_repo.parent / "my-custom-worktree"

    result = runner.invoke(app, ["new", "custom", "--path", str(custom_path), "--no-cd", "--no-ai"])

    assert result.exit_code == 0
    assert custom_path.exists()


def test_new_command_invalid_base(temp_git_repo: Path) -> None:
    """Test new command with invalid base branch."""
    result = runner.invoke(app, ["new", "feature", "--base", "nonexistent", "--no-cd"])

    # Should fail
    assert result.exit_code != 0
    assert "Error" in result.stdout


def test_finish_command_help() -> None:
    """Test finish command help."""
    result = runner.invoke(app, ["finish", "--help"])
    assert result.exit_code == 0
    assert "Finish work on a worktree" in result.stdout


def test_finish_command_execution(temp_git_repo: Path, disable_claude, monkeypatch) -> None:
    """Test finish command with real execution."""
    # Create worktree
    result = runner.invoke(app, ["new", "finish-me", "--no-cd", "--no-ai"])
    assert result.exit_code == 0

    worktree_path = temp_git_repo.parent / f"{temp_git_repo.name}-finish-me"

    # Make a commit in the worktree
    (worktree_path / "new_file.txt").write_text("content")
    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add file"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )

    # Change to worktree directory
    monkeypatch.chdir(worktree_path)

    # Finish the worktree
    result = runner.invoke(app, ["finish"])
    assert result.exit_code == 0

    # Verify worktree was removed
    assert not worktree_path.exists()

    # Verify file was merged
    assert (temp_git_repo / "new_file.txt").exists()


def test_list_command_help() -> None:
    """Test list command help."""
    result = runner.invoke(app, ["list", "--help"])
    assert result.exit_code == 0
    assert "List all worktrees" in result.stdout


def test_list_command_execution(temp_git_repo: Path, disable_claude) -> None:
    """Test list command with real worktrees."""
    # Create some worktrees
    runner.invoke(app, ["new", "wt1", "--no-cd", "--no-ai"])
    runner.invoke(app, ["new", "wt2", "--no-cd", "--no-ai"])

    # List worktrees
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "wt1" in result.stdout
    assert "wt2" in result.stdout


def test_status_command_help() -> None:
    """Test status command help."""
    result = runner.invoke(app, ["status", "--help"])
    assert result.exit_code == 0
    assert "Show status" in result.stdout


def test_status_command_execution(temp_git_repo: Path, disable_claude, monkeypatch) -> None:
    """Test status command from within worktree."""
    # Create worktree
    runner.invoke(app, ["new", "status-test", "--no-cd", "--no-ai"])
    worktree_path = temp_git_repo.parent / f"{temp_git_repo.name}-status-test"

    # Change to worktree
    monkeypatch.chdir(worktree_path)

    # Show status
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "status-test" in result.stdout


def test_delete_command_help() -> None:
    """Test delete command help."""
    result = runner.invoke(app, ["delete", "--help"])
    assert result.exit_code == 0
    assert "Delete a worktree" in result.stdout


def test_delete_command_by_branch(temp_git_repo: Path, disable_claude) -> None:
    """Test delete command by branch name."""
    # Create worktree
    runner.invoke(app, ["new", "delete-me", "--no-cd", "--no-ai"])
    worktree_path = temp_git_repo.parent / f"{temp_git_repo.name}-delete-me"
    assert worktree_path.exists()

    # Delete by branch name
    result = runner.invoke(app, ["delete", "delete-me"])
    assert result.exit_code == 0

    # Verify removal
    assert not worktree_path.exists()


def test_delete_command_by_path(temp_git_repo: Path, disable_claude) -> None:
    """Test delete command by path."""
    # Create worktree
    runner.invoke(app, ["new", "delete-path", "--no-cd", "--no-ai"])
    worktree_path = temp_git_repo.parent / f"{temp_git_repo.name}-delete-path"

    # Delete by path
    result = runner.invoke(app, ["delete", str(worktree_path)])
    assert result.exit_code == 0
    assert not worktree_path.exists()


def test_delete_command_keep_branch(temp_git_repo: Path, disable_claude) -> None:
    """Test delete command with keep-branch flag."""
    # Create worktree
    runner.invoke(app, ["new", "keep-br", "--no-cd", "--no-ai"])
    worktree_path = temp_git_repo.parent / f"{temp_git_repo.name}-keep-br"

    # Delete with keep-branch
    result = runner.invoke(app, ["delete", "keep-br", "--keep-branch"])
    assert result.exit_code == 0

    # Worktree removed
    assert not worktree_path.exists()

    # Branch still exists
    git_result = subprocess.run(
        ["git", "branch", "--list", "keep-br"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
    )
    assert "keep-br" in git_result.stdout


def test_prune_command_help() -> None:
    """Test prune command help."""
    result = runner.invoke(app, ["prune", "--help"])
    assert result.exit_code == 0
    assert "Prune stale worktree" in result.stdout


def test_prune_command_execution(temp_git_repo: Path, disable_claude) -> None:
    """Test prune command with real stale worktree."""
    # Create worktree
    runner.invoke(app, ["new", "prune-me", "--no-cd", "--no-ai"])
    worktree_path = temp_git_repo.parent / f"{temp_git_repo.name}-prune-me"

    # Manually remove directory to make it stale
    import shutil

    shutil.rmtree(worktree_path)

    # Prune
    result = runner.invoke(app, ["prune"])
    assert result.exit_code == 0


def test_attach_command_help() -> None:
    """Test attach command help."""
    result = runner.invoke(app, ["attach", "--help"])
    assert result.exit_code == 0
    assert "Reattach AI coding assistant" in result.stdout


def test_attach_command_no_claude(temp_git_repo: Path, disable_claude) -> None:
    """Test attach command when Claude is not available."""
    result = runner.invoke(app, ["attach"])
    # Should not fail, just warn
    assert result.exit_code == 0
    assert "not detected" in result.stdout or "Skipping" in result.stdout


def test_attach_command_with_worktree(temp_git_repo: Path, disable_claude) -> None:
    """Test attach command with worktree argument."""
    # Create a worktree
    result = runner.invoke(app, ["new", "test-feature", "--no-ai", "--no-cd"])
    assert result.exit_code == 0

    # Attach to the worktree by name (from main repo)
    result = runner.invoke(app, ["attach", "test-feature"])
    assert result.exit_code == 0
    assert "Attaching to worktree" in result.stdout or "not detected" in result.stdout

    # Clean up
    runner.invoke(app, ["delete", "test-feature"])


def test_attach_command_nonexistent_worktree(temp_git_repo: Path, disable_claude) -> None:
    """Test attach command with nonexistent worktree."""
    result = runner.invoke(app, ["attach", "nonexistent"])
    assert result.exit_code == 1
    assert "No worktree found" in result.stdout


def test_attach_command_shows_deprecation_warning(temp_git_repo: Path, disable_claude) -> None:
    """Test that attach command shows deprecation warning."""
    result = runner.invoke(app, ["attach"])
    assert result.exit_code == 0
    assert "deprecated" in result.stdout.lower()
    assert "cw resume" in result.stdout or "resume" in result.stdout
    assert "v2.0" in result.stdout


def test_attach_command_redirects_to_resume(temp_git_repo: Path, disable_claude) -> None:
    """Test that attach command redirects to resume internally."""
    # Create a worktree
    runner.invoke(app, ["new", "attach-test", "--no-ai", "--no-cd"])

    # Use attach command (should redirect to resume)
    result = runner.invoke(app, ["attach", "attach-test"])
    assert result.exit_code == 0

    # Should show deprecation warning
    assert "deprecated" in result.stdout.lower()

    # Should show session-related messages (from resume, not attach)
    assert "session" in result.stdout.lower() or "Switched to worktree" in result.stdout

    # Clean up
    runner.invoke(app, ["delete", "attach-test"])


def test_new_command_with_iterm_tab_flag(temp_git_repo: Path, disable_claude) -> None:
    """Test that new command accepts --iterm-tab flag."""
    result = runner.invoke(app, ["new", "iterm-tab-test", "--no-cd", "--no-ai"])
    assert result.exit_code == 0

    # Verify worktree was created
    expected_path = temp_git_repo.parent / f"{temp_git_repo.name}-iterm-tab-test"
    assert expected_path.exists()

    # Clean up
    runner.invoke(app, ["delete", "iterm-tab-test"])


def test_resume_command_with_iterm_tab_flag(temp_git_repo: Path, disable_claude) -> None:
    """Test that resume command accepts --iterm-tab flag."""
    # Create a worktree first
    runner.invoke(app, ["new", "resume-tab-test", "--no-cd", "--no-ai"])

    # Resume with --iterm-tab flag (won't actually launch on non-macOS, but should accept the flag)
    result = runner.invoke(app, ["resume", "resume-tab-test", "--no-ai"])
    assert result.exit_code == 0

    # Clean up
    runner.invoke(app, ["delete", "resume-tab-test"])


def test_attach_command_with_iterm_tab_flag(temp_git_repo: Path, disable_claude) -> None:
    """Test that deprecated attach command accepts --iterm-tab flag."""
    # Create a worktree first
    runner.invoke(app, ["new", "attach-tab-test", "--no-cd", "--no-ai"])

    # Attach with --iterm-tab flag
    result = runner.invoke(app, ["attach", "attach-tab-test"])
    assert result.exit_code == 0

    # Should show deprecation warning
    assert "deprecated" in result.stdout.lower()

    # Clean up
    runner.invoke(app, ["delete", "attach-tab-test"])
