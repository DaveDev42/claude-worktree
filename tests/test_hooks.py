"""Tests for the hook system."""

import pytest

from claude_worktree.hooks import (
    HOOK_EVENTS,
    HookError,
    add_hook,
    generate_hook_id,
    get_hooks,
    get_hooks_file_path,
    get_repo_root_for_hooks,
    remove_hook,
    run_hooks,
    set_hook_enabled,
)


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository for testing hooks."""
    repo_path = tmp_path / "test-repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    return repo_path


class TestHookEvents:
    """Test hook event definitions."""

    def test_hook_events_list(self):
        """Verify all expected hook events are defined."""
        assert "worktree.pre_create" in HOOK_EVENTS
        assert "worktree.post_create" in HOOK_EVENTS
        assert "worktree.pre_delete" in HOOK_EVENTS
        assert "worktree.post_delete" in HOOK_EVENTS
        assert "merge.pre" in HOOK_EVENTS
        assert "merge.post" in HOOK_EVENTS
        assert "pr.pre" in HOOK_EVENTS
        assert "pr.post" in HOOK_EVENTS
        assert "resume.pre" in HOOK_EVENTS
        assert "resume.post" in HOOK_EVENTS
        assert "sync.pre" in HOOK_EVENTS
        assert "sync.post" in HOOK_EVENTS
        assert len(HOOK_EVENTS) == 12


class TestGenerateHookId:
    """Test hook ID generation."""

    def test_generates_consistent_id(self):
        """Same command should generate same ID."""
        id1 = generate_hook_id("npm install")
        id2 = generate_hook_id("npm install")
        assert id1 == id2

    def test_different_commands_different_ids(self):
        """Different commands should generate different IDs."""
        id1 = generate_hook_id("npm install")
        id2 = generate_hook_id("npm test")
        assert id1 != id2

    def test_id_format(self):
        """ID should follow expected format."""
        hook_id = generate_hook_id("echo hello")
        assert hook_id.startswith("hook-")
        assert len(hook_id) == 13  # "hook-" + 8 hex chars


class TestRepoDetection:
    """Test repository detection for hooks."""

    def test_get_repo_root_for_hooks(self, git_repo):
        """Find repo root from a subdirectory."""
        subdir = git_repo / "src" / "components"
        subdir.mkdir(parents=True)

        found = get_repo_root_for_hooks(subdir)
        assert found == git_repo

    def test_get_repo_root_not_in_repo(self, tmp_path):
        """Return None when not in a repository."""
        non_repo = tmp_path / "not-a-repo"
        non_repo.mkdir()

        found = get_repo_root_for_hooks(non_repo)
        assert found is None

    def test_get_hooks_file_path(self, git_repo):
        """Get correct hooks file path."""
        path = get_hooks_file_path(git_repo)
        assert path == git_repo / ".cwconfig.json"


class TestAddHook:
    """Test adding hooks."""

    def test_add_hook_basic(self, git_repo):
        """Add a basic hook."""
        hook_id = add_hook("worktree.post_create", "npm install", repo_root=git_repo)

        assert hook_id.startswith("hook-")
        hooks = get_hooks("worktree.post_create", repo_root=git_repo)
        assert len(hooks) == 1
        assert hooks[0]["command"] == "npm install"
        assert hooks[0]["enabled"] is True

    def test_add_hook_with_custom_id(self, git_repo):
        """Add hook with custom ID."""
        hook_id = add_hook(
            "worktree.post_create", "npm install", hook_id="deps", repo_root=git_repo
        )

        assert hook_id == "deps"
        hooks = get_hooks("worktree.post_create", repo_root=git_repo)
        assert hooks[0]["id"] == "deps"

    def test_add_hook_with_description(self, git_repo):
        """Add hook with description."""
        add_hook(
            "worktree.post_create",
            "npm install",
            hook_id="deps",
            description="Install dependencies",
            repo_root=git_repo,
        )

        hooks = get_hooks("worktree.post_create", repo_root=git_repo)
        assert hooks[0]["description"] == "Install dependencies"

    def test_add_hook_invalid_event(self, git_repo):
        """Adding hook with invalid event should raise error."""
        with pytest.raises(HookError, match="Invalid hook event"):
            add_hook("invalid.event", "echo hello", repo_root=git_repo)

    def test_add_hook_duplicate_id(self, git_repo):
        """Adding hook with duplicate ID should raise error."""
        add_hook("worktree.post_create", "npm install", hook_id="deps", repo_root=git_repo)

        with pytest.raises(HookError, match="already exists"):
            add_hook("worktree.post_create", "npm test", hook_id="deps", repo_root=git_repo)

    def test_add_multiple_hooks(self, git_repo):
        """Multiple hooks can be added to same event."""
        add_hook("worktree.post_create", "npm install", hook_id="deps", repo_root=git_repo)
        add_hook("worktree.post_create", "npm test", hook_id="test", repo_root=git_repo)

        hooks = get_hooks("worktree.post_create", repo_root=git_repo)
        assert len(hooks) == 2

    def test_add_hook_not_in_repo(self, tmp_path):
        """Adding hook outside repository should raise error."""
        non_repo = tmp_path / "not-a-repo"
        non_repo.mkdir()

        with pytest.raises(HookError, match="Not in a git repository"):
            add_hook("worktree.post_create", "npm install", repo_root=non_repo)


class TestRemoveHook:
    """Test removing hooks."""

    def test_remove_hook(self, git_repo):
        """Remove an existing hook."""
        add_hook("worktree.post_create", "npm install", hook_id="deps", repo_root=git_repo)
        remove_hook("worktree.post_create", "deps", repo_root=git_repo)

        hooks = get_hooks("worktree.post_create", repo_root=git_repo)
        assert len(hooks) == 0

    def test_remove_nonexistent_hook(self, git_repo):
        """Removing nonexistent hook should raise error."""
        with pytest.raises(HookError, match="not found"):
            remove_hook("worktree.post_create", "nonexistent", repo_root=git_repo)


class TestSetHookEnabled:
    """Test enabling/disabling hooks."""

    def test_disable_hook(self, git_repo):
        """Disable a hook."""
        add_hook("worktree.post_create", "npm install", hook_id="deps", repo_root=git_repo)
        set_hook_enabled("worktree.post_create", "deps", False, repo_root=git_repo)

        hooks = get_hooks("worktree.post_create", repo_root=git_repo)
        assert hooks[0]["enabled"] is False

    def test_enable_hook(self, git_repo):
        """Enable a disabled hook."""
        add_hook("worktree.post_create", "npm install", hook_id="deps", repo_root=git_repo)
        set_hook_enabled("worktree.post_create", "deps", False, repo_root=git_repo)
        set_hook_enabled("worktree.post_create", "deps", True, repo_root=git_repo)

        hooks = get_hooks("worktree.post_create", repo_root=git_repo)
        assert hooks[0]["enabled"] is True

    def test_enable_nonexistent_hook(self, git_repo):
        """Enabling nonexistent hook should raise error."""
        with pytest.raises(HookError, match="not found"):
            set_hook_enabled("worktree.post_create", "nonexistent", True, repo_root=git_repo)


class TestRunHooks:
    """Test hook execution."""

    def test_run_hooks_success(self, git_repo):
        """Successfully run a hook."""
        add_hook("worktree.post_create", "echo hello", hook_id="test", repo_root=git_repo)

        context = {
            "branch": "feature-1",
            "base_branch": "main",
            "worktree_path": str(git_repo),
            "repo_path": str(git_repo),
            "event": "worktree.post_create",
            "operation": "new",
        }

        result = run_hooks("worktree.post_create", context, cwd=git_repo, repo_root=git_repo)
        assert result is True

    def test_run_hooks_no_hooks(self, git_repo):
        """Running hooks when none exist should succeed."""
        context = {"event": "worktree.post_create"}
        result = run_hooks("worktree.post_create", context, repo_root=git_repo)
        assert result is True

    def test_run_hooks_disabled_skipped(self, git_repo):
        """Disabled hooks should be skipped."""
        add_hook("worktree.post_create", "exit 1", hook_id="failing", repo_root=git_repo)
        set_hook_enabled("worktree.post_create", "failing", False, repo_root=git_repo)

        context = {"event": "worktree.post_create"}
        result = run_hooks("worktree.post_create", context, cwd=git_repo, repo_root=git_repo)
        assert result is True

    def test_run_hooks_env_vars(self, git_repo):
        """Hook should receive context as environment variables."""
        import sys

        # Create a Python script that writes env vars to a file (cross-platform)
        script_file = git_repo / "check_env.py"
        output_file = git_repo / "output.txt"
        script_file.write_text(f"""
