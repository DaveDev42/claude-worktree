"""Tests for export/import configuration functionality."""

import json
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from claude_worktree.config import load_config, save_config
from claude_worktree.exceptions import GitError
from claude_worktree.git_utils import get_config
from claude_worktree.operations import create_worktree, export_config, import_config


def test_export_config_basic(temp_git_repo: Path, disable_claude, tmp_path: Path) -> None:
    """Test basic configuration export."""
    # Create a couple of worktrees
    create_worktree(branch_name="feature1", no_cd=True)
    create_worktree(branch_name="feature2", no_cd=True)

    # Export to a specific file
    output_file = tmp_path / "test-export.json"
    export_config(output_file=output_file)

    # Verify file was created
    assert output_file.exists()

    # Load and verify JSON structure
    with open(output_file) as f:
        data = json.load(f)

    assert data["export_version"] == "1.0"
    assert "exported_at" in data
    assert "repository" in data
    assert "config" in data
    assert "worktrees" in data
    assert len(data["worktrees"]) == 2

    # Verify worktree data
    branches = {wt["branch"] for wt in data["worktrees"]}
    assert "feature1" in branches
    assert "feature2" in branches

    # Verify each worktree has required fields
    for wt in data["worktrees"]:
        assert "branch" in wt
        assert "base_branch" in wt
        assert "base_path" in wt
        assert "path" in wt
        assert "status" in wt


def test_export_config_default_filename(temp_git_repo: Path, disable_claude) -> None:
    """Test export with default timestamped filename."""
    # Export without specifying output file
    export_config(output_file=None)

    # Find the exported file (should be cw-export-TIMESTAMP.json in current directory)
    export_files = list(Path(".").glob("cw-export-*.json"))
    assert len(export_files) == 1

    export_file = export_files[0]
    assert export_file.exists()

    # Verify it's valid JSON
    with open(export_file) as f:
        data = json.load(f)
    assert data["export_version"] == "1.0"

    # Cleanup
    export_file.unlink()


def test_export_config_empty_worktrees(temp_git_repo: Path, tmp_path: Path) -> None:
    """Test export when no worktrees exist."""
    output_file = tmp_path / "empty-export.json"
    export_config(output_file=output_file)

    assert output_file.exists()

    with open(output_file) as f:
        data = json.load(f)

    # Should still have valid structure with empty worktrees list
    assert data["export_version"] == "1.0"
    assert data["worktrees"] == []
    assert "config" in data


def test_export_config_with_custom_config(
    temp_git_repo: Path, disable_claude, tmp_path: Path
) -> None:
    """Test export includes custom configuration values."""
    # Modify config
    config = load_config()
    config["ai_tool"]["command"] = "custom-ai-tool"
    config["git"]["default_base_branch"] = "develop"
    save_config(config)

    # Create worktree
    create_worktree(branch_name="test-branch", no_cd=True)

    # Export
    output_file = tmp_path / "custom-config-export.json"
    export_config(output_file=output_file)

    # Verify exported config
    with open(output_file) as f:
        data = json.load(f)

    assert data["config"]["ai_tool"]["command"] == "custom-ai-tool"
    assert data["config"]["git"]["default_base_branch"] == "develop"


def test_import_config_preview_mode(
    temp_git_repo: Path, disable_claude, tmp_path: Path, capsys
) -> None:
    """Test import in preview mode (default)."""
    # Create and export some worktrees
    create_worktree(branch_name="feature1", no_cd=True)
    create_worktree(branch_name="feature2", no_cd=True)

    export_file = tmp_path / "test-import.json"
    export_config(output_file=export_file)

    # Modify config to make preview show changes
    config = load_config()
    config["ai_tool"]["command"] = "different-tool"
    save_config(config)

    # Import in preview mode (apply=False)
    import_config(import_file=export_file, apply=False)

    # Check output
    captured = capsys.readouterr()
    assert "Preview mode" in captured.out  # Changed from "PREVIEW MODE"
    assert "Import Preview" in captured.out

    # Verify config was NOT changed
    current_config = load_config()
    assert current_config["ai_tool"]["command"] == "different-tool"


def test_import_config_apply_mode(temp_git_repo: Path, disable_claude, tmp_path: Path) -> None:
    """Test import with apply flag."""
    # Create worktrees and export
    create_worktree(branch_name="feature1", no_cd=True)

    export_file = tmp_path / "test-apply.json"
    export_config(output_file=export_file)

    # Load the export data for reference
    with open(export_file) as f:
        export_data = json.load(f)

    original_command = export_data["config"]["ai_tool"]["command"]

    # Modify config
    config = load_config()
    config["ai_tool"]["command"] = "different-tool"
    save_config(config)

    # Import with apply=True
    import_config(import_file=export_file, apply=True)

    # Verify config was restored
    current_config = load_config()
    assert current_config["ai_tool"]["command"] == original_command


