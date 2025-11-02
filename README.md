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
- 🔧 **Health Monitoring**: Check worktree health, detect stale branches, and get recommendations
- 📊 **Analytics & Visualization**: View statistics, tree hierarchy, and compare branches
- 🎯 **AI-Assisted Workflows**: Get AI help with conflict resolution during merges
- 📦 **Template System**: Save and reuse worktree setups across projects
- 💾 **Smart Stash Management**: Organize stashes by worktree for easy context switching
- 🧹 **Batch Cleanup**: Clean up multiple worktrees based on merge status, age, or criteria
- ⚡ **Shell Completion**: Tab completion for bash/zsh/fish with quick navigation
- ⚙️ **Flexible Configuration**: Customize AI tool, presets, and defaults
- 📤 **Configuration Portability**: Export/import settings and metadata across machines
- 🎨 **Type-Safe**: Built with type hints and modern Python practices

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

### 3. Complete your work

Choose your workflow:

**For team/PR workflows:**
```bash
cw pr          # Create pull request, keep worktree
```

**For solo/direct merge:**
```bash
cw merge --push   # Merge and cleanup
```

The `cw pr` command creates a GitHub Pull Request and leaves the worktree for further work.

The `cw merge` command rebases, merges, cleans up the worktree, and optionally pushes with `--push`.

## Usage

### Create a new worktree

```bash
# Create from current branch
cw new feature-name

# Specify base branch
cw new fix-bug --base develop

# Custom path
cw new hotfix --path /tmp/urgent-fix

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
- `stale` (red) - Directory deleted, needs cleanup

### Show status

```bash
cw status
```

### Resume AI work in a worktree

```bash
# Resume in current worktree
cw resume

# Resume in a specific worktree
cw resume fix-auth
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

### Batch cleanup worktrees

```bash
# Delete merged worktrees
cw clean --merged

# Delete stale worktrees
cw clean --stale

# Delete worktrees older than 30 days
cw clean --older-than 30

# Interactive selection
cw clean -i

# Preview what would be deleted
cw clean --merged --dry-run
```

Use `--dry-run` to preview which worktrees would be deleted before actually removing them.

### Synchronize with base branch

```bash
# Sync current worktree
cw sync

# Sync specific worktree
cw sync fix-auth

# Sync all worktrees
cw sync --all

# Only fetch, don't rebase
cw sync --fetch-only

# Get AI help with rebase conflicts
cw sync --ai-merge
```

Fetches latest changes and rebases your feature branch onto the updated base branch. Useful for long-running features. Use `--ai-merge` to get AI assistance when rebase conflicts occur.

### Change base branch

```bash
# Change base branch for current worktree
cw change-base master

# Change base for specific worktree
cw change-base develop -t fix-auth

# Interactive rebase
cw change-base main -i

# Preview changes
cw change-base master --dry-run
```

Use this when you realize after creating a worktree that you should have based it on a different branch. The command will rebase your feature branch onto the new base and update the metadata.

### Health check

```bash
cw doctor
```

Performs comprehensive health checks:
- Git version compatibility (minimum 2.31.0)
- Worktree accessibility (detects stale worktrees)
- Uncommitted changes detection
- Worktrees behind base branch
- Existing merge conflicts
- Cleanup recommendations

### Compare branches

```bash
# Full diff between branches
cw diff main feature-api

# Show diff statistics only
cw diff main feature-api --summary

# Show changed files list
cw diff main feature-api --files
```

### Visualize worktree hierarchy

```bash
cw tree
```

Displays an ASCII tree showing:
- Base repository at the root
- Feature worktrees as branches
- Status indicators (clean, modified, stale)
- Current worktree highlighting

### View statistics

```bash
cw stats
```

Shows comprehensive analytics:
- Total worktrees count and status distribution
- Age statistics (average, oldest, newest)
- Commit activity across worktrees
- Top 5 oldest worktrees
- Top 5 most active worktrees by commit count

### Template management

```bash
# Create template from current directory
cw template create my-python-setup

# Create with description
cw template create my-setup . -d "My project template"

# List all templates
cw template list

# Show template details
cw template show my-setup

# Apply template to current directory
cw template apply my-setup

# Apply to specific path
cw template apply my-setup ../feature

# Delete template
cw template delete my-setup
```

