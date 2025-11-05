"""
Platform-independent E2E tests.

These tests verify complete user workflows by running actual CLI commands
and checking real filesystem/git state. They work on all platforms
(Windows, macOS, Linux) without shell-specific dependencies.
"""

import subprocess
from pathlib import Path


def run_cw_command(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    """
    Helper: Run cw command and return result.

    Args:
        args: Command arguments (e.g., ["new", "feature"])
        cwd: Working directory for command execution

    Returns:
        CompletedProcess with stdout, stderr, and returncode
    """
    return subprocess.run(
        ["cw"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestFeatureDevelopmentWorkflow:
    """E2E tests for complete feature development workflows."""

    def test_complete_feature_workflow(self, temp_git_repo: Path, disable_claude) -> None:
        """
        Test complete feature development workflow:
        1. cw new feature-login
        2. Make changes and commit
        3. cw list (verify it shows up)
        4. cw status (check worktree status)
        5. cw merge (merge back to main)
        6. Verify cleanup and changes in main
        """
        # 1. Create new worktree
        result = run_cw_command(["new", "feature-login", "--no-cd"], cwd=temp_git_repo)
        assert result.returncode == 0, f"Failed to create worktree: {result.stderr}"

        worktree_path = temp_git_repo.parent / f"{temp_git_repo.name}-feature-login"
        assert worktree_path.exists(), "Worktree directory was not created"

        # 2. Make changes and commit
        test_file = worktree_path / "login.py"
        test_file.write_text("def login():\n    pass\n")

        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add login function"],
            cwd=worktree_path,
            check=True,
            capture_output=True,
        )

        # 3. List worktrees (verify it shows up)
        result = run_cw_command(["list"], cwd=temp_git_repo)
        assert result.returncode == 0
        assert "feature-login" in result.stdout, "Worktree not shown in list"

        # 4. Check status
        result = run_cw_command(["status"], cwd=worktree_path)
        assert result.returncode == 0
        assert "feature-login" in result.stdout, "Status doesn't show current worktree"

        # 5. Merge back to main (no push by default)
        result = run_cw_command(["merge"], cwd=worktree_path)
        assert result.returncode == 0, f"Merge failed: {result.stderr}"

        # 6. Verify worktree was cleaned up
        assert not worktree_path.exists(), "Worktree directory should be removed after merge"

        # 7. Verify changes are in main
        assert (temp_git_repo / "login.py").exists(), "Changes not merged to main branch"
        assert "def login()" in (temp_git_repo / "login.py").read_text()

    def test_multi_worktree_workflow(self, temp_git_repo: Path, disable_claude) -> None:
        """
        Test managing multiple worktrees simultaneously:
        1. Create 3 different worktrees
        2. List should show all 3
        3. Delete one
        4. Others should still exist
        """
        # 1. Create multiple worktrees
        branches = ["feature-auth", "feature-ui", "bugfix-crash"]
        for branch in branches:
            result = run_cw_command(["new", branch, "--no-cd"], cwd=temp_git_repo)
            assert result.returncode == 0, f"Failed to create {branch}"

        # 2. List should show all 3
        result = run_cw_command(["list"], cwd=temp_git_repo)
        assert result.returncode == 0
        for branch in branches:
            assert branch in result.stdout, f"{branch} not in worktree list"

        # 3. Delete one worktree
        result = run_cw_command(["delete", "feature-auth"], cwd=temp_git_repo)
        assert result.returncode == 0

        auth_path = temp_git_repo.parent / f"{temp_git_repo.name}-feature-auth"
        assert not auth_path.exists(), "Deleted worktree still exists"

        # 4. Others should still exist
        result = run_cw_command(["list"], cwd=temp_git_repo)
        assert "feature-auth" not in result.stdout
        assert "feature-ui" in result.stdout
        assert "bugfix-crash" in result.stdout

    def test_delete_with_keep_branch_flag(self, temp_git_repo: Path, disable_claude) -> None:
        """
        Test deleting worktree while keeping the branch:
        1. Create worktree
        2. Make commit
        3. Delete with --keep-branch
        4. Worktree gone but branch exists
        """
        # 1. Create worktree
        result = run_cw_command(["new", "keep-branch-test", "--no-cd"], cwd=temp_git_repo)
        assert result.returncode == 0

        worktree_path = temp_git_repo.parent / f"{temp_git_repo.name}-keep-branch-test"

        # 2. Make commit
        test_file = worktree_path / "test.txt"
        test_file.write_text("test content")
        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Test commit"],
            cwd=worktree_path,
            check=True,
            capture_output=True,
        )

        # 3. Delete with --keep-branch
        result = run_cw_command(["delete", "keep-branch-test", "--keep-branch"], cwd=temp_git_repo)
        assert result.returncode == 0

        # 4. Verify worktree gone but branch exists
        assert not worktree_path.exists(), "Worktree should be deleted"

        # Check branch still exists
        git_result = subprocess.run(
            ["git", "branch", "--list", "keep-branch-test"],
            cwd=temp_git_repo,
            capture_output=True,
            text=True,
        )
        assert "keep-branch-test" in git_result.stdout, "Branch should still exist"


class TestRebaseConflictWorkflow:
    """E2E tests for handling rebase conflicts."""

    def test_merge_with_conflict_detection(self, temp_git_repo: Path, disable_claude) -> None:
        """
        Test that merge detects conflicts and fails gracefully:
        1. Create worktree
        2. Make conflicting changes in main and worktree
        3. Try to merge (should fail)
        4. Worktree should still exist (not cleaned up on failure)
        """
        # 1. Create worktree
        result = run_cw_command(["new", "conflict-test", "--no-cd"], cwd=temp_git_repo)
        assert result.returncode == 0

        worktree_path = temp_git_repo.parent / f"{temp_git_repo.name}-conflict-test"

        # 2. Make conflicting changes
        # In main repo
        conflict_file = temp_git_repo / "shared.txt"
        conflict_file.write_text("main version\n")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Main change"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        # In worktree (conflicting change)
        worktree_conflict_file = worktree_path / "shared.txt"
        worktree_conflict_file.write_text("worktree version\n")
        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Worktree change"],
            cwd=worktree_path,
            check=True,
            capture_output=True,
        )

        # 3. Try to merge (should fail with conflict)
        result = run_cw_command(["merge"], cwd=worktree_path)
        assert result.returncode != 0, "Merge should fail due to conflict"

        # Check error message mentions conflict
        output = result.stdout + result.stderr
        assert "conflict" in output.lower() or "rebase failed" in output.lower(), (
            "Error message should mention conflict"
        )

        # 4. Worktree should still exist (not cleaned up on failure)
        assert worktree_path.exists(), "Worktree should not be deleted on merge failure"

    def test_dry_run_shows_plan_without_changes(self, temp_git_repo: Path, disable_claude) -> None:
        """
        Test dry-run mode shows what would happen without making changes:
        1. Create worktree with commit
        2. Run merge --dry-run
        3. Should show plan but not actually merge
        4. Worktree should still exist
        """
        # 1. Create worktree with commit
        result = run_cw_command(["new", "dry-run-test", "--no-cd"], cwd=temp_git_repo)
        assert result.returncode == 0

        worktree_path = temp_git_repo.parent / f"{temp_git_repo.name}-dry-run-test"

        test_file = worktree_path / "feature.txt"
        test_file.write_text("feature content\n")
        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add feature"],
            cwd=worktree_path,
            check=True,
            capture_output=True,
        )

        # 2. Run merge --dry-run
        result = run_cw_command(["merge", "--dry-run"], cwd=worktree_path)
        assert result.returncode == 0

        # 3. Should show plan
        assert "DRY RUN" in result.stdout or "dry run" in result.stdout.lower()
        assert "Rebase" in result.stdout or "Merge" in result.stdout

        # 4. Verify nothing was actually changed
        assert worktree_path.exists(), "Worktree should still exist"
        assert not (temp_git_repo / "feature.txt").exists(), "Changes should not be merged"


