# TODO - claude-worktree

This document tracks planned features, enhancements, and known issues for the claude-worktree project.

## High Priority

### UX Improvements

- [x] **`cw resume [branch]`** ✅ Implemented in v0.4.0
  - Resume AI work in a worktree with context restoration
  - Optional branch argument: `cw resume fix-auth` or `cw resume` (current dir)
  - Session storage: `~/.config/claude-worktree/sessions/<branch>/`
  - Supports Claude Code, Codex, Happy, and custom AI tools
  - Flags: `--no-ai`, `--bg`, `--iterm`, `--iterm-tab`, `--tmux`

- [x] **Deprecate `cw attach`** ✅ Implemented in v0.4.0
  - Shows deprecation warning and redirects to `cw resume`
  - Backward compatible, will be removed in v2.0

- [x] **iTerm tab support** ✅ Implemented in v0.5.0
  - `--iterm-tab` flag available for `cw new`, `cw resume`, `cw attach`
  - Opens AI tool in new iTerm2 tab instead of window

- [x] **Shell function for `cw cd`** ✅ Implemented in v0.6.0
  - `cw-cd` shell function enables `cw cd <branch>` navigation
  - Supports bash, zsh, and fish shells
  - Install with `cw config install-shell-function` or manually source

### Terminology Cleanup

- [x] **Update help text** ✅ Implemented in v0.4.0
  - All user-facing text uses generic "AI tool" terminology
  - `--no-claude` deprecated in favor of `--no-ai`
  - Project description kept as "Claude Code × git worktree"

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

- [x] **Update CLAUDE.md with new features** ✅ Partially complete
  - Resume command and session management documented
  - AI tool integration documented
  - Shell function documented
- [x] **Add dog-fooding section** ✅ Implemented in v0.4.0
  - Development installation methods documented in CLAUDE.md
  - Covers uv, pipx, and pip methods with PEP 668 notes
- [ ] Create troubleshooting guide for iTerm/terminal issues
- [x] **Document shell function installation** ✅ Implemented in v0.6.0
  - CLAUDE.md includes shell function documentation
  - README should include installation instructions
- [ ] Add more examples for common workflows to README

## Testing

- [x] **Add tests for `cw resume` command** ✅ Implemented in v0.4.0
  - Context restoration with mocked session files
  - Optional branch argument behavior
  - Backward compatibility with `cw attach`
- [x] **Add tests for session manager** ✅ Implemented in v0.4.0
  - Session backup/restore logic (test_session_manager.py has 20+ tests)
  - Multi-AI tool support
  - Session file format validation
  - Special branch name handling
  - Corrupted JSON handling
- [x] **Add tests for iTerm tab functionality** ✅ Implemented in v0.5.0
  - Tests for `--iterm-tab` flag in resume and attach commands
- [x] **Add tests for shell function generation (`cw _path`)** ✅ Implemented in v0.6.0
  - Tests for internal `_path` command
  - Tests for shell function output
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
