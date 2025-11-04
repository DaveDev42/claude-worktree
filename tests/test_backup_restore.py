"""Tests for backup and restore functionality."""

import json
from pathlib import Path

import pytest

from claude_worktree.exceptions import GitError, WorktreeNotFoundError
from claude_worktree.operations import (
    backup_worktree,
    create_worktree,
    get_backups_dir,
    list_backups,
    restore_worktree,
)


def test_get_backups_dir(tmp_path: Path, monkeypatch) -> None:
    """Test backups directory creation."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    from claude_worktree import config

    monkeypatch.setattr(config, "get_config_path", lambda: config_dir / "config.json")

    backups_dir = get_backups_dir()
    assert backups_dir.exists()
    assert backups_dir.is_dir()
    assert backups_dir == config_dir / "backups"


def test_backup_worktree_current(temp_git_repo: Path, disable_claude, tmp_path: Path) -> None:
    """Test backing up current worktree."""
    # Create a worktree
    create_worktree(branch_name="test-branch", no_cd=True)

    # Create some changes in the worktree
    worktree_path = temp_git_repo.parent / f"{temp_git_repo.name}-test-branch"
    test_file = worktree_path / "test.txt"
    test_file.write_text("test content")

    # Change to worktree directory
    import os

    original_dir = os.getcwd()
    os.chdir(worktree_path)

    try:
        # Backup current worktree
        backup_output = tmp_path / "backups"
        backup_worktree(output=backup_output)

        # Verify backup was created
        assert backup_output.exists()
        branch_backups = list((backup_output / "test-branch").iterdir())
        assert len(branch_backups) == 1

        backup_dir = branch_backups[0]
        assert (backup_dir / "bundle.git").exists()
        assert (backup_dir / "metadata.json").exists()

        # Verify metadata
        with open(backup_dir / "metadata.json") as f:
            metadata = json.load(f)
        assert metadata["branch"] == "test-branch"
        assert metadata["base_branch"] == "main"
        assert "backed_up_at" in metadata

    finally:
        os.chdir(original_dir)


def test_backup_worktree_specific_branch(
    temp_git_repo: Path, disable_claude, tmp_path: Path
) -> None:
    """Test backing up a specific worktree by branch name."""
    # Create a worktree
    create_worktree(branch_name="feature-x", no_cd=True)

    # Backup specific branch
    backup_output = tmp_path / "backups"
    backup_worktree(branch="feature-x", output=backup_output)

    # Verify backup was created
    assert (backup_output / "feature-x").exists()
    branch_backups = list((backup_output / "feature-x").iterdir())
    assert len(branch_backups) == 1


def test_backup_worktree_all(temp_git_repo: Path, disable_claude, tmp_path: Path) -> None:
    """Test backing up all worktrees."""
    # Create multiple worktrees
    create_worktree(branch_name="feature-1", no_cd=True)
    create_worktree(branch_name="feature-2", no_cd=True)

    # Backup all worktrees
    backup_output = tmp_path / "backups"
    backup_worktree(all_worktrees=True, output=backup_output)

    # Verify both backups were created
    assert (backup_output / "feature-1").exists()
    assert (backup_output / "feature-2").exists()
    assert len(list((backup_output / "feature-1").iterdir())) == 1
    assert len(list((backup_output / "feature-2").iterdir())) == 1


def test_backup_worktree_with_uncommitted_changes(
    temp_git_repo: Path, disable_claude, tmp_path: Path
) -> None:
    """Test backup includes uncommitted changes."""
    # Create a worktree
    create_worktree(branch_name="test-branch", no_cd=True)

    # Create uncommitted changes
    worktree_path = temp_git_repo.parent / f"{temp_git_repo.name}-test-branch"
    test_file = worktree_path / "uncommitted.txt"
    test_file.write_text("uncommitted content")

    # Backup the worktree
    backup_output = tmp_path / "backups"
    backup_worktree(branch="test-branch", output=backup_output)

    # Verify stash file was created
    backup_dir = list((backup_output / "test-branch").iterdir())[0]
    assert (backup_dir / "stash.patch").exists()

    # Verify metadata indicates uncommitted changes
    with open(backup_dir / "metadata.json") as f:
        metadata = json.load(f)
    assert metadata["has_uncommitted_changes"] is True
    assert metadata["stash_file"] is not None


def test_backup_worktree_nonexistent_branch(
    temp_git_repo: Path, disable_claude, tmp_path: Path
) -> None:
    """Test backup fails for nonexistent branch."""
    with pytest.raises(WorktreeNotFoundError):
        backup_worktree(branch="nonexistent", output=tmp_path)


def test_list_backups_empty(tmp_path: Path, monkeypatch, capsys) -> None:
    """Test listing backups when none exist."""
    from claude_worktree import config

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    monkeypatch.setattr(config, "get_config_path", lambda: config_dir / "config.json")

    list_backups()

    captured = capsys.readouterr()
    assert "No backups found" in captured.out


def test_list_backups(
    temp_git_repo: Path, disable_claude, tmp_path: Path, capsys, monkeypatch
) -> None:
    """Test listing backups."""
    from claude_worktree.operations import backup_ops

    # Create and backup a worktree
    create_worktree(branch_name="test-branch", no_cd=True)
    backup_output = tmp_path / "backups"
    backup_worktree(branch="test-branch", output=backup_output)

    # Override get_backups_dir to use our test backup location
    monkeypatch.setattr(backup_ops, "get_backups_dir", lambda: backup_output)

    list_backups()

    captured = capsys.readouterr()
    assert "test-branch" in captured.out
    assert "Available Backups" in captured.out


def test_list_backups_filter_by_branch(
    temp_git_repo: Path, disable_claude, tmp_path: Path, capsys, monkeypatch
) -> None:
    """Test listing backups filtered by branch."""
    # Create and backup multiple worktrees
    create_worktree(branch_name="feature-1", no_cd=True)
    create_worktree(branch_name="feature-2", no_cd=True)

    backup_output = tmp_path / "backups"
    backup_worktree(branch="feature-1", output=backup_output)
    backup_worktree(branch="feature-2", output=backup_output)

    # Clear capsys buffer before the test
    capsys.readouterr()

    # List backups for specific branch
    from claude_worktree.operations import backup_ops

    monkeypatch.setattr(backup_ops, "get_backups_dir", lambda: backup_output)

    list_backups(branch="feature-1")

    captured = capsys.readouterr()
    assert "feature-1" in captured.out
    assert "feature-2" not in captured.out


def test_restore_worktree(temp_git_repo: Path, disable_claude, tmp_path: Path, monkeypatch) -> None:
    """Test restoring a worktree from backup."""
    # Create and backup a worktree
    create_worktree(branch_name="test-branch", no_cd=True)
    worktree_path = temp_git_repo.parent / f"{temp_git_repo.name}-test-branch"

    # Add some content to the worktree
    test_file = worktree_path / "test.txt"
    test_file.write_text("test content")

    # Commit the change
    import subprocess

    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True)
    subprocess.run(["git", "commit", "-m", "Add test file"], cwd=worktree_path, check=True)

    # Backup the worktree
    backup_output = tmp_path / "backups"
    backup_worktree(branch="test-branch", output=backup_output)

    # Delete the worktree
    import shutil

    shutil.rmtree(worktree_path)

    # Restore the worktree
    from claude_worktree.operations import backup_ops

    monkeypatch.setattr(backup_ops, "get_backups_dir", lambda: backup_output)

    restored_path = temp_git_repo.parent / f"{temp_git_repo.name}-test-branch-restored"
    restore_worktree(branch="test-branch", path=restored_path)

    # Verify worktree was restored
    assert restored_path.exists()
    assert (restored_path / "test.txt").exists()
    assert (restored_path / "test.txt").read_text() == "test content"


def test_restore_worktree_with_uncommitted_changes(
    temp_git_repo: Path, disable_claude, tmp_path: Path, monkeypatch
) -> None:
    """Test restoring a worktree with uncommitted changes."""
    # Create a worktree
    create_worktree(branch_name="test-branch", no_cd=True)
    worktree_path = temp_git_repo.parent / f"{temp_git_repo.name}-test-branch"

    # Add committed content
    test_file = worktree_path / "committed.txt"
    test_file.write_text("committed content")

    import subprocess

    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True)
    subprocess.run(["git", "commit", "-m", "Add committed file"], cwd=worktree_path, check=True)

    # Modify committed file (this will be tracked by git diff)
    test_file.write_text("modified committed content")

    # Backup the worktree (with uncommitted changes)
    backup_output = tmp_path / "backups"
    backup_worktree(branch="test-branch", output=backup_output)

    # Verify backup has stash file and it's not empty
    backup_dir = list((backup_output / "test-branch").iterdir())[0]
    assert (backup_dir / "stash.patch").exists()
    patch_content = (backup_dir / "stash.patch").read_text()
    assert len(patch_content) > 0  # Patch should contain diff of modified file
    assert "committed.txt" in patch_content

    # Delete the worktree
    import shutil

    shutil.rmtree(worktree_path)

    # Restore the worktree
    from claude_worktree.operations import backup_ops

    monkeypatch.setattr(backup_ops, "get_backups_dir", lambda: backup_output)

    restored_path = temp_git_repo.parent / f"{temp_git_repo.name}-test-branch-restored"
    restore_worktree(branch="test-branch", path=restored_path)

    # Verify committed file was restored
    assert (restored_path / "committed.txt").exists()
    # File should have modified content after patch is applied
    # Strip whitespace to handle trailing newline differences (Windows git apply --whitespace=fix)
    content = (restored_path / "committed.txt").read_text().strip()
    assert content == "modified committed content"


def test_restore_worktree_latest_backup(
    temp_git_repo: Path, disable_claude, tmp_path: Path, monkeypatch
) -> None:
    """Test restoring from latest backup when multiple exist."""
    # Create a worktree
    create_worktree(branch_name="test-branch", no_cd=True)
    worktree_path = temp_git_repo.parent / f"{temp_git_repo.name}-test-branch"

    # Create first backup
    backup_output = tmp_path / "backups"

    test_file = worktree_path / "version1.txt"
    test_file.write_text("version 1")
    import subprocess

    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True)
    subprocess.run(["git", "commit", "-m", "Version 1"], cwd=worktree_path, check=True)

    backup_worktree(branch="test-branch", output=backup_output)

    # Wait a moment to ensure different timestamp
    import time

    time.sleep(1)

    # Create second backup
    test_file.write_text("version 2")
    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True)
    subprocess.run(["git", "commit", "-m", "Version 2"], cwd=worktree_path, check=True)

    backup_worktree(branch="test-branch", output=backup_output)

    # Verify two backups exist
    backups = list((backup_output / "test-branch").iterdir())
    assert len(backups) == 2

    # Delete the worktree
    import shutil

    shutil.rmtree(worktree_path)

    # Restore without specifying backup_id (should use latest)
    from claude_worktree.operations import backup_ops

    monkeypatch.setattr(backup_ops, "get_backups_dir", lambda: backup_output)

    restored_path = temp_git_repo.parent / f"{temp_git_repo.name}-test-branch-restored"
    restore_worktree(branch="test-branch", path=restored_path)

    # Verify latest version was restored
    assert (restored_path / "version1.txt").exists()
    assert (restored_path / "version1.txt").read_text() == "version 2"


def test_restore_worktree_specific_backup(
    temp_git_repo: Path, disable_claude, tmp_path: Path, monkeypatch
) -> None:
    """Test restoring from a specific backup by ID."""
    # Create a worktree and two backups
    create_worktree(branch_name="test-branch", no_cd=True)
    worktree_path = temp_git_repo.parent / f"{temp_git_repo.name}-test-branch"

    backup_output = tmp_path / "backups"

    # First backup
    test_file = worktree_path / "version.txt"
    test_file.write_text("version 1")
    import subprocess

    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True)
    subprocess.run(["git", "commit", "-m", "Version 1"], cwd=worktree_path, check=True)
    backup_worktree(branch="test-branch", output=backup_output)

    # Get first backup ID
    backups = sorted((backup_output / "test-branch").iterdir())
    first_backup_id = backups[0].name

    # Wait and create second backup
    import time

    time.sleep(1)

    test_file.write_text("version 2")
    subprocess.run(["git", "add", "."], cwd=worktree_path, check=True)
    subprocess.run(["git", "commit", "-m", "Version 2"], cwd=worktree_path, check=True)
    backup_worktree(branch="test-branch", output=backup_output)

    # Delete the worktree
    import shutil

    shutil.rmtree(worktree_path)

    # Restore from first backup specifically
    from claude_worktree.operations import backup_ops

    monkeypatch.setattr(backup_ops, "get_backups_dir", lambda: backup_output)

    restored_path = temp_git_repo.parent / f"{temp_git_repo.name}-test-branch-restored"
    restore_worktree(branch="test-branch", backup_id=first_backup_id, path=restored_path)

    # Verify first version was restored
    assert (restored_path / "version.txt").exists()
    assert (restored_path / "version.txt").read_text() == "version 1"


def test_restore_worktree_nonexistent_backup(
    temp_git_repo: Path, tmp_path: Path, monkeypatch
) -> None:
    """Test restore fails for nonexistent backup."""
    from claude_worktree.operations import backup_ops

    monkeypatch.setattr(backup_ops, "get_backups_dir", lambda: tmp_path / "backups")

    with pytest.raises(GitError, match="No backups found"):
        restore_worktree(branch="nonexistent")


def test_restore_worktree_existing_path(
    temp_git_repo: Path, disable_claude, tmp_path: Path, monkeypatch
) -> None:
    """Test restore fails when target path already exists."""
    # Create and backup a worktree
    create_worktree(branch_name="test-branch", no_cd=True)
    worktree_path = temp_git_repo.parent / f"{temp_git_repo.name}-test-branch"

    backup_output = tmp_path / "backups"
    backup_worktree(branch="test-branch", output=backup_output)

    # Try to restore to existing path
    from claude_worktree.operations import backup_ops

    monkeypatch.setattr(backup_ops, "get_backups_dir", lambda: backup_output)

    with pytest.raises(GitError, match="already exists"):
        restore_worktree(branch="test-branch", path=worktree_path)
