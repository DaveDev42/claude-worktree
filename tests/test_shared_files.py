"""Tests for shared files functionality."""

import os
import platform
from pathlib import Path
from unittest.mock import MagicMock, patch

from claude_worktree.shared_files import (
    _create_windows_junction,
    detect_project_types,
    get_shared_files,
    share_files,
)


def _is_link_or_junction(path: Path) -> bool:
    """Check if path is a symlink or Windows junction point.

    Windows junctions are not reliably detected by is_symlink() or os.path.islink().
    We use ctypes to call GetFileAttributesW and check for the reparse point flag.
    """
    if not path.exists():
        return False

    if platform.system() == "Windows":
        try:
            import ctypes

            # FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
            FILE_ATTRIBUTE_REPARSE_POINT = 0x400

            # Get file attributes using Windows API
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            if attrs == -1:  # INVALID_FILE_ATTRIBUTES
                return False

            # Check if it has the reparse point attribute (junctions have this)
            return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)
        except (ImportError, OSError, AttributeError):
            # Fallback: if we can't check attributes, assume it's OK if it exists
            return path.is_symlink() or os.path.islink(str(path))
    else:
        # On Unix/Linux, use standard check
        return os.path.islink(str(path)) or path.is_symlink()


def test_detect_nodejs_project(tmp_path: Path) -> None:
    """Test detection of Node.js project."""
    # Create package.json
    (tmp_path / "package.json").write_text("{}")

    detected = detect_project_types(tmp_path)
    assert "nodejs" in detected


def test_detect_python_project(tmp_path: Path) -> None:
    """Test detection of Python project."""
    # Create pyproject.toml
    (tmp_path / "pyproject.toml").write_text("")

    detected = detect_project_types(tmp_path)
    assert "python" in detected


def test_detect_rust_project(tmp_path: Path) -> None:
    """Test detection of Rust project."""
    # Create Cargo.toml
    (tmp_path / "Cargo.toml").write_text("")

    detected = detect_project_types(tmp_path)
    assert "rust" in detected


def test_detect_multiple_project_types(tmp_path: Path) -> None:
    """Test detection of multiple project types (polyglot)."""
    # Create both package.json and pyproject.toml
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "pyproject.toml").write_text("")

    detected = detect_project_types(tmp_path)
    assert "nodejs" in detected
    assert "python" in detected


def test_detect_no_project_type(tmp_path: Path) -> None:
    """Test detection when no known project markers exist."""
    detected = detect_project_types(tmp_path)
    assert len(detected) == 0


def test_get_shared_files_nodejs(tmp_path: Path) -> None:
    """Test getting shared files for Node.js project."""
    (tmp_path / "package.json").write_text("{}")

    shared = get_shared_files(tmp_path)
    paths = [f["path"] for f in shared]
    assert "node_modules" in paths


def test_get_shared_files_python(tmp_path: Path) -> None:
    """Test getting shared files for Python project."""
    (tmp_path / "pyproject.toml").write_text("")

    shared = get_shared_files(tmp_path)
    paths = [f["path"] for f in shared]
    # Should include both .venv and venv
    assert ".venv" in paths
    assert "venv" in paths


def test_share_files_symlink(tmp_path: Path) -> None:
    """Test sharing files via symlink or junction."""
    # Setup: create source repo with node_modules
    source_repo = tmp_path / "source"
    source_repo.mkdir()
    (source_repo / "package.json").write_text("{}")
    node_modules = source_repo / "node_modules"
    node_modules.mkdir()
    (node_modules / "test-pkg").mkdir()

    # Create target worktree
    target_worktree = tmp_path / "target"
    target_worktree.mkdir()

    # Share files
    share_files(source_repo, target_worktree)

    # Verify link was created (symlink or junction)
    target_node_modules = target_worktree / "node_modules"
    assert target_node_modules.exists()
    assert _is_link_or_junction(target_node_modules)
    # Verify it points to the right place
    assert (target_node_modules / "test-pkg").exists()


def test_share_files_skip_if_not_exists(tmp_path: Path) -> None:
    """Test that sharing skips files that don't exist in source."""
    # Setup: create source repo WITHOUT node_modules
    source_repo = tmp_path / "source"
    source_repo.mkdir()
    (source_repo / "package.json").write_text("{}")

    # Create target worktree
    target_worktree = tmp_path / "target"
    target_worktree.mkdir()

    # Share files (should skip node_modules since it doesn't exist)
    share_files(source_repo, target_worktree)

    # Verify node_modules was NOT created
    target_node_modules = target_worktree / "node_modules"
    assert not target_node_modules.exists()


