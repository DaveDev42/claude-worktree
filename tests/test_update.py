"""Tests for update module."""

from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

from claude_worktree.update import (
    detect_installer,
    is_newer_version,
    load_update_cache,
    mark_update_checked,
    save_update_cache,
    should_check_update,
)


def test_is_newer_version() -> None:
    """Test version comparison."""
    assert is_newer_version("0.2.0", "0.1.0")
    assert is_newer_version("0.1.1", "0.1.0")
    assert is_newer_version("1.0.0", "0.9.9")
    assert not is_newer_version("0.1.0", "0.1.0")
    assert not is_newer_version("0.1.0", "0.2.0")
    assert not is_newer_version("0.1.0", "0.1.1")
    # Dev versions should not trigger update
    assert not is_newer_version("0.2.0", "0.1.0.dev")


def test_cache_operations(tmp_path: Path, monkeypatch) -> None:
    """Test cache save and load operations."""
    # Set up temporary cache directory
    cache_dir = tmp_path / ".cache" / "claude-worktree"
    cache_file = cache_dir / "update_check.json"

    monkeypatch.setattr("claude_worktree.update.CACHE_DIR", cache_dir)
    monkeypatch.setattr("claude_worktree.update.UPDATE_CHECK_FILE", cache_file)

    # Test empty cache
    assert load_update_cache() == {}

    # Test save and load
    test_data = {"last_check_date": "2025-10-22", "last_check_failed": False}
    save_update_cache(test_data)
    assert load_update_cache() == test_data

    # Test update
    test_data["last_check_failed"] = True
    save_update_cache(test_data)
    cached = load_update_cache()
    assert cached["last_check_failed"] is True


def test_should_check_update(tmp_path: Path, monkeypatch) -> None:
    """Test update check frequency."""
    cache_dir = tmp_path / ".cache" / "claude-worktree"
    cache_file = cache_dir / "update_check.json"

    monkeypatch.setattr("claude_worktree.update.CACHE_DIR", cache_dir)
    monkeypatch.setattr("claude_worktree.update.UPDATE_CHECK_FILE", cache_file)

    # Should check when no cache exists
    assert should_check_update() is True

    # Mark as checked today
    mark_update_checked(failed=False)

    # Should not check again today
    assert should_check_update() is False


def test_mark_update_checked(tmp_path: Path, monkeypatch) -> None:
    """Test marking update as checked."""
    cache_dir = tmp_path / ".cache" / "claude-worktree"
    cache_file = cache_dir / "update_check.json"

    monkeypatch.setattr("claude_worktree.update.CACHE_DIR", cache_dir)
    monkeypatch.setattr("claude_worktree.update.UPDATE_CHECK_FILE", cache_file)

    # Mark as checked with success
    mark_update_checked(failed=False)
    cache = load_update_cache()
    assert cache["last_check_date"] == str(date.today())
    assert cache["last_check_failed"] is False

    # Mark as checked with failure
    mark_update_checked(failed=True)
    cache = load_update_cache()
    assert cache["last_check_failed"] is True


def test_detect_installer() -> None:
    """Test installer detection."""
    # Just verify it returns a valid installer type
    installer = detect_installer()
    assert installer in ("pipx", "uv-tool", "uv-pip", "pip", "source", None)


@patch("claude_worktree.update.httpx.get")
def test_get_latest_version_success(mock_get) -> None:
    """Test fetching latest version from PyPI."""
    from claude_worktree.update import get_latest_version

    # Mock successful response
    mock_response = Mock()
    mock_response.json.return_value = {"info": {"version": "0.5.0"}}
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    version = get_latest_version()
    assert version == "0.5.0"


@patch("claude_worktree.update.httpx.get")
def test_get_latest_version_failure(mock_get) -> None:
    """Test handling of network failure."""
    from claude_worktree.update import get_latest_version

    # Mock network failure
    mock_get.side_effect = Exception("Network error")

    version = get_latest_version()
    assert version is None


@patch("claude_worktree.update.httpx.get")
def test_check_for_updates_no_update_available(mock_get, tmp_path: Path, monkeypatch) -> None:
    """Test check_for_updates when already on latest version."""
    from claude_worktree.update import check_for_updates

    cache_dir = tmp_path / ".cache" / "claude-worktree"
    cache_file = cache_dir / "update_check.json"

    monkeypatch.setattr("claude_worktree.update.CACHE_DIR", cache_dir)
    monkeypatch.setattr("claude_worktree.update.UPDATE_CHECK_FILE", cache_file)

    # Mock PyPI response with current version
    mock_response = Mock()
    mock_response.json.return_value = {"info": {"version": "0.1.4"}}  # Same as current
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    # Should return False (no update available)
    result = check_for_updates(auto=False)
    assert result is False


@patch("claude_worktree.update.httpx.get")
def test_check_for_updates_network_failure(mock_get, tmp_path: Path, monkeypatch) -> None:
    """Test check_for_updates when network fails."""
    from claude_worktree.update import check_for_updates

    cache_dir = tmp_path / ".cache" / "claude-worktree"
    cache_file = cache_dir / "update_check.json"

    monkeypatch.setattr("claude_worktree.update.CACHE_DIR", cache_dir)
    monkeypatch.setattr("claude_worktree.update.UPDATE_CHECK_FILE", cache_file)

    # Mock network failure
    mock_get.side_effect = Exception("Network error")

    # Should return False and not raise
    result = check_for_updates(auto=True)
    assert result is False

    # Should have marked the check as failed
    cache = load_update_cache()
    assert cache["last_check_failed"] is True
