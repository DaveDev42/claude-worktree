# Configuration Guide

Complete guide to configuring `claude-worktree`.

## Configuration File

Configuration is stored in:
```
~/.config/claude-worktree/config.json
```

## AI Tool Configuration

### Default Behavior

By default, `claude-worktree` launches Claude Code when creating or resuming worktrees.

### Changing the AI Tool

```bash
# View current configuration
cw config show

# Set a custom AI tool
cw config set ai-tool claude
cw config set ai-tool codex
cw config set ai-tool "happy --backend claude"

# Use a predefined preset
cw config use-preset claude
cw config use-preset codex
cw config use-preset happy

# List available presets
cw config list-presets

# Reset to defaults
cw config reset
```

### Available Presets

#### `claude` (default)
Claude Code - Anthropic's official AI coding assistant.

```bash
cw config use-preset claude
```

#### `codex`
OpenAI Codex integration.

```bash
cw config use-preset codex
```

#### `happy`
Happy with Claude Code - mobile-enabled wrapper for Claude.

```bash
cw config use-preset happy
```

**Requires:** `npm install -g happy-coder`

#### `happy-codex`
Happy with Codex mode and bypass permissions for faster iteration.

```bash
cw config use-preset happy-codex
```

#### `happy-yolo`
Happy with bypass all permissions (fastest, use in sandboxes).

```bash
cw config use-preset happy-yolo
```

#### `no-op`
Disable AI tool launching entirely.

```bash
cw config use-preset no-op
```

Use this when you just want worktree management without AI assistance.

### Configuration Priority

Configuration is resolved in this order:

1. **Environment variable** - `CW_AI_TOOL`
2. **Config file** - `~/.config/claude-worktree/config.json`
3. **Default** - `claude`

Example using environment variable:
```bash
CW_AI_TOOL="aider" cw new feature-name
```

### Custom AI Tools

You can use any AI coding assistant:

```bash
# Set custom command
cw config set ai-tool "my-ai-tool --option value"

# Or use environment variable for one-time override
CW_AI_TOOL="aider" cw new my-feature
```

The tool will be launched with the worktree directory as the working directory.

## Using Happy (Mobile Claude Code)

