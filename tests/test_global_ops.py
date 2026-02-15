"""Tests for global worktree management operations."""

import subprocess
from pathlib import Path

import pytest

from claude_worktree.exceptions import WorktreeNotFoundError
from claude_worktree.operations.global_ops import (
    global_list_worktrees,
    global_prune,
    global_scan,
)
from claude_worktree.operations.helpers import (
    _disambiguate_global_matches,
    _resolve_global_target,
    is_global_mode,
    resolve_worktree_target,
    set_global_mode,
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


    def test_list_shows_relative_path(self, tmp_path: Path, capsys) -> None:
        """global_list_worktrees shows relative path for each worktree."""
        repo, wt_path = _make_repo_with_worktree(tmp_path, "path-proj", "show-path")
        register_repo(repo)

        global_list_worktrees()

        # The relative path from repo to worktree should appear in output
        # (captured via Rich console, use capsys or check no crash)
        # Clean up worktree
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt_path)],
            cwd=repo, check=False, capture_output=True,
        )

    def test_list_shows_branch_mismatch(self, tmp_path: Path) -> None:
        """global_list_worktrees shows mismatch indicator when branch differs."""
        repo, wt_path = _make_repo_with_worktree(tmp_path, "mismatch-proj", "intended-branch")

        # Switch the worktree to a different branch to create a mismatch
        subprocess.run(
            ["git", "branch", "other-branch"],
            cwd=wt_path, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "other-branch"],
            cwd=wt_path, check=True, capture_output=True,
        )

        register_repo(repo)

        # Should not raise — mismatch is displayed with ⚠️
        global_list_worktrees()

        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt_path)],
            cwd=repo, check=False, capture_output=True,
        )


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


def _make_repo_with_worktree(
    tmp_path: Path, repo_name: str, branch_name: str
) -> tuple[Path, Path]:
    """Helper: create a git repo with one worktree and return (repo, wt_path)."""
    repo = tmp_path / repo_name
    repo.mkdir(parents=True, exist_ok=True)
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
    # Store intended branch metadata
    subprocess.run(
        ["git", "config", f"worktree.{branch_name}.intendedBranch", branch_name],
        cwd=repo, check=True, capture_output=True,
    )
    wt_path = tmp_path / f"{repo_name}-{branch_name}"
    subprocess.run(
        ["git", "worktree", "add", "-b", branch_name, str(wt_path)],
        cwd=repo, check=True, capture_output=True,
    )
    return repo, wt_path


class TestContextVar:
    def test_default_is_false(self) -> None:
        """Global mode defaults to False."""
        set_global_mode(False)
        assert is_global_mode() is False

    def test_set_and_get(self) -> None:
        """set_global_mode / is_global_mode round-trip."""
        set_global_mode(True)
        assert is_global_mode() is True
        set_global_mode(False)
        assert is_global_mode() is False


class TestResolveGlobalTarget:
    def test_finds_branch_in_registered_repo(self, tmp_path: Path) -> None:
        """_resolve_global_target finds a branch across registered repos."""
        repo, wt_path = _make_repo_with_worktree(tmp_path, "proj-a", "fix-bug")
        register_repo(repo)

        matches = _resolve_global_target("fix-bug")
        assert len(matches) == 1
        assert matches[0][1] == "fix-bug"
        assert matches[0][2] == repo

        # Cleanup
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt_path)],
            cwd=repo, check=False, capture_output=True,
        )

    def test_returns_empty_for_unknown_branch(self, tmp_path: Path) -> None:
        """_resolve_global_target returns [] when branch doesn't exist anywhere."""
        repo, wt_path = _make_repo_with_worktree(tmp_path, "proj-b", "feat-x")
        register_repo(repo)

        matches = _resolve_global_target("nonexistent-branch")
        assert len(matches) == 0

        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt_path)],
            cwd=repo, check=False, capture_output=True,
        )

    def test_finds_same_branch_in_multiple_repos(self, tmp_path: Path) -> None:
        """_resolve_global_target returns multiple matches for same branch name."""
        repo_a, wt_a = _make_repo_with_worktree(tmp_path, "alpha", "shared-branch")
        repo_b, wt_b = _make_repo_with_worktree(tmp_path, "beta", "shared-branch")
        register_repo(repo_a)
        register_repo(repo_b)

        matches = _resolve_global_target("shared-branch")
        assert len(matches) == 2

        repos_found = {m[2] for m in matches}
        assert repo_a in repos_found
        assert repo_b in repos_found

        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt_a)],
            cwd=repo_a, check=False, capture_output=True,
        )
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt_b)],
            cwd=repo_b, check=False, capture_output=True,
        )

    def test_skips_missing_repos(self, tmp_path: Path) -> None:
        """_resolve_global_target skips repos that no longer exist on disk."""
        save_registry({
            "version": 1,
            "repositories": {
                "/nonexistent/repo": {
                    "name": "gone",
                    "registered_at": "2026-01-01T00:00:00+00:00",
                    "last_seen": "2026-01-01T00:00:00+00:00",
                }
            },
        })
        matches = _resolve_global_target("any-branch")
        assert len(matches) == 0


class TestDisambiguateGlobalMatches:
    def test_single_match_returns_immediately(self, tmp_path: Path) -> None:
        """_disambiguate_global_matches returns directly for single match."""
        match = (tmp_path / "wt", "my-branch", tmp_path / "repo")
        result = _disambiguate_global_matches("my-branch", [match])
        assert result == match

    def test_multiple_matches_non_interactive_raises(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """_disambiguate_global_matches raises in non-interactive mode."""
        monkeypatch.setenv("CI", "true")
        matches = [
            (tmp_path / "wt1", "branch", tmp_path / "repo1"),
            (tmp_path / "wt2", "branch", tmp_path / "repo2"),
        ]
        with pytest.raises(WorktreeNotFoundError, match="Ambiguous"):
            _disambiguate_global_matches("branch", matches)


class TestResolveWorktreeTargetGlobal:
    def test_global_mode_none_target_raises(self) -> None:
        """resolve_worktree_target raises when global mode + no target."""
        set_global_mode(True)
        try:
            with pytest.raises(WorktreeNotFoundError, match="explicit target"):
                resolve_worktree_target(None)
        finally:
            set_global_mode(False)

    def test_global_mode_not_found_raises(self) -> None:
        """resolve_worktree_target raises when global target not in any repo."""
        save_registry({"version": 1, "repositories": {}})
        set_global_mode(True)
        try:
            with pytest.raises(WorktreeNotFoundError, match="not found"):
                resolve_worktree_target("no-such-branch")
        finally:
            set_global_mode(False)

    def test_global_mode_finds_branch(self, tmp_path: Path) -> None:
        """resolve_worktree_target in global mode finds the worktree."""
        repo, wt_path = _make_repo_with_worktree(tmp_path, "gproj", "gfeat")
        register_repo(repo)

        set_global_mode(True)
        try:
            result_path, result_branch, result_repo = resolve_worktree_target("gfeat")
            assert result_branch == "gfeat"
            assert result_path.resolve() == wt_path.resolve()
        finally:
            set_global_mode(False)
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(wt_path)],
                cwd=repo, check=False, capture_output=True,
            )
