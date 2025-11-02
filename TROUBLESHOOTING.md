# Troubleshooting Guide

This guide helps you resolve common issues you might encounter while using `claude-worktree`.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Git Related Issues](#git-related-issues)
- [AI Tool Launch Issues](#ai-tool-launch-issues)
- [Terminal & iTerm Issues](#terminal--iterm-issues)
- [Session Restoration Problems](#session-restoration-problems)
- [Worktree Management Issues](#worktree-management-issues)
- [Network & Update Issues](#network--update-issues)
- [Platform-Specific Issues](#platform-specific-issues)

---

## Installation Issues

### `command not found: cw`

**Problem**: After installing, the `cw` command is not recognized.

**Solutions**:

1. **Check installation method**:
   ```bash
   # If installed with uv
   uv tool list  # Should show claude-worktree

   # If installed with pip
   pip list | grep claude-worktree
   ```

2. **Ensure the binary is in your PATH**:
   ```bash
   # For uv tool install
   echo $PATH | grep -o "[^:]*\.local/bin"

   # Add to PATH if needed (add to ~/.bashrc or ~/.zshrc)
   export PATH="$HOME/.local/bin:$PATH"
   ```

3. **Reinstall**:
   ```bash
   # Using uv (recommended)
   uv tool install --force claude-worktree

   # Using pip
   pip install --force-reinstall claude-worktree
   ```

### Python version incompatibility

**Problem**: Installation fails with Python version error.

**Solution**: `claude-worktree` requires Python 3.11 or higher.

```bash
# Check Python version
python3 --version

# Install Python 3.11+ if needed (using uv)
uv python install 3.11

# Or use pyenv
pyenv install 3.11
pyenv global 3.11
```

---

## Git Related Issues

### "Not a git repository"

**Problem**: Commands fail with "Not a git repository" error.

**Solution**:
```bash
# Make sure you're in a git repository
git status

# If not initialized, initialize git
git init
git add .
git commit -m "Initial commit"
```

### "Git version too old"

**Problem**: `cw doctor` reports Git version is too old.

**Solution**: Upgrade to Git 2.31.0 or higher.

```bash
# Check current version
git --version

# macOS (using Homebrew)
brew install git
brew link --overwrite git

# Ubuntu/Debian
sudo add-apt-repository ppa:git-core/ppa
sudo apt update
sudo apt install git

# Verify upgrade
git --version
```

### Rebase conflicts during `cw finish`

**Problem**: Conflicts detected during rebase.

**Solutions**:

**Option 1: AI-Assisted Resolution (Recommended)**
```bash
cw finish --ai-merge
```
Your configured AI tool will launch to help resolve conflicts.

**Option 2: Manual Resolution**
```bash
# The tool automatically aborts the rebase
# Navigate to the worktree
cd <worktree-path>

# Start rebase manually
git rebase origin/<base-branch>

# Resolve conflicts in your editor
# Then continue
git add .
git rebase --continue

# After successful rebase, finish the merge
cw finish
```

**Option 3: Preview Before Finishing**
```bash
# Use dry-run to see what will happen
cw finish --dry-run

# Use interactive mode for step-by-step control
cw finish -i
```

### Cannot delete worktree: "has uncommitted changes"

**Problem**: Deletion fails due to uncommitted changes.

**Solutions**:

```bash
# Option 1: Stash changes
cw stash save "work in progress"
cw delete <branch>

# Option 2: Force delete (use with caution)
cd <worktree-path>
git reset --hard
cw delete <branch>

# Option 3: Commit changes first
cd <worktree-path>
git add .
git commit -m "Save progress"
cw delete <branch> --keep-branch  # Keep branch, delete worktree only
```

---

## AI Tool Launch Issues

### "AI tool not detected" or "Command not found"

**Problem**: `cw` cannot find your AI coding assistant.

**Solutions**:

1. **Check if AI tool is installed**:
   ```bash
   # For Claude Code
   which claude

   # For Codex
   which codex

   # For Happy
   which happy
   ```

2. **Install the AI tool**:
   ```bash
   # Claude Code
   # Download from https://claude.ai/download

   # Happy (mobile Claude Code)
   npm install -g happy-coder

   # Verify installation
   claude --version
   happy --version
   ```

3. **Configure `cw` to use your AI tool**:
   ```bash
   # Check current configuration
   cw config show

   # Set AI tool explicitly
   cw config set ai-tool claude
   cw config set ai-tool happy

   # Or use a preset
   cw config use-preset claude
   cw config use-preset happy
   ```

4. **Disable AI tool launch temporarily**:
   ```bash
   # Use no-op preset to skip AI tool launch
   cw config use-preset no-op

   # Now create worktree without launching AI
   cw new my-feature
   ```

5. **Use environment variable override**:
   ```bash
   # Temporarily use a different AI tool
   CW_AI_TOOL="aider" cw new my-feature
   ```

### AI tool launches but immediately exits

**Problem**: AI tool starts but closes right away.

**Possible causes and solutions**:

1. **Shell initialization issues**:
   ```bash
   # Check your shell config files for errors
   # .bashrc, .zshrc, .bash_profile, etc.

   # Test your shell config
   bash -l -c "echo test"
   zsh -l -c "echo test"
   ```

2. **Working directory issues**:
   ```bash
   # Make sure worktree directory exists and is accessible
   ls -la <worktree-path>
   cd <worktree-path>
   pwd
   ```

3. **AI tool configuration issues**:
   ```bash
   # Test AI tool directly
   cd <worktree-path>
   claude  # or your AI tool command
   ```

---

## Terminal & iTerm Issues

### `--iterm` option not working

**Problem**: `cw new --iterm` or `cw resume --iterm` fails.

**Solutions**:

1. **Verify you're on macOS**:
   ```bash
   uname -s  # Should output "Darwin"
   ```
   The `--iterm` option only works on macOS.

2. **Check iTerm2 is installed and running**:
   ```bash
   # iTerm2 must be installed
   ls /Applications/iTerm.app

   # iTerm2 must be running
   ps aux | grep iTerm
   ```

3. **Try `--iterm-tab` instead**:
   ```bash
   # Opens in new tab instead of new window
   cw new my-feature --iterm-tab
   ```

4. **Fallback to default behavior**:
   ```bash
   # Launch in current terminal
   cw new my-feature
   ```

### iTerm window opens but command doesn't execute

**Problem**: iTerm window opens but AI tool doesn't start.

**Solution**:

1. **Check iTerm shell integration**:
   - iTerm2 > Preferences > Profiles > General
   - Command: Should be "Login shell" or your shell path

2. **Verify shell PATH**:
   ```bash
   # Add to ~/.zshrc or ~/.bashrc
   export PATH="/usr/local/bin:$HOME/.local/bin:$PATH"
   ```

3. **Test manual launch**:
   ```bash
   # Create worktree without AI launch
   cw config use-preset no-op
   cw new test-feature

   # Manually launch AI in iTerm
   cd ../myproject-test-feature
   claude
   ```

### `--tmux` option issues

**Problem**: tmux session creation fails.

**Solutions**:

1. **Check tmux is installed**:
   ```bash
   which tmux
   tmux -V

   # Install if needed
   brew install tmux  # macOS
   sudo apt install tmux  # Ubuntu/Debian
   ```

2. **Check tmux is running**:
   ```bash
   # List tmux sessions
   tmux ls

   # If server not started
   tmux new-session -d -s test
   tmux ls
   ```

3. **Use different session name**:
   ```bash
   # Avoid conflicts with existing sessions
   cw new my-feature --tmux my-unique-session
   ```

---

## Session Restoration Problems

### "No previous session found" when resuming

**Problem**: `cw resume` can't find session even though you worked in the worktree before.

**Explanation**: Sessions are created when you use `cw resume` or `cw new`, not automatically.

**Solutions**:

1. **Check if session exists**:
   ```bash
   # Session data is stored here
   ls ~/.config/claude-worktree/sessions/

   # Check specific branch
   ls ~/.config/claude-worktree/sessions/<branch-name>/
   ```

2. **Resume creates session for next time**:
   ```bash
   # First resume - creates session
   cw resume my-feature

   # Future resumes - restores session
   cw resume my-feature
   ```

3. **Manually save context**:
   ```bash
   # Session context is not automatically captured
   # Use your AI tool's session persistence if available
   ```

### Session metadata corrupted

**Problem**: `cw resume` fails with JSON parse error.

**Solution**:

```bash
# Check session metadata
cat ~/.config/claude-worktree/sessions/<branch>/metadata.json

# If corrupted, delete and recreate
rm -rf ~/.config/claude-worktree/sessions/<branch>/
cw resume <branch>  # Creates fresh session
```

### Old sessions taking up space

**Problem**: Many old session directories consuming disk space.

**Solution**:

```bash
# View session storage
du -sh ~/.config/claude-worktree/sessions/

# Clean up sessions for deleted branches
cd ~/.config/claude-worktree/sessions/
ls

# Remove specific session
rm -rf ~/.config/claude-worktree/sessions/<old-branch>/

# Or clean all sessions (use with caution)
rm -rf ~/.config/claude-worktree/sessions/*
```

---

## Worktree Management Issues

### Stale worktrees appearing in `cw list`

**Problem**: `cw list` shows worktrees that no longer exist.

**Solution**:

```bash
# Remove stale administrative data
cw prune

# Or use git directly
git worktree prune
```

### Cannot create worktree: "path already exists"

**Problem**: Path conflict when creating worktree.

**Solutions**:

```bash
# Option 1: Use different path
cw new my-feature --path /tmp/my-feature

# Option 2: Remove existing directory
rm -rf ../myproject-my-feature
cw new my-feature

# Option 3: Use different branch name
cw new my-feature-v2
```

### `cw-cd` shell function not working

**Problem**: `cw-cd <branch>` command not found.

**Solution**:

1. **Install the shell function**:
   ```bash
   # For bash/zsh (add to ~/.bashrc or ~/.zshrc)
   source <(cw _shell-function bash)

   # For fish (add to ~/.config/fish/config.fish)
   cw _shell-function fish | source
   ```

2. **Reload shell**:
   ```bash
   # bash
   source ~/.bashrc

   # zsh
   source ~/.zshrc

   # fish
   source ~/.config/fish/config.fish

   # Or restart terminal
   ```

3. **Verify installation**:
   ```bash
   # Should show the function
   type cw-cd

   # Test it
   cw-cd <branch-name>
   ```

### Worktree has uncommitted changes, cannot clean

**Problem**: `cw clean --merged` skips worktrees with changes.

**Solution**:

```bash
# Use stash to save changes
cw stash save "WIP before cleanup"

# Now clean
cw clean --merged

# Restore changes if needed
cw stash list
cw stash apply <branch>
```

---

## Network & Update Issues

### Auto-update check fails or times out

**Problem**: `cw` hangs or shows network errors during startup.

**Solutions**:

1. **Disable auto-update checks**:
   ```bash
   cw config set update.auto_check false
   ```

2. **Check network connectivity**:
   ```bash
   # Test PyPI connectivity
   curl -I https://pypi.org/pypi/claude-worktree/json
   ```

3. **Behind corporate proxy**:
   ```bash
   # Set proxy environment variables
   export HTTP_PROXY=http://proxy.company.com:8080
   export HTTPS_PROXY=http://proxy.company.com:8080

   # Retry
   cw upgrade
   ```

4. **Manual upgrade**:
   ```bash
   # Even with auto-check disabled, manual upgrade works
   cw upgrade
   ```

### Cannot upgrade: "Permission denied"

**Problem**: `cw upgrade` fails with permission error.

**Solutions**:

```bash
# If installed with pip (user install)
pip install --upgrade --user claude-worktree

# If installed with uv
uv tool upgrade claude-worktree

# If installed system-wide (requires sudo)
sudo pip install --upgrade claude-worktree
```

---

## Platform-Specific Issues

### macOS: "Operation not permitted"

**Problem**: Git operations fail with permission errors on macOS.

**Solution**:

1. **Grant Terminal/iTerm Full Disk Access**:
   - System Preferences > Security & Privacy > Privacy
   - Full Disk Access
   - Add Terminal.app and/or iTerm.app

2. **Check Gatekeeper**:
   ```bash
   # If git or other tools are blocked
   xattr -d com.apple.quarantine /path/to/command
   ```

### Linux: Shell completion not working

**Problem**: Tab completion doesn't work after installation.

**Solution**:

```bash
# Install completion
cw --install-completion

# Reload shell
exec $SHELL

# For bash, ensure bash-completion is installed
sudo apt install bash-completion  # Ubuntu/Debian
sudo yum install bash-completion  # RHEL/CentOS

# Add to ~/.bashrc if needed
[ -f /etc/bash_completion ] && . /etc/bash_completion
```

### Windows/WSL: Path issues

**Problem**: Worktrees created with Windows-style paths.

**Solution**:

```bash
# Ensure you're using WSL paths
cd /mnt/c/Users/...  # Wrong (Windows path)
cd ~/projects/...    # Correct (WSL path)

# Configure git to use Unix paths
git config --global core.autocrlf input
```

---

## Getting More Help

If you're still experiencing issues:

1. **Run health check**:
   ```bash
   cw doctor
   ```

2. **Check verbose output**:
   ```bash
   # Most commands show detailed output by default
   cw list
   cw status
   ```

3. **Report an issue**:
   - GitHub Issues: https://github.com/DaveDev42/claude-worktree/issues
   - Include:
     - `cw --version` output
     - `git --version` output
     - Operating system and version
     - Full error message
     - Steps to reproduce

4. **Check documentation**:
   - README: https://github.com/DaveDev42/claude-worktree/blob/main/README.md
   - Commands Reference: https://github.com/DaveDev42/claude-worktree/blob/main/docs/commands.md
   - Configuration Guide: https://github.com/DaveDev42/claude-worktree/blob/main/docs/configuration.md
   - Advanced Features: https://github.com/DaveDev42/claude-worktree/blob/main/docs/advanced-features.md

---

## Common Error Messages

### Quick Reference

| Error Message | Likely Cause | Quick Fix |
|--------------|--------------|-----------|
| `Not a git repository` | Not in git repo | Run `git init` |
| `Branch not found` | Typo in branch name | Check with `git branch` |
| `Worktree already exists` | Path conflict | Use different path or delete existing |
| `Cannot delete main repository` | Trying to delete base repo | Only delete feature worktrees |
| `AI tool not found` | AI tool not installed/configured | Run `cw config use-preset no-op` or install AI tool |
| `Rebase failed` | Merge conflicts | Use `cw finish --ai-merge` or resolve manually |
| `--iterm option only works on macOS` | Wrong platform | Remove `--iterm` flag or use macOS |
| `No worktree found` | Branch doesn't exist | Check `cw list` |

---

**Last Updated**: 2025-10-27
**Version**: 0.9.5+