class TestErrorHandling:
    """E2E tests for error handling and edge cases."""

    def test_create_duplicate_worktree(self, temp_git_repo: Path, disable_claude) -> None:
        """Test error when trying to create duplicate worktree."""
        # Create first worktree
        result = run_cw_command(["new", "duplicate", "--no-cd"], cwd=temp_git_repo)
        assert result.returncode == 0

        # Try to create again with same name
        result = run_cw_command(["new", "duplicate", "--no-cd"], cwd=temp_git_repo)
        assert result.returncode != 0, "Should fail when creating duplicate"

        output = result.stdout + result.stderr
        assert "already exists" in output.lower(), "Should mention branch already exists"

    def test_delete_nonexistent_worktree(self, temp_git_repo: Path) -> None:
        """Test error when trying to delete non-existent worktree."""
        result = run_cw_command(["delete", "nonexistent-branch"], cwd=temp_git_repo)
        assert result.returncode != 0, "Should fail when deleting non-existent worktree"

        output = result.stdout + result.stderr
        assert "not found" in output.lower() or "no worktree" in output.lower(), (
            "Should mention worktree not found"
        )

    def test_invalid_branch_name(self, temp_git_repo: Path, disable_claude) -> None:
        """Test error when using invalid branch name."""
        invalid_names = [
            "feat..ure",  # Double dots
            "feat//test",  # Double slashes
            "feat~test",  # Tilde
            "feat^test",  # Caret
        ]

        for invalid_name in invalid_names:
            result = run_cw_command(["new", invalid_name, "--no-cd"], cwd=temp_git_repo)
            assert result.returncode != 0, f"Should reject invalid name: {invalid_name}"

            output = result.stdout + result.stderr
            assert "invalid" in output.lower() or "error" in output.lower(), (
                f"Should mention invalid name: {invalid_name}"
            )

    def test_merge_from_main_repo_fails(self, temp_git_repo: Path) -> None:
        """Test that merge command fails when run from main repository."""
        result = run_cw_command(["merge"], cwd=temp_git_repo)
        assert result.returncode != 0, "Merge should fail from main repo"

        output = result.stdout + result.stderr
        # Should indicate this needs to be run from a worktree
        assert "worktree" in output.lower() or "error" in output.lower(), (
            "Should indicate worktree required"
        )


