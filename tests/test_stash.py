"""Tests for stash functionality."""

import subprocess
from pathlib import Path

import pytest

from claude_worktree.exceptions import GitError, WorktreeNotFoundError
from claude_worktree.operations import stash_apply, stash_list, stash_save


def test_stash_save_with_message(temp_git_repo: Path, monkeypatch) -> None:
    """Test saving stash with custom message."""
    monkeypatch.chdir(temp_git_repo)

    # Create a file to stash
    test_file = temp_git_repo / "test.txt"
    test_file.write_text("test content")

    # Save stash with message
    stash_save(message="my custom message")

    # Verify stash was created
    result = subprocess.run(
        ["git", "stash", "list"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
        check=True,
    )

    # Check stash message includes branch and custom message
    branch_name = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    assert f"[{branch_name}] my custom message" in result.stdout

    # Verify working directory is clean
    assert not test_file.exists()


def test_stash_save_without_message(temp_git_repo: Path, monkeypatch) -> None:
    """Test saving stash with default WIP message."""
    monkeypatch.chdir(temp_git_repo)

    # Create a file to stash
    test_file = temp_git_repo / "test.txt"
    test_file.write_text("test content")

    # Save stash without message
    stash_save()

    # Verify stash was created with default message
    result = subprocess.run(
        ["git", "stash", "list"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
        check=True,
    )

    branch_name = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    assert f"[{branch_name}] WIP" in result.stdout


def test_stash_save_no_changes(temp_git_repo: Path, monkeypatch, capsys) -> None:
    """Test stash save when there are no changes."""
    monkeypatch.chdir(temp_git_repo)

    # Try to stash with no changes
    stash_save()

    # Should print warning
    captured = capsys.readouterr()
    assert "No changes to stash" in captured.out


def test_stash_list_empty(temp_git_repo: Path, capsys) -> None:
    """Test listing stashes when none exist."""
    stash_list()

    captured = capsys.readouterr()
    assert "No stashes found" in captured.out


def test_stash_list_multiple_branches(temp_git_repo: Path, monkeypatch, capsys) -> None:
    """Test listing stashes from multiple branches."""
    # Create stash on main branch
    monkeypatch.chdir(temp_git_repo)
    test_file = temp_git_repo / "test.txt"
    test_file.write_text("main content")
    stash_save(message="main work")

    # Create a new branch and stash
    subprocess.run(
        ["git", "checkout", "-b", "feature"],
        cwd=temp_git_repo,
        capture_output=True,
        check=True,
    )

    test_file2 = temp_git_repo / "test2.txt"
    test_file2.write_text("feature content")
    stash_save(message="feature work")

    # List stashes
    stash_list()

    captured = capsys.readouterr()
    # Should show both branches
    assert "main" in captured.out or "master" in captured.out
    assert "feature" in captured.out
    assert "main work" in captured.out
    assert "feature work" in captured.out


def test_stash_apply_to_same_worktree(temp_git_repo: Path, monkeypatch) -> None:
    """Test applying stash to the same worktree."""
    monkeypatch.chdir(temp_git_repo)

    # Create and stash a file
    test_file = temp_git_repo / "test.txt"
    test_file.write_text("test content")

    branch_name = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    stash_save(message="my work")

    # File should be gone
    assert not test_file.exists()

    # Apply stash back
    stash_apply(target_branch=branch_name)

    # File should be restored
    assert test_file.exists()
    assert test_file.read_text() == "test content"


def test_stash_apply_to_different_worktree(temp_git_repo: Path, monkeypatch) -> None:
    """Test applying stash to a different worktree."""
    monkeypatch.chdir(temp_git_repo)

    # Create and stash a file on main
    test_file = temp_git_repo / "test.txt"
    test_file.write_text("main content")
    stash_save(message="main work")

    # Create a new worktree
    feature_path = temp_git_repo.parent / "feature"
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature-branch", str(feature_path), "HEAD"],
        cwd=temp_git_repo,
        capture_output=True,
        check=True,
    )

    # Apply stash to the new worktree
    stash_apply(target_branch="refs/heads/feature-branch")

    # Verify file exists in feature worktree
    feature_test_file = feature_path / "test.txt"
    assert feature_test_file.exists()
    assert feature_test_file.read_text() == "main content"


def test_stash_apply_nonexistent_branch(temp_git_repo: Path) -> None:
    """Test applying stash to nonexistent branch."""
    with pytest.raises(WorktreeNotFoundError, match="No worktree found for branch"):
        stash_apply(target_branch="nonexistent-branch")


def test_stash_apply_invalid_stash_ref(temp_git_repo: Path, monkeypatch) -> None:
    """Test applying invalid stash reference."""
    monkeypatch.chdir(temp_git_repo)

    branch_name = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    with pytest.raises(GitError, match="Stash .* not found"):
        stash_apply(target_branch=branch_name, stash_ref="stash@{999}")


def test_stash_apply_specific_ref(temp_git_repo: Path, monkeypatch) -> None:
    """Test applying a specific stash by reference."""
    monkeypatch.chdir(temp_git_repo)

    # Create multiple stashes
    test_file1 = temp_git_repo / "test1.txt"
    test_file1.write_text("first")
    stash_save(message="first stash")

    test_file2 = temp_git_repo / "test2.txt"
    test_file2.write_text("second")
    stash_save(message="second stash")

    # Both files should be gone
    assert not test_file1.exists()
    assert not test_file2.exists()

    branch_name = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    # Apply the older stash (stash@{1})
    stash_apply(target_branch=branch_name, stash_ref="stash@{1}")

    # Only first file should be restored
    assert test_file1.exists()
    assert not test_file2.exists()
