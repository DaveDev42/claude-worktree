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

# Use a predefined preset
cw config use-preset claude
cw config use-preset codex
cw config use-preset claude-remote

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

#### `claude-remote`
Claude Code with remote control — works in local terminal AND accessible from phone, tablet, or browser.

```bash
cw config use-preset claude-remote
```

**Requires:** Claude Code Pro/Max plan.

#### `claude-yolo-remote`
Claude Code remote control with `--dangerously-skip-permissions`.

```bash
cw config use-preset claude-yolo-remote
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

## Using Claude Remote Control

Claude Code's remote control feature lets you use the local terminal normally while also accessing the session from any device (phone, tablet, browser).

### Quick Start

```bash
# Use remote control preset
cw config use-preset claude-remote

# Create worktree — Claude starts locally with remote control enabled
cw new my-feature

# Use /rc or scan QR code to connect from another device
```

**Requires:** Claude Code Pro/Max plan.

### With Skip Permissions

```bash
cw config use-preset claude-yolo-remote
```

**Warning:** Bypasses all permission prompts. Only use in sandboxed environments.

## Launch Options

Control how the AI tool is launched when creating or resuming worktrees using the `--term/-T` option.

### Terminal Launch Methods

The `--term` option supports multiple terminal multiplexers with short aliases:

```bash
# iTerm (macOS)
cw new feature --term i-w           # New window
cw new feature --term i-t           # New tab
cw new feature --term i-p-h         # Horizontal pane
cw new feature --term i-p-v         # Vertical pane

# tmux
cw new feature --term t             # New session (auto-named: cw-<branch>)
cw new feature --term t:mywork      # New session named "mywork"
cw new feature --term t-w           # New window in current session
cw new feature --term t-p-h         # Horizontal pane
cw new feature --term t-p-v         # Vertical pane

# Zellij
cw new feature --term z             # New session (auto-named)
cw new feature --term z:dev         # New session named "dev"
cw new feature --term z-t           # New tab in current session
cw new feature --term z-p-h         # Horizontal pane
cw new feature --term z-p-v         # Vertical pane

# WezTerm
cw new feature --term w-w           # New window
cw new feature --term w-t           # New tab
cw new feature --term w-p-h         # Horizontal pane
cw new feature --term w-p-v         # Vertical pane

# Other
cw new feature --term bg            # Background process
cw new feature --term fg            # Foreground (default)
```

**Alias pattern:**
- First letter: `i`=iTerm, `t`=tmux, `z`=Zellij, `w`=WezTerm
- Second letter: `w`=window, `t`=tab, `p`=pane
- For panes: `h`=horizontal, `v`=vertical

### Default Launch Method

Set a default launch method in config or environment:

```bash
# Via config
cw config set launch.method i-t     # Default to iTerm tab

# Via environment variable (overrides config)
CW_LAUNCH_METHOD=z cw new feature   # Use Zellij for this command
```

### Session Name Prefix

Customize the auto-generated session name prefix for tmux/Zellij:

```bash
cw config set launch.session_prefix myproject
cw new feature --term t             # Creates session: myproject-feature
```

Default prefix is `cw`.

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

## Sharing Files Between Worktrees (.cwshare)

Use a `.cwshare` file to automatically copy specific files to new worktrees.

### Overview

When you run `cw new <branch>`, files listed in `.cwshare` are copied from the main repository to the new worktree. This is useful for:

- Environment files (`.env`, `.env.local`)
- Local configuration files (`config/local.json`)
- IDE settings that shouldn't be in git

### Creating a .cwshare File

Create a `.cwshare` file in your repository root:

```
# Files to copy to new worktrees
.env
.env.local
config/local.json
```

### File Format

- One file or directory path per line
- Lines starting with `#` are comments
- Empty lines are ignored
- Paths are relative to repository root

### Example

**`.cwshare` file:**
```
# Environment files
.env
.env.local

# Local configuration
config/local.json
secrets/api-keys.json
```

**Result when running `cw new feature`:**
```
Creating worktree for branch 'feature'...
* Worktree created successfully

Copying shared files:
  ✓ Copied: .env
  ✓ Copied: .env.local
  ✓ Copied: config/local.json
  ✓ Copied: secrets/api-keys.json
```

### Notes

- Files are **copied**, not symlinked (each worktree has independent copies)
- Non-existent source files are silently skipped
- Existing files in target are not overwritten
- Directories are copied recursively
- The `.cwshare` file itself should typically be in `.gitignore`

### Why Copy Instead of Symlink?

Previous versions used symlinks for `node_modules`, `.venv`, etc. However, this caused issues with:
- pnpm's nested symlink structure
- Build tools that don't handle symlinks well
- Different dependency versions per branch

The new approach:
- Only copies files you explicitly specify
- Works reliably across all platforms and tools
- Each worktree has independent copies (no conflicts)

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
# Use Claude remote control for mobile access
cw config use-preset claude-remote

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