Templates help you reuse common worktree setups across projects.

### Stash management

```bash
# Save changes in current worktree
cw stash save
cw stash save "work in progress"

# List all stashes (organized by worktree)
cw stash list

# Apply stash to different worktree
cw stash apply fix-auth
cw stash apply feature-api --stash stash@{1}
```

Worktree-aware stashing makes it easy to move changes between worktrees.

### Completing Your Work

**claude-worktree** supports two workflows for completing your feature work:

#### Pull Request Workflow (Recommended for Teams)

Create a GitHub Pull Request without merging locally:

```bash
# Create PR from current worktree
cw pr

# Create PR with custom title and body
cw pr --title "Add authentication" --body "Implements user login"

# Create draft PR
cw pr --draft

# Create PR without pushing (for testing)
cw pr --no-push

# Create PR from specific worktree
cw pr fix-auth
```

The `cw pr` command:
1. Rebases your feature onto the base branch
2. Pushes to remote
3. Creates a GitHub Pull Request using `gh` CLI
4. **Leaves the worktree intact** for further work

After the PR is merged on GitHub, clean up with:
```bash
cw delete fix-auth
```

**Requires**: GitHub CLI (`gh`) - https://cli.github.com/

#### Direct Merge Workflow (For Solo Development)

Merge directly to the base branch and clean up:

```bash
# Merge current worktree
cw merge

# Merge and push to remote
cw merge --push

# Interactive mode with confirmations
cw merge -i

# Preview merge without executing
cw merge --dry-run

# Merge specific worktree from anywhere
cw merge fix-auth --push
```

The `cw merge` command:
1. Rebases your feature onto the base branch
2. Fast-forward merges into the base branch
3. Removes the worktree
4. Deletes the feature branch
5. Optionally pushes to remote with `--push`

## Command Reference

### Core Commands

| Command | Description |
|---------|-------------|
| `cw new <name>` | Create new worktree with specified branch name |
| `cw pr [branch]` | Create GitHub Pull Request (leaves worktree intact) |
| `cw merge [branch]` | Merge to base branch and cleanup worktree |
| `cw resume [branch]` | Resume AI work in worktree with context restoration |
| `cw list` | List all worktrees with status |
| `cw status` | Show current worktree metadata |
| `cw delete <target>` | Delete worktree by branch name or path |

### Maintenance & Cleanup

| Command | Description |
|---------|-------------|
| `cw clean --merged` | Delete worktrees for merged branches |
| `cw clean --stale` | Delete worktrees with stale status |
| `cw clean --older-than <days>` | Delete worktrees older than N days |
| `cw clean -i` | Interactive cleanup with selection UI |
| `cw sync [branch]` | Sync worktree(s) with base branch |
| `cw sync --all` | Sync all worktrees |
| `cw change-base <new-base>` | Change base branch and rebase |
| `cw doctor` | Health check and diagnostics |

### Analysis & Visualization

| Command | Description |
|---------|-------------|
| `cw tree` | Display worktree hierarchy in tree format |
| `cw stats` | Show usage analytics and statistics |
| `cw diff <branch1> <branch2>` | Compare two branches |
| `cw diff <branch1> <branch2> --summary` | Show diff statistics only |
| `cw diff <branch1> <branch2> --files` | Show changed files list |

### Template Management

| Command | Description |
|---------|-------------|
| `cw template create <name> [path]` | Create template from directory |
| `cw template list` | List all available templates |
| `cw template show <name>` | Show template details |
| `cw template apply <name> [path]` | Apply template to directory |
| `cw template delete <name>` | Delete template |

### Stash Management

| Command | Description |
|---------|-------------|
| `cw stash save [message]` | Save changes with worktree prefix |
| `cw stash list` | List stashes organized by worktree |
| `cw stash apply <branch>` | Apply stash to different worktree |

### Configuration & Portability

| Command | Description |
|---------|-------------|
| `cw config show` | Show current configuration |
| `cw config set <key> <value>` | Set configuration value |
| `cw config use-preset <name>` | Use AI tool preset |
| `cw config list-presets` | List available presets |
| `cw config reset` | Reset to defaults |
| `cw export [-o <file>]` | Export configuration and worktree metadata |
| `cw import <file> [--apply]` | Import configuration from file |
| `cw upgrade` | Upgrade to latest version |

