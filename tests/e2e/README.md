# E2E Tests for claude-worktree

This directory contains **End-to-End (E2E) tests** that verify complete user workflows.

## Test Organization

### Platform-Independent Tests (`test_workflows.py`)

**Run on all platforms (Windows, macOS, Linux)**

These tests verify core functionality by running actual `cw` CLI commands:

- ✅ **TestFeatureDevelopmentWorkflow** - Complete feature development lifecycle
  - Create → Commit → List → Status → Merge
  - Multiple worktrees simultaneously
  - Delete with --keep-branch

- ✅ **TestRebaseConflictWorkflow** - Conflict handling
  - Merge with conflicts (should fail gracefully)
  - Dry-run mode (preview without changes)

- ✅ **TestErrorHandling** - Edge cases
  - Duplicate worktree creation
  - Non-existent worktree deletion
  - Invalid branch names
  - Merge from main repo (should fail)

- ✅ **TestConfigWorkflow** - Configuration management
  - Change AI tool presets
  - List available presets

- ✅ **TestCustomPathWorkflow** - Custom worktree paths
  - Create with --path option
  - Merge from custom location

- ✅ **TestBasebranchWorkflow** - Different base branches
  - Create from develop instead of main
  - Merge back to correct base

### Platform-Specific Tests (`test_shell_functions.py`)

**Optional tests marked with `@pytest.mark.shell`**

These tests verify shell functions (`cw-cd`) work in actual shells:

- **TestBashShellFunction** - bash/zsh testing
  - Directory changes with `cw-cd`
  - Tab completion
  - Error handling

- **TestZshShellFunction** - zsh-specific tests

- **TestFishShellFunction** - fish shell tests
  - Directory changes
  - Fish completion

- **TestPowerShellFunction** - Windows PowerShell
  - Directory changes (Windows only)
  - Error handling

- **TestShellScriptSyntax** - Syntax validation
  - Bash script syntax check
  - Fish script syntax check
  - PowerShell script syntax check

## Running Tests

### Quick Start (Platform-Independent)

```bash
# Run all E2E tests (excluding shell-specific)
pytest tests/e2e/ -v -m "not shell"

# Run specific workflow test
pytest tests/e2e/test_workflows.py::TestFeatureDevelopmentWorkflow -v
```

### Shell Function Tests (Optional)

```bash
# Run all shell-specific tests (requires actual shells installed)
pytest tests/e2e/test_shell_functions.py -v -m shell

# Run bash tests only (Unix)
pytest tests/e2e/test_shell_functions.py::TestBashShellFunction -v

# Run PowerShell tests only (Windows)
pytest tests/e2e/test_shell_functions.py::TestPowerShellFunction -v
```

### CI/CD Usage

```yaml
# GitHub Actions example
- name: Run E2E tests (all platforms)
  run: pytest tests/e2e/test_workflows.py -v

- name: Run shell tests (Unix only)
  if: runner.os != 'Windows'
  run: pytest tests/e2e/test_shell_functions.py -m shell
```

## Test Execution Time

| Test Suite | Duration | When to Run |
|------------|----------|-------------|
| `test_workflows.py` | ~11s | Every commit (required) |
| `test_shell_functions.py` | ~5s | Pre-release (optional) |

## Test Markers

Tests use pytest markers for filtering:

```python
@pytest.mark.shell    # Shell-specific tests (optional)
```

Configure in `pyproject.toml`:
```toml
markers = [
    "shell: Platform-specific shell function tests (optional)",
]
```

## Platform Requirements

### Platform-Independent Tests
- ✅ Python 3.11+
- ✅ Git 2.31+
- ✅ `cw` CLI installed

### Shell Function Tests
- Unix: bash, zsh (optional: fish)
- Windows: PowerShell or pwsh

## Writing New E2E Tests

### Template for Workflow Test

```python
class TestYourWorkflow:
    """E2E test for your workflow."""

    def test_your_scenario(self, temp_git_repo: Path, disable_claude) -> None:
        """Test description."""
        # 1. Setup - create worktree
        result = run_cw_command(["new", "my-branch", "--no-cd"], cwd=temp_git_repo)
        assert result.returncode == 0

        # 2. Action - perform operations
        worktree_path = temp_git_repo.parent / f"{temp_git_repo.name}-my-branch"
        # ... do something ...

        # 3. Verify - check results
        result = run_cw_command(["list"], cwd=temp_git_repo)
        assert "my-branch" in result.stdout
```

### Template for Shell Test

```python
@pytest.mark.shell
@SKIP_ON_WINDOWS  # or @SKIP_ON_UNIX
class TestYourShellFunction:
    """Shell-specific test."""

    def test_in_bash(self, temp_git_repo: Path, disable_claude) -> None:
        """Test shell function in bash."""
        create_worktree(branch_name="test-shell", no_cd=True)

        bash_script = """
        source <(cw _shell-function bash)
        # Your test commands here
        """

        result = subprocess.run(
            ["bash", "-c", bash_script],
            cwd=temp_git_repo,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
```

## Best Practices

1. **Platform-Independent First**: Always write platform-independent tests when possible
2. **Shell Tests Are Optional**: Only add shell tests for critical shell-specific features
3. **Clear Assertions**: Use descriptive assertion messages
4. **Cleanup**: Tests should clean up worktrees (or rely on temp_git_repo fixture)
5. **Real Operations**: E2E tests should use real git operations, not mocks

## Troubleshooting

### Tests Fail on Windows
- Check if using Unix-specific paths (use `Path` objects)
- Ensure commands don't use Unix-specific flags

### Shell Tests Skipped
- Shell not installed → Expected (tests will skip)
- Wrong platform → Expected (tests skip on wrong OS)

### Tests Timeout
- Default timeout: 30s per command
- Increase in `run_cw_command()` if needed
- Check for infinite loops in shell scripts

## See Also

- `../integration/` - Integration tests (git + filesystem)
- `../unit/` - Unit tests (pure functions)
- `conftest.py` - Shared fixtures
