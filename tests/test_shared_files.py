"""Tests for shared files functionality."""

from pathlib import Path

from claude_worktree.shared_files import (
    detect_project_types,
    get_shared_files,
    share_files,
)


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
    """Test sharing files via symlink."""
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

    # Verify symlink was created
    target_node_modules = target_worktree / "node_modules"
    assert target_node_modules.exists()
    assert target_node_modules.is_symlink()
    assert target_node_modules.resolve() == node_modules.resolve()


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
    assert not existing_node_modules.is_symlink()
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

    # Verify both were symlinked
    assert (target_worktree / "node_modules").is_symlink()
    assert (target_worktree / ".venv").is_symlink()