### Navigation

| Command | Description |
|---------|-------------|
| `cw cd <branch>` | Print worktree path (or use `cw-cd` shell function) |
| `cw _shell-function <shell>` | Output shell function for sourcing |

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

## Shell Function for Quick Navigation

Install the `cw-cd` shell function to quickly navigate between worktrees:

```bash
# For bash/zsh
source <(cw _shell-function bash)

# For fish
cw _shell-function fish | source

# Add to your shell config for permanent installation
echo 'source <(cw _shell-function bash)' >> ~/.bashrc  # or ~/.zshrc
```

Usage:
```bash
# Navigate to any worktree by branch name
cw-cd fix-auth
cw-cd feature-api

# Tab completion works too!
cw-cd <TAB>
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
cw config use-preset claude         # Claude Code (default)
cw config use-preset codex          # OpenAI Codex
cw config use-preset happy          # Happy with Claude Code
cw config use-preset happy-codex    # Happy with Codex mode
cw config use-preset happy-yolo     # Happy with bypass all permissions
cw config use-preset no-op          # Disable AI tool launch

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

#### Permission Modes

Happy supports different permission modes for faster iteration:

```bash
# Standard mode (default)
cw config use-preset happy

# Codex mode with bypass permissions
cw config use-preset happy-codex

# YOLO mode - bypass all permissions (fastest, use in sandboxes)
cw config use-preset happy-yolo
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

Control how the AI tool is launched when creating or resuming worktrees:

- `--bg`: Launch in background
- `--iterm`: Launch in new iTerm window (macOS only)
- `--iterm-tab`: Launch in new iTerm tab (macOS only)
- `--tmux <name>`: Launch in new tmux session

To skip AI tool launch entirely, use the `no-op` preset:
```bash
cw config use-preset no-op
```

### Auto-Update Settings

By default, `claude-worktree` checks for updates once per day. You can configure this behavior:

```bash
# Disable automatic update checks
cw config set update.auto_check false

# Re-enable automatic update checks
cw config set update.auto_check true

# Manual upgrade always works regardless of setting
cw upgrade
```

**When to disable auto-check:**
- Corporate environments with restricted internet
- Air-gapped systems
- CI/CD pipelines
- Personal preference for manual updates

**Note:** The `cw upgrade` command always works, even if auto-check is disabled.

### Configuration Portability

Export and import your worktree configuration and metadata to share setups across machines or backup your workspace.

#### Export Configuration

```bash
# Export to timestamped file (cw-export-TIMESTAMP.json)
cw export

# Export to specific file
cw export -o my-worktrees.json
cw export --output backup.json
```

The export file contains:
- Global configuration settings (AI tool, default base branch, etc.)
- Worktree metadata for all worktrees (branch names, base branches, paths, status)
- Export timestamp and repository information

#### Import Configuration

```bash
# Preview import (shows what would change, default mode)
cw import my-worktrees.json

# Apply import (actually updates configuration)
cw import my-worktrees.json --apply
```

**Preview mode** (default):
- Shows what configuration changes would be applied
- Lists worktrees that would be imported
- Shows any warnings or conflicts
- Does not modify anything

**Apply mode** (`--apply` flag):
- Updates global configuration settings
- Restores worktree metadata for matching branches
- Does not automatically create worktrees (metadata only)

#### Use Cases

**Backup your workspace:**
```bash
# Export current setup
cw export -o backup-$(date +%Y%m%d).json

# Later, restore if needed
cw import backup-20250101.json --apply
```

**Share configuration across machines:**
```bash
# On machine 1: Export
cw export -o ~/Dropbox/cw-config.json

# On machine 2: Import
cw import ~/Dropbox/cw-config.json --apply
```

**Team onboarding:**
```bash
# Team lead exports team configuration
cw export -o team-setup.json

# New team member imports
cw import team-setup.json --apply
# Then create the actual worktrees as needed
cw new feature-branch-1
cw new feature-branch-2
```

**Migration workflow:**
```bash
# Old machine
cw export -o migration.json

# Transfer file to new machine
# New machine
cw import migration.json --apply
# Worktree metadata restored, can continue work seamlessly
```

### Backup & Restore

