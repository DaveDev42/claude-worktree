# Claude Worktree - Project Guide for Claude Code

## Project Overview

**claude-worktree** is a CLI tool that seamlessly integrates git worktree with AI coding assistants to streamline feature development workflows. It allows developers to quickly create isolated worktrees for feature branches, work with their preferred AI tool (Claude Code, Codex, Happy, or custom) in those environments, and cleanly merge changes back to the base branch.

## Core Concept

Instead of switching branches in a single working directory, `claude-worktree` creates separate directories (worktrees) for each feature branch. This allows:
- Multiple features to be worked on simultaneously
- Clean isolation between different tasks
- Automatic AI coding assistant session management per feature (configurable per user)
- Safe merge workflows with automatic cleanup

## Project Structure

```
claude-worktree/
├── src/claude_worktree/          # Main package
│   ├── __init__.py               # Package initialization
│   ├── __main__.py               # Entry point for `python -m claude_worktree`
│   ├── cli.py                    # Typer-based CLI definitions
│   ├── core.py                   # Core business logic (commands implementation)
│   ├── config.py                 # Configuration management
│   ├── git_utils.py              # Git operations wrapper
│   ├── exceptions.py             # Custom exception classes
│   └── constants.py              # Constants and default values
├── tests/                        # Test suite
│   ├── test_core.py
│   ├── test_config.py
│   ├── test_git_utils.py
│   ├── test_cli.py
│   └── conftest.py               # pytest fixtures
├── .github/workflows/
│   ├── test.yml                  # CI: Run tests on push/PR
│   └── publish.yml               # CD: Publish to PyPI on release
├── pyproject.toml                # Project metadata, dependencies (uv format)
├── README.md                     # User-facing documentation
├── CLAUDE.md                     # This file (for Claude Code)
├── LICENSE                       # MIT License
├── .gitignore
└── cw.py                         # Legacy single-file version (to be migrated)
```

## Key Features

### 1. Worktree Management
- **`cw new <name>`**: Create new worktree with specified branch name
  - Default path: `../<repo>-<branch>` (e.g., `../myproject-fix-auth/`)
  - Customizable with `--path` option
  - Automatically launches configured AI tool in the new worktree

- **`cw finish`**: Complete feature work
  - Rebases feature branch on base branch
  - Fast-forward merges into base branch
  - Cleans up worktree and feature branch
  - Optional `--push` to push to remote

- **`cw delete <target>`**: Remove worktree by branch name or path
  - Options: `--keep-branch`, `--delete-remote`

- **`cw list`**: Show all worktrees
- **`cw status`**: Show current worktree metadata
- **`cw prune`**: Clean up orphaned worktrees

### 2. AI Tool Integration
- **`cw attach`**: Reattach AI tool to current worktree
- Launch options:
  - `--bg`: Background process
  - `--iterm`: New iTerm2 window (macOS)
  - `--tmux <session>`: New tmux session
  - `--no-ai`: Skip AI tool launch (deprecated: `--no-claude`)
- Supports multiple AI tools:
  - Claude Code (default)
  - Codex
  - Happy (with Claude or Codex backend)
  - Custom commands

### 3. Configuration Management
- **`cw config show`**: Display current configuration
- **`cw config set <key> <value>`**: Set configuration value
- **`cw config use-preset <name>`**: Use predefined AI tool preset
- **`cw config list-presets`**: List available presets
- **`cw config reset`**: Reset to defaults
- Configuration stored in `~/.config/claude-worktree/config.json`
- Environment variable override: `CW_AI_TOOL`

### 4. Shell Completion
- Typer provides automatic shell completion for bash/zsh/fish
- Install with: `cw --install-completion`

## Technology Stack

- **Python 3.8+**: Core language
- **uv**: Fast Python package manager
- **Typer**: Modern CLI framework with type hints
- **pytest**: Testing framework
- **GitHub Actions**: CI/CD automation

## Development Workflow Changes from Legacy

