# TODO - claude-worktree

This document tracks planned features, enhancements, and known issues for the claude-worktree project.

## High Priority

### UX Improvements

- [ ] **`cw resume [branch]`** - Resume AI work in a worktree with context restoration
  - Replaces `cw attach` with better semantics and context management
  - Optional branch argument: `cw resume fix-auth` or `cw resume` (current dir)
  - **Context restoration**: Restore previous AI session history for seamless work continuation
  - Session storage: `~/.config/claude-worktree/sessions/<branch>/`
  - Support Claude Code, Codex, Happy (pluggable architecture)
  - Flags: `--no-ai`, `--bg`, `--iterm`, `--iterm-tab`, `--tmux`
  - Implementation phases:
    1. Investigate Claude Code CLI session management
    2. Build session backup/restore system
    3. Implement `cw resume` command
    4. Add multi-AI tool support

- [ ] **Deprecate `cw attach`** - Migrate users to `cw resume`
  - Show deprecation warning: "Warning: 'cw attach' is deprecated and will be removed in v2.0. Use 'cw resume' instead."
  - Internally calls `resume_worktree()` for backward compatibility
  - Update all documentation to reference `cw resume`
  - Remove in next major version (v2.0)

- [ ] **iTerm tab support** - Add `--iterm-tab` flag to open AI tool in a new iTerm tab instead of a new window
  - Applies to: `cw new`, `cw resume`
  - Related: `--iterm` currently opens new windows

- [ ] **Shell function for `cw cd`** - Enable direct directory navigation to worktrees
  - Implement `cw _cd <branch>` internal command (outputs worktree path)
  - Add `cw install-shell-function` command to install shell wrapper
  - Support bash, zsh, and fish shells
  - Usage: `cw cd <branch>` changes to the worktree directory
  - Lower priority: can manually `cd` for now

### Terminology Cleanup

- [ ] **Update help text** - Replace "Claude" references with "AI tool" in user-facing strings
  - Update function docstrings in core.py
  - Keep backward compatibility for `--no-claude` flag (already deprecated)
  - Keep project description "Claude Code × git worktree" as-is

### AI Integration

- [ ] **AI-assisted conflict resolution** - Automatically offer AI help when rebase conflicts occur
  - Add `--ai-merge` flag to `cw finish` for automatic AI conflict resolution
  - Interactive prompt when conflicts detected: "Would you like AI to help resolve conflicts?"
  - Launch AI tool with context about conflicted files and resolution steps

## Medium Priority

### Worktree Management

- [ ] **`cw sync`** - Synchronize worktrees with base branch changes
  - `cw sync [branch]` - Rebase specified or current worktree onto base
  - `cw sync --all` - Rebase all worktrees
  - `cw sync --fetch-only` - Fetch updates without rebasing
  - Use case: Long-running feature branches that need periodic base branch updates

- [ ] **`cw clean`** - Batch cleanup of worktrees
  - `cw clean --merged` - Delete worktrees for branches already merged to base
  - `cw clean --stale` - Delete worktrees with "stale" status
  - `cw clean --older-than <days>` - Delete worktrees older than N days
  - `cw clean --interactive` - Interactive selection UI
  - Use case: Periodic cleanup of accumulated worktrees

### Safety & Preview

- [ ] **`cw finish --dry-run`** - Preview merge without executing
  - Show what would happen: rebase steps, merge result, cleanup actions
  - Detect potential conflicts before starting

- [ ] **`cw finish --interactive`** - Step-by-step merge confirmation
  - Pause at each step for user confirmation
  - Allow abort at any stage

- [ ] **`cw doctor`** - Health check for all worktrees
  - Check Git version compatibility
  - Verify all worktrees are accessible
  - Report uncommitted changes
  - Detect worktrees behind base branch
  - Identify existing merge conflicts
  - Show recommendations for cleanup

### Cross-worktree Operations

- [ ] **`cw diff <branch1> <branch2>`** - Compare worktrees
  - Show diff between two feature branches
  - `--summary` flag for stats only
  - `--files` flag to list changed files only

- [ ] **`cw stash`** - Worktree-aware stash management
  - `cw stash save` - Stash changes in current worktree
  - `cw stash apply <branch>` - Apply stash to different worktree
  - `cw stash list` - List stashes organized by worktree

## Low Priority / Future Enhancements

### Visualization

- [ ] **`cw tree`** - Visual worktree hierarchy
  - ASCII tree showing base repo and all feature worktrees
  - Show branch names, status indicators, and paths
  - Highlight current/active worktree

- [ ] **`cw stats`** - Usage analytics
  - Total worktrees count
  - Active development time per worktree
  - Most frequently used worktrees
  - Average time to finish (creation → merge)

### Advanced Features

- [ ] **Worktree templates** - Reusable worktree configurations
  - `cw template create <name>` - Save current setup as template
  - `cw new <branch> --template <name>` - Create worktree from template
  - Templates can include: git hooks, IDE settings, env files
  - Store templates in `~/.config/claude-worktree/templates/`

- [ ] **Git hook integration** - Automated workflow helpers
  - `cw hooks install` - Install claude-worktree-specific hooks
  - pre-commit: Check if AI tool is running
  - post-checkout: Auto-attach AI tool
  - pre-push: Remind to run `cw finish` if appropriate

- [ ] **AI session management** - Control AI tool lifecycle
  - `cw ai start [branch]` - Start AI in specified worktree
  - `cw ai stop [branch]` - Stop AI session
  - `cw ai restart [branch]` - Restart AI session
  - `cw ai logs [branch]` - View AI session logs

- [ ] **Configuration portability** - Share setups across machines
  - `cw export` - Export all worktree metadata and config
  - `cw import <file>` - Import worktree setup on another machine
  - Use case: Team collaboration, multiple development machines

- [ ] **Backup & restore** - Worktree state preservation
  - `cw backup [branch]` - Create backup of worktree state
  - `cw backup --all` - Backup all worktrees
  - `cw restore <branch> <backup-id>` - Restore from backup
  - Implementation: Git bundles or tar archives

### AI Enhancements

- [ ] **`cw finish --ai-review`** - AI code review before merge
  - AI analyzes all changes before merging to base
  - Generates summary and suggests improvements
  - Optional: Block merge if AI finds critical issues

- [ ] **`cw new --with-context`** - Enhanced AI context
  - AI receives context about base branch when starting
  - Include recent commits, active files, project structure

## Documentation

- [ ] Update CLAUDE.md with new features as they're implemented
- [ ] Add dog-fooding section to README/CLAUDE.md
  - Document `pip install -e .` for development
  - Add development workflow best practices
- [ ] Create troubleshooting guide for iTerm/terminal issues
- [ ] Document shell function installation and setup
- [ ] Add examples for common workflows

## Testing

- [ ] Add tests for `cw resume` command
  - Test context restoration with mocked session files
  - Test optional branch argument behavior
  - Test backward compatibility with `cw attach`
- [ ] Add tests for session manager
  - Session backup/restore logic
  - Multi-AI tool support
  - Session file format validation
- [ ] Add tests for iTerm tab functionality
- [ ] Add tests for shell function generation (`cw _cd`)
- [ ] Add tests for AI conflict resolution workflow
- [ ] Add tests for `cw sync` command
- [ ] Add tests for `cw clean` command
- [ ] Increase test coverage to >90%

## Known Issues

_No known issues at this time_

---

## Contributing

When adding new items to this TODO:
1. Choose appropriate priority level
2. Provide clear description of the feature
3. Include use case or rationale when relevant
4. Add related testing requirements to Testing section
