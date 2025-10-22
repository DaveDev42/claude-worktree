"""Tests for constants module."""

from pathlib import Path

from claude_worktree.constants import default_worktree_path, sanitize_branch_name


def test_sanitize_branch_name_simple() -> None:
    """Test sanitization of simple branch names."""
    assert sanitize_branch_name("fix-auth") == "fix-auth"
    assert sanitize_branch_name("feature") == "feature"
    assert sanitize_branch_name("v1.0") == "v1.0"


def test_sanitize_branch_name_with_slashes() -> None:
    """Test sanitization of branch names with slashes."""
    assert sanitize_branch_name("feat/auth") == "feat-auth"
    assert sanitize_branch_name("bugfix/issue-123") == "bugfix-issue-123"
    assert sanitize_branch_name("feature/user/login") == "feature-user-login"
    assert sanitize_branch_name("hotfix/v2.0") == "hotfix-v2.0"


def test_sanitize_branch_name_special_characters() -> None:
    """Test sanitization of branch names with special characters."""
    # Unsafe filesystem characters
    assert sanitize_branch_name("feature<test>") == "feature-test"
    assert sanitize_branch_name("fix:issue") == "fix-issue"
    assert sanitize_branch_name('bug"quote') == "bug-quote"
    assert sanitize_branch_name("test|pipe") == "test-pipe"
    assert sanitize_branch_name("star*test") == "star-test"
    assert sanitize_branch_name("back\\slash") == "back-slash"
    assert sanitize_branch_name("question?mark") == "question-mark"


def test_sanitize_branch_name_whitespace() -> None:
    """Test sanitization of branch names with whitespace."""
    assert sanitize_branch_name("fix auth") == "fix-auth"
    assert sanitize_branch_name("feature  multi  space") == "feature-multi-space"
    assert sanitize_branch_name("tab\there") == "tab-here"


def test_sanitize_branch_name_multiple_hyphens() -> None:
    """Test that multiple consecutive hyphens are collapsed."""
    assert sanitize_branch_name("feat//auth") == "feat-auth"
    assert sanitize_branch_name("fix///bug") == "fix-bug"
    assert sanitize_branch_name("test<<>>name") == "test-name"


def test_sanitize_branch_name_leading_trailing() -> None:
    """Test that leading/trailing hyphens are removed."""
    assert sanitize_branch_name("/feat/auth") == "feat-auth"
    assert sanitize_branch_name("feat/auth/") == "feat-auth"
    assert sanitize_branch_name("/feat/auth/") == "feat-auth"
    assert sanitize_branch_name("-branch-") == "branch"


def test_sanitize_branch_name_edge_cases() -> None:
    """Test edge cases for branch name sanitization."""
    # Empty or all-special-chars should fallback
    assert sanitize_branch_name("///") == "worktree"
    assert sanitize_branch_name("***") == "worktree"
    assert sanitize_branch_name("   ") == "worktree"

    # Single character
    assert sanitize_branch_name("a") == "a"
    assert sanitize_branch_name("/") == "worktree"


def test_sanitize_branch_name_unicode() -> None:
    """Test that Unicode characters are preserved."""
    # Most filesystems support UTF-8
    assert sanitize_branch_name("feature-日本語") == "feature-日本語"
    assert sanitize_branch_name("émoji-test") == "émoji-test"


def test_sanitize_branch_name_complex() -> None:
    """Test complex real-world branch name patterns."""
    assert sanitize_branch_name("feature/USER-123/add-authentication") == (
        "feature-USER-123-add-authentication"
    )
    assert sanitize_branch_name("bugfix/issue#456") == "bugfix-issue-456"
    assert sanitize_branch_name("release/v2.0.1-beta") == "release-v2.0.1-beta"


def test_default_worktree_path_simple() -> None:
    """Test default worktree path generation with simple branch names."""
    repo = Path("/Users/dave/myproject")
    assert default_worktree_path(repo, "fix-auth") == Path("/Users/dave/myproject-fix-auth")
    assert default_worktree_path(repo, "feature") == Path("/Users/dave/myproject-feature")


def test_default_worktree_path_with_slashes() -> None:
    """Test default worktree path generation with branch names containing slashes."""
    repo = Path("/Users/dave/myproject")
    assert default_worktree_path(repo, "feat/auth") == Path("/Users/dave/myproject-feat-auth")
    assert default_worktree_path(repo, "bugfix/issue-123") == Path(
        "/Users/dave/myproject-bugfix-issue-123"
    )
    assert default_worktree_path(repo, "release/v2.0") == Path("/Users/dave/myproject-release-v2.0")


def test_default_worktree_path_special_chars() -> None:
    """Test default worktree path generation with special characters."""
    repo = Path("/Users/dave/myproject")
    # Should sanitize unsafe characters
    assert default_worktree_path(repo, "fix:auth") == Path("/Users/dave/myproject-fix-auth")
    assert default_worktree_path(repo, "feature<test>") == Path(
        "/Users/dave/myproject-feature-test"
    )