### Path Naming (IMPORTANT)
**Before (cw.py):**
- Path: `../.cw_worktrees/<repo>/<topic>-<timestamp>/`
- Branch: `<topic>-<timestamp>` (e.g., `fix-auth-20250122-143052`)

**After (new design):**
- Path: `../<repo>-<branch>/` (e.g., `../myproject-fix-auth/`)
- Branch: User-specified name (e.g., `fix-auth`)
- Cleaner, more predictable naming
- No timestamp clutter

### CLI Framework
**Before:** argparse with manual completion setup
**After:** Typer with:
- Type hints for automatic validation
- Built-in shell completion
- Better help text generation
- Cleaner command definitions

### Error Handling
**Before:** Generic RuntimeError with string messages
**After:** Custom exception hierarchy:
- `ClaudeWorktreeError`: Base exception
- `GitError`: Git operation failures
- `WorktreeNotFoundError`: Missing worktree
- `InvalidBranchError`: Invalid branch state

## Metadata Storage

The tool stores metadata in git config:
- `branch.<feature>.worktreeBase`: The base branch name
- `worktree.<feature>.basePath`: Path to the base repository

This allows the `finish` command to know:
1. Which branch to rebase onto
2. Where the main repository is located
3. How to perform the merge safely

## Git Requirements

- Git 2.31+ (for modern worktree support)
- Repository must be initialized
- Remote origin recommended for fetch/push operations

## Installation Methods

1. **uv (recommended):**
   ```bash
   uv tool install claude-worktree
   ```

2. **pip:**
   ```bash
   pip install claude-worktree
   ```

3. **From source:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/claude-worktree
   cd claude-worktree
   uv pip install -e .
   ```

## Testing Strategy

- **Unit tests**: Test individual functions in isolation
- **Integration tests**: Test full command workflows
- **Mocking**: Mock git commands to avoid filesystem changes
- **Fixtures**: Reusable test repositories

## Common Development Tasks

### Running tests (MANDATORY before commits)
**IMPORTANT**: Always run the full test suite locally before committing changes!

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_core.py

# Run with coverage report
uv run pytest --cov=claude_worktree --cov-report=term
```

**Pre-commit checklist:**
1. ✅ Run `uv run pytest` - all tests must pass
2. ✅ Run `ruff check src/ tests/` - no linting errors
3. ✅ Run `mypy src/claude_worktree` - no type errors
4. ✅ Verify changes work as expected locally

The pre-commit hooks will automatically run ruff and mypy, but **you must run pytest manually** before committing. GitHub Actions will run all checks, but catching issues locally saves time and CI resources.

### Running the CLI during development
```bash
uv run python -m claude_worktree --help
uv run python -m claude_worktree new my-feature

# Or install in editable mode for easier testing
uv pip install -e .
cw --help
```

### Building the package
```bash
uv build
```

### Publishing to PyPI
```bash
uv publish
```

## Code Style Guidelines

- Type hints for all function signatures
- Docstrings for public functions (Google style)
- Follow PEP 8 (enforced by ruff)
- Keep functions focused and testable
- Separate business logic from CLI interface

## Future Enhancements (Ideas)

- Configuration file support (`.cwrc`, `pyproject.toml`)
- Interactive mode for command selection
- Git hook integration
- Support for alternative Claude Code commands
- Worktree templates
- Better conflict resolution guidance

## Troubleshooting

### Common Issues

1. **"Not a git repository"**
   - Run from within a git repository

2. **"Claude CLI not found"**
   - Install Claude Code CLI: https://claude.ai/download

3. **"Rebase failed"**
   - Conflicts detected; resolve manually
   - Tool aborts rebase automatically

4. **Shell completion not working**
   - Run `cw --install-completion`
   - Restart your shell

## Contributing

This is an open-source project. Contributions welcome!
- Report bugs via GitHub Issues
- Submit PRs for features/fixes
- Discuss ideas in GitHub Discussions

## License

MIT License - see LICENSE file
