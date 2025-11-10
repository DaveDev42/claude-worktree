"""Tests for core module - classicist style with real git operations."""

import subprocess
from pathlib import Path

import pytest

from claude_worktree.exceptions import (
    GitError,
    InvalidBranchError,
    WorktreeNotFoundError,
)
from claude_worktree.operations import (
    change_base_branch,
    create_pr_worktree,
    create_worktree,
    delete_worktree,
    finish_worktree,
    get_worktree_status,
    list_worktrees,
    merge_worktree,
    resume_worktree,
    show_status,
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
    # Use as_posix() for cross-platform path comparison (git uses forward slashes)
    assert result_path.as_posix() in result.stdout


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


def test_finish_worktree_dry_run(temp_git_repo: Path, disable_claude, monkeypatch, capsys) -> None:
    """Test dry-run mode doesn't modify anything."""
    # Create worktree
    worktree_path = create_worktree(
        branch_name="dry-run-test",
        no_cd=True,
    )

    # Make commit in worktree
    (worktree_path / "feature.txt").write_text("feature content")
    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add feature"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )

    # Run finish with dry_run=True
    monkeypatch.chdir(worktree_path)
    finish_worktree(push=False, dry_run=True)

    # Verify output shows dry-run mode
    captured = capsys.readouterr()
    assert "DRY RUN MODE" in captured.out
    assert "No changes will be made" in captured.out
    assert "Rebase" in captured.out
    assert "Merge" in captured.out
    assert "Remove" in captured.out

    # Verify nothing was actually changed
    # Worktree should still exist
    assert worktree_path.exists()
    assert (worktree_path / "feature.txt").exists()

    # Branch should still exist
    result = subprocess.run(
        ["git", "branch", "--list", "dry-run-test"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
    )
    assert "dry-run-test" in result.stdout

    # Changes should NOT be merged to main
    assert not (temp_git_repo / "feature.txt").exists()

    # Worktree should still be registered
    result = subprocess.run(
        ["git", "worktree", "list"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
    )
    # Use as_posix() for cross-platform path comparison (git uses forward slashes)
    assert worktree_path.as_posix() in result.stdout


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
    temp_git_repo: Path, disable_claude, monkeypatch, capsys, tmp_path
) -> None:
    """Test resuming with existing session metadata and conversation history."""
    import json

    from claude_worktree import session_manager

    # Create worktree
    worktree_path = create_worktree(
        branch_name="session-test",
        no_cd=True,
    )

    # Create session metadata
    session_manager.save_session_metadata("session-test", "claude", str(worktree_path))
    session_manager.save_context("session-test", "Working on authentication feature")

    # Create Claude conversation history
    claude_dir = Path.home() / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    history_file = claude_dir / "history.jsonl"

    # Add a conversation entry for this project
    with open(history_file, "a") as f:
        f.write(
            json.dumps(
                {
                    "display": "test message",
                    "timestamp": 1234567890,
                    "project": str(worktree_path),
                }
            )
            + "\n"
        )

    # Change to worktree
    monkeypatch.chdir(worktree_path)

    try:
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
    finally:
        # Clean up: remove the test entry from history
        if history_file.exists():
            with open(history_file) as f:
                lines = f.readlines()
            with open(history_file, "w") as f:
                for line in lines:
                    try:
                        entry = json.loads(line)
                        if entry.get("project") != str(worktree_path):
                            f.write(line)
                    except json.JSONDecodeError:
                        f.write(line)


def test_resume_worktree_nonexistent_branch(temp_git_repo: Path, disable_claude) -> None:
    """Test error when resuming nonexistent worktree."""
    with pytest.raises(WorktreeNotFoundError, match="No worktree found"):
        resume_worktree(
            worktree="nonexistent-branch",
        )


def test_resume_worktree_creates_session_metadata(
    temp_git_repo: Path, disable_claude, monkeypatch
) -> None:
    """Test that resume doesn't create session metadata when AI tool is disabled."""
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

    # Resume with AI tool disabled (due to disable_claude fixture and autouse fixture)
    resume_worktree(
        worktree=None,
    )

    # With AI tool disabled, no session metadata should be created
    # (This is the new expected behavior - sessions are only created when AI tool runs)
    assert not session_manager.session_exists("metadata-test")


def test_launch_ai_tool_with_iterm_tab(temp_git_repo: Path, mocker) -> None:
    """Test launch_ai_tool with iterm_tab parameter on macOS."""
    from claude_worktree.operations import launch_ai_tool

    # Override autouse fixture - enable AI tool for this test
    mocker.patch.dict("os.environ", {"CW_AI_TOOL": "claude"})

    # Mock has_command to return True for AI tool
    mocker.patch("claude_worktree.operations.ai_tools.has_command", return_value=True)

    # Mock sys.platform to be darwin (macOS)
    mocker.patch("claude_worktree.operations.ai_tools.sys.platform", "darwin")

    # Mock subprocess.run to capture the AppleScript command
    mock_run = mocker.patch("claude_worktree.operations.ai_tools.subprocess.run")

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
    from claude_worktree.exceptions import GitError
    from claude_worktree.operations import launch_ai_tool

    # Override autouse fixture - enable AI tool for this test
    mocker.patch.dict("os.environ", {"CW_AI_TOOL": "claude"})

    # Mock has_command to return True for AI tool
    mocker.patch("claude_worktree.operations.ai_tools.has_command", return_value=True)

    # Mock sys.platform to be linux (non-macOS)
    mocker.patch("claude_worktree.operations.ai_tools.sys.platform", "linux")

    # Should raise GitError on non-macOS
    with pytest.raises(GitError, match="--iterm-tab option only works on macOS"):
        launch_ai_tool(temp_git_repo, iterm_tab=True)


def test_create_pr_worktree_missing_gh_cli(temp_git_repo: Path, disable_claude, mocker) -> None:
    """Test create_pr_worktree raises error when gh CLI is not available."""
    # Create worktree
    worktree_path = create_worktree(
        branch_name="pr-test",
        no_cd=True,
    )

    # Make a commit
    (worktree_path / "feature.txt").write_text("feature content")
    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add feature"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )

    # Mock has_command to return False for gh
    mocker.patch("claude_worktree.operations.git_ops.has_command", return_value=False)

    # Should raise GitError about missing gh CLI
    with pytest.raises(GitError, match="GitHub CLI \\(gh\\) is required"):
        create_pr_worktree(target="pr-test", push=False)


def test_create_pr_worktree_no_push(
    temp_git_repo: Path, disable_claude, monkeypatch, mocker
) -> None:
    """Test create_pr_worktree with --no-push flag."""
    # Create worktree
    worktree_path = create_worktree(
        branch_name="pr-no-push",
        no_cd=True,
    )

    # Make a commit
    (worktree_path / "feature.txt").write_text("feature content")
    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add feature"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )

    # Change to worktree directory
    monkeypatch.chdir(worktree_path)

    # Mock has_command to return True for gh
    mocker.patch("claude_worktree.operations.git_ops.has_command", return_value=True)

    # Mock subprocess.run only for gh pr create
    original_run = subprocess.run

    def mock_subprocess_run(cmd, *args, **kwargs):
        # Only mock gh pr create
        if isinstance(cmd, list) and len(cmd) > 0 and cmd[0] == "gh":
            return mocker.Mock(
                stdout="https://github.com/user/repo/pull/1\n", returncode=0, stderr=""
            )
        # Use original subprocess.run for git commands
        return original_run(cmd, *args, **kwargs)

    mocker.patch(
        "claude_worktree.operations.git_ops.subprocess.run", side_effect=mock_subprocess_run
    )

    # Create PR without pushing
    create_pr_worktree(push=False)

    # Verify worktree still exists (not cleaned up)
    assert worktree_path.exists()


def test_merge_worktree_success(temp_git_repo: Path, disable_claude, monkeypatch) -> None:
    """Test merge_worktree successfully merges and cleans up."""
    # Create worktree
    worktree_path = create_worktree(
        branch_name="merge-test",
        no_cd=True,
    )

    # Make a commit
    (worktree_path / "merge.txt").write_text("merge content")
    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add merge file"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )

    # Change to worktree
    monkeypatch.chdir(worktree_path)

    # Merge the worktree (should call finish_worktree internally)
    merge_worktree(push=False)

    # Change back to main repo
    monkeypatch.chdir(temp_git_repo)

    # Verify worktree was removed
    assert not worktree_path.exists()

    # Verify branch was deleted
    result = subprocess.run(
        ["git", "branch", "--list", "merge-test"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
    )
    assert "merge-test" not in result.stdout

    # Verify changes were merged to main
    assert (temp_git_repo / "merge.txt").exists()
    assert (temp_git_repo / "merge.txt").read_text() == "merge content"


def test_merge_worktree_with_rebase(temp_git_repo: Path, disable_claude, monkeypatch) -> None:
    """Test merge_worktree when base branch has new commits."""
    # Create worktree
    worktree_path = create_worktree(
        branch_name="merge-rebase-test",
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

    # Merge should rebase and merge
    monkeypatch.chdir(worktree_path)
    merge_worktree(push=False)

    # Change back to main repo for verification
    monkeypatch.chdir(temp_git_repo)

    # Verify both files exist in main
    assert (temp_git_repo / "feature.txt").exists()
    assert (temp_git_repo / "main.txt").exists()


def test_merge_worktree_dry_run(temp_git_repo: Path, disable_claude, monkeypatch, capsys) -> None:
    """Test merge_worktree dry-run mode doesn't modify anything."""
    # Create worktree
    worktree_path = create_worktree(
        branch_name="merge-dry-run-test",
        no_cd=True,
    )

    # Make commit in worktree
    (worktree_path / "feature.txt").write_text("feature content")
    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add feature"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )

    # Run merge with dry_run=True
    monkeypatch.chdir(worktree_path)
    merge_worktree(push=False, dry_run=True)

    # Verify output shows dry-run mode
    captured = capsys.readouterr()
    assert "DRY RUN MODE" in captured.out
    assert "No changes will be made" in captured.out

    # Verify nothing was actually changed
    # Worktree should still exist
    assert worktree_path.exists()
    assert (worktree_path / "feature.txt").exists()

    # Branch should still exist
    result = subprocess.run(
        ["git", "branch", "--list", "merge-dry-run-test"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
    )
    assert "merge-dry-run-test" in result.stdout

    # Changes should NOT be merged to main
    assert not (temp_git_repo / "feature.txt").exists()


def test_change_base_branch_success(temp_git_repo: Path, disable_claude, monkeypatch) -> None:
    """Test successfully changing base branch."""
    # Create master branch
    subprocess.run(
        ["git", "branch", "master"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    # Create worktree from main
    worktree_path = create_worktree(
        branch_name="feature-test",
        base_branch="main",
        no_cd=True,
    )

    # Make a commit in the worktree
    (worktree_path / "feature.txt").write_text("feature content")
    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add feature"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )

    # Change to worktree
    monkeypatch.chdir(worktree_path)

    # Change base to master
    change_base_branch(new_base="master")

    # Verify base branch metadata was updated
    result = subprocess.run(
        ["git", "config", "--local", "--get", "branch.feature-test.worktreeBase"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "master"


def test_change_base_branch_with_target(temp_git_repo: Path, disable_claude) -> None:
    """Test changing base branch with --target option."""
    # Create master branch
    subprocess.run(
        ["git", "branch", "master"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    # Create worktree from main
    worktree_path = create_worktree(
        branch_name="target-test",
        base_branch="main",
        no_cd=True,
    )

    # Make a commit
    (worktree_path / "file.txt").write_text("content")
    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add file"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )

    # Change base from main repo (not from within worktree)
    change_base_branch(new_base="master", target="target-test")

    # Verify base branch metadata was updated
    result = subprocess.run(
        ["git", "config", "--local", "--get", "branch.target-test.worktreeBase"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "master"


def test_change_base_branch_dry_run(
    temp_git_repo: Path, disable_claude, monkeypatch, capsys
) -> None:
    """Test dry-run mode for change-base."""
    # Create master branch
    subprocess.run(
        ["git", "branch", "master"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    # Create worktree
    worktree_path = create_worktree(
        branch_name="dry-run-base",
        base_branch="main",
        no_cd=True,
    )

    # Change to worktree
    monkeypatch.chdir(worktree_path)

    # Run change-base with dry_run=True
    change_base_branch(new_base="master", dry_run=True)

    # Verify output shows dry-run mode
    captured = capsys.readouterr()
    assert "DRY RUN MODE" in captured.out
    assert "No changes will be made" in captured.out
    assert "Fetch" in captured.out
    assert "Rebase" in captured.out
    assert "Update" in captured.out
    assert "main -> master" in captured.out

    # Verify base branch was NOT changed
    result = subprocess.run(
        ["git", "config", "--local", "--get", "branch.dry-run-base.worktreeBase"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "main"  # Still the original


def test_change_base_branch_invalid_base(temp_git_repo: Path, disable_claude, monkeypatch) -> None:
    """Test error when new base branch doesn't exist."""
    # Create worktree
    worktree_path = create_worktree(
        branch_name="invalid-base-test",
        no_cd=True,
    )

    # Change to worktree
    monkeypatch.chdir(worktree_path)

    # Try to change to nonexistent base
    with pytest.raises(InvalidBranchError, match="not found"):
        change_base_branch(new_base="nonexistent-branch")


def test_change_base_branch_no_metadata(temp_git_repo: Path, disable_claude) -> None:
    """Test error when worktree has no base branch metadata."""

    # Create a branch manually (without metadata)
    subprocess.run(
        ["git", "branch", "manual-branch"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    # Create worktree manually
    manual_path = temp_git_repo.parent / "manual-worktree"
    subprocess.run(
        ["git", "worktree", "add", str(manual_path), "manual-branch"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    # Try to change base (should fail - no metadata)
    with pytest.raises(GitError, match="No base branch metadata found"):
        change_base_branch(new_base="main", target="manual-branch")


def test_change_base_branch_with_conflicts(
    temp_git_repo: Path, disable_claude, monkeypatch
) -> None:
    """Test change-base when rebase has conflicts."""
    from claude_worktree.exceptions import RebaseError

    # Create develop branch with conflicting change
    subprocess.run(
        ["git", "checkout", "-b", "develop"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )
    (temp_git_repo / "conflict.txt").write_text("develop content")
    subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Develop change"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    # Switch back to main
    subprocess.run(
        ["git", "checkout", "main"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    # Create worktree from main with conflicting change
    worktree_path = create_worktree(
        branch_name="conflict-test",
        base_branch="main",
        no_cd=True,
    )
    (worktree_path / "conflict.txt").write_text("main content")
    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Main change"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )

    # Change to worktree
    monkeypatch.chdir(worktree_path)

    # Try to change base to develop (should fail with conflicts)
    with pytest.raises(RebaseError, match="Rebase failed"):
        change_base_branch(new_base="develop")

    # Verify base branch was NOT changed (rebase was aborted)
    result = subprocess.run(
        ["git", "config", "--local", "--get", "branch.conflict-test.worktreeBase"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "main"  # Still the original


def test_sync_worktree_with_ai_merge_conflicts(
    temp_git_repo: Path, disable_claude, monkeypatch
) -> None:
    """Test sync with --ai-merge when conflicts occur."""
    from claude_worktree.exceptions import RebaseError
    from claude_worktree.operations import sync_worktree

    # Create develop branch with conflicting change
    subprocess.run(
        ["git", "checkout", "-b", "develop"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )
    (temp_git_repo / "sync-conflict.txt").write_text("develop content")
    subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Develop change"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    # Switch back to main
    subprocess.run(
        ["git", "checkout", "main"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    # Create worktree from main
    worktree_path = create_worktree(
        branch_name="sync-conflict-test",
        base_branch="main",
        no_cd=True,
    )

    # Make conflicting change in worktree
    (worktree_path / "sync-conflict.txt").write_text("main content")
    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Main change"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )

    # Update base branch metadata to develop
    subprocess.run(
        ["git", "config", "--local", "branch.sync-conflict-test.worktreeBase", "develop"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    # Change to worktree
    monkeypatch.chdir(worktree_path)

    # Try to sync without AI merge (should just fail with helpful message)
    with pytest.raises(RebaseError, match="Rebase failed"):
        sync_worktree(ai_merge=False)


def test_sync_worktree_success(temp_git_repo: Path, disable_claude, monkeypatch) -> None:
    """Test successful sync without conflicts."""
    from claude_worktree.operations import sync_worktree

    # Create worktree
    worktree_path = create_worktree(
        branch_name="sync-success-test",
        base_branch="main",
        no_cd=True,
    )

    # Make a commit in the worktree
    (worktree_path / "sync-feature.txt").write_text("feature content")
    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add feature"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )

    # Make a non-conflicting commit in main
    (temp_git_repo / "main-work.txt").write_text("main work")
    subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Main work"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    # Change to worktree
    monkeypatch.chdir(worktree_path)

    # Sync should succeed
    sync_worktree()

    # Verify both files exist in worktree after rebase
    assert (worktree_path / "sync-feature.txt").exists()
    assert (worktree_path / "main-work.txt").exists()


def test_sync_all_worktrees(temp_git_repo: Path, disable_claude, monkeypatch) -> None:
    """Test sync --all updates local base branches and rebases all worktrees."""
    from claude_worktree.operations import sync_worktree

    # Create two worktrees from main
    worktree1 = create_worktree(
        branch_name="wt1",
        base_branch="main",
        no_cd=True,
    )
    worktree2 = create_worktree(
        branch_name="wt2",
        base_branch="main",
        no_cd=True,
    )

    # Make commits in each worktree
    (worktree1 / "wt1-file.txt").write_text("wt1 content")
    subprocess.run(["git", "add", "."], cwd=worktree1, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "wt1 work"],
        cwd=worktree1,
        check=True,
        capture_output=True,
    )

    (worktree2 / "wt2-file.txt").write_text("wt2 content")
    subprocess.run(["git", "add", "."], cwd=worktree2, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "wt2 work"],
        cwd=worktree2,
        check=True,
        capture_output=True,
    )

    # Make a new commit in main (simulating upstream changes)
    (temp_git_repo / "main-work.txt").write_text("main work")
    subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Main work"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    # Run sync --all from main repo
    monkeypatch.chdir(temp_git_repo)
    sync_worktree(all_worktrees=True)

    # Verify both worktrees were rebased and now have the main-work.txt file
    assert (worktree1 / "main-work.txt").exists()
    assert (worktree1 / "wt1-file.txt").exists()

    assert (worktree2 / "main-work.txt").exists()
    assert (worktree2 / "wt2-file.txt").exists()


def test_sync_nested_worktrees(temp_git_repo: Path, disable_claude, monkeypatch) -> None:
    """Test sync --all with nested worktrees (worktree depending on another worktree)."""
    from claude_worktree.operations import sync_worktree

    # Create first worktree from main
    worktree_a = create_worktree(
        branch_name="feature-a",
        base_branch="main",
        no_cd=True,
    )

    # Make a commit in feature-a
    (worktree_a / "feature-a.txt").write_text("feature A")
    subprocess.run(["git", "add", "."], cwd=worktree_a, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add feature A"],
        cwd=worktree_a,
        check=True,
        capture_output=True,
    )

    # Create nested worktree from feature-a
    worktree_a_refinement = create_worktree(
        branch_name="feature-a-refinement",
        base_branch="feature-a",
        no_cd=True,
    )

    # Make a commit in feature-a-refinement
    (worktree_a_refinement / "refinement.txt").write_text("refinement")
    subprocess.run(["git", "add", "."], cwd=worktree_a_refinement, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add refinement"],
        cwd=worktree_a_refinement,
        check=True,
        capture_output=True,
    )

    # Make a new commit in main (simulating upstream changes)
    (temp_git_repo / "main-update.txt").write_text("main update")
    subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Update main"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    # Run sync --all from main repo
    monkeypatch.chdir(temp_git_repo)
    sync_worktree(all_worktrees=True)

    # Verify feature-a has main's update
    assert (worktree_a / "main-update.txt").exists()
    assert (worktree_a / "feature-a.txt").exists()

    # Verify feature-a-refinement has both main's update and feature-a's update
    # This proves topological sort worked: feature-a was synced before feature-a-refinement
    assert (worktree_a_refinement / "main-update.txt").exists()
    assert (worktree_a_refinement / "feature-a.txt").exists()
    assert (worktree_a_refinement / "refinement.txt").exists()


def test_create_worktree_existing_worktree_non_interactive(
    temp_git_repo: Path, disable_claude
) -> None:
    """Test creating worktree when one already exists (non-interactive mode)."""
    # Create initial worktree
    worktree_path = create_worktree(
        branch_name="duplicate-test",
        no_cd=True,
    )
    assert worktree_path.exists()

    # Try to create again with same branch name (non-interactive = no stdin.isatty())
    # Should raise InvalidBranchError with helpful message
    with pytest.raises(InvalidBranchError, match="already exists"):
        create_worktree(
            branch_name="duplicate-test",
            no_cd=True,
        )


def test_create_worktree_existing_branch_non_interactive(
    temp_git_repo: Path, disable_claude
) -> None:
    """Test creating worktree from existing branch (non-interactive mode)."""
    # Create a branch manually (no worktree)
    subprocess.run(
        ["git", "branch", "existing-branch"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )

    # Verify branch exists
    result = subprocess.run(
        ["git", "branch", "--list", "existing-branch"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
    )
    assert "existing-branch" in result.stdout

    # Create worktree from existing branch (non-interactive mode should proceed)
    worktree_path = create_worktree(
        branch_name="existing-branch",
        no_cd=True,
    )

    # Verify worktree was created
    assert worktree_path.exists()
    assert (worktree_path / "README.md").exists()

    # Verify worktree is registered
    result = subprocess.run(
        ["git", "worktree", "list"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
    )
    assert worktree_path.as_posix() in result.stdout


def test_delete_worktree_current_directory(
    temp_git_repo: Path, disable_claude, monkeypatch
) -> None:
    """Test deleting worktree from within that worktree (current directory)."""
    worktree_path = create_worktree(branch_name="delete-current", no_cd=True)
    assert worktree_path.exists()

    # Change to the worktree directory
    monkeypatch.chdir(worktree_path)

    # Delete without specifying target (should use current directory)
    delete_worktree(target=None, keep_branch=False)

    # Verify worktree and branch were removed
    assert not worktree_path.exists()
    result = subprocess.run(
        ["git", "branch", "--list", "delete-current"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
    )
    assert "delete-current" not in result.stdout


def test_delete_worktree_current_directory_main_repo_error(
    temp_git_repo: Path, monkeypatch
) -> None:
    """Test that deleting main repo from within main repo raises error."""
    # Change to main repo directory
    monkeypatch.chdir(temp_git_repo)

    # Try to delete without specifying target (current directory = main repo)
    with pytest.raises(GitError, match="Cannot delete main repository"):
        delete_worktree(target=None)
