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
    normalize_branch_name,
    parse_worktrees,
    remote_branch_exists,
    set_config,
    unset_config,
)


def test_normalize_branch_name() -> None:
    """Test branch name normalization."""
    # Test with refs/heads/ prefix
    assert normalize_branch_name("refs/heads/main") == "main"
    assert normalize_branch_name("refs/heads/feature-branch") == "feature-branch"
    assert normalize_branch_name("refs/heads/fix/auth") == "fix/auth"
    assert normalize_branch_name("refs/heads/release/v1.0.0") == "release/v1.0.0"

    # Test without refs/heads/ prefix (should return as-is)
    assert normalize_branch_name("main") == "main"
    assert normalize_branch_name("feature-branch") == "feature-branch"
    assert normalize_branch_name("fix/auth") == "fix/auth"

    # Edge cases
    assert normalize_branch_name("refs/heads/") == ""  # Empty branch name after prefix
    assert normalize_branch_name("") == ""  # Empty string
    assert normalize_branch_name("refs/heads") == "refs/heads"  # No trailing slash

    # Branch names that start with similar patterns but aren't refs/heads/
    assert normalize_branch_name("refs/heads-like") == "refs/heads-like"
    assert normalize_branch_name("refs/tags/v1.0.0") == "refs/tags/v1.0.0"


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


def test_remote_branch_exists(temp_git_repo: Path) -> None:
    """Test checking if a remote branch exists."""
    # No remote configured - should return False
    assert not remote_branch_exists("main", temp_git_repo)
    assert not remote_branch_exists("nonexistent-branch", temp_git_repo)


def test_remote_branch_exists_with_remote(temp_git_repo: Path, tmp_path: Path) -> None:
    """Test remote_branch_exists with an actual remote repository."""
    # Create a bare "remote" repository
    remote_path = tmp_path / "remote_repo.git"
    subprocess.run(["git", "clone", "--bare", str(temp_git_repo), str(remote_path)],
                    check=True, capture_output=True)

    # Add the bare repo as a remote
    subprocess.run(
        ["git", "remote", "add", "origin", str(remote_path)],
        cwd=temp_git_repo, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "fetch", "origin"],
        cwd=temp_git_repo, check=True, capture_output=True,
    )

    # Now origin/main should exist
    assert remote_branch_exists("main", temp_git_repo)

    # Non-existent branch should not exist
    assert not remote_branch_exists("nonexistent-branch", temp_git_repo)

    # Create a branch on remote only
    subprocess.run(
        ["git", "branch", "remote-only-branch"],
        cwd=temp_git_repo, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "push", "origin", "remote-only-branch"],
        cwd=temp_git_repo, check=True, capture_output=True,
    )
    # Delete local branch
    subprocess.run(
        ["git", "branch", "-D", "remote-only-branch"],
        cwd=temp_git_repo, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "fetch", "origin"],
        cwd=temp_git_repo, check=True, capture_output=True,
    )

    # Should exist on remote but not locally
    assert not branch_exists("remote-only-branch", temp_git_repo)
    assert remote_branch_exists("remote-only-branch", temp_git_repo)


def test_remote_branch_exists_with_slashes(temp_git_repo: Path, tmp_path: Path) -> None:
    """Test remote_branch_exists with branch names containing slashes."""
    # Create a bare "remote" repository
    remote_path = tmp_path / "remote_repo.git"
    subprocess.run(
        ["git", "clone", "--bare", str(temp_git_repo), str(remote_path)],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "remote", "add", "origin", str(remote_path)],
        cwd=temp_git_repo, check=True, capture_output=True,
    )

    # Create and push branch with slashes
    subprocess.run(
        ["git", "branch", "feature/auth"],
        cwd=temp_git_repo, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "push", "origin", "feature/auth"],
        cwd=temp_git_repo, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "branch", "-D", "feature/auth"],
        cwd=temp_git_repo, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "fetch", "origin"],
        cwd=temp_git_repo, check=True, capture_output=True,
    )

    assert remote_branch_exists("feature/auth", temp_git_repo)
    assert not remote_branch_exists("feature", temp_git_repo)  # prefix should not match


def test_remote_branch_exists_custom_remote(temp_git_repo: Path, tmp_path: Path) -> None:
    """Test remote_branch_exists with a non-default remote name."""
    # Create a bare "remote" repository
    remote_path = tmp_path / "upstream_repo.git"
    subprocess.run(
        ["git", "clone", "--bare", str(temp_git_repo), str(remote_path)],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "remote", "add", "upstream", str(remote_path)],
        cwd=temp_git_repo, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "fetch", "upstream"],
        cwd=temp_git_repo, check=True, capture_output=True,
    )

    # Should find on upstream, not on origin
    assert remote_branch_exists("main", temp_git_repo, remote="upstream")
    assert not remote_branch_exists("main", temp_git_repo, remote="origin")


