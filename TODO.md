# TODO - claude-worktree

This document tracks planned features, enhancements, and known issues for the claude-worktree project.

## High Priority

No high priority items at this time.

## Medium Priority

### Advanced Features

- [x] **Configuration portability** - Share setups across machines ✅ Completed in v0.9.8 (PR #23)
  - `cw export` - Export all worktree metadata and config
  - `cw import <file>` - Import worktree setup on another machine
  - Use case: Team collaboration, multiple development machines
  - 13 comprehensive tests added
  - Documentation added to README with use cases

- [x] **Backup & restore** - Worktree state preservation ✅ Completed in v0.10.0 (PR #24)
  - `cw backup create [branch]` - Create backup of current or specific worktree
  - `cw backup create --all` - Backup all worktrees
  - `cw backup list [branch]` - List available backups
  - `cw backup restore <branch>` - Restore from latest backup
  - `cw backup restore <branch> --id <timestamp>` - Restore from specific backup
  - Implementation: Git bundles with full history + uncommitted changes as patches
  - Storage: `~/.config/claude-worktree/backups/<branch>/<timestamp>/`
  - 15 comprehensive tests added
  - Documentation added to README with 5 use cases

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
