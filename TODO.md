# TODO - claude-worktree

This document tracks planned features, enhancements, and known issues for the claude-worktree project.

## High Priority

### Bug Fixes & Corrections

- [x] **Fix `happy-yolo` preset command** ✅ Completed in v0.9.0
  - **Was**: `happy --permission-mode bypassPermissions` (incorrect)
  - **Now**: `happy --yolo` (sugar syntax for `--dangerously-skip-permissions`)
  - Updated `AI_TOOL_PRESETS` in `config.py:33`
  - The `--yolo` flag is the proper way to bypass all permissions in Happy

- [x] **Fix shell function installation documentation** ✅ Completed in v0.9.0
  - **Incorrect docs claimed**: `cw config install-shell-function`
  - **Command does not exist**
  - **Correct method**: `source <(cw _shell-function bash)` for bash/zsh, or `cw _shell-function fish | source` for fish
  - Updated CHANGELOG.md with correct installation instructions
  - Internal command exists: `cw _shell-function <shell>` (hidden command in cli.py:417-470)
  - Consider: Implementing `cw config install-shell-function` as a user-friendly wrapper (future enhancement)

### Documentation Sync Issues

- [x] **Update README.md - Remove deprecated features** ✅ Completed in v0.9.0
  - Removed `--no-ai` flag documentation
    - Replacement: `cw config use-preset no-op`
  - Removed `cw attach` command documentation
    - Replacement: `cw resume`
  - Updated command reference table to reflect current CLI
  - Added missing `--iterm-tab` flag documentation

- [x] **Update preset documentation across all files** ✅ Completed in v0.9.0
  - **Removed incorrect presets**: `happy-sonnet`, `happy-opus`, `happy-haiku`
  - **Documented actual presets**: `no-op`, `claude`, `codex`, `happy`, `happy-codex`, `happy-yolo`
  - Updated files:
    - README.md
    - CLAUDE.md
    - CHANGELOG.md

- [x] **Update CLAUDE.md "In Progress" section** ✅ Completed in v0.9.0
  - Moved `cw-cd` shell function from "In Progress" to "Completed" features
  - Feature was implemented in v0.6.0 as `cw-cd` shell function
  - Moved AI session context restoration to "Completed" (v0.4.0)

### UX Improvements

- [x] **`cw resume [branch]`** ✅ Implemented in v0.4.0
  - Resume AI work in a worktree with context restoration
  - Optional branch argument: `cw resume fix-auth` or `cw resume` (current dir)
  - Session storage: `~/.config/claude-worktree/sessions/<branch>/`
  - Supports Claude Code, Codex, Happy, and custom AI tools
  - Flags: `--bg`, `--iterm`, `--iterm-tab`, `--tmux`

- [x] **Remove `cw attach` command** ✅ Completed in v0.8.0
  - Command was deprecated in v0.4.0 and fully removed in v0.8.0
  - Use `cw resume` instead for better context management

- [x] **iTerm tab support** ✅ Implemented in v0.5.0
  - `--iterm-tab` flag available for `cw new` and `cw resume`
  - Opens AI tool in new iTerm2 tab instead of window

- [x] **Shell function for `cw-cd`** ✅ Implemented in v0.6.0
  - `cw-cd <branch>` shell function enables quick navigation to worktrees
  - Supports bash, zsh, and fish shells
  - Implementation: `src/claude_worktree/shell_functions/cw.bash` and `cw.fish`
  - Installation: `source <(cw _shell-function bash)` or `cw _shell-function fish | source`
  - **Enhancement needed**: Add `cw cd <branch>` CLI command for better discoverability
    - Command would print the worktree path and guide users to install shell function
    - Alternative: Wrapper that attempts to change directory with helpful error message

- [x] **Terminology cleanup** ✅ Completed in v0.7.0
  - All user-facing text uses generic "AI tool" terminology
  - `--no-claude` and `--no-ai` flags removed in v0.7.0
  - Use preset-based configuration instead: `cw config use-preset no-op`
  - Project description kept as "Claude Code × git worktree"

### Update Management

- [x] **Automatic update check** ✅ Implemented in v0.8.0
  - Daily automatic update check on first `cw` command execution (local timezone)
  - Checks PyPI for new versions silently in background
  - Prompts user to upgrade if new version is available
  - Cache stored in `~/.cache/claude-worktree/update_check.json`
  - Manual upgrade available via `cw upgrade` command
  - Implementation: `cli.py:99` calls `check_for_updates(auto=True)`

