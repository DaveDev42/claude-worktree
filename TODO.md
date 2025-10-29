# TODO - claude-worktree

This document tracks planned features, enhancements, and known issues for the claude-worktree project.

## High Priority

No high priority items at this time.

## Medium Priority

### Advanced Features

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

- [x] **Create troubleshooting guide** ✅ Completed in v0.9.6 (PR #21)
  - iTerm/terminal launch issues
  - Session restoration problems
  - Common git worktree errors
  - Network/PyPI connectivity for updates
  - Platform-specific issues (macOS, Linux, WSL)
  - Quick reference table for common errors
  - TROUBLESHOOTING.md: 692 lines of comprehensive solutions

- [x] **Add more workflow examples to README** ✅ Completed in v0.9.6 (PR #21)
  - Multi-feature development workflow
  - Team collaboration scenarios
  - CI/CD integration examples
  - Code review workflow
  - Hotfix workflow
  - Template usage patterns
  - Stash management across worktrees
  - 10 real-world workflow examples added

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