def test_share_files_skip_if_already_exists(tmp_path: Path) -> None:
    """Test that sharing skips files that already exist in target."""
    # Setup: create source repo with node_modules
    source_repo = tmp_path / "source"
    source_repo.mkdir()
    (source_repo / "package.json").write_text("{}")
    (source_repo / "node_modules").mkdir()

    # Create target worktree with existing node_modules
    target_worktree = tmp_path / "target"
    target_worktree.mkdir()
    existing_node_modules = target_worktree / "node_modules"
    existing_node_modules.mkdir()
    (existing_node_modules / "existing-file").write_text("test")

    # Share files (should skip node_modules since it already exists)
    share_files(source_repo, target_worktree)

    # Verify existing node_modules was NOT replaced
    assert existing_node_modules.exists()
    assert not _is_link_or_junction(existing_node_modules)
    assert (existing_node_modules / "existing-file").exists()


def test_share_files_multiple_types(tmp_path: Path) -> None:
    """Test sharing files for polyglot project."""
    # Setup: create source repo with both Node.js and Python
    source_repo = tmp_path / "source"
    source_repo.mkdir()
    (source_repo / "package.json").write_text("{}")
    (source_repo / "pyproject.toml").write_text("")
    (source_repo / "node_modules").mkdir()
    (source_repo / ".venv").mkdir()

    # Create target worktree
    target_worktree = tmp_path / "target"
    target_worktree.mkdir()

    # Share files
    share_files(source_repo, target_worktree)

    # Verify both were linked (symlink or junction)
    assert _is_link_or_junction(target_worktree / "node_modules")
    assert _is_link_or_junction(target_worktree / ".venv")


