# E2E Tests for claude-worktree

This directory contains **End-to-End (E2E) tests** that verify complete user workflows.

**🚀 All tests run on every commit** - Both platform-independent workflow tests AND shell-specific function tests are executed in CI on every push/PR across all platforms (bash, zsh, fish, PowerShell) to ensure complete compatibility.

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

### Shell Function Tests (`test_shell_functions.py`)

**Run on EVERY commit across ALL shells** - Marked with `@pytest.mark.shell` but executed in CI automatically.

These tests verify shell functions (`cw-cd`) work in actual shells:

- **TestBashShellFunction** - bash testing
  - Directory changes with `cw-cd`
  - Tab completion
  - Error handling

- **TestZshShellFunction** - zsh-specific tests (Unix only)

- **TestFishShellFunction** - fish shell tests (auto-installed in CI)
  - Directory changes
  - Fish completion

- **TestPowerShellFunction** - Windows PowerShell (Windows only)
  - Directory changes
  - Error handling

- **TestShellScriptSyntax** - Syntax validation
  - Bash script syntax check
  - Fish script syntax check
  - PowerShell script syntax check

## Running Tests

### Quick Start (All Tests)

```bash
# Run all E2E tests (workflows + shells)
pytest tests/e2e/ -v

# Run specific workflow test
pytest tests/e2e/test_workflows.py::TestFeatureDevelopmentWorkflow -v

# Run only shell function tests
pytest tests/e2e/test_shell_functions.py -v -m shell
```

### Local Development

```bash
# Skip shell tests if shells not installed locally
pytest tests/e2e/ -v -m "not shell"

# Run bash tests only
pytest tests/e2e/test_shell_functions.py::TestBashShellFunction -v

# Run PowerShell tests only (Windows)
pytest tests/e2e/test_shell_functions.py::TestPowerShellFunction -v
```

### CI/CD (Automatic)

**All tests run automatically on every push/PR:**

```yaml
# Ubuntu/macOS: Installs bash, zsh, fish → runs all shell tests
- name: Install shells
  run: |
    sudo apt-get install -y zsh fish  # Ubuntu
    brew install fish                  # macOS

# Windows: Uses built-in PowerShell → runs PowerShell tests
- name: Run tests
  run: pytest tests/e2e/ -v  # ALL tests including shells
```

## Test Execution Time

| Test Suite | Duration | CI Execution |
|------------|----------|--------------|
| `test_workflows.py` | ~11s | ✅ Every commit |
| `test_shell_functions.py` | ~5s | ✅ Every commit |
| **Total E2E** | **~16s** | **Every commit** |

## Test Markers

Tests use pytest markers for filtering:

```python
@pytest.mark.shell    # Shell-specific tests (run in CI, optional locally)
```

Configure in `pyproject.toml`:
```toml
markers = [
    "shell: Platform-specific shell function tests",
]
```

## Platform Requirements

### CI (Automatic Installation)
- ✅ **Ubuntu**: bash (pre-installed), zsh, fish (auto-installed)
- ✅ **macOS**: bash, zsh (pre-installed), fish (auto-installed via brew)
- ✅ **Windows**: PowerShell (pre-installed)

### Local Development
- **Platform-Independent Tests**: Python 3.11+, Git 2.31+, `cw` CLI
- **Shell Tests**: Install shells manually or skip with `-m "not shell"`

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

## CI Strategy

### Every Push/PR
✅ **Ubuntu** (Python 3.11, 3.12)
- Installs: bash (✓), zsh (auto), fish (auto)
- Runs: All workflow tests + bash/zsh/fish shell tests

✅ **macOS** (Python 3.11, 3.12)
- Installs: bash (✓), zsh (✓), fish (auto)
- Runs: All workflow tests + bash/zsh/fish shell tests

✅ **Windows** (Python 3.11, 3.12)
- Installs: PowerShell (✓)
- Runs: All workflow tests + PowerShell shell tests

**Total CI Matrix**: 3 OS × 2 Python × (workflow tests + shell tests) = **6 comprehensive test runs per commit**

## Best Practices

1. **All Tests Are Critical**: Both workflow and shell tests run on every commit
2. **Cross-Platform**: Use `Path` objects, avoid platform-specific assumptions
3. **Clear Assertions**: Use descriptive assertion messages
4. **Cleanup**: Tests should clean up worktrees (or rely on temp_git_repo fixture)
5. **Real Operations**: E2E tests use real git operations and real shells, not mocks

## Troubleshooting

### Tests Fail on Windows
- Check if using Unix-specific paths (use `Path` objects)
- Ensure commands don't use Unix-specific flags

### Shell Tests Skipped Locally
- Install required shells: `sudo apt-get install zsh fish` (Ubuntu)
- Or skip with: `pytest tests/e2e/ -m "not shell"`

### Tests Timeout
- Default timeout: 30s per command
- Increase in `run_cw_command()` if needed
- Check for infinite loops in shell scripts

## See Also

- `../integration/` - Integration tests (git + filesystem)
- `../unit/` - Unit tests (pure functions)
- `conftest.py` - Shared fixtures
- `.github/workflows/test.yml` - CI configuration with shell installation
