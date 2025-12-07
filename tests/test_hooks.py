"""Tests for the hook system."""

import pytest

from claude_worktree.hooks import (
    HOOK_EVENTS,
    HookError,
    add_hook,
    generate_hook_id,
    get_hooks,
    remove_hook,
    run_hooks,
    set_hook_enabled,
)


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


class TestAddHook:
    """Test adding hooks."""

    def test_add_hook_basic(self, tmp_path, monkeypatch):
        """Add a basic hook."""
        monkeypatch.setenv("HOME", str(tmp_path))

        hook_id = add_hook("worktree.post_create", "npm install")

        assert hook_id.startswith("hook-")
        hooks = get_hooks("worktree.post_create")
        assert len(hooks) == 1
        assert hooks[0]["command"] == "npm install"
        assert hooks[0]["enabled"] is True

    def test_add_hook_with_custom_id(self, tmp_path, monkeypatch):
        """Add hook with custom ID."""
        monkeypatch.setenv("HOME", str(tmp_path))

        hook_id = add_hook("worktree.post_create", "npm install", hook_id="deps")

        assert hook_id == "deps"
        hooks = get_hooks("worktree.post_create")
        assert hooks[0]["id"] == "deps"

    def test_add_hook_with_description(self, tmp_path, monkeypatch):
        """Add hook with description."""
        monkeypatch.setenv("HOME", str(tmp_path))

        add_hook(
            "worktree.post_create",
            "npm install",
            hook_id="deps",
            description="Install dependencies",
        )

        hooks = get_hooks("worktree.post_create")
        assert hooks[0]["description"] == "Install dependencies"

    def test_add_hook_invalid_event(self, tmp_path, monkeypatch):
        """Adding hook with invalid event should raise error."""
        monkeypatch.setenv("HOME", str(tmp_path))

        with pytest.raises(HookError, match="Invalid hook event"):
            add_hook("invalid.event", "echo hello")

    def test_add_hook_duplicate_id(self, tmp_path, monkeypatch):
        """Adding hook with duplicate ID should raise error."""
        monkeypatch.setenv("HOME", str(tmp_path))

        add_hook("worktree.post_create", "npm install", hook_id="deps")

        with pytest.raises(HookError, match="already exists"):
            add_hook("worktree.post_create", "npm test", hook_id="deps")

    def test_add_multiple_hooks(self, tmp_path, monkeypatch):
        """Multiple hooks can be added to same event."""
        monkeypatch.setenv("HOME", str(tmp_path))

        add_hook("worktree.post_create", "npm install", hook_id="deps")
        add_hook("worktree.post_create", "npm test", hook_id="test")

        hooks = get_hooks("worktree.post_create")
        assert len(hooks) == 2


class TestRemoveHook:
    """Test removing hooks."""

    def test_remove_hook(self, tmp_path, monkeypatch):
        """Remove an existing hook."""
        monkeypatch.setenv("HOME", str(tmp_path))

        add_hook("worktree.post_create", "npm install", hook_id="deps")
        remove_hook("worktree.post_create", "deps")

        hooks = get_hooks("worktree.post_create")
        assert len(hooks) == 0

    def test_remove_nonexistent_hook(self, tmp_path, monkeypatch):
        """Removing nonexistent hook should raise error."""
        monkeypatch.setenv("HOME", str(tmp_path))

        with pytest.raises(HookError, match="not found"):
            remove_hook("worktree.post_create", "nonexistent")


class TestSetHookEnabled:
    """Test enabling/disabling hooks."""

    def test_disable_hook(self, tmp_path, monkeypatch):
        """Disable a hook."""
        monkeypatch.setenv("HOME", str(tmp_path))

        add_hook("worktree.post_create", "npm install", hook_id="deps")
        set_hook_enabled("worktree.post_create", "deps", False)

        hooks = get_hooks("worktree.post_create")
        assert hooks[0]["enabled"] is False

    def test_enable_hook(self, tmp_path, monkeypatch):
        """Enable a disabled hook."""
        monkeypatch.setenv("HOME", str(tmp_path))

        add_hook("worktree.post_create", "npm install", hook_id="deps")
        set_hook_enabled("worktree.post_create", "deps", False)
        set_hook_enabled("worktree.post_create", "deps", True)

        hooks = get_hooks("worktree.post_create")
        assert hooks[0]["enabled"] is True

    def test_enable_nonexistent_hook(self, tmp_path, monkeypatch):
        """Enabling nonexistent hook should raise error."""
        monkeypatch.setenv("HOME", str(tmp_path))

        with pytest.raises(HookError, match="not found"):
            set_hook_enabled("worktree.post_create", "nonexistent", True)