Create backups of your worktrees with full git history and uncommitted changes, then restore them later or on different machines.

#### Create Backups

```bash
# Backup current worktree
cw backup create

# Backup specific worktree by branch name
cw backup create fix-auth

# Backup all worktrees
cw backup create --all

# Custom backup location
cw backup create -o ~/my-backups
cw backup create --output /external/drive/backups
```

Backups include:
- Complete git bundle with full history
- Uncommitted changes (as patch files)
- Worktree metadata (branch, base branch, paths)
- Timestamp for organization

Default backup location: `~/.config/claude-worktree/backups/`

#### List Backups

```bash
# List all backups
cw backup list

# List backups for specific branch
cw backup list fix-auth
```

Output shows:
- Branch name
- Backup timestamp
- Creation date/time
- Indicator for uncommitted changes

#### Restore from Backup

```bash
# Restore latest backup for a branch
cw backup restore fix-auth

# Restore specific backup by timestamp
cw backup restore fix-auth --id 20250129-143052

# Restore to custom path
cw backup restore fix-auth --path /tmp/my-restore
```

Restore process:
1. Clones from git bundle (full history restored)
2. Checks out the branch
3. Restores worktree metadata
4. Applies uncommitted changes if they exist

#### Backup & Restore Use Cases

**Before risky operations:**
```bash
# Backup before major refactoring
cw backup create my-feature
# ... make changes ...
# If something goes wrong:
cw backup restore my-feature
```

**Archive completed work:**
```bash
# Backup before cleanup
cw backup create old-feature
cw merge old-feature --push
# Can restore later if needed
```

**Transfer work between machines:**
```bash
# Machine 1
cw backup create feature-x -o ~/Dropbox/backups

# Machine 2
cp ~/Dropbox/backups/feature-x/20250129-143052 ~/.config/claude-worktree/backups/
cw backup restore feature-x
```

**Disaster recovery:**
```bash
# Regular backup schedule
cw backup create --all  # Backup all worktrees

# After disk failure or accidental deletion
cw backup list
cw backup restore important-feature --id 20250128-120000
```

**Experimentation with safety net:**
```bash
# Backup stable state
cw backup create experiment

# Try risky changes
# ... changes didn't work out ...

# Restore to stable state
cw delete experiment
cw backup restore experiment
```

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

This allows the `pr` and `merge` commands to know:
1. Which branch to rebase onto
2. Where the main repository is located
3. How to safely perform the merge

## Workflow Examples

### Basic Feature Development

The most common workflow for developing a single feature:

```bash
# 1. Create feature worktree
cw new add-user-auth

# 2. Work in the worktree (AI tool launches automatically)
# Make changes, commit as needed...

# 3. Complete your work

# For PR-based workflow (recommended for teams):
cw pr                    # Create pull request
# After PR merged on GitHub:
cw delete add-user-auth  # Clean up worktree

# For direct merge workflow (solo development):
cw merge --push          # Merge and cleanup in one step
```

### Multi-Feature Parallel Development

Work on multiple features simultaneously without branch switching:

```bash
# Start three features in parallel
cw new feature-api
cw new fix-bug-123
cw new refactor-db

# Check status of all worktrees
cw list
cw tree

# Navigate between features
cw-cd feature-api    # Jump to feature-api worktree
cw-cd fix-bug-123    # Jump to bug fix worktree

# Resume AI work in specific feature
cw resume refactor-db

# Complete features as they're done (choose your workflow)
cw pr feature-api        # Create PR
cw pr fix-bug-123        # Create PR
# Or for direct merge:
cw merge feature-api --push
cw merge fix-bug-123 --push
```

### Team Collaboration Workflow

Collaborate with team members using shared remote branches:

```bash
# Create feature and push to remote
cw new team-feature
git push -u origin team-feature

# Team member pulls your worktree
cw new team-feature --base origin/team-feature

# Sync with latest changes from team
cw sync team-feature

# Or sync all your worktrees
cw sync --all

# Review changes before merging
cw diff main team-feature --summary

# Create PR for team review
cw pr team-feature --title "Implement team feature"

# Or preview merge locally
cw merge team-feature --dry-run
cw merge team-feature --push
```

### Long-Running Feature Branch

Maintain a long-lived feature branch while keeping it up-to-date:

