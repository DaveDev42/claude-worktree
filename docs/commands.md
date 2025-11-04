# Command Reference

Complete reference for all `claude-worktree` commands.

## Worktree Management

### `cw new <name>`

Create a new worktree with the specified branch name.

```bash
# Create from current branch
cw new feature-name

# Specify base branch
cw new fix-bug --base develop

# Custom path
cw new hotfix --path /tmp/urgent-fix

# Launch options
cw new feature --iterm              # Launch in iTerm window (macOS)
cw new feature --iterm-tab          # Launch in iTerm tab (macOS)
cw new feature --tmux my-session    # Launch in tmux session
cw new feature --bg                 # Launch in background
```

**Options:**
- `--base <branch>` - Base branch to branch from (default: current branch)
- `--path <path>` - Custom worktree path (default: `../<repo>-<branch>/`)
- `--iterm` - Launch AI tool in new iTerm window (macOS only)
- `--iterm-tab` - Launch AI tool in new iTerm tab (macOS only)
- `--tmux <name>` - Launch AI tool in new tmux session
- `--bg` - Launch AI tool in background

### `cw list`

List all worktrees with their status.

```bash
cw list
```

**Status indicators:**
- `active` (bold green) - Currently in this worktree directory
- `clean` (green) - No uncommitted changes
- `modified` (yellow) - Has uncommitted changes
- `stale` (red) - Directory deleted, needs `cw prune`

### `cw status`

Show metadata for the current worktree.

```bash
cw status
```

### `cw resume [branch]`

Resume AI work in a worktree with context restoration.

```bash
# Resume in current worktree
cw resume

# Resume in specific worktree
cw resume fix-auth

# Launch options (same as `cw new`)
cw resume --iterm
cw resume --iterm-tab
cw resume --tmux my-session
cw resume --bg
```

### `cw delete <target>`

Remove a worktree by branch name or path.

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

**Options:**
- `--keep-branch` - Don't delete the git branch, only remove worktree
- `--delete-remote` - Also delete the branch from remote repository

### `cw prune`

Remove administrative data for stale worktrees (directories that have been manually deleted).

```bash
cw prune
```

## Completion Workflows

### `cw pr [branch]`

Create a GitHub Pull Request (recommended for team workflows).

```bash
# Create PR from current worktree
cw pr

# Create PR from specific worktree
cw pr fix-auth

# Custom title and body
cw pr --title "Add authentication" --body "Implements user login"

# Create draft PR
cw pr --draft

# Don't push to remote (for testing)
cw pr --no-push
```

**What it does:**
1. Rebases feature branch onto base branch
2. Pushes to remote
3. Creates PR using GitHub CLI (`gh`)
4. Leaves worktree intact for further work

**Requirements:** GitHub CLI (`gh`) - https://cli.github.com/

**Options:**
- `--title <title>` - PR title (default: branch name)
- `--body <body>` - PR description
- `--draft` - Create as draft PR
- `--no-push` - Don't push to remote (for testing)

### `cw merge [branch]`

Merge feature branch to base branch and cleanup (recommended for solo development).

```bash
# Merge current worktree
cw merge

# Merge specific worktree
cw merge fix-auth

# Merge and push to remote
cw merge --push

# Interactive mode with confirmations
cw merge -i

# Preview without executing
cw merge --dry-run
```

**What it does:**
1. Rebases feature branch onto base branch
2. Fast-forward merges into base branch
3. Removes the worktree
4. Deletes the feature branch
5. Optionally pushes to remote with `--push`

**Options:**
- `--push` - Push to remote after merging
- `-i, --interactive` - Show confirmations before each step
- `--dry-run` - Preview what would happen without executing

### `cw finish [branch]` (deprecated)

**⚠️ DEPRECATED** - Use `cw pr` or `cw merge` instead.

Still functional for backward compatibility but shows deprecation warning.

## Maintenance & Cleanup

### `cw clean`

Batch cleanup of worktrees based on various criteria.

```bash
# Delete merged worktrees
cw clean --merged

# Delete stale worktrees
cw clean --stale

# Delete worktrees older than N days
cw clean --older-than 30

# Interactive selection
cw clean -i

# Preview without executing
cw clean --merged --dry-run

# Combine criteria
cw clean --merged --older-than 7
```

**Options:**
- `--merged` - Delete worktrees for branches merged to base
- `--stale` - Delete worktrees with stale status (deleted directories)
- `--older-than <days>` - Delete worktrees older than N days
- `-i, --interactive` - Interactive selection UI
- `--dry-run` - Preview what would be deleted

### `cw sync [branch]`

Synchronize worktree(s) with base branch.

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

**What it does:**
1. Fetches latest changes from remote
2. Rebases feature branch onto updated base branch

**Options:**
- `--all` - Sync all worktrees
- `--fetch-only` - Only fetch updates, don't rebase
- `--ai-merge` - Get AI assistance when rebase conflicts occur

### `cw change-base <new-base>`

Change the base branch for a worktree and rebase onto it.

```bash
# Change base for current worktree
cw change-base master

# Change base for specific worktree
cw change-base develop -t fix-auth

# Interactive rebase
cw change-base main -i

# Preview changes
cw change-base master --dry-run
```

**Use case:** When you realize after creating a worktree that you should have based it on a different branch.

**Options:**
- `-t, --target <branch>` - Target worktree branch (default: current)
- `-i, --interactive` - Interactive rebase
- `--dry-run` - Preview without executing

### `cw doctor`