- [x] **Configurable auto-update behavior** ✅ Implemented in v0.9.0
  - Added `update.auto_check` config option (default: `true`)
  - `cw config set update.auto_check false` - Disable automatic update checks
  - `cw config set update.auto_check true` - Enable automatic update checks
  - Setting persists across sessions in `~/.config/claude-worktree/config.json`
  - Updated `DEFAULT_CONFIG` in `config.py`
  - Manual `cw upgrade` always works regardless of auto-check setting
  - Use case: Corporate environments, air-gapped systems, or users who prefer manual updates

### AI Integration

- [ ] **AI-assisted conflict resolution** - Automatically offer AI help when rebase conflicts occur
  - Add `--ai-merge` flag to `cw finish` for automatic AI conflict resolution
  - Interactive prompt when conflicts detected: "Would you like AI to help resolve conflicts?"
  - Launch AI tool with context about conflicted files and resolution steps

## Medium Priority

### Worktree Management

- [ ] **`cw cd <branch>` CLI command** - Improve worktree navigation discoverability
  - **Problem**: `cw-cd` is only a shell function, not discoverable via `cw --help`
  - **Solution 1**: Add `cw cd <branch>` command that:
    - Prints the worktree path: `/path/to/repo-branch`
    - Provides helpful message: "To navigate directly, install shell function: `source <(cw _shell-function bash)`"
    - Optionally: `cw cd <branch> --print` outputs path only (for scripting)
  - **Solution 2**: Make it a wrapper command that:
    - Attempts to create a subshell in the target directory
    - Or exports a variable that shell prompt can use
  - **Recommended approach**: Implement both CLI command (for path printing) and keep shell function (for actual cd)
  - **Benefits**: Better UX, discoverable in help text, works in scripts
  - Implementation: Add new command in `cli.py`, reuse existing `_path` logic

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

- [ ] **`cw finish --interactive` (or `-i`)** - Step-by-step merge confirmation
  - Short form: `cw finish -i`
  - Pause at each step for user confirmation
  - Allow abort at any stage
  - Interactive prompts for each phase: rebase, merge, cleanup, push

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

## Documentation Tasks

- [x] **Fix shell function installation docs** ✅ Completed in v0.9.0
  - Updated README.md with correct installation method
  - Added examples for bash, zsh, and fish
  - Consider adding `cw config install-shell-function` command for better UX (future enhancement)

- [x] **Remove deprecated feature documentation from README.md** ✅ Completed in v0.9.0
  - Removed `--no-ai` flag references
  - Removed `cw attach` command documentation
  - Updated all examples to use current syntax

- [x] **Update preset documentation** ✅ Completed in v0.9.0
  - Listed correct presets: `no-op`, `claude`, `codex`, `happy`, `happy-codex`, `happy-yolo`
  - Documented what each preset does in README.md
  - Updated CLAUDE.md and CHANGELOG.md with accurate preset information

- [ ] **Create troubleshooting guide**
  - iTerm/terminal launch issues
  - Session restoration problems
  - Common git worktree errors
  - Network/PyPI connectivity for updates

- [ ] **Add more workflow examples to README**
  - Multi-feature development workflow
  - Team collaboration scenarios
  - CI/CD integration examples

## Testing Tasks

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

- [ ] **Add tests for auto-update functionality**
  - Test daily check logic
  - Test version comparison
  - Test installer detection
  - Mock PyPI responses

- [ ] **Add tests for AI conflict resolution workflow**
  - Mock git conflicts
  - Test AI launch with conflict context

- [ ] **Add tests for `cw sync` command** (when implemented)

- [ ] **Add tests for `cw clean` command** (when implemented)

- [ ] **Increase test coverage to >90%**

## Known Issues

All high-priority issues from v0.9.0 have been resolved:
- ✅ Shell function installation documentation - Fixed in v0.9.0
- ✅ `happy-yolo` preset - Fixed in v0.9.0
- ✅ README.md deprecated features - Fixed in v0.9.0
- ✅ Preset documentation - Fixed in v0.9.0

No currently known issues.

---

## Contributing

When adding new items to this TODO:
1. Choose appropriate priority level (High/Medium/Low)
2. Provide clear description of the feature or fix
3. Include implementation details, file locations, and use cases when relevant
4. Add related testing requirements to Testing section
5. Mark items as complete with ✅ and version number when implemented
6. Move known issues to "Known Issues" section until resolved
