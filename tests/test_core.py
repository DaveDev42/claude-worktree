"""Tests for core module - classicist style with real git operations."""

import subprocess
from pathlib import Path

import pytest

from claude_worktree.core import (
    create_worktree,
    delete_worktree,
    finish_worktree,
    get_worktree_status,
    list_worktrees,
    prune_worktrees,
    resume_worktree,
    show_status,
)
from claude_worktree.exceptions import (
    GitError,
    InvalidBranchError,
    WorktreeNotFoundError,
)


def test_create_worktree_basic(temp_git_repo: Path, disable_claude) -> None:
    """Test basic worktree creation."""
    # Create worktree
    result_path = create_worktree(
        branch_name="fix-auth",
        base_branch=None,  # Will use current branch
        path=None,  # Will use default path
        no_cd=True,  # Don't change directory
    )

    # Verify worktree was created
    expected_path = temp_git_repo.parent / f"{temp_git_repo.name}-fix-auth"
    assert result_path == expected_path
    assert result_path.exists()
    assert (result_path / "README.md").exists()

    # Verify branch was created
    result = subprocess.run(
        ["git", "branch", "--list", "fix-auth"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
    )
    assert "fix-auth" in result.stdout

    # Verify worktree is registered
    result = subprocess.run(
        ["git", "worktree", "list"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
    )
    assert str(result_path) in result.stdout


def test_create_worktree_custom_path(temp_git_repo: Path, disable_claude) -> None:
    """Test worktree creation with custom path."""
    custom_path = temp_git_repo.parent / "my_custom_path"

    result_path = create_worktree(
        branch_name="custom-branch",
        path=custom_path,
        no_cd=True,
    )

    assert result_path == custom_path
    assert custom_path.exists()


def test_create_worktree_with_base_branch(temp_git_repo: Path, disable_claude) -> None:
    """Test worktree creation from specific base branch."""
    # Create a develop branch
    subprocess.run(
        ["git", "branch", "develop"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    # Create worktree from develop
    result_path = create_worktree(
        branch_name="feature",
        base_branch="develop",
        no_cd=True,
    )

    # Verify it was created from develop
    result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=result_path,
        capture_output=True,
        text=True,
    )
    assert "Initial commit" in result.stdout


def test_create_worktree_invalid_base(temp_git_repo: Path, disable_claude) -> None:
    """Test error when base branch doesn't exist."""
    with pytest.raises(InvalidBranchError, match="not found"):
        create_worktree(
            branch_name="feature",
            base_branch="nonexistent-branch",
            no_cd=True,
        )


def test_finish_worktree_success(temp_git_repo: Path, disable_claude, monkeypatch) -> None:
    """Test successful worktree finish workflow."""
    # Create worktree
    worktree_path = create_worktree(
        branch_name="finish-test",
        no_cd=True,
    )

    # Change to worktree and make a commit
    monkeypatch.chdir(worktree_path)
    (worktree_path / "test.txt").write_text("test content")
    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add test file"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )

    # Finish the worktree (will change back to base repo automatically)
    finish_worktree(push=False)

    # Change back to main repo for verification
    monkeypatch.chdir(temp_git_repo)

    # Verify worktree was removed
    assert not worktree_path.exists()

    # Verify branch was deleted
    result = subprocess.run(
        ["git", "branch", "--list", "finish-test"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
    )
    assert "finish-test" not in result.stdout

    # Verify changes were merged to main
    assert (temp_git_repo / "test.txt").exists()
    assert (temp_git_repo / "test.txt").read_text() == "test content"


def test_finish_worktree_with_rebase(temp_git_repo: Path, disable_claude, monkeypatch) -> None:
    """Test finish workflow when base branch has new commits."""
    # Create worktree
    worktree_path = create_worktree(
        branch_name="rebase-test",
        no_cd=True,
    )

    # Make commit in worktree
    (worktree_path / "feature.txt").write_text("feature")
    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add feature"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )

    # Make commit in main repo (simulating other work)
    (temp_git_repo / "main.txt").write_text("main work")
    subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Work on main"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    # Finish should rebase and merge
    monkeypatch.chdir(worktree_path)
    finish_worktree(push=False)

    # Change back to main repo for verification
    monkeypatch.chdir(temp_git_repo)

    # Verify both files exist in main
    assert (temp_git_repo / "feature.txt").exists()
    assert (temp_git_repo / "main.txt").exists()


def test_delete_worktree_by_branch(temp_git_repo: Path, disable_claude) -> None:
    """Test deleting worktree by branch name."""
    # Create worktree
    worktree_path = create_worktree(
        branch_name="delete-me",
        no_cd=True,
    )

    assert worktree_path.exists()

    # Delete by branch name
    delete_worktree(target="delete-me", keep_branch=False)

    # Verify worktree was removed
    assert not worktree_path.exists()

    # Verify branch was deleted
    result = subprocess.run(
        ["git", "branch", "--list", "delete-me"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
    )
    assert "delete-me" not in result.stdout


def test_delete_worktree_by_path(temp_git_repo: Path, disable_claude) -> None:
    """Test deleting worktree by path."""
    # Create worktree
    worktree_path = create_worktree(
        branch_name="delete-by-path",
        no_cd=True,
    )

    # Delete by path
    delete_worktree(target=str(worktree_path), keep_branch=False)

    # Verify removal
    assert not worktree_path.exists()


def test_delete_worktree_keep_branch(temp_git_repo: Path, disable_claude) -> None:
    """Test deleting worktree but keeping branch."""
    # Create worktree
    worktree_path = create_worktree(
        branch_name="keep-branch",
        no_cd=True,
    )

    # Delete worktree but keep branch
    delete_worktree(target="keep-branch", keep_branch=True)

    # Verify worktree was removed
    assert not worktree_path.exists()

    # Verify branch still exists
    result = subprocess.run(
        ["git", "branch", "--list", "keep-branch"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
    )
    assert "keep-branch" in result.stdout


def test_delete_worktree_not_found(temp_git_repo: Path) -> None:
    """Test error when worktree doesn't exist."""
    with pytest.raises(WorktreeNotFoundError):
        delete_worktree(target="nonexistent-branch")


def test_delete_main_repo_protection(temp_git_repo: Path, monkeypatch) -> None:
    """Test that main repository cannot be deleted."""
    # Try to delete the main repository
    with pytest.raises(GitError, match="Cannot delete main repository"):
        delete_worktree(target=str(temp_git_repo))


def test_list_worktrees(temp_git_repo: Path, disable_claude, capsys) -> None:
    """Test listing worktrees."""
    # Create a couple of worktrees
    create_worktree(
        branch_name="wt1",
        no_cd=True,
    )
    create_worktree(
        branch_name="wt2",
        no_cd=True,
    )

    # List worktrees
    list_worktrees()

    # Check output
    captured = capsys.readouterr()
    assert "wt1" in captured.out
    assert "wt2" in captured.out


def test_show_status_in_worktree(temp_git_repo: Path, disable_claude, monkeypatch, capsys) -> None:
    """Test showing status from within a worktree."""
    # Create worktree
    worktree_path = create_worktree(
        branch_name="status-test",
        no_cd=True,
    )

    # Change to worktree
    monkeypatch.chdir(worktree_path)

    # Show status
    show_status()

    # Check output
    captured = capsys.readouterr()
    assert "status-test" in captured.out


def test_show_status_in_main_repo(temp_git_repo: Path, capsys) -> None:
    """Test showing status from main repository."""
    show_status()

    # Should not error, just show worktree list
    captured = capsys.readouterr()
    assert "Worktrees" in captured.out


def test_prune_worktrees(temp_git_repo: Path, disable_claude) -> None:
    """Test pruning stale worktrees."""
    # Create a worktree
    worktree_path = create_worktree(
        branch_name="prune-test",
        no_cd=True,
    )

    # Manually remove the worktree directory (making it stale)
    import shutil

    shutil.rmtree(worktree_path)

    # Prune should clean it up
    prune_worktrees()

    # Verify it's no longer listed
    result = subprocess.run(
        ["git", "worktree", "list"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
    )
    assert str(worktree_path) not in result.stdout


def test_create_worktree_invalid_branch_name(temp_git_repo: Path, disable_claude) -> None:
    """Test error when branch name is invalid."""
    # Test various invalid branch names
    invalid_names = [
        "feat:auth",  # Contains colon
        "feat*test",  # Contains asterisk
        "feat..test",  # Consecutive dots
        "/feature",  # Starts with slash
        "feature/",  # Ends with slash
        "feat//test",  # Consecutive slashes
        "feat~test",  # Contains tilde
        "feat^test",  # Contains caret
        "feat auth",  # Contains space
        "feat\\test",  # Contains backslash
    ]

    for invalid_name in invalid_names:
        with pytest.raises(InvalidBranchError, match="Invalid branch name"):
            create_worktree(
                branch_name=invalid_name,
                no_cd=True,
            )


def test_get_worktree_status_stale(temp_git_repo: Path, disable_claude) -> None:
    """Test status detection for stale worktree (directory deleted)."""
    # Create worktree
    worktree_path = create_worktree(
        branch_name="stale-test",
        no_cd=True,
    )

    # Manually remove the directory
    import shutil

    shutil.rmtree(worktree_path)

    # Status should be "stale"
    status = get_worktree_status(str(worktree_path), temp_git_repo)
    assert status == "stale"


def test_get_worktree_status_active(temp_git_repo: Path, disable_claude, monkeypatch) -> None:
    """Test status detection for active worktree (current directory)."""
    # Create worktree
    worktree_path = create_worktree(
        branch_name="active-test",
        no_cd=True,
    )

    # Change to the worktree directory
    monkeypatch.chdir(worktree_path)

    # Status should be "active"
    status = get_worktree_status(str(worktree_path), temp_git_repo)
    assert status == "active"


def test_get_worktree_status_modified(temp_git_repo: Path, disable_claude) -> None:
    """Test status detection for modified worktree (uncommitted changes)."""
    # Create worktree
    worktree_path = create_worktree(
        branch_name="modified-test",
        no_cd=True,
    )

    # Add uncommitted changes
    (worktree_path / "uncommitted.txt").write_text("uncommitted changes")

    # Status should be "modified"
    status = get_worktree_status(str(worktree_path), temp_git_repo)
    assert status == "modified"


def test_get_worktree_status_clean(temp_git_repo: Path, disable_claude) -> None:
    """Test status detection for clean worktree (no uncommitted changes)."""
    # Create worktree
    worktree_path = create_worktree(
        branch_name="clean-test",
        no_cd=True,
    )

    # Status should be "clean" (no uncommitted changes, not current directory)
    status = get_worktree_status(str(worktree_path), temp_git_repo)
    assert status == "clean"


def test_resume_worktree_current_directory(
    temp_git_repo: Path, disable_claude, monkeypatch, capsys
) -> None:
    """Test resuming in current directory without existing session."""
    from claude_worktree import session_manager

    # Create worktree
    worktree_path = create_worktree(
        branch_name="resume-test",
        no_cd=True,
    )

    # Clean up any existing session (from previous test runs)
    if session_manager.session_exists("resume-test"):
        session_manager.delete_session("resume-test")

    # Change to worktree directory
    monkeypatch.chdir(worktree_path)

    # Resume without AI tool
    resume_worktree(
        worktree=None,
    )

    # Check output
    captured = capsys.readouterr()
    assert "No previous session found" in captured.out
    assert "resume-test" in captured.out


def test_resume_worktree_with_branch_name(
    temp_git_repo: Path, disable_claude, monkeypatch, capsys
) -> None:
    """Test resuming by specifying branch name."""
    import os

    # Create worktree
    worktree_path = create_worktree(
        branch_name="resume-branch",
        no_cd=True,
    )

    # Start from main repo
    monkeypatch.chdir(temp_git_repo)

    # Resume by branch name
    resume_worktree(
        worktree="resume-branch",
    )

    # Verify we're now in the worktree directory
    assert os.getcwd() == str(worktree_path)

    # Check output
    captured = capsys.readouterr()
    assert "Switched to worktree" in captured.out
    assert "resume-branch" in captured.out


def test_resume_worktree_with_session(
    temp_git_repo: Path, disable_claude, monkeypatch, capsys
) -> None:
    """Test resuming with existing session metadata."""
    from claude_worktree import session_manager

    # Create worktree
    worktree_path = create_worktree(
        branch_name="session-test",
        no_cd=True,
    )

    # Create session metadata
    session_manager.save_session_metadata("session-test", "claude", str(worktree_path))
    session_manager.save_context("session-test", "Working on authentication feature")

    # Change to worktree
    monkeypatch.chdir(worktree_path)

    # Resume without AI tool
    resume_worktree(
        worktree=None,
    )

    # Check output shows session info
    captured = capsys.readouterr()
    assert "Found session" in captured.out
    assert "session-test" in captured.out
    assert "claude" in captured.out
    assert "Previous context" in captured.out
    assert "Working on authentication feature" in captured.out


def test_resume_worktree_nonexistent_branch(temp_git_repo: Path, disable_claude) -> None:
    """Test error when resuming nonexistent worktree."""
    with pytest.raises(WorktreeNotFoundError, match="No worktree found"):
        resume_worktree(
            worktree="nonexistent-branch",
        )


def test_resume_worktree_creates_session_metadata(
    temp_git_repo: Path, disable_claude, monkeypatch
) -> None:
    """Test that resume creates session metadata."""
    from claude_worktree import session_manager

    # Create worktree
    worktree_path = create_worktree(
        branch_name="metadata-test",
        no_cd=True,
    )

    # Clean up any existing session (from previous test runs)
    if session_manager.session_exists("metadata-test"):
        session_manager.delete_session("metadata-test")

    # Verify no session exists initially
    assert not session_manager.session_exists("metadata-test")

    # Change to worktree
    monkeypatch.chdir(worktree_path)

    # Resume without AI tool
    resume_worktree(
        worktree=None,
    )

    # Verify session metadata was created
    assert session_manager.session_exists("metadata-test")
    metadata = session_manager.load_session_metadata("metadata-test")
    assert metadata["branch"] == "metadata-test"
    assert metadata["worktree_path"] == str(worktree_path)


def test_launch_ai_tool_with_iterm_tab(temp_git_repo: Path, mocker) -> None:
    """Test launch_ai_tool with iterm_tab parameter on macOS."""
    from claude_worktree.core import launch_ai_tool

    # Mock has_command to return True for AI tool
    mocker.patch("claude_worktree.core.has_command", return_value=True)

    # Mock sys.platform to be darwin (macOS)
    mocker.patch("claude_worktree.core.sys.platform", "darwin")

    # Mock subprocess.run to capture the AppleScript command
    mock_run = mocker.patch("claude_worktree.core.subprocess.run")

    # Call launch_ai_tool with iterm_tab=True
    launch_ai_tool(temp_git_repo, iterm_tab=True)

    # Verify subprocess.run was called
    assert mock_run.called
    call_args = mock_run.call_args

    # Verify the command includes osascript and expected iTerm tab commands
    command = call_args[0][0]
    assert command[0] == "bash"
    assert command[1] == "-lc"

    # Verify AppleScript content
    script = command[2]
    assert "osascript" in script
    assert 'tell application "iTerm"' in script
    assert "create tab with default profile" in script
    assert "tell current window" in script


def test_launch_ai_tool_with_iterm_tab_non_macos(temp_git_repo: Path, mocker) -> None:
    """Test that iterm_tab raises error on non-macOS platforms."""
    from claude_worktree.core import launch_ai_tool
    from claude_worktree.exceptions import GitError

    # Mock has_command to return True for AI tool
    mocker.patch("claude_worktree.core.has_command", return_value=True)

    # Mock sys.platform to be linux (non-macOS)
    mocker.patch("claude_worktree.core.sys.platform", "linux")

    # Should raise GitError on non-macOS
    with pytest.raises(GitError, match="--iterm-tab option only works on macOS"):
        launch_ai_tool(temp_git_repo, iterm_tab=True)