def test_windows_junction_creation(tmp_path: Path) -> None:
    """Test Windows junction point creation (mocked on non-Windows)."""
    # Setup: create source and target directories
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "test-file.txt").write_text("test content")

    target_dir = tmp_path / "target"

    if platform.system() == "Windows":
        # On Windows, actually test junction creation
        _create_windows_junction(source_dir, target_dir)

        # Verify junction was created
        assert target_dir.exists()
        assert _is_link_or_junction(target_dir)
        assert (target_dir / "test-file.txt").read_text() == "test content"
    else:
        # On non-Windows, test that the function would call subprocess correctly
        with patch("claude_worktree.shared_files.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            _create_windows_junction(source_dir, target_dir)

            # Verify subprocess was called with correct arguments
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "cmd"
            assert call_args[1] == "/c"
            assert call_args[2] == "mklink"
            assert call_args[3] == "/J"


def test_windows_junction_failure_handling(tmp_path: Path) -> None:
    """Test that junction creation failures are properly handled."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    target_dir = tmp_path / "target"

    # Mock subprocess to simulate failure
    with patch("claude_worktree.shared_files.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1, stderr="Access denied or junction creation failed"
        )

        # Should raise OSError
        import pytest

        with pytest.raises(OSError, match="Failed to create junction"):
            _create_windows_junction(source_dir, target_dir)


def test_share_files_windows_fallback(tmp_path: Path) -> None:
    """Test Windows file sharing with fallback from junction to symlink."""
    # Setup: create source repo with node_modules
    source_repo = tmp_path / "source"
    source_repo.mkdir()
    (source_repo / "package.json").write_text("{}")
    node_modules = source_repo / "node_modules"
    node_modules.mkdir()

    # Create target worktree
    target_worktree = tmp_path / "target"
    target_worktree.mkdir()

    # Mock Windows platform
    with patch("claude_worktree.shared_files.IS_WINDOWS", True):
        # Mock junction creation to fail (simulating no privileges)
        with patch("claude_worktree.shared_files._create_windows_junction") as mock_junction:
            mock_junction.side_effect = OSError("Access denied")

            # Share files - should fall back to symlink
            share_files(source_repo, target_worktree)

            # Verify junction was attempted
            mock_junction.assert_called_once()

            # Verify link was created as fallback
            target_node_modules = target_worktree / "node_modules"
            assert target_node_modules.exists()
            assert _is_link_or_junction(target_node_modules)


def test_share_files_with_copy_files_config(tmp_path: Path, monkeypatch) -> None:
    """Test sharing files with copy_files configuration."""
    # Setup: mock config to return copy files
    from claude_worktree import config

    def mock_get_copy_files() -> list[str]:
        return [".env", ".env.local"]

    monkeypatch.setattr(config, "get_copy_files", mock_get_copy_files)

    # Setup: create source repo with .env files
    source_repo = tmp_path / "source"
    source_repo.mkdir()
    (source_repo / "package.json").write_text("{}")
    (source_repo / ".env").write_text("SECRET=value1")
    (source_repo / ".env.local").write_text("SECRET=value2")

    # Create target worktree
    target_worktree = tmp_path / "target"
    target_worktree.mkdir()

    # Share files
    share_files(source_repo, target_worktree)

    # Verify .env files were copied (not symlinked)
    target_env = target_worktree / ".env"
    target_env_local = target_worktree / ".env.local"

    assert target_env.exists()
    assert target_env_local.exists()
    assert not _is_link_or_junction(target_env)
    assert not _is_link_or_junction(target_env_local)

    # Verify contents were copied correctly
    assert target_env.read_text() == "SECRET=value1"
    assert target_env_local.read_text() == "SECRET=value2"


def test_share_files_with_nested_copy_files(tmp_path: Path, monkeypatch) -> None:
    """Test sharing nested files with copy_files configuration."""
    # Setup: mock config to return nested copy files
    from claude_worktree import config

    def mock_get_copy_files() -> list[str]:
        return ["config/local.json"]

    monkeypatch.setattr(config, "get_copy_files", mock_get_copy_files)

    # Setup: create source repo with nested config file
    source_repo = tmp_path / "source"
    source_repo.mkdir()
    (source_repo / "package.json").write_text("{}")
    config_dir = source_repo / "config"
    config_dir.mkdir()
    (config_dir / "local.json").write_text('{"key": "value"}')

    # Create target worktree
    target_worktree = tmp_path / "target"
    target_worktree.mkdir()

    # Share files
    share_files(source_repo, target_worktree)

    # Verify nested config file was copied
    target_config = target_worktree / "config" / "local.json"
    assert target_config.exists()
    assert not _is_link_or_junction(target_config)
    assert target_config.read_text() == '{"key": "value"}'


def test_share_files_copy_files_skip_if_not_exists(tmp_path: Path, monkeypatch) -> None:
    """Test that copy_files skips files that don't exist in source."""
    # Setup: mock config to return copy files
    from claude_worktree import config

    def mock_get_copy_files() -> list[str]:
        return [".env", ".env.local"]

    monkeypatch.setattr(config, "get_copy_files", mock_get_copy_files)

    # Setup: create source repo WITHOUT .env files
    source_repo = tmp_path / "source"
    source_repo.mkdir()
    (source_repo / "package.json").write_text("{}")

    # Create target worktree
    target_worktree = tmp_path / "target"
    target_worktree.mkdir()

    # Share files (should skip .env files since they don't exist)
    share_files(source_repo, target_worktree)

    # Verify .env files were NOT created
    assert not (target_worktree / ".env").exists()
    assert not (target_worktree / ".env.local").exists()


def test_share_files_combined_symlink_and_copy(tmp_path: Path, monkeypatch) -> None:
    """Test sharing files with both symlinks and copies."""
    # Setup: mock config to return copy files
    from claude_worktree import config

    def mock_get_copy_files() -> list[str]:
        return [".env"]

    monkeypatch.setattr(config, "get_copy_files", mock_get_copy_files)

    # Setup: create source repo with both node_modules and .env
    source_repo = tmp_path / "source"
    source_repo.mkdir()
    (source_repo / "package.json").write_text("{}")
    (source_repo / "node_modules").mkdir()
    (source_repo / ".env").write_text("SECRET=value")

    # Create target worktree
    target_worktree = tmp_path / "target"
    target_worktree.mkdir()

    # Share files
    share_files(source_repo, target_worktree)

    # Verify node_modules was symlinked
    target_node_modules = target_worktree / "node_modules"
    assert target_node_modules.exists()
    assert _is_link_or_junction(target_node_modules)

    # Verify .env was copied
    target_env = target_worktree / ".env"
    assert target_env.exists()
    assert not _is_link_or_junction(target_env)
    assert target_env.read_text() == "SECRET=value"
