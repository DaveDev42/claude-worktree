# TODO - claude-worktree

This document tracks planned features, enhancements, and known issues for the claude-worktree project.

## High Priority

### AI Integration

- [ ] **AI-assisted conflict resolution** - Automatically offer AI help when rebase conflicts occur
  - Add `--ai-merge` flag to `cw finish` for automatic AI conflict resolution
  - Interactive prompt when conflicts detected: "Would you like AI to help resolve conflicts?"
  - Launch AI tool with context about conflicted files and resolution steps

## Medium Priority

### Worktree Management

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

- [ ] **Add tests for AI conflict resolution workflow**
  - Mock git conflicts
  - Test AI launch with conflict context

- [ ] **Increase test coverage to >90%**

## Known Issues

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
