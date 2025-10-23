# Claude Worktree

> Seamlessly integrate git worktree with Claude Code for streamlined feature development workflows

[![Tests](https://github.com/DaveDev42/claude-worktree/workflows/Tests/badge.svg)](https://github.com/DaveDev42/claude-worktree/actions)
[![PyPI version](https://badge.fury.io/py/claude-worktree.svg)](https://pypi.org/project/claude-worktree/)
[![Python versions](https://img.shields.io/pypi/pyversions/claude-worktree.svg)](https://pypi.org/project/claude-worktree/)
[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

## What is Claude Worktree?

**claude-worktree** (or `cw` for short) is a CLI tool that makes it effortless to work on multiple git branches simultaneously using git worktrees, with automatic AI coding assistant integration. No more branch switching, stashing changes, or losing context—each feature gets its own directory and AI session.

Works with Claude Code, Codex, Happy, and any custom AI tool.

### Key Features

- 🌳 **Easy Worktree Management**: Create isolated directories for each feature branch
- 🤖 **Multi-AI Support**: Works with Claude Code, Codex, Happy, and custom AI tools
- 🔄 **Clean Merge Workflow**: Rebase, merge, and cleanup with a single command
- 📦 **Simple Naming**: Use clean branch names without timestamp clutter
- ⚙️ **Flexible Configuration**: Customize AI tool, presets, and defaults
- ⚡ **Shell Completion**: Tab completion for bash/zsh/fish
- 🎯 **Type-Safe**: Built with type hints and modern Python practices

## Installation

### Using uv (recommended)

```bash
uv tool install claude-worktree
```

### Using pip

```bash
pip install claude-worktree
```

### From source

```bash
git clone https://github.com/DaveDev42/claude-worktree.git
cd claude-worktree
uv pip install -e .
```

## Quick Start

### 1. Create a new feature worktree

```bash
cw new fix-auth
```

This will:
- Create a new branch named `fix-auth`
- Create a worktree at `../myproject-fix-auth/`
- Launch Claude Code in that directory

### 2. Work on your feature

Make changes, commit them, and test your code in the isolated worktree.

### 3. Finish and merge

```bash
cw finish --push
```

This will:
- Rebase your feature onto the base branch
- Fast-forward merge into the base branch
- Clean up the worktree and feature branch
- Optionally push to remote with `--push`

## Usage

### Create a new worktree

```bash
# Create from current branch
cw new feature-name

# Specify base branch
cw new fix-bug --base develop

# Custom path
cw new hotfix --path /tmp/urgent-fix

# Skip AI tool launch
cw new refactor --no-ai

# Launch Claude in iTerm (macOS)
cw new feature --iterm

# Launch Claude in tmux
cw new feature --tmux my-session
```

### List worktrees

```bash
cw list
```

Output:
```
Worktrees for repository: /Users/dave/myproject

BRANCH                              STATUS     PATH
refs/heads/main                     clean      .
refs/heads/fix-auth                 active     ../myproject-fix-auth
refs/heads/feature-api              modified   ../myproject-feature-api
```

**Status Types:**
- `active` (bold green) - Currently in this worktree directory
- `clean` (green) - No uncommitted changes
- `modified` (yellow) - Has uncommitted changes
- `stale` (red) - Directory deleted, needs `cw prune`

### Show status

```bash
cw status
```

### Reattach Claude Code

```bash
cw attach
```

### Delete a worktree

```bash
# Delete by branch name
cw delete fix-auth

# Delete by path
cw delete ../myproject-old-feature

# Keep branch, only remove worktree
cw delete feature --keep-branch

# Also delete remote branch
cw delete feature --delete-remote
```

### Prune stale worktrees

```bash
cw prune
```

Removes administrative data for worktrees with "stale" status (directories that have been manually deleted).

## Command Reference

| Command | Description |
|---------|-------------|
| `cw new <name>` | Create new worktree with specified branch name |
| `cw finish` | Rebase, merge, and cleanup current worktree |
| `cw attach` | Reattach AI tool to current worktree |
| `cw list` | List all worktrees |
| `cw status` | Show current worktree status |
| `cw delete <target>` | Delete worktree by branch name or path |
| `cw prune` | Prune stale worktree data |
| `cw config show` | Show current configuration |
| `cw config set <key> <value>` | Set configuration value |
| `cw config use-preset <name>` | Use a predefined AI tool preset |
| `cw config list-presets` | List available presets |
| `cw config reset` | Reset configuration to defaults |
| `cw upgrade` | Upgrade to the latest version |

## Shell Completion

Enable shell completion for better productivity:

```bash
# Install completion for your shell
cw --install-completion

# Restart your shell or source your config
```

Now you can use tab completion:
```bash
cw <TAB>          # Shows available commands
cw new --<TAB>    # Shows available options
```

## Configuration

### AI Tool Configuration

By default, `claude-worktree` launches Claude Code, but you can configure it to work with other AI coding assistants like Codex or Happy:

```bash
# Show current configuration
cw config show

# Set a custom AI tool
cw config set ai-tool claude
cw config set ai-tool codex
cw config set ai-tool "happy --backend claude"

# Use a predefined preset
cw config use-preset claude
cw config use-preset codex
cw config use-preset happy
cw config use-preset happy-codex
cw config use-preset happy-sonnet
cw config use-preset happy-opus
cw config use-preset happy-haiku

# List available presets
cw config list-presets

# Reset to defaults
cw config reset
```

Configuration is stored in `~/.config/claude-worktree/config.json`.

#### Configuration Priority

1. Environment variable (`CW_AI_TOOL`)
2. Config file (`~/.config/claude-worktree/config.json`)
3. Default (`claude`)

Example using environment variable:
```bash
CW_AI_TOOL="aider" cw new feature-name
```

### Using Happy (Mobile Claude Code)

[Happy](https://github.com/slopus/happy-cli) is a mobile-enabled wrapper for Claude Code that allows you to control coding sessions from your phone.

#### Installation

```bash
npm install -g happy-coder
```

#### Quick Start

```bash
# Use Happy preset (Claude Code with mobile)
cw config use-preset happy

# Create worktree with Happy
cw new my-feature

# QR code will appear for mobile connection
```

#### Model Selection

```bash
# Use specific Claude model
cw config use-preset happy-opus
cw new my-feature

# Or customize directly
cw config set ai-tool "happy -m sonnet"
```

#### Using Happy with Codex

```bash
# Switch to Codex mode
cw config use-preset happy-codex
cw new my-feature
```

#### Advanced Configuration

```bash
# Custom Happy server
export HAPPY_SERVER_URL=https://my-server.com
cw config set ai-tool "happy"

# Pass additional arguments to Claude
cw config set ai-tool "happy --claude-arg --dangerously-skip-permissions"
```

### Custom AI Tools

You can use any AI coding assistant by setting a custom command:

```bash
# Set custom command
cw config set ai-tool "my-ai-tool --option value"

# Or use environment variable for one-time override
CW_AI_TOOL="aider" cw new my-feature
```

### Default Worktree Path

By default, `cw new <branch>` creates worktrees at:
```
../<repo-name>-<branch-name>/
```

For example, if your repository is at `/Users/dave/myproject` and you run `cw new fix-auth`:
- Worktree path: `/Users/dave/myproject-fix-auth/`
- Branch name: `fix-auth` (no timestamp)

### Launch Options

- `--no-ai`: Skip launching AI tool (deprecated: `--no-claude`)
- `--bg`: Launch in background
- `--iterm`: Launch in new iTerm window (macOS only)
- `--tmux <name>`: Launch in new tmux session

## Requirements

- **Git**: Version 2.31 or higher
- **Python**: 3.11 or higher
- **AI Tool** (optional): Claude Code, Codex, Happy, or any custom AI coding assistant

## How It Works

### Metadata Storage

`claude-worktree` stores metadata in git config:

```bash
# Stores base branch for feature branches
git config branch.<feature>.worktreeBase <base>

# Stores path to main repository
git config worktree.<feature>.basePath <path>
```

This allows the `finish` command to know:
1. Which branch to rebase onto
2. Where the main repository is located
3. How to safely perform the merge

### Workflow Example

1. **Start**: You're on `main` branch in `/Users/dave/myproject`
2. **Create**: Run `cw new fix-auth`
   - Creates branch `fix-auth` from `main`
   - Creates worktree at `/Users/dave/myproject-fix-auth/`
   - Launches your configured AI tool (Claude Code by default)
3. **Work**: Make changes and commit in the worktree
4. **Finish**: Run `cw finish --push`
   - Rebases `fix-auth` onto `main`
   - Merges into `main` with fast-forward
   - Removes worktree and branch
   - Pushes to `origin/main`

## Troubleshooting

### "Not a git repository"

Make sure you're running commands from within a git repository.

### "AI tool not detected"

Install your preferred AI coding assistant:
- **Claude Code**: https://claude.ai/download
- **Codex**: Follow OpenAI's installation instructions
- **Happy**: Check Happy's documentation

Or use `--no-ai` flag to skip AI tool launch.

Alternatively, configure a different AI tool:
```bash
cw config set ai-tool <your-tool>
```

### "Rebase failed"

Conflicts were detected during rebase. The tool automatically aborts the rebase. Resolve conflicts manually:

```bash
cd <worktree-path>
git rebase origin/<base-branch>
# Resolve conflicts
git rebase --continue
# Then run: cw finish
```

### Shell completion not working

1. Install completion: `cw --install-completion`
2. Restart your shell or source your config file
3. If still not working, check your shell's completion system is enabled

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/DaveDev42/claude-worktree.git
cd claude-worktree

# Install development dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check src/ tests/

# Run type checking
mypy src/claude_worktree
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by git worktree workflows
- Built with [Typer](https://typer.tiangolo.com/) for the CLI
- Uses [Rich](https://rich.readthedocs.io/) for beautiful terminal output

## Links

- **Documentation**: See [CLAUDE.md](CLAUDE.md) for detailed project information
- **Issues**: https://github.com/DaveDev42/claude-worktree/issues
- **PyPI**: https://pypi.org/project/claude-worktree/
- **Changelog**: See GitHub Releases

---

Made with ❤️ for developers who love Claude Code and clean git workflows