class TestConfigWorkflow:
    """E2E tests for configuration management."""

    def test_config_preset_workflow(self, temp_git_repo: Path) -> None:
        """
        Test changing AI tool presets:
        1. Show current config
        2. Change to no-op preset
        3. Verify change
        4. Reset to defaults
        """
        # 1. Show current config
        result = run_cw_command(["config", "show"], cwd=temp_git_repo)
        assert result.returncode == 0
        assert "AI Tool" in result.stdout or "claude" in result.stdout.lower()

        # 2. Change to no-op preset
        result = run_cw_command(["config", "use-preset", "no-op"], cwd=temp_git_repo)
        assert result.returncode == 0

        # 3. Verify change
        result = run_cw_command(["config", "show"], cwd=temp_git_repo)
        assert "no-op" in result.stdout.lower()

        # 4. Reset to defaults
        result = run_cw_command(["config", "reset"], cwd=temp_git_repo)
        assert result.returncode == 0

        # Verify reset
        result = run_cw_command(["config", "show"], cwd=temp_git_repo)
        assert "claude" in result.stdout.lower()

    def test_list_presets(self, temp_git_repo: Path) -> None:
        """Test listing available presets."""
        result = run_cw_command(["config", "list-presets"], cwd=temp_git_repo)
        assert result.returncode == 0

        # Should show common presets
        expected_presets = ["claude", "codex", "happy", "no-op"]
        for preset in expected_presets:
            assert preset in result.stdout, f"Preset {preset} not in list"


class TestCustomPathWorkflow:
    """E2E tests for custom worktree paths."""

    def test_create_worktree_with_custom_path(
        self, temp_git_repo: Path, tmp_path: Path, disable_claude
    ) -> None:
        """
        Test creating worktree with custom path:
        1. Create with --path option
        2. Verify created at custom location
        3. Can still merge from custom path
        """
        # 1. Create with custom path
        custom_path = tmp_path / "my-custom-worktree"
        result = run_cw_command(
            ["new", "custom-branch", "--path", str(custom_path), "--no-cd"],
            cwd=temp_git_repo,
        )
        assert result.returncode == 0

        # 2. Verify created at custom location
        assert custom_path.exists(), "Worktree not created at custom path"
        assert (custom_path / "README.md").exists()

        # 3. Make a commit and merge
        test_file = custom_path / "custom.txt"
        test_file.write_text("custom content\n")
        subprocess.run(["git", "add", "."], cwd=custom_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Custom change"],
            cwd=custom_path,
            check=True,
            capture_output=True,
        )

        result = run_cw_command(["merge"], cwd=custom_path)
        assert result.returncode == 0

        # Verify merged and cleaned up
        assert not custom_path.exists()
        assert (temp_git_repo / "custom.txt").exists()


class TestBasebranchWorkflow:
    """E2E tests for working with different base branches."""

    def test_create_from_different_base(self, temp_git_repo: Path, disable_claude) -> None:
        """
        Test creating worktree from non-main base branch:
        1. Create develop branch
        2. Create worktree from develop
        3. Merge back to develop
        """
        # 1. Create develop branch
        subprocess.run(
            ["git", "checkout", "-b", "develop"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        # 2. Create worktree from develop
        result = run_cw_command(
            ["new", "feature-from-dev", "--base", "develop", "--no-cd"], cwd=temp_git_repo
        )
        assert result.returncode == 0

        worktree_path = temp_git_repo.parent / f"{temp_git_repo.name}-feature-from-dev"
        assert worktree_path.exists()

        # 3. Make commit
        test_file = worktree_path / "dev-feature.txt"
        test_file.write_text("feature content\n")
        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add feature"],
            cwd=worktree_path,
            check=True,
            capture_output=True,
        )

        # 4. Merge back (should merge to develop, not main)
        result = run_cw_command(["merge"], cwd=worktree_path)
        assert result.returncode == 0

        # Verify merged to develop
        subprocess.run(
            ["git", "checkout", "develop"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )
        assert (temp_git_repo / "dev-feature.txt").exists()