def test_import_config_worktree_metadata(
    temp_git_repo: Path, disable_claude, tmp_path: Path, monkeypatch
) -> None:
    """Test import restores worktree metadata."""
    # Create worktree
    create_worktree(branch_name="metadata-test", no_cd=True)

    # Export
    export_file = tmp_path / "metadata-export.json"
    export_config(output_file=export_file)

    # Clear metadata by running git config --unset
    subprocess.run(
        ["git", "config", "--unset", "branch.metadata-test.worktreeBase"],
        cwd=temp_git_repo,
        capture_output=True,
    )

    # Verify metadata is cleared
    base_branch = get_config("branch.metadata-test.worktreeBase", temp_git_repo)
    assert base_branch is None

    # Import with apply
    import_config(import_file=export_file, apply=True)

    # Verify metadata was restored
    base_branch = get_config("branch.metadata-test.worktreeBase", temp_git_repo)
    assert base_branch == "main"


def test_import_config_invalid_json(temp_git_repo: Path, tmp_path: Path) -> None:
    """Test import with invalid JSON file."""
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{ invalid json content")

    with pytest.raises(GitError, match="Failed to read import file"):
        import_config(import_file=invalid_file, apply=False)


def test_import_config_missing_fields(temp_git_repo: Path, tmp_path: Path, capsys) -> None:
    """Test import with incomplete data structure."""
    incomplete_file = tmp_path / "incomplete.json"
    incomplete_data = {
        "export_version": "1.0",
        "exported_at": datetime.now().isoformat(),
        # Missing "config" and "worktrees" fields
    }

    with open(incomplete_file, "w") as f:
        json.dump(incomplete_data, f)

    # Import should handle missing fields gracefully (using .get() with defaults)
    import_config(import_file=incomplete_file, apply=False)

    # Verify it handled gracefully
    captured = capsys.readouterr()
    assert "Import Preview" in captured.out
    assert "Worktrees: 0" in captured.out


def test_import_config_version_check(temp_git_repo: Path, tmp_path: Path) -> None:
    """Test import handles different export versions."""
    future_version_file = tmp_path / "future.json"
    future_data = {
        "export_version": "99.0",  # Future version
        "exported_at": datetime.now().isoformat(),
        "repository": str(temp_git_repo),
        "config": load_config(),
        "worktrees": [],
    }

    with open(future_version_file, "w") as f:
        json.dump(future_data, f)

    # Should handle gracefully (maybe with warning) or accept it
    # Current implementation doesn't validate version, so this should work
    import_config(import_file=future_version_file, apply=False)


def test_export_import_roundtrip(temp_git_repo: Path, disable_claude, tmp_path: Path) -> None:
    """Test full roundtrip: export, modify, import, verify."""
    # Setup: Create worktrees and custom config
    create_worktree(branch_name="roundtrip1", no_cd=True)
    create_worktree(branch_name="roundtrip2", no_cd=True)

    original_config = load_config()
    original_config["ai_tool"]["command"] = "original-tool"
    original_config["git"]["default_base_branch"] = "main"
    save_config(original_config)

    # Export
    export_file = tmp_path / "roundtrip.json"
    export_config(output_file=export_file)

    # Modify config
    modified_config = load_config()
    modified_config["ai_tool"]["command"] = "modified-tool"
    modified_config["git"]["default_base_branch"] = "develop"
    save_config(modified_config)

    # Clear one worktree's metadata
    subprocess.run(
        ["git", "config", "--unset", "branch.roundtrip1.worktreeBase"],
        cwd=temp_git_repo,
        capture_output=True,
    )

    # Import to restore
    import_config(import_file=export_file, apply=True)

    # Verify config was restored
    restored_config = load_config()
    assert restored_config["ai_tool"]["command"] == "original-tool"
    assert restored_config["git"]["default_base_branch"] == "main"

    # Verify worktree metadata was restored
    base_branch = get_config("branch.roundtrip1.worktreeBase", temp_git_repo)
    assert base_branch == "main"


def test_export_config_with_stale_worktree(
    temp_git_repo: Path, disable_claude, tmp_path: Path
) -> None:
    """Test export handles stale worktrees (deleted directories) gracefully."""
    import shutil

    # Create worktree
    worktree_path = create_worktree(branch_name="stale-wt", no_cd=True)

    # Delete the worktree directory manually
    shutil.rmtree(worktree_path)

    # Export should still work
    export_file = tmp_path / "stale-export.json"
    export_config(output_file=export_file)

    assert export_file.exists()

    with open(export_file) as f:
        data = json.load(f)

    # Should include the stale worktree with status "stale"
    stale_wt = next((wt for wt in data["worktrees"] if wt["branch"] == "stale-wt"), None)
    assert stale_wt is not None
    assert stale_wt["status"] == "stale"


def test_import_config_partial_worktrees(
    temp_git_repo: Path, disable_claude, tmp_path: Path, capsys
) -> None:
    """Test import when some worktrees from export don't exist locally."""
    # Create export data with worktrees that don't exist
    export_data = {
        "export_version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "repository": str(temp_git_repo),
        "config": load_config(),
        "worktrees": [
            {
                "branch": "nonexistent-branch",
                "base_branch": "main",
                "base_path": str(temp_git_repo),
                "path": "/tmp/nonexistent-path",
                "status": "clean",
            }
        ],
    }

    export_file = tmp_path / "partial.json"
    with open(export_file, "w") as f:
        json.dump(export_data, f, indent=2)

    # Import should work but skip nonexistent worktrees
    import_config(import_file=export_file, apply=True)

    # Check output for warning or info about skipped worktrees
    _captured = capsys.readouterr()
    # The import should complete without error
    # (implementation may warn about missing worktrees)