import os
with open(r"{output_file}", "a") as f:
    f.write(f"BRANCH={{os.environ.get('CW_BRANCH', '')}}\\n")
    f.write(f"BASE={{os.environ.get('CW_BASE_BRANCH', '')}}\\n")
""")

        add_hook(
            "worktree.post_create",
            f"{sys.executable} {script_file}",
            hook_id="env-check",
            repo_root=git_repo,
        )

        context = {
            "branch": "feature-test",
            "base_branch": "main",
            "worktree_path": str(git_repo),
            "repo_path": str(git_repo),
            "event": "worktree.post_create",
            "operation": "new",
        }

        run_hooks("worktree.post_create", context, cwd=git_repo, repo_root=git_repo)

        output = output_file.read_text()
        assert "BRANCH=feature-test" in output
        assert "BASE=main" in output

    def test_pre_hook_abort_on_failure(self, git_repo):
        """Pre-hook failure should abort operation."""
        add_hook("worktree.pre_create", "exit 1", hook_id="failing", repo_root=git_repo)

        context = {"event": "worktree.pre_create"}

        with pytest.raises(HookError, match="Pre-hook.*failed"):
            run_hooks("worktree.pre_create", context, cwd=git_repo, repo_root=git_repo)

    def test_post_hook_continues_on_failure(self, git_repo):
        """Post-hook failure should not abort (returns False but no exception)."""
        add_hook("worktree.post_create", "exit 1", hook_id="failing", repo_root=git_repo)

        context = {"event": "worktree.post_create"}

        # Should not raise, but return False
        result = run_hooks("worktree.post_create", context, cwd=git_repo, repo_root=git_repo)
        assert result is False

    def test_run_multiple_hooks_in_order(self, git_repo):
        """Multiple hooks should run in order."""
        import sys

        output_file = git_repo / "order.txt"

        # Use Python for cross-platform compatibility (Windows echo has trailing spaces)
        add_hook(
            "worktree.post_create",
            f"{sys.executable} -c \"open(r'{output_file}', 'a').write('first\\n')\"",
            hook_id="first",
            repo_root=git_repo,
        )
        add_hook(
            "worktree.post_create",
            f"{sys.executable} -c \"open(r'{output_file}', 'a').write('second\\n')\"",
            hook_id="second",
            repo_root=git_repo,
        )

        context = {"event": "worktree.post_create"}
        run_hooks("worktree.post_create", context, cwd=git_repo, repo_root=git_repo)

        output = output_file.read_text()
        lines = output.strip().split("\n")
        assert lines[0] == "first"
        assert lines[1] == "second"


class TestHookCLI:
    """Test hook CLI commands."""

    def test_hook_add_command(self, git_repo, monkeypatch):
        """Test cw hook add command."""
        from typer.testing import CliRunner

        from claude_worktree.cli import app

        # Change to git repo directory so CLI can detect it
        monkeypatch.chdir(git_repo)
        # Set HOME to tmp_path to avoid polluting real config
        monkeypatch.setenv("HOME", str(git_repo.parent))
        runner = CliRunner()

        result = runner.invoke(
            app, ["hook", "add", "worktree.post_create", "npm install", "--id", "deps"]
        )

        assert result.exit_code == 0
        assert "Added hook 'deps'" in result.output

        # Verify hook file was created in repo
        hooks_file = git_repo / ".cwconfig.json"
        assert hooks_file.exists()

    def test_hook_list_command(self, git_repo, monkeypatch):
        """Test cw hook list command."""
        from typer.testing import CliRunner

        from claude_worktree.cli import app

        monkeypatch.chdir(git_repo)
        monkeypatch.setenv("HOME", str(git_repo.parent))
        runner = CliRunner()

        # Add a hook first
        runner.invoke(app, ["hook", "add", "worktree.post_create", "npm install", "--id", "deps"])

        result = runner.invoke(app, ["hook", "list"])

        assert result.exit_code == 0
        assert "worktree.post_create" in result.output
        assert "deps" in result.output

    def test_hook_remove_command(self, git_repo, monkeypatch):
        """Test cw hook remove command."""
        from typer.testing import CliRunner

        from claude_worktree.cli import app

        monkeypatch.chdir(git_repo)
        monkeypatch.setenv("HOME", str(git_repo.parent))
        runner = CliRunner()

        # Add then remove
        runner.invoke(app, ["hook", "add", "worktree.post_create", "npm install", "--id", "deps"])
        result = runner.invoke(app, ["hook", "remove", "worktree.post_create", "deps"])

        assert result.exit_code == 0
        assert "Removed hook 'deps'" in result.output

    def test_hook_disable_enable_commands(self, git_repo, monkeypatch):
        """Test cw hook disable/enable commands."""
        from typer.testing import CliRunner

        from claude_worktree.cli import app

        monkeypatch.chdir(git_repo)
        monkeypatch.setenv("HOME", str(git_repo.parent))
        runner = CliRunner()

        # Add a hook
        runner.invoke(app, ["hook", "add", "worktree.post_create", "npm install", "--id", "deps"])

        # Disable
        result = runner.invoke(app, ["hook", "disable", "worktree.post_create", "deps"])
        assert result.exit_code == 0
        assert "Disabled hook 'deps'" in result.output

        # Enable
        result = runner.invoke(app, ["hook", "enable", "worktree.post_create", "deps"])
        assert result.exit_code == 0
        assert "Enabled hook 'deps'" in result.output

    def test_hook_run_dry_run(self, git_repo, monkeypatch):
        """Test cw hook run --dry-run command."""
        from typer.testing import CliRunner

        from claude_worktree.cli import app

        monkeypatch.chdir(git_repo)
        monkeypatch.setenv("HOME", str(git_repo.parent))
        runner = CliRunner()

        # Add a hook
        runner.invoke(app, ["hook", "add", "worktree.post_create", "npm install", "--id", "deps"])

        result = runner.invoke(app, ["hook", "run", "worktree.post_create", "--dry-run"])

        assert result.exit_code == 0
        assert "Would run" in result.output
        assert "deps" in result.output

    def test_hook_add_not_in_repo(self, tmp_path, monkeypatch):
        """Test cw hook add fails outside of a git repository."""
        from typer.testing import CliRunner

        from claude_worktree.cli import app

        # Create a non-repo directory
        non_repo = tmp_path / "not-a-repo"
        non_repo.mkdir()
        monkeypatch.chdir(non_repo)
        monkeypatch.setenv("HOME", str(tmp_path))
        runner = CliRunner()

        result = runner.invoke(
            app, ["hook", "add", "worktree.post_create", "npm install", "--id", "deps"]
        )

        assert result.exit_code == 1
        assert "Not in a git repository" in result.output