class TestRunHooks:
    """Test hook execution."""

    def test_run_hooks_success(self, tmp_path, monkeypatch):
        """Successfully run a hook."""
        monkeypatch.setenv("HOME", str(tmp_path))

        add_hook("worktree.post_create", "echo hello", hook_id="test")

        context = {
            "branch": "feature-1",
            "base_branch": "main",
            "worktree_path": str(tmp_path),
            "repo_path": str(tmp_path),
            "event": "worktree.post_create",
            "operation": "new",
        }

        result = run_hooks("worktree.post_create", context, cwd=tmp_path)
        assert result is True

    def test_run_hooks_no_hooks(self, tmp_path, monkeypatch):
        """Running hooks when none exist should succeed."""
        monkeypatch.setenv("HOME", str(tmp_path))

        context = {"event": "worktree.post_create"}
        result = run_hooks("worktree.post_create", context)
        assert result is True

    def test_run_hooks_disabled_skipped(self, tmp_path, monkeypatch):
        """Disabled hooks should be skipped."""
        monkeypatch.setenv("HOME", str(tmp_path))

        add_hook("worktree.post_create", "exit 1", hook_id="failing")
        set_hook_enabled("worktree.post_create", "failing", False)

        context = {"event": "worktree.post_create"}
        result = run_hooks("worktree.post_create", context, cwd=tmp_path)
        assert result is True

    def test_run_hooks_env_vars(self, tmp_path, monkeypatch):
        """Hook should receive context as environment variables."""
        import sys

        monkeypatch.setenv("HOME", str(tmp_path))

        # Create a Python script that writes env vars to a file (cross-platform)
        script_file = tmp_path / "check_env.py"
        output_file = tmp_path / "output.txt"
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
        )

        context = {
            "branch": "feature-test",
            "base_branch": "main",
            "worktree_path": str(tmp_path),
            "repo_path": str(tmp_path),
            "event": "worktree.post_create",
            "operation": "new",
        }

        run_hooks("worktree.post_create", context, cwd=tmp_path)

        output = output_file.read_text()
        assert "BRANCH=feature-test" in output
        assert "BASE=main" in output

    def test_pre_hook_abort_on_failure(self, tmp_path, monkeypatch):
        """Pre-hook failure should abort operation."""
        monkeypatch.setenv("HOME", str(tmp_path))

        add_hook("worktree.pre_create", "exit 1", hook_id="failing")

        context = {"event": "worktree.pre_create"}

        with pytest.raises(HookError, match="Pre-hook.*failed"):
            run_hooks("worktree.pre_create", context, cwd=tmp_path)

    def test_post_hook_continues_on_failure(self, tmp_path, monkeypatch):
        """Post-hook failure should not abort (returns False but no exception)."""
        monkeypatch.setenv("HOME", str(tmp_path))

        add_hook("worktree.post_create", "exit 1", hook_id="failing")

        context = {"event": "worktree.post_create"}

        # Should not raise, but return False
        result = run_hooks("worktree.post_create", context, cwd=tmp_path)
        assert result is False

    def test_run_multiple_hooks_in_order(self, tmp_path, monkeypatch):
        """Multiple hooks should run in order."""
        import sys

        monkeypatch.setenv("HOME", str(tmp_path))

        output_file = tmp_path / "order.txt"

        # Use Python for cross-platform compatibility (Windows echo has trailing spaces)
        add_hook(
            "worktree.post_create",
            f"{sys.executable} -c \"open(r'{output_file}', 'a').write('first\\n')\"",
            hook_id="first",
        )
        add_hook(
            "worktree.post_create",
            f"{sys.executable} -c \"open(r'{output_file}', 'a').write('second\\n')\"",
            hook_id="second",
        )

        context = {"event": "worktree.post_create"}
        run_hooks("worktree.post_create", context, cwd=tmp_path)

        output = output_file.read_text()
        lines = output.strip().split("\n")
        assert lines[0] == "first"
        assert lines[1] == "second"


class TestHookCLI:
    """Test hook CLI commands."""

    def test_hook_add_command(self, tmp_path, monkeypatch):
        """Test cw hook add command."""
        from typer.testing import CliRunner

        from claude_worktree.cli import app

        monkeypatch.setenv("HOME", str(tmp_path))
        runner = CliRunner()

        result = runner.invoke(
            app, ["hook", "add", "worktree.post_create", "npm install", "--id", "deps"]
        )

        assert result.exit_code == 0
        assert "Added hook 'deps'" in result.output

    def test_hook_list_command(self, tmp_path, monkeypatch):
        """Test cw hook list command."""
        from typer.testing import CliRunner

        from claude_worktree.cli import app

        monkeypatch.setenv("HOME", str(tmp_path))
        runner = CliRunner()

        # Add a hook first
        runner.invoke(app, ["hook", "add", "worktree.post_create", "npm install", "--id", "deps"])

        result = runner.invoke(app, ["hook", "list"])

        assert result.exit_code == 0
        assert "worktree.post_create" in result.output
        assert "deps" in result.output

    def test_hook_remove_command(self, tmp_path, monkeypatch):
        """Test cw hook remove command."""
        from typer.testing import CliRunner

        from claude_worktree.cli import app

        monkeypatch.setenv("HOME", str(tmp_path))
        runner = CliRunner()

        # Add then remove
        runner.invoke(app, ["hook", "add", "worktree.post_create", "npm install", "--id", "deps"])
        result = runner.invoke(app, ["hook", "remove", "worktree.post_create", "deps"])

        assert result.exit_code == 0
        assert "Removed hook 'deps'" in result.output

    def test_hook_disable_enable_commands(self, tmp_path, monkeypatch):
        """Test cw hook disable/enable commands."""
        from typer.testing import CliRunner

        from claude_worktree.cli import app

        monkeypatch.setenv("HOME", str(tmp_path))
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

    def test_hook_run_dry_run(self, tmp_path, monkeypatch):
        """Test cw hook run --dry-run command."""
        from typer.testing import CliRunner

        from claude_worktree.cli import app

        monkeypatch.setenv("HOME", str(tmp_path))
        runner = CliRunner()

        # Add a hook
        runner.invoke(app, ["hook", "add", "worktree.post_create", "npm install", "--id", "deps"])

        result = runner.invoke(app, ["hook", "run", "worktree.post_create", "--dry-run"])

        assert result.exit_code == 0
        assert "Would run" in result.output
        assert "deps" in result.output