Run comprehensive health checks on all worktrees.

```bash
cw doctor
```

**Checks:**
- Git version compatibility (minimum 2.31.0)
- Worktree accessibility (detects stale worktrees)
- Uncommitted changes detection
- Worktrees behind base branch
- Existing merge conflicts
- Cleanup recommendations

## Analysis & Visualization

### `cw tree`

Display worktree hierarchy in tree format.

```bash
cw tree
```

Shows:
- Base repository at root
- Feature worktrees as branches
- Status indicators (clean, modified, stale)
- Current worktree highlighting

### `cw stats`

Show usage analytics and statistics.

```bash
cw stats
```

Displays:
- Total worktrees count and status distribution
- Age statistics (average, oldest, newest)
- Commit activity across worktrees
- Top 5 oldest worktrees
- Top 5 most active worktrees by commit count

### `cw diff <branch1> <branch2>`

Compare two branches.

```bash
# Full diff
cw diff main feature-api

# Show statistics only
cw diff main feature-api --summary

# Show changed files list
cw diff main feature-api --files
```

**Options:**
- `--summary` - Show diff statistics only
- `--files` - Show changed files list only

## Stash Management

### `cw stash save [message]`

Save changes in current worktree with worktree prefix.

```bash
cw stash save
cw stash save "work in progress"
```

### `cw stash list`

List all stashes, organized by worktree.

```bash
cw stash list
```

### `cw stash apply <branch>`

Apply a stash to a different worktree.

```bash
# Apply latest stash for branch
cw stash apply fix-auth

# Apply specific stash
cw stash apply feature-api --stash stash@{1}
```

**Options:**
- `--stash <ref>` - Specific stash reference (default: latest for branch)

## Backup & Restore

### `cw backup create [branch]`

Create backup of worktree with full git history.

```bash
# Backup current worktree
cw backup create

# Backup specific worktree
cw backup create fix-auth

# Backup all worktrees
cw backup create --all

# Custom backup location
cw backup create -o ~/my-backups
cw backup create --output /external/drive/backups
```

**What's included:**
- Complete git bundle with full history
- Uncommitted changes (as patch files)
- Worktree metadata (branch, base branch, paths)
- Timestamp

**Options:**
- `--all` - Backup all worktrees
- `-o, --output <path>` - Custom backup location (default: `~/.config/claude-worktree/backups/`)

### `cw backup list [branch]`

List all backups.

```bash
# List all backups
cw backup list

# List backups for specific branch
cw backup list fix-auth
```

### `cw backup restore <branch>`

Restore worktree from backup.

```bash
# Restore latest backup for branch
cw backup restore fix-auth

# Restore specific backup by timestamp
cw backup restore fix-auth --id 20250129-143052

# Restore to custom path
cw backup restore fix-auth --path /tmp/my-restore
```

**Options:**
- `--id <timestamp>` - Specific backup timestamp (default: latest)
- `--path <path>` - Custom restore path (default: standard worktree path)

## Configuration

### `cw config show`

Display current configuration.

```bash
cw config show
```

### `cw config set <key> <value>`

Set configuration value.

```bash
cw config set ai-tool claude
cw config set update.auto_check false
```

**Available keys:**
- `ai-tool` - AI tool command to launch
- `update.auto_check` - Enable/disable automatic update checks (true/false)

### `cw config use-preset <name>`

Use a predefined AI tool preset.

```bash
cw config use-preset claude         # Claude Code (default)
cw config use-preset codex          # OpenAI Codex
cw config use-preset happy          # Happy with Claude Code
cw config use-preset happy-codex    # Happy with Codex mode
cw config use-preset happy-yolo     # Happy with bypass all permissions
cw config use-preset no-op          # Disable AI tool launch
```

### `cw config list-presets`

List all available presets.

```bash
cw config list-presets
```

### `cw config reset`

Reset configuration to defaults.

```bash
cw config reset
```

## Configuration Portability

### `cw export`

Export configuration and worktree metadata.

```bash
# Export to timestamped file
cw export

# Export to specific file
cw export -o my-worktrees.json
cw export --output backup.json
```

**Export includes:**
- Global configuration settings
- Worktree metadata for all worktrees
- Export timestamp and repository info

### `cw import <file>`

Import configuration from file.

```bash
# Preview import (default - shows what would change)
cw import my-worktrees.json

# Apply import (actually updates configuration)
cw import my-worktrees.json --apply
```

**Options:**
- `--apply` - Actually apply changes (default is preview mode)

## Upgrade

### `cw upgrade`

Upgrade to the latest version.

```bash
cw upgrade
```

Automatically detects installation method (uv or pip) and upgrades appropriately.

## Navigation

### `cw cd <branch>`

Print the path to a worktree (for scripting).

```bash
cd $(cw cd fix-auth)
```

**Better alternative:** Use the `cw-cd` shell function instead:

```bash
# Install shell function (add to shell config)
source <(cw _shell-function bash)   # bash/zsh
cw _shell-function fish | source    # fish

# Then use:
cw-cd fix-auth                      # Directly navigate
```

### `cw _shell-function <shell>`

Output shell function for sourcing.

```bash
cw _shell-function bash    # For bash/zsh
cw _shell-function fish    # For fish
```

## Shell Completion

### Install completion

```bash
cw --install-completion
```

After installation, restart your shell or source your config file.

### Usage

```bash
cw <TAB>          # Shows available commands
cw new --<TAB>    # Shows available options
cw resume <TAB>   # Shows available branches
```