[Happy](https://github.com/slopus/happy-cli) is a mobile-enabled wrapper for Claude Code that allows you to control coding sessions from your phone.

### Installation

```bash
npm install -g happy-coder
```

### Quick Start

```bash
# Use Happy preset (Claude Code with mobile)
cw config use-preset happy

# Create worktree with Happy
cw new my-feature

# QR code will appear for mobile connection
```

### Permission Modes

Happy supports different permission modes for faster iteration:

#### Standard Mode (default)
```bash
cw config use-preset happy
```

Normal Claude Code behavior with permission prompts.

#### Codex Mode with Bypass Permissions
```bash
cw config use-preset happy-codex
```

Uses Codex backend and bypasses some permission prompts.

#### YOLO Mode - Bypass All Permissions
```bash
cw config use-preset happy-yolo
```

**⚠️ Use with caution!** Bypasses all permission prompts. Only use in sandboxed environments.

### Using Happy with Codex

```bash
# Switch to Codex mode
cw config use-preset happy-codex
cw new my-feature
```

### Advanced Happy Configuration

```bash
# Custom Happy server
export HAPPY_SERVER_URL=https://my-server.com
cw config set ai-tool "happy"

# Pass additional arguments to Claude
cw config set ai-tool "happy --claude-arg --dangerously-skip-permissions"
```

## Launch Options

Control how the AI tool is launched when creating or resuming worktrees.

### Background Launch

```bash
cw new feature --bg
cw resume feature --bg
```

Launches AI tool in background process.

### iTerm Integration (macOS)

```bash
# New iTerm window
cw new feature --iterm

# New iTerm tab
cw new feature --iterm-tab
```

**Requires:** iTerm2 on macOS

### tmux Integration

```bash
cw new feature --tmux my-session
cw resume feature --tmux my-session
```

Creates a new tmux session with the specified name.

### Skip AI Launch

To disable AI tool launch for specific commands:

```bash
# Temporarily use no-op preset
cw config use-preset no-op
cw new feature
cw config use-preset claude  # Re-enable

# Or use environment variable
CW_AI_TOOL="echo" cw new feature
```

## Worktree Path Configuration

### Default Behavior

By default, `cw new <branch>` creates worktrees at:
```
../<repo-name>-<branch-name>/
```

**Example:** If your repository is at `/Users/dave/myproject` and you run `cw new fix-auth`:
- Worktree path: `/Users/dave/myproject-fix-auth/`
- Branch name: `fix-auth`

### Custom Path

Override with `--path` option:

```bash
cw new feature --path /tmp/urgent-fix
cw new hotfix --path ~/projects/hotfix-dir
```

## Auto-Update Configuration

By default, `claude-worktree` checks for updates once per day.

### Disable Auto-Update Checks

```bash
cw config set update.auto_check false
```

### Re-enable Auto-Update Checks

```bash
cw config set update.auto_check true
```

### When to Disable

Consider disabling auto-update checks in:
- Corporate environments with restricted internet access
- Air-gapped systems
- CI/CD pipelines
- Personal preference for manual updates

### Manual Upgrade

```bash
cw upgrade
```

The `cw upgrade` command always works, even if auto-check is disabled.

## Configuration Portability

Export and import your configuration across machines.

### Export Configuration

```bash
# Export to timestamped file (cw-export-TIMESTAMP.json)
cw export

# Export to specific file
cw export -o my-worktrees.json
cw export --output backup.json
```

**Export includes:**
- Global configuration settings (AI tool, default base branch, etc.)
- Worktree metadata for all worktrees (branch names, base branches, paths, status)
- Export timestamp and repository information

### Import Configuration

```bash
# Preview import (shows what would change, default mode)
cw import my-worktrees.json

# Apply import (actually updates configuration)
cw import my-worktrees.json --apply
```

#### Preview Mode (default)

Shows what configuration changes would be applied without modifying anything:
- Configuration changes
- Worktrees that would be imported
- Warnings or conflicts

#### Apply Mode (`--apply` flag)

Actually applies the changes:
- Updates global configuration settings
- Restores worktree metadata for matching branches
- Does not automatically create worktrees (metadata only)

### Use Cases

#### Backup Your Workspace

```bash
# Export current setup
cw export -o backup-$(date +%Y%m%d).json

# Later, restore if needed
cw import backup-20250101.json --apply
```

#### Share Configuration Across Machines

```bash
# On machine 1: Export
cw export -o ~/Dropbox/cw-config.json

# On machine 2: Import
cw import ~/Dropbox/cw-config.json --apply
```

#### Team Onboarding

```bash
# Team lead exports team configuration
cw export -o team-setup.json

# New team member imports
cw import team-setup.json --apply

# Then create the actual worktrees as needed
cw new feature-branch-1
cw new feature-branch-2
```

#### Migration Workflow

```bash
# Old machine
cw export -o migration.json

# Transfer file to new machine

# New machine
cw import migration.json --apply
# Worktree metadata restored, can continue work seamlessly
```

## Shell Completion

### Installation

**Unix shells (bash/zsh/fish):**
```bash
cw --install-completion
```

**Windows PowerShell:**
```powershell
cw --install-completion powershell
```

After installation, restart your shell or source your config file.

### Supported Shells

- **bash** (Linux/macOS/WSL)
- **zsh** (Linux/macOS)
- **fish** (Linux/macOS)
- **PowerShell** (Windows 10+, PowerShell 5.1+ and PowerShell Core 7+)

### Usage

**Unix shells:**
```bash
cw <TAB>          # Shows available commands
cw new --<TAB>    # Shows available options
cw resume <TAB>   # Shows available branches
```

**Windows PowerShell:**
```powershell
cw <TAB>          # Shows available commands
cw new --<TAB>    # Shows available options
cw resume <TAB>   # Shows available branches
```

### Platform-Specific Notes

**Windows:**
- PowerShell 5.1 or later required for completion support
- PowerShell Core 7+ recommended for best experience
- Tab completion works in both PowerShell and PowerShell Core
- Command Prompt does not support tab completion

## Shell Integration (cw-cd + Tab Completion)

Install the `cw-cd` shell function and tab completion for a better shell experience.

### Quick Setup (Recommended)

```bash
cw shell-setup
```

This interactive command will:
1. Detect your current shell (bash/zsh/fish/PowerShell)
2. Install both `cw-cd` function and tab completion
3. Automatically add configuration to your shell profile
4. Provide next steps

**What it installs:**
- **cw-cd function:** Navigate between worktrees with `cw-cd <branch>`
- **Tab completion:** Autocomplete for `cw` commands, options, and branch names

### Manual Installation

**For bash/zsh:**
```bash
# Add to ~/.bashrc or ~/.zshrc
source <(cw _shell-function bash)
```

**For fish:**
```bash
# Add to ~/.config/fish/config.fish
cw _shell-function fish | source
```

**For PowerShell:**
```powershell
# Add to your PowerShell profile ($PROFILE)
cw _shell-function powershell | Invoke-Expression
```

To find your PowerShell profile location, run `$PROFILE` in PowerShell.

### Usage

**Unix shells (bash/zsh/fish):**
```bash
# Navigate to any worktree by branch name
cw-cd fix-auth
cw-cd feature-api

# Tab completion works too!
cw-cd <TAB>
```

**PowerShell:**
```powershell
# Navigate to any worktree by branch name
cw-cd fix-auth
cw-cd feature-api

# Tab completion works too!
cw-cd <TAB>
```

This changes the current directory to the worktree path.

### Platform Support

- ✅ **bash** (Linux/macOS/WSL)
- ✅ **zsh** (Linux/macOS)
- ✅ **fish** (Linux/macOS)
- ✅ **PowerShell** (Windows 10+, PowerShell 5.1+ and PowerShell Core 7+)

## Environment Variables

### `CW_AI_TOOL`

Override the AI tool for a single command.

```bash
CW_AI_TOOL="aider" cw new my-feature
CW_AI_TOOL="echo" cw new feature  # Skip AI launch
```

### `HAPPY_SERVER_URL`

Custom Happy server URL (when using Happy).

```bash
export HAPPY_SERVER_URL=https://my-server.com
```

## Configuration Examples

### Example 1: Solo Developer (Direct Merge Workflow)

```bash
# Use Claude Code (default)
cw config use-preset claude

# Enable auto-updates
cw config set update.auto_check true

# Install shell completion and navigation
cw --install-completion
echo 'source <(cw _shell-function bash)' >> ~/.bashrc
```

### Example 2: Team Developer (PR Workflow)

```bash
# Use Happy for mobile access
cw config use-preset happy

# Install shell helpers
cw --install-completion
echo 'source <(cw _shell-function bash)' >> ~/.zshrc

# Export configuration for team
cw export -o team-setup.json
```

### Example 3: CI/CD Environment

```bash
# Disable AI tool and auto-updates
export CW_AI_TOOL="echo"
cw config set update.auto_check false

# Create isolated test environment
cw new ci-test-${CI_BUILD_ID} --base ${CI_COMMIT_BRANCH}
cd ../repo-ci-test-${CI_BUILD_ID}
pytest

# Cleanup
cw delete ci-test-${CI_BUILD_ID}
```

### Example 4: Air-Gapped System

```bash
# Disable auto-update checks
cw config set update.auto_check false

# Use custom AI tool (or no-op)
cw config use-preset no-op
```

## Troubleshooting Configuration

### "AI tool not detected"

Install your preferred AI tool or skip AI launch:

```bash
cw config use-preset no-op
```

Alternatively, configure a different AI tool:

```bash
cw config set ai-tool <your-tool>
```

### Shell completion not working

1. Install completion: `cw --install-completion`
2. Restart your shell or source your config file
3. If still not working, check your shell's completion system is enabled

### Configuration not persisting

Check file permissions on `~/.config/claude-worktree/config.json`:

```bash
ls -la ~/.config/claude-worktree/config.json
```

If it doesn't exist, run any `cw config` command to create it:

```bash
cw config show
```

### Reset everything

```bash
# Reset configuration to defaults
cw config reset

# Or delete configuration file
rm ~/.config/claude-worktree/config.json
```
