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
    result = runner.invoke(app, ["new", "test-feature", "--no-cd"])

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


def test_new_command_with_base(temp_git_repo: Path, disable_claude) -> None:
    """Test new command with base branch specification."""
    # Create develop branch
    subprocess.run(
        ["git", "branch", "develop"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    result = runner.invoke(app, ["new", "from-develop", "--base", "develop", "--no-cd"])

    assert result.exit_code == 0
    expected_path = temp_git_repo.parent / f"{temp_git_repo.name}-from-develop"
    assert expected_path.exists()


def test_new_command_custom_path(temp_git_repo: Path, disable_claude) -> None:
    """Test new command with custom path."""
    custom_path = temp_git_repo.parent / "my-custom-worktree"

    result = runner.invoke(app, ["new", "custom", "--path", str(custom_path), "--no-cd"])

    assert result.exit_code == 0
    assert custom_path.exists()


def test_new_command_invalid_base(temp_git_repo: Path) -> None:
    """Test new command with invalid base branch."""
    result = runner.invoke(app, ["new", "feature", "--base", "nonexistent", "--no-cd"])

    # Should fail
    assert result.exit_code != 0
    assert "Error" in result.stdout


def test_list_command_help() -> None:
    """Test list command help."""
    result = runner.invoke(app, ["list", "--help"])
    assert result.exit_code == 0
    assert "List all worktrees" in result.stdout


def test_list_command_execution(temp_git_repo: Path, disable_claude) -> None:
    """Test list command with real worktrees."""
    # Create some worktrees
    runner.invoke(app, ["new", "wt1", "--no-cd"])
    runner.invoke(app, ["new", "wt2", "--no-cd"])

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
    runner.invoke(app, ["new", "status-test", "--no-cd"])
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
    runner.invoke(app, ["new", "delete-me", "--no-cd"])
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
    runner.invoke(app, ["new", "delete-path", "--no-cd"])
    worktree_path = temp_git_repo.parent / f"{temp_git_repo.name}-delete-path"

    # Delete by path
    result = runner.invoke(app, ["delete", str(worktree_path)])
    assert result.exit_code == 0
    assert not worktree_path.exists()


def test_delete_command_keep_branch(temp_git_repo: Path, disable_claude) -> None:
    """Test delete command with keep-branch flag."""
    # Create worktree
    runner.invoke(app, ["new", "keep-br", "--no-cd"])
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


def test_new_command_with_iterm_tab_flag(temp_git_repo: Path, disable_claude) -> None:
    """Test that new command accepts --iterm-tab flag."""
    result = runner.invoke(app, ["new", "iterm-tab-test", "--no-cd"])
    assert result.exit_code == 0

    # Verify worktree was created
    expected_path = temp_git_repo.parent / f"{temp_git_repo.name}-iterm-tab-test"
    assert expected_path.exists()

    # Clean up
    runner.invoke(app, ["delete", "iterm-tab-test"])


def test_resume_command_with_iterm_tab_flag(temp_git_repo: Path, disable_claude) -> None:
    """Test that resume command accepts --iterm-tab flag."""
    # Create a worktree first
    runner.invoke(app, ["new", "resume-tab-test", "--no-cd"])

    # Resume with --iterm-tab flag (won't actually launch on non-macOS, but should accept the flag)
    result = runner.invoke(app, ["resume", "resume-tab-test"])
    assert result.exit_code == 0

    # Clean up
    runner.invoke(app, ["delete", "resume-tab-test"])


def test_shell_command_help() -> None:
    """Test shell command help."""
    result = runner.invoke(app, ["shell", "--help"])
    assert result.exit_code == 0
    assert "shell" in result.stdout.lower()
    assert "command" in result.stdout.lower()


def test_shell_command_with_branch_and_command(temp_git_repo: Path, disable_claude) -> None:
    """Test shell command executes command in worktree."""
    # Create worktree
    runner.invoke(app, ["new", "shell-test", "--no-cd"])
    worktree_path = temp_git_repo.parent / f"{temp_git_repo.name}-shell-test"

    # Execute command in worktree (no -- separator needed)
    result = runner.invoke(app, ["shell", "shell-test", "echo", "test"])
    # Command execution exits with the command's exit code
    assert result.exit_code == 0
    # Check that command was executed (shows in message)
    assert "Executing in" in result.stdout
    # Check for worktree path (may be split across lines in CI, so check without whitespace)
    stdout_no_ws = result.stdout.replace("\n", "").replace(" ", "")
    path_no_ws = str(worktree_path).replace(" ", "")
    assert path_no_ws in stdout_no_ws

    # Clean up
    runner.invoke(app, ["delete", "shell-test"])


def test_shell_command_nonexistent_branch(temp_git_repo: Path) -> None:
    """Test shell command with nonexistent branch."""
    result = runner.invoke(app, ["shell", "nonexistent", "ls"])
    assert result.exit_code != 0
    assert "Error" in result.stdout


def test_cd_command_help() -> None:
    """Test cd command help."""
    result = runner.invoke(app, ["cd", "--help"])
    assert result.exit_code == 0
    assert "Print the path to a worktree" in result.stdout


def test_cd_command_execution(temp_git_repo: Path, disable_claude, monkeypatch) -> None:
    """Test cd command with real worktree."""
    # Mock is_non_interactive to return False (simulate interactive environment)
    from claude_worktree import git_utils

    monkeypatch.setattr(git_utils, "is_non_interactive", lambda: False)

    # Mock typer.confirm to avoid blocking prompt
    import typer

    monkeypatch.setattr(typer, "confirm", lambda *args, **kwargs: False)

    # Create worktree
    runner.invoke(app, ["new", "cd-test", "--no-cd"])
    expected_path = temp_git_repo.parent / f"{temp_git_repo.name}-cd-test"

    # Get path via cd command
    result = runner.invoke(app, ["cd", "cd-test"])
    assert result.exit_code == 0
    # Path should be in output (may be split across lines due to formatting)
    # Remove newlines to handle line wrapping from Rich console
    output_no_newlines = result.stdout.replace("\n", "")
    assert expected_path.name in output_no_newlines or str(expected_path) in output_no_newlines
    assert "cw-cd" in result.stdout  # Should show shell function hint

    # Clean up
    runner.invoke(app, ["delete", "cd-test"])


def test_cd_command_print_only(temp_git_repo: Path, disable_claude) -> None:
    """Test cd command with --print flag."""
    # Create worktree
    runner.invoke(app, ["new", "cd-print", "--no-cd"])
    expected_path = temp_git_repo.parent / f"{temp_git_repo.name}-cd-print"

    # Get path with --print flag
    result = runner.invoke(app, ["cd", "cd-print", "--print"])
    assert result.exit_code == 0
    # Should output only the path, no hints
    assert result.stdout.strip() == str(expected_path)
    assert "cw-cd" not in result.stdout

    # Clean up
    runner.invoke(app, ["delete", "cd-print"])


def test_cd_command_nonexistent_branch(temp_git_repo: Path) -> None:
    """Test cd command with nonexistent branch."""
    result = runner.invoke(app, ["cd", "nonexistent-branch"])
    assert result.exit_code != 0
    assert "Error" in result.stdout


def test_sync_command_help(temp_git_repo: Path) -> None:
    """Test sync command help."""
    result = runner.invoke(app, ["sync", "--help"])
    assert result.exit_code == 0
    assert "Synchronize worktree" in result.stdout


def test_sync_command_accepts_flags(temp_git_repo: Path, disable_claude) -> None:
    """Test sync command accepts all flags."""
    result = runner.invoke(app, ["sync", "--help"])
    assert result.exit_code == 0
    # Check for flag names (ANSI codes may be present in colored output)
    assert "all" in result.stdout and "Sync all worktrees" in result.stdout
    assert (
        "fetch" in result.stdout and "only" in result.stdout and "without rebasing" in result.stdout
    )


def test_clean_command_help(temp_git_repo: Path) -> None:
    """Test clean command help."""
    result = runner.invoke(app, ["clean", "--help"])
    assert result.exit_code == 0
    assert "Batch cleanup of worktrees" in result.stdout


def test_clean_command_accepts_flags(temp_git_repo: Path, disable_claude) -> None:
    """Test clean command accepts all flags."""
    result = runner.invoke(app, ["clean", "--help"])
    assert result.exit_code == 0
    # Check for flag names (ANSI codes may be present in colored output)
    assert "merged" in result.stdout and "branches already merged" in result.stdout
    assert "older" in result.stdout and "than" in result.stdout and "days" in result.stdout
    assert "interactive" in result.stdout.lower() or "-i" in result.stdout
    assert "dry" in result.stdout and "run" in result.stdout
    # Check that auto-prune is mentioned in help
    assert "prune" in result.stdout.lower()


def test_pr_command_help(temp_git_repo: Path) -> None:
    """Test pr command help."""
    result = runner.invoke(app, ["pr", "--help"])
    assert result.exit_code == 0
    assert "pull request" in result.stdout.lower() or "pull-request" in result.stdout.lower()
    assert "GitHub" in result.stdout


def test_pr_command_flags(temp_git_repo: Path) -> None:
    """Test pr command accepts all flags."""
    result = runner.invoke(app, ["pr", "--help"])
    assert result.exit_code == 0
    # Check for flag names (handle ANSI color codes by checking components)
    assert "no" in result.stdout and "push" in result.stdout
    assert "title" in result.stdout and "-t" in result.stdout
    assert "body" in result.stdout and "-b" in result.stdout
    assert "draft" in result.stdout


def test_merge_command_help(temp_git_repo: Path) -> None:
    """Test merge command help."""
    result = runner.invoke(app, ["merge", "--help"])
    assert result.exit_code == 0
    assert "merge" in result.stdout.lower()
    assert "base branch" in result.stdout.lower()


def test_merge_command_flags(temp_git_repo: Path) -> None:
    """Test merge command accepts all flags."""
    result = runner.invoke(app, ["merge", "--help"])
    assert result.exit_code == 0
    # Check for flag names (handle ANSI color codes by checking components)
    assert "push" in result.stdout
    assert "interactive" in result.stdout and "-i" in result.stdout
    assert "dry" in result.stdout and "run" in result.stdout


# Shell function tests


def test_shell_function_help() -> None:
    """Test _shell-function command help."""
    result = runner.invoke(app, ["_shell-function", "--help"])
    assert result.exit_code == 0
    assert "shell function" in result.stdout.lower()


def test_shell_function_bash() -> None:
    """Test _shell-function outputs bash script."""
    result = runner.invoke(app, ["_shell-function", "bash"])
    assert result.exit_code == 0
    assert "cw-cd()" in result.stdout
    assert "bash" in result.stdout.lower() or "zsh" in result.stdout.lower()
    assert "_cw_cd_completion" in result.stdout


def test_shell_function_zsh() -> None:
    """Test _shell-function outputs zsh script."""
    result = runner.invoke(app, ["_shell-function", "zsh"])
    assert result.exit_code == 0
    assert "cw-cd()" in result.stdout
    assert "_cw_cd_zsh" in result.stdout


def test_shell_function_fish() -> None:
    """Test _shell-function outputs fish script."""
    result = runner.invoke(app, ["_shell-function", "fish"])
    assert result.exit_code == 0
    assert "function cw-cd" in result.stdout
    assert "complete -c cw-cd" in result.stdout


def test_shell_function_powershell() -> None:
    """Test _shell-function outputs PowerShell script."""
    result = runner.invoke(app, ["_shell-function", "powershell"])
    assert result.exit_code == 0
    assert "function cw-cd" in result.stdout
    assert "Register-ArgumentCompleter" in result.stdout
    assert "Set-Location" in result.stdout


def test_shell_function_pwsh_alias() -> None:
    """Test _shell-function accepts 'pwsh' as PowerShell alias."""
    result = runner.invoke(app, ["_shell-function", "pwsh"])
    assert result.exit_code == 0
    assert "function cw-cd" in result.stdout
    assert "Register-ArgumentCompleter" in result.stdout


def test_shell_function_invalid_shell() -> None:
    """Test _shell-function rejects invalid shell."""
    result = runner.invoke(app, ["_shell-function", "invalid"])
    assert result.exit_code != 0
    assert "Error" in result.stderr or "Invalid" in result.stderr


def test_shell_setup_help() -> None:
    """Test shell-setup command help."""
    result = runner.invoke(app, ["shell-setup", "--help"])
    assert result.exit_code == 0
    assert "shell" in result.stdout.lower()
    assert "setup" in result.stdout.lower() or "install" in result.stdout.lower()


def test_cd_command_suggests_shell_setup(temp_git_repo: Path, disable_claude, monkeypatch) -> None:
    """Test cd command suggests shell-setup."""
    # Mock is_non_interactive to return False (simulate interactive environment)
    from claude_worktree import git_utils

    monkeypatch.setattr(git_utils, "is_non_interactive", lambda: False)

    # Mock typer.confirm to avoid blocking prompt
    import typer

    monkeypatch.setattr(typer, "confirm", lambda *args, **kwargs: False)

    # Create worktree
    runner.invoke(app, ["new", "setup-test", "--no-cd"])

    # Get path via cd command (without --print)
    result = runner.invoke(app, ["cd", "setup-test"])
    assert result.exit_code == 0
    # Should suggest shell-setup
    assert "shell-setup" in result.stdout

    # Clean up
    runner.invoke(app, ["delete", "setup-test"])
