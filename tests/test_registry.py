"""Tests for the global repository registry."""

import json
from pathlib import Path

from claude_worktree.registry import (
    get_all_registered_repos,
    get_registry_path,
    load_registry,
    prune_registry,
    register_repo,
    save_registry,
    scan_for_repos,
    update_last_seen,
)


class TestRegistryPath:
    def test_registry_path_under_config_dir(self, tmp_path: Path, monkeypatch) -> None:
        """Registry file should be under ~/.config/claude-worktree/."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        path = get_registry_path()
        assert path == tmp_path / ".config" / "claude-worktree" / "registry.json"


class TestLoadRegistry:
    def test_load_empty_registry(self) -> None:
        """Loading when no file exists returns empty registry."""
        registry = load_registry()
        assert registry["version"] == 1
        assert registry["repositories"] == {}

    def test_load_existing_registry(self, tmp_path: Path) -> None:
        """Loading an existing registry file returns its contents."""
        registry_path = get_registry_path()
        registry_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": 1,
            "repositories": {
                "/some/repo": {
                    "name": "repo",
                    "registered_at": "2026-01-01T00:00:00+00:00",
                    "last_seen": "2026-01-01T00:00:00+00:00",
                }
            },
        }
        registry_path.write_text(json.dumps(data))

        registry = load_registry()
        assert "/some/repo" in registry["repositories"]
        assert registry["repositories"]["/some/repo"]["name"] == "repo"

    def test_load_corrupt_registry(self, tmp_path: Path) -> None:
        """Loading a corrupt file returns empty registry."""
        registry_path = get_registry_path()
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text("not valid json{{{")

        registry = load_registry()
        assert registry["version"] == 1
        assert registry["repositories"] == {}


class TestSaveRegistry:
    def test_save_creates_file(self) -> None:
        """save_registry creates the file and parent directories."""
        data = {"version": 1, "repositories": {"test": {"name": "test"}}}
        save_registry(data)

        registry_path = get_registry_path()
        assert registry_path.exists()

        loaded = json.loads(registry_path.read_text())
        assert loaded == data


class TestRegisterRepo:
    def test_register_new_repo(self, tmp_path: Path) -> None:
        """Registering a new repo adds it to the registry."""
        repo_path = tmp_path / "my-project"
        repo_path.mkdir()

        register_repo(repo_path)

        registry = load_registry()
        key = str(repo_path.resolve())
        assert key in registry["repositories"]
        assert registry["repositories"][key]["name"] == "my-project"
        assert "registered_at" in registry["repositories"][key]
        assert "last_seen" in registry["repositories"][key]

    def test_register_existing_repo_updates_last_seen(self, tmp_path: Path) -> None:
        """Re-registering updates the last_seen timestamp."""
        repo_path = tmp_path / "my-project"
        repo_path.mkdir()

        register_repo(repo_path)
        registry1 = load_registry()
        key = str(repo_path.resolve())
        first_seen = registry1["repositories"][key]["last_seen"]

        # Register again
        register_repo(repo_path)
        registry2 = load_registry()
        second_seen = registry2["repositories"][key]["last_seen"]

        # last_seen should be updated (or equal if very fast)
        assert second_seen >= first_seen
        # registered_at should remain the same
        assert (
            registry2["repositories"][key]["registered_at"]
            == registry1["repositories"][key]["registered_at"]
        )


class TestUpdateLastSeen:
    def test_update_registered_repo(self, tmp_path: Path) -> None:
        """update_last_seen updates timestamp for registered repos."""
        repo_path = tmp_path / "my-project"
        repo_path.mkdir()

        register_repo(repo_path)
        registry1 = load_registry()
        key = str(repo_path.resolve())
        first_seen = registry1["repositories"][key]["last_seen"]

        update_last_seen(repo_path)
        registry2 = load_registry()
        second_seen = registry2["repositories"][key]["last_seen"]

        assert second_seen >= first_seen

    def test_update_unregistered_repo_is_noop(self, tmp_path: Path) -> None:
        """update_last_seen is a no-op for unregistered repos."""
        repo_path = tmp_path / "unknown-project"
        repo_path.mkdir()

        update_last_seen(repo_path)

        registry = load_registry()
        assert str(repo_path.resolve()) not in registry["repositories"]


class TestPruneRegistry:
    def test_prune_removes_missing_repos(self, tmp_path: Path) -> None:
        """prune_registry removes entries for non-existent paths."""
        # Register a repo that doesn't exist
        data = {
            "version": 1,
            "repositories": {
                "/nonexistent/repo": {
                    "name": "repo",
                    "registered_at": "2026-01-01T00:00:00+00:00",
                    "last_seen": "2026-01-01T00:00:00+00:00",
                }
            },
        }
        save_registry(data)

        removed = prune_registry()
        assert "/nonexistent/repo" == removed[0]

        registry = load_registry()
        assert len(registry["repositories"]) == 0

    def test_prune_keeps_existing_repos(self, tmp_path: Path) -> None:
        """prune_registry keeps entries for existing git repos."""
        repo_path = tmp_path / "real-repo"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()

        data = {
            "version": 1,
            "repositories": {
                str(repo_path): {
                    "name": "real-repo",
                    "registered_at": "2026-01-01T00:00:00+00:00",
                    "last_seen": "2026-01-01T00:00:00+00:00",
                }
            },
        }
        save_registry(data)

        removed = prune_registry()
        assert removed == []

        registry = load_registry()
        assert str(repo_path) in registry["repositories"]

    def test_prune_removes_non_git_dirs(self, tmp_path: Path) -> None:
        """prune_registry removes dirs that exist but aren't git repos."""
        dir_path = tmp_path / "not-a-repo"
        dir_path.mkdir()
        # No .git directory

        data = {
            "version": 1,
            "repositories": {
                str(dir_path): {
                    "name": "not-a-repo",
                    "registered_at": "2026-01-01T00:00:00+00:00",
                    "last_seen": "2026-01-01T00:00:00+00:00",
                }
            },
        }
        save_registry(data)

        removed = prune_registry()
        assert str(dir_path) in removed

    def test_prune_empty_registry(self) -> None:
        """prune_registry on empty registry returns empty list."""
        removed = prune_registry()
        assert removed == []


