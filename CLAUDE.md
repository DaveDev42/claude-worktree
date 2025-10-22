# Claude Worktree - Project Guide for Claude Code

## Project Overview

**claude-worktree** is a CLI tool that seamlessly integrates git worktree with Claude Code to streamline feature development workflows. It allows developers to quickly create isolated worktrees for feature branches, work with Claude Code in those environments, and cleanly merge changes back to the base branch.

## Core Concept

Instead of switching branches in a single working directory, `claude-worktree` creates separate directories (worktrees) for each feature branch. This allows:
- Multiple features to be worked on simultaneously
- Clean isolation between different tasks
- Automatic Claude Code session management per feature
- Safe merge workflows with automatic cleanup

## Project Structure

```
claude-worktree/
├── src/claude_worktree/          # Main package
│   ├── __init__.py               # Package initialization
│   ├── __main__.py               # Entry point for `python -m claude_worktree`
│   ├── cli.py                    # Typer-based CLI definitions
│   ├── core.py                   # Core business logic (commands implementation)
│   ├── git_utils.py              # Git operations wrapper
│   ├── exceptions.py             # Custom exception classes
│   └── constants.py              # Constants and default values
├── tests/                        # Test suite
│   ├── test_core.py
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
  - Automatically launches Claude Code in the new worktree

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

### 2. Claude Code Integration
- **`cw attach`**: Reattach Claude Code to current worktree
- Launch options:
  - `--bg`: Background process
  - `--iterm`: New iTerm2 window (macOS)
  - `--tmux <session>`: New tmux session
  - `--no-claude`: Skip Claude launch

### 3. Shell Completion
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

### Running tests
```bash
uv run pytest
uv run pytest -v  # verbose
uv run pytest tests/test_core.py  # specific file
```

### Running the CLI during development
```bash
uv run python -m claude_worktree --help
uv run python -m claude_worktree new my-feature
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
