"""Tests for git_utils module."""

import subprocess
from pathlib import Path

import pytest

from claude_worktree.exceptions import GitError, InvalidBranchError
from claude_worktree.git_utils import (
    branch_exists,
    find_worktree_by_branch,
    get_config,
    get_current_branch,
    get_repo_root,
    has_command,
    parse_worktrees,
    set_config,
    unset_config,
)


def test_get_repo_root(temp_git_repo: Path) -> None:
    """Test getting repository root."""
    root = get_repo_root()
    assert root == temp_git_repo


def test_get_repo_root_not_in_repo(tmp_path: Path, monkeypatch) -> None:
    """Test error when not in a git repository."""
    non_repo = tmp_path / "not_a_repo"
    non_repo.mkdir()
    monkeypatch.chdir(non_repo)

    with pytest.raises(GitError, match="Not in a git repository"):
        get_repo_root()


def test_get_current_branch(temp_git_repo: Path) -> None:
    """Test getting current branch name."""
    branch = get_current_branch(temp_git_repo)
    # Should be on main or master
    assert branch in ("main", "master")


def test_get_current_branch_detached(temp_git_repo: Path, monkeypatch) -> None:
    """Test error when in detached HEAD state."""
    # Get current commit hash
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    commit_hash = result.stdout.strip()

    # Checkout detached HEAD
    subprocess.run(
        ["git", "checkout", commit_hash],
        cwd=temp_git_repo,
        capture_output=True,
        check=True,
    )

    monkeypatch.chdir(temp_git_repo)

    with pytest.raises(InvalidBranchError, match="detached HEAD"):
        get_current_branch()


def test_branch_exists(temp_git_repo: Path) -> None:
    """Test checking if branch exists."""
    # Main/master branch should exist
    assert branch_exists("main", temp_git_repo) or branch_exists("master", temp_git_repo)

    # Non-existent branch
    assert not branch_exists("nonexistent-branch-xyz", temp_git_repo)

    # Create a new branch
    subprocess.run(
        ["git", "branch", "test-branch"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True,
    )
    assert branch_exists("test-branch", temp_git_repo)


def test_parse_worktrees(temp_git_repo: Path) -> None:
    """Test parsing worktree list."""
    worktrees = parse_worktrees(temp_git_repo)

    # Should have at least the main worktree
    assert len(worktrees) >= 1

    # Main worktree should be present
    branches = [br for br, _ in worktrees]
    assert any("main" in branch or "master" in branch for branch in branches)


def test_parse_worktrees_multiple(temp_git_repo: Path) -> None:
    """Test parsing multiple worktrees."""
    # Create a new worktree
    feature_path = temp_git_repo.parent / "feature"
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature-branch", str(feature_path), "HEAD"],
        cwd=temp_git_repo,
        capture_output=True,
        check=True,
    )

    worktrees = parse_worktrees(temp_git_repo)
    assert len(worktrees) == 2

    branches = [br for br, _ in worktrees]
    assert "refs/heads/feature-branch" in branches


def test_find_worktree_by_branch(temp_git_repo: Path) -> None:
    """Test finding worktree by branch name."""
    # Create a new worktree
    feature_path = temp_git_repo.parent / "feature"
    subprocess.run(
        ["git", "worktree", "add", "-b", "my-feature", str(feature_path), "HEAD"],
        cwd=temp_git_repo,
        capture_output=True,
        check=True,
    )

    # Should find the worktree
    found_path = find_worktree_by_branch(temp_git_repo, "refs/heads/my-feature")
    assert found_path == str(feature_path)

    # Should not find non-existent branch
    assert find_worktree_by_branch(temp_git_repo, "refs/heads/nonexistent") is None


def test_has_command() -> None:
    """Test checking if command exists."""
    # Git must exist for tests to run
    assert has_command("git")

    # This command definitely doesn't exist
    assert not has_command("definitely-not-a-real-command-xyz-12345")


def test_config_operations(temp_git_repo: Path) -> None:
    """Test git config get/set/unset operations."""
    # Set a config value
    set_config("test.key", "test_value", temp_git_repo)

    # Get the value
    value = get_config("test.key", temp_git_repo)
    assert value == "test_value"

    # Unset the value
    unset_config("test.key", temp_git_repo)

    # Should return None after unset
    value = get_config("test.key", temp_git_repo)
    assert value is None


def test_is_valid_branch_name(temp_git_repo: Path) -> None:
    """Test branch name validation."""
    from claude_worktree.git_utils import is_valid_branch_name

    # Valid branch names
    assert is_valid_branch_name("feature", temp_git_repo)
    assert is_valid_branch_name("fix-auth", temp_git_repo)
    assert is_valid_branch_name("feat/auth", temp_git_repo)
    assert is_valid_branch_name("bugfix/issue-123", temp_git_repo)
    assert is_valid_branch_name("release/v2.0.1", temp_git_repo)
    assert is_valid_branch_name("user-123", temp_git_repo)

    # Korean is valid in UTF-8
    assert is_valid_branch_name("안녕하세요", temp_git_repo)

    # Invalid branch names
    assert not is_valid_branch_name("", temp_git_repo)  # Empty
    # Note: "@" alone is actually valid in git (becomes refs/heads/@)
    assert not is_valid_branch_name("branch.lock", temp_git_repo)  # Ends with .lock
    assert not is_valid_branch_name("/branch", temp_git_repo)  # Starts with /
    assert not is_valid_branch_name("branch/", temp_git_repo)  # Ends with /
    assert not is_valid_branch_name("feat//auth", temp_git_repo)  # Consecutive //
    assert not is_valid_branch_name("feat..auth", temp_git_repo)  # Consecutive ..
    assert not is_valid_branch_name("feat@{auth", temp_git_repo)  # Contains @{
    assert not is_valid_branch_name("feat~auth", temp_git_repo)  # Contains ~
    assert not is_valid_branch_name("feat^auth", temp_git_repo)  # Contains ^
    assert not is_valid_branch_name("feat:auth", temp_git_repo)  # Contains :
    assert not is_valid_branch_name("feat?auth", temp_git_repo)  # Contains ?
    assert not is_valid_branch_name("feat*auth", temp_git_repo)  # Contains *
    assert not is_valid_branch_name("feat[auth", temp_git_repo)  # Contains [
    assert not is_valid_branch_name("feat\\auth", temp_git_repo)  # Contains backslash
    assert not is_valid_branch_name("feat auth", temp_git_repo)  # Contains space

    # Note: Git actually allows emojis in branch names (as UTF-8)
    # They may cause issues with some tools, but git check-ref-format allows them


def test_get_branch_name_error() -> None:
    """Test error message generation for invalid branch names."""
    from claude_worktree.git_utils import get_branch_name_error

    assert "empty" in get_branch_name_error("").lower()
    assert "@" in get_branch_name_error("@")
    assert ".lock" in get_branch_name_error("branch.lock")
    assert "/" in get_branch_name_error("/branch")
    assert "/" in get_branch_name_error("branch/")
    assert "//" in get_branch_name_error("feat//auth")
    assert ".." in get_branch_name_error("feat..auth")
    assert "@{" in get_branch_name_error("feat@{auth")
    assert "~" in get_branch_name_error("feat~auth")
    assert "space" in get_branch_name_error("feat auth").lower()