class TestGetAllRegisteredRepos:
    def test_returns_all_repos(self, tmp_path: Path) -> None:
        """get_all_registered_repos returns all entries."""
        repo1 = tmp_path / "project-a"
        repo1.mkdir()
        repo2 = tmp_path / "project-b"
        repo2.mkdir()

        register_repo(repo1)
        register_repo(repo2)

        repos = get_all_registered_repos()
        names = [name for name, _ in repos]
        assert "project-a" in names
        assert "project-b" in names

    def test_returns_empty_for_empty_registry(self) -> None:
        """get_all_registered_repos returns empty list when no repos."""
        repos = get_all_registered_repos()
        assert repos == []


class TestScanForRepos:
    def test_scan_finds_repos_with_worktrees(self, tmp_path: Path) -> None:
        """scan_for_repos finds git repos that have worktrees.

        This test creates a real git repo with a worktree to verify
        the scan logic works end-to-end.
        """
        import subprocess

        # Create a git repo
        repo = tmp_path / "scan_target" / "my-project"
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

        # Create a worktree
        wt_path = tmp_path / "scan_target" / "my-project-feature"
        subprocess.run(
            ["git", "worktree", "add", "-b", "feature", str(wt_path)],
            cwd=repo, check=True, capture_output=True,
        )

        found = scan_for_repos(base_dir=tmp_path / "scan_target", max_depth=3)
        assert any(p.name == "my-project" for p in found)

        # Clean up worktree
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt_path)],
            cwd=repo, check=False, capture_output=True,
        )

    def test_scan_skips_repos_without_worktrees(self, tmp_path: Path) -> None:
        """scan_for_repos skips repos without extra worktrees."""
        import subprocess

        repo = tmp_path / "scan_target" / "plain-repo"
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

        found = scan_for_repos(base_dir=tmp_path / "scan_target", max_depth=3)
        assert not any(p.name == "plain-repo" for p in found)

    def test_scan_empty_directory(self, tmp_path: Path) -> None:
        """scan_for_repos returns empty for directory with no repos."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        found = scan_for_repos(base_dir=empty_dir)
        assert found == []

    def test_scan_respects_max_depth(self, tmp_path: Path) -> None:
        """scan_for_repos doesn't go deeper than max_depth."""
        # Create deeply nested directory
        deep = tmp_path / "a" / "b" / "c" / "d" / "e" / "f"
        deep.mkdir(parents=True)

        # This should not scan that deep with depth=2
        found = scan_for_repos(base_dir=tmp_path, max_depth=2)
        assert found == []
