# TODO - claude-worktree

This document tracks planned features, enhancements, and known issues for the claude-worktree project.

## High Priority

No high priority tasks at this time.

## Medium Priority

### AI Enhancements

- [ ] **`cw finish --ai-review`** - AI code review before merge
  - AI analyzes all changes before merging to base
  - Generates summary and suggests improvements
  - Optional: Block merge if AI finds critical issues

- [ ] **`cw new --with-context`** - Enhanced AI context
  - AI receives context about base branch when starting
  - Include recent commits, active files, project structure

## Testing Tasks

- [ ] **Add tests for refactored helper functions**
  - ✅ ~~Test `normalize_branch_name()` edge cases~~ (completed in PR #69)
  - Test `resolve_worktree_target()` with various inputs (branch name, refs/heads/branch, None, invalid)
  - Test `get_worktree_metadata()` with missing/invalid metadata

- [ ] **Add tests for AI conflict resolution workflow**
  - Mock git conflicts
  - Test AI launch with conflict context

- [ ] **Increase test coverage to >90%**
  - Current coverage: 54% (3102 statements, 1418 missing)
  - Focus on edge cases in core.py and operations modules
  - Add integration tests for common workflows

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
