# Claude Worktree

> Work on multiple git branches simultaneously with isolated AI coding sessions

[![Tests](https://github.com/DaveDev42/claude-worktree/workflows/Tests/badge.svg)](https://github.com/DaveDev42/claude-worktree/actions)
[![PyPI version](https://badge.fury.io/py/claude-worktree.svg)](https://pypi.org/project/claude-worktree/)
[![Python versions](https://img.shields.io/pypi/pyversions/claude-worktree.svg)](https://pypi.org/project/claude-worktree/)
[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

## What is this?

**claude-worktree** (command: `cw`) helps you work on multiple features at the same time by creating separate directories for each branch. No more switching branches, stashing changes, or losing context.

Each feature gets:
- ✅ Its own directory (git worktree)
- ✅ Its own AI coding session (Claude Code, Codex, Happy, or custom)
- ✅ Zero interference with other work

Perfect for developers who want to:
- Work on multiple features in parallel
- Keep AI conversation context for each feature
- Never lose work when switching tasks
- Cleanly merge features without conflicts

## Why Use This?

### No More Branch Switching Chaos

**Before claude-worktree:**
```bash
# Working on feature-api
git add .
git stash  # Save current work
git checkout main
git checkout -b fix-urgent-bug
# Fix bug, commit
git checkout feature-api
git stash pop  # Hope nothing conflicts
# Where was I?
```

**With claude-worktree:**
```bash
cw new fix-urgent-bug
# Fix bug in separate directory
cw merge fix-urgent-bug --push
# Return to feature-api - it's untouched
```

Each feature stays isolated, AI context is preserved, and switching is instant.

### Lightning-Fast Workflow with Shell Completion

Tab completion makes everything faster:

```bash
cw <TAB>              # All commands appear
cw new --<TAB>        # All options for 'new' command
cw resume <TAB>       # Your branch names
cw-cd <TAB>           # Jump to any worktree instantly
```

No more typing long commands or remembering branch names - just type and press Tab.

## Quick Start

### Install

```bash
# Using uv (recommended)
uv tool install claude-worktree

# Or using pip
pip install claude-worktree
```

### Basic Usage

```bash
# 1. Create a new feature worktree
cw new fix-login-bug

# This creates:
# - A new branch: fix-login-bug
# - A new directory: ../myproject-fix-login-bug/
# - Launches Claude Code in that directory

# 2. Work on your feature
# (AI helps you, you commit changes, etc.)

# 3. When done, create a PR
cw pr

# Or merge directly (for solo projects)
cw merge --push
```

That's it! You've just created an isolated workspace with AI assistance, worked on your feature, and merged it back.

## Key Features

### Essential Commands

| Command | What it does |
|---------|-------------|
| `cw new <name>` | Create new feature worktree + launch AI |
| `cw list` | Show all your worktrees |
| `cw resume [branch]` | Resume AI session in a worktree |
| `cw pr` | Create GitHub pull request |
| `cw merge` | Merge to base branch and cleanup |
| `cw delete <name>` | Remove a worktree |

### Shell Completion & Navigation

**Enable tab completion for faster workflow:**

```bash
# Install completion (bash/zsh/fish/PowerShell)
cw --install-completion

# Restart your shell, then enjoy:
cw <TAB>          # Shows available commands
cw new --<TAB>    # Shows available options
cw resume <TAB>   # Shows branch names
```

**Windows PowerShell users:**
```powershell
# Install completion for PowerShell
cw --install-completion powershell

# Restart PowerShell, then use tab completion:
cw <TAB>          # Shows available commands
cw resume <TAB>   # Shows branch names
```

**Quick navigation between worktrees:**

```bash
# Interactive setup (recommended):
cw shell-setup

# Or install manually:
# bash/zsh: Add to ~/.bashrc or ~/.zshrc
source <(cw _shell-function bash)

# fish: Add to ~/.config/fish/config.fish
cw _shell-function fish | source

# PowerShell: Add to $PROFILE
cw _shell-function powershell | Invoke-Expression

# Then use:
cw-cd feature-api    # Jump to any worktree instantly
cw-cd <TAB>          # Tab completion works!
```

## Example Workflow

### Scenario: Working on multiple features

```bash
# Start 3 features at once
cw new feature-api
cw new fix-bug-123
cw new refactor-db

# Check what you have
cw list
#  BRANCH           STATUS    PATH
#  main             clean     .
#  feature-api      active    ../myproject-feature-api
#  fix-bug-123      modified  ../myproject-fix-bug-123
#  refactor-db      clean     ../myproject-refactor-db

# Resume work on a specific feature
cw resume fix-bug-123

# Complete features as they're done
cw pr feature-api        # Create PR
cw merge fix-bug-123 --push  # Direct merge
```

### Scenario: Team collaboration

```bash
# Create feature and share
cw new team-feature
git push -u origin team-feature

# Stay in sync with team
cw sync team-feature

# Compare before merging
cw diff main team-feature --summary

# Create PR for review
cw pr --title "Add awesome feature"
```

## Configuration

### AI Tool Selection

By default, `cw` launches Claude Code. You can easily change this:

```bash
# Use a preset
cw config use-preset claude         # Claude Code (default)
cw config use-preset happy          # Happy (mobile Claude)
cw config use-preset codex          # OpenAI Codex
cw config use-preset no-op          # Skip AI launch

# Or set custom tool
cw config set ai-tool "your-ai-tool"

# List available presets
cw config list-presets
```

### Auto-Copy Files

Automatically copy project-specific files (like `.env`) to new worktrees:

```bash
# Add files to copy list
cw config copy-files add .env
cw config copy-files add .env.local
cw config copy-files add config/local.json

# List configured files
cw config copy-files list

# Remove a file from the list
cw config copy-files remove .env
```

**Note:** Dependencies like `node_modules` and `.venv` are automatically symlinked (not copied) to save disk space.

For detailed configuration options (Happy setup, auto-updates, export/import, etc.), see **[Configuration Guide](docs/configuration.md)**.

## More Features

**Maintenance & Cleanup:** `cw clean`, `cw sync`, `cw doctor`
**Analysis:** `cw tree`, `cw stats`, `cw diff`
**Backup & Restore:** `cw backup create/restore`
**Stash Management:** `cw stash save/apply`

See **[Advanced Features Guide](docs/advanced-features.md)** for details.

## Command Reference

For the complete command reference with all options, see **[Commands Documentation](docs/commands.md)** or run:

```bash
cw --help
cw <command> --help
```

## Requirements

- **Git**: 2.31+ (for worktree support)
- **Python**: 3.11+
- **AI Tool** (optional): Claude Code, Codex, Happy, or custom

## Installation Methods

<details>
<summary>Using uv (recommended)</summary>

```bash
uv tool install claude-worktree
```
</details>

<details>
<summary>Using pip</summary>

```bash
pip install claude-worktree
```
</details>

<details>
<summary>From source</summary>

```bash
git clone https://github.com/DaveDev42/claude-worktree.git
cd claude-worktree
uv pip install -e .
```
</details>

## Troubleshooting

<details>
<summary>"Not a git repository"</summary>

Run commands from within a git repository.
</details>

<details>
<summary>"AI tool not detected"</summary>

Install your AI tool or skip AI launch:
```bash
cw config use-preset no-op
```
</details>

<details>
<summary>"Rebase failed"</summary>

Resolve conflicts manually:
```bash
cd <worktree-path>
git rebase <base-branch>
# Fix conflicts
git rebase --continue
cw pr  # or cw merge --push
```
</details>

<details>
<summary>Shell completion not working</summary>

```bash
cw --install-completion
# Restart shell
```
</details>

For more troubleshooting help, see **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**.

## Documentation

### User Guides
- **[Commands Reference](docs/commands.md)** - Complete command reference with all options
- **[Configuration Guide](docs/configuration.md)** - AI tools, presets, shell completion, export/import
- **[Advanced Features](docs/advanced-features.md)** - Backup/restore, sync, cleanup, CI/CD
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions

### Links
- **[GitHub Issues](https://github.com/DaveDev42/claude-worktree/issues)** - Report bugs or request features
- **[PyPI](https://pypi.org/project/claude-worktree/)** - Package page
- **[Changelog](https://github.com/DaveDev42/claude-worktree/releases)** - Release history

## Contributing

Contributions welcome! For development setup:

```bash
git clone https://github.com/DaveDev42/claude-worktree.git
cd claude-worktree
uv pip install -e ".[dev]"

# Run tests
uv run --extra dev pytest

# Run linting
ruff check src/ tests/
mypy src/claude_worktree
```

**For maintainers:** Use the automated release script to create new releases:

```bash
# Create a patch release (0.10.20 → 0.10.21)
uv run python scripts/release.py

# Create a minor release (0.10.20 → 0.11.0)
uv run python scripts/release.py --minor

# Create a major release (0.11.0 → 1.0.0)
uv run python scripts/release.py --major
```

**CHANGELOG management:** The changelog is automatically generated from GitHub Releases. When a release PR is merged:
1. GitHub automatically creates a Release with notes (PR-based)
2. Workflow updates `CHANGELOG.md` from Releases
3. Changes are committed to main

To manually update the changelog:
```bash
python scripts/changelog_sync.py
```

See [CLAUDE.md](CLAUDE.md) for detailed development and release workflows.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

Built with [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/) for a great CLI experience.

---

**Made for developers who love AI-assisted coding and clean git workflows** 🚀
