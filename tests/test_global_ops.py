"""Tests for global worktree management operations."""

import subprocess
from pathlib import Path

from claude_worktree.operations.global_ops import (
    global_list_worktrees,
    global_prune,
    global_scan,
)
from claude_worktree.registry import (
    load_registry,
    register_repo,
    save_registry,
)


class TestGlobalListWorktrees:
    def test_list_empty_registry(self, capsys) -> None:
        """global_list_worktrees shows message when no repos registered."""
        global_list_worktrees()
        # Should not raise

    def test_list_with_registered_repo(self, tmp_path: Path, capsys) -> None:
        """global_list_worktrees shows worktrees for registered repos."""
        # Create a real git repo with a worktree
        repo = tmp_path / "my-project"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "commit.gpgsign", "false"],
            cwd=repo, check=True, capture_output=True,
        )
        (repo / "README.md").write_text("test")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=repo, check=True, capture_output=True,
        )

        # Create a worktree
        wt_path = tmp_path / "my-project-feature"
        subprocess.run(
            ["git", "worktree", "add", "-b", "feature", str(wt_path)],
            cwd=repo, check=True, capture_output=True,
        )

        # Register the repo
        register_repo(repo)

        # Run global list
        global_list_worktrees()
        # Should not raise

        # Clean up worktree
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt_path)],
            cwd=repo, check=False, capture_output=True,
        )

    def test_list_with_missing_repo(self, tmp_path: Path) -> None:
        """global_list_worktrees handles repos that no longer exist."""
        data = {
            "version": 1,
            "repositories": {
                "/nonexistent/path": {
                    "name": "gone-project",
                    "registered_at": "2026-01-01T00:00:00+00:00",
                    "last_seen": "2026-01-01T00:00:00+00:00",
                }
            },
        }
        save_registry(data)

        # Should not raise
        global_list_worktrees()

    def test_list_with_repo_no_feature_worktrees(self, tmp_path: Path) -> None:
        """global_list_worktrees skips repos with no feature worktrees."""
        repo = tmp_path / "no-features"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "commit.gpgsign", "false"],
            cwd=repo, check=True, capture_output=True,
        )
        (repo / "README.md").write_text("test")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=repo, check=True, capture_output=True,
        )

        register_repo(repo)

        # Should not raise, and should report no active worktrees
        global_list_worktrees()


class TestGlobalScan:
    def test_scan_and_register(self, tmp_path: Path) -> None:
        """global_scan discovers and registers repos."""
        # Create a repo with worktrees
        repo = tmp_path / "scan_area" / "project"
        repo.mkdir(parents=True)
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "commit.gpgsign", "false"],
            cwd=repo, check=True, capture_output=True,
        )
        (repo / "README.md").write_text("test")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=repo, check=True, capture_output=True,
        )

        wt_path = tmp_path / "scan_area" / "project-feat"
        subprocess.run(
            ["git", "worktree", "add", "-b", "feat", str(wt_path)],
            cwd=repo, check=True, capture_output=True,
        )

        global_scan(base_dir=tmp_path / "scan_area")

        registry = load_registry()
        assert any("project" in path for path in registry["repositories"])

        # Clean up
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt_path)],
            cwd=repo, check=False, capture_output=True,
        )

    def test_scan_empty_dir(self, tmp_path: Path) -> None:
        """global_scan on empty directory finds nothing."""
        empty = tmp_path / "empty_scan"
        empty.mkdir()

        global_scan(base_dir=empty)

        registry = load_registry()
        assert registry["repositories"] == {}


class TestGlobalPrune:
    def test_prune_removes_stale(self, tmp_path: Path) -> None:
        """global_prune removes entries for non-existent repos."""
        data = {
            "version": 1,
            "repositories": {
                "/nonexistent/old-project": {
                    "name": "old-project",
                    "registered_at": "2026-01-01T00:00:00+00:00",
                    "last_seen": "2026-01-01T00:00:00+00:00",
                }
            },
        }
        save_registry(data)

        global_prune()

        registry = load_registry()
        assert len(registry["repositories"]) == 0

    def test_prune_clean_registry(self) -> None:
        """global_prune on clean registry reports nothing to prune."""
        # Empty registry
        global_prune()
        # Should not raise