def test_remote_branch_exists_stale_ref(temp_git_repo: Path, tmp_path: Path) -> None:
    """Test remote_branch_exists with stale remote tracking ref (not yet pruned)."""
    # Create a bare "remote" repository
    remote_path = tmp_path / "remote_repo.git"
    subprocess.run(
        ["git", "clone", "--bare", str(temp_git_repo), str(remote_path)],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "remote", "add", "origin", str(remote_path)],
        cwd=temp_git_repo, check=True, capture_output=True,
    )

    # Create and push a branch
    subprocess.run(
        ["git", "branch", "stale-branch"],
        cwd=temp_git_repo, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "push", "origin", "stale-branch"],
        cwd=temp_git_repo, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "branch", "-D", "stale-branch"],
        cwd=temp_git_repo, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "fetch", "origin"],
        cwd=temp_git_repo, check=True, capture_output=True,
    )

    # Verify it exists
    assert remote_branch_exists("stale-branch", temp_git_repo)

    # Delete from remote directly (simulate another user deleting)
    subprocess.run(
        ["git", "branch", "-D", "stale-branch"],
        cwd=remote_path, check=True, capture_output=True,
    )

    # Without prune, stale ref should still return True (based on local tracking ref)
    assert remote_branch_exists("stale-branch", temp_git_repo)

    # After prune, should return False
    subprocess.run(
        ["git", "fetch", "--prune", "origin"],
        cwd=temp_git_repo, check=True, capture_output=True,
    )
    assert not remote_branch_exists("stale-branch", temp_git_repo)


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
    assert found_path == feature_path

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


def test_remove_worktree_safe_success(temp_git_repo: Path, monkeypatch) -> None:
    """Test successful worktree removal via git command."""
    from unittest.mock import Mock

    from claude_worktree.git_utils import remove_worktree_safe

    # Mock successful git worktree remove
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = ""

    mock_git_command = Mock(return_value=mock_result)
    monkeypatch.setattr("claude_worktree.git_utils.git_command", mock_git_command)

    # Test worktree path
    worktree_path = temp_git_repo.parent / "test-worktree"

    # Should succeed without raising exception
    remove_worktree_safe(worktree_path, temp_git_repo, force=True)

    # Verify git worktree remove was called with --force
    mock_git_command.assert_called_once()
    args = mock_git_command.call_args[0]
    assert args[0] == "worktree"
    assert args[1] == "remove"
    assert str(worktree_path.resolve()) in args
    assert "--force" in args


def test_remove_worktree_safe_windows_fallback(
    temp_git_repo: Path, monkeypatch, tmp_path: Path
) -> None:
    """Test Windows fallback when git worktree remove fails with 'Directory not empty'."""
    from unittest.mock import Mock

    from claude_worktree.git_utils import remove_worktree_safe

    # Force Windows behavior
    monkeypatch.setattr("platform.system", lambda: "Windows")

    # Create a real worktree directory with files and nested structure
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()
    (worktree_path / "test.txt").write_text("test content")

    # Create nested directory structure (simulating node_modules)
    nested_dir = worktree_path / "node_modules" / ".pnpm" / "package"
    nested_dir.mkdir(parents=True)
    (nested_dir / "file.js").write_text("console.log('test');")

    # Mock git worktree remove to fail with "Directory not empty"
    def mock_git_command(*args, **kwargs):
        if args[0] == "worktree" and args[1] == "remove":
            result = Mock()
            result.returncode = 128
            result.stdout = "error: failed to delete '...': Directory not empty"
            return result
        elif args[0] == "worktree" and args[1] == "prune":
            result = Mock()
            result.returncode = 0
            result.stdout = ""
            return result
        return Mock(returncode=0, stdout="")

    monkeypatch.setattr("claude_worktree.git_utils.git_command", mock_git_command)

    # Should succeed using shutil.rmtree fallback
    remove_worktree_safe(worktree_path, temp_git_repo, force=True)

    # Verify directory was removed
    assert not worktree_path.exists()


def test_remove_worktree_safe_non_windows_failure(temp_git_repo: Path, monkeypatch) -> None:
    """Test that non-Windows errors are propagated."""
    from unittest.mock import Mock

    from claude_worktree.exceptions import GitError
    from claude_worktree.git_utils import remove_worktree_safe

    # Force non-Windows behavior
    monkeypatch.setattr("platform.system", lambda: "Linux")

    # Mock git worktree remove to fail
    mock_result = Mock()
    mock_result.returncode = 128
    mock_result.stdout = "error: some other error"

    mock_git_command = Mock(return_value=mock_result)
    monkeypatch.setattr("claude_worktree.git_utils.git_command", mock_git_command)

    worktree_path = temp_git_repo.parent / "test-worktree"

    # Should raise GitError on non-Windows platforms
    with pytest.raises(GitError) as exc_info:
        remove_worktree_safe(worktree_path, temp_git_repo, force=True)

    assert "Command failed" in str(exc_info.value)


def test_remove_worktree_safe_windows_different_error(temp_git_repo: Path, monkeypatch) -> None:
    """Test that Windows errors other than 'Directory not empty' are propagated."""
    from unittest.mock import Mock

    from claude_worktree.exceptions import GitError
    from claude_worktree.git_utils import remove_worktree_safe

    # Force Windows behavior
    monkeypatch.setattr("platform.system", lambda: "Windows")

    # Mock git worktree remove to fail with different error
    mock_result = Mock()
    mock_result.returncode = 128
    mock_result.stdout = "error: permission denied"

    mock_git_command = Mock(return_value=mock_result)
    monkeypatch.setattr("claude_worktree.git_utils.git_command", mock_git_command)

    worktree_path = temp_git_repo.parent / "test-worktree"

    # Should raise GitError even on Windows for different errors
    with pytest.raises(GitError) as exc_info:
        remove_worktree_safe(worktree_path, temp_git_repo, force=True)

    assert "Command failed" in str(exc_info.value)