```bash
# Start feature from develop branch
cw new big-refactor --base develop

# Work for a few days...
# Meanwhile, develop branch gets updates

# Stay synchronized with develop
cw sync big-refactor

# Or fetch without rebasing
cw sync big-refactor --fetch-only

# Check if you're behind
cw doctor

# Review changes before finishing
cw diff develop big-refactor --files

# Create PR or merge with interactive confirmation
cw pr big-refactor --draft
# Or for direct merge:
cw merge big-refactor -i --push  # Interactive mode
```

### Hotfix Workflow

Quickly create and deploy an urgent hotfix:

```bash
# Create hotfix from production branch
cw new hotfix-security --base production

# Make fix and test
# ...

# Merge to production (direct merge for hotfixes)
cw merge hotfix-security --push

# Also apply to main/develop
git checkout main
git cherry-pick hotfix-security
git push
```

### Experimentation & Clean Cleanup

Try experimental features and easily clean up:

```bash
# Create experimental worktrees
cw new experiment-approach-a
cw new experiment-approach-b
cw new experiment-approach-c

# After testing, keep only what works
cw delete experiment-approach-a
cw delete experiment-approach-b
cw merge experiment-approach-c --push  # Keep the winner

# Or use batch cleanup
cw clean --merged           # Remove already-merged features
cw clean --older-than 7     # Remove week-old experiments
cw clean --stale            # Remove deleted directories
```

### Using Templates for Consistency

Create and apply templates for common project setups:

```bash
# Create a template from current worktree
cd myproject-feature
cw template create python-api -d "Python API with tests"

# Apply template to new worktrees
cw new another-feature
cw template apply python-api

# Share templates across projects
cw template list
cw template show python-api
```

### Stash Management Across Worktrees

Move work-in-progress between worktrees:

```bash
# Working on feature-a, need to switch to urgent bug fix
cd myproject-feature-a
cw stash save "Half-done refactoring"

# Work on bug fix
cw resume fix-urgent-bug
# Fix bug...
cw merge fix-urgent-bug --push

# Return to original work
cw resume feature-a
cw stash list  # See all stashes by worktree
cw stash apply feature-a
```

### CI/CD Integration

Use `claude-worktree` in continuous integration pipelines:

```bash
# In CI pipeline script
# Disable AI tool and auto-updates
export CW_AI_TOOL="echo"  # No-op AI tool
cw config set update.auto_check false

# Create isolated test environment
cw new ci-test-${CI_BUILD_ID} --base ${CI_COMMIT_BRANCH}

# Run tests in worktree
cd ../repo-ci-test-${CI_BUILD_ID}
pytest

# Cleanup
cw delete ci-test-${CI_BUILD_ID}
```

### Code Review Workflow

Review pull requests in isolated worktrees:

```bash
# Fetch PR branch
git fetch origin pull/123/head:pr-123

# Create worktree for review
cw new review-pr-123 --base pr-123

# Review and test changes
cw diff main review-pr-123 --summary
cw diff main review-pr-123 --files

# Run tests in isolated environment
cd ../myproject-review-pr-123
npm test

# Clean up after review
cw delete review-pr-123
```

## Troubleshooting

For detailed troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

### Quick Solutions

### "Not a git repository"

Make sure you're running commands from within a git repository.

### "AI tool not detected"

Install your preferred AI coding assistant:
- **Claude Code**: https://claude.ai/download
- **Codex**: Follow OpenAI's installation instructions
- **Happy**: npm install -g happy-coder

Or skip AI tool launch with the no-op preset:
```bash
cw config use-preset no-op
```

Alternatively, configure a different AI tool:
```bash
cw config set ai-tool <your-tool>
```

### "Rebase failed"

Conflicts were detected during rebase. Resolve them manually:

```bash
cd <worktree-path>
git rebase origin/<base-branch>
# Resolve conflicts
git rebase --continue

# Then complete your work:
cw pr              # Create PR, or
cw merge --push    # Direct merge
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
- **Troubleshooting**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions
- **Issues**: https://github.com/DaveDev42/claude-worktree/issues
- **PyPI**: https://pypi.org/project/claude-worktree/
- **Changelog**: See GitHub Releases

---

Made with ❤️ for developers who love Claude Code and clean git workflows
