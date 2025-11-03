# TODO - claude-worktree

This document tracks planned features, enhancements, and known issues for the claude-worktree project.

## High Priority

### Code Quality & Refactoring

- [x] **Fix default AI tool configuration** ✅ v0.10.15 (PR #66)
  - ~~Current: `"command": "claude-yolo"` (uses dangerous permissions by default)~~
  - Solution: Changed default from `claude-yolo` to `claude` (safer default)
  - File: `src/claude_worktree/config.py`
  - Impact: New users now have safer defaults
  - Merged: 2025-11-03

## Medium Priority

### Code Quality & Refactoring (Critical Improvements)

- [x] **Extract duplicated worktree resolution logic** ✅ v0.10.15 (PR #68)
  - ~~Problem: Same 30-40 line pattern repeated in 7+ functions~~
  - Solution: Created `resolve_worktree_target(target: str | None) -> tuple[Path, str, Path]` helper
  - Impact: Reduced 82 lines of duplicated code, improved maintainability
  - File: `src/claude_worktree/core.py`
  - Testing: All affected commands tested and working
  - Merged: 2025-11-03

- [x] **Add branch name normalization utility** ✅ v0.10.15 (PR #69)
  - ~~Problem: `refs/heads/` prefix removal logic duplicated throughout codebase~~
  - Solution: Added `normalize_branch_name(branch: str) -> str` to git_utils.py
  - Impact: Removed 18 instances of duplicate code, DRY principle applied
  - File: `src/claude_worktree/git_utils.py`
  - Testing: 10 test cases added for edge cases
  - Merged: 2025-11-03

- [x] **Extract worktree metadata retrieval helper** ✅ v0.10.15 (PR #70)
  - ~~Problem: Metadata fetching logic repeated in finish_worktree, create_pr_worktree, merge_worktree~~
  - Solution: Created `get_worktree_metadata(branch: str, repo: Path) -> tuple[str, Path]` helper
  - Impact: Reduced 22 lines of duplicated code, consistent error handling
  - File: `src/claude_worktree/core.py`
  - Testing: All 232 tests passing
  - Merged: 2025-11-03

- [x] **Consolidate duplicate imports** ✅ v0.10.15 (PR #71)
  - ~~Problem: Two separate import statements from same module `.config`~~
  - Solution: Merged duplicate imports into single block
  - File: `src/claude_worktree/cli.py`
  - Impact: Improved code cleanliness
  - Merged: 2025-11-03

- [x] **Standardize error messages** ✅ v0.10.15 (PR #72)
  - ~~Problem: Inconsistent error message formats for similar situations~~
  - Solution: Created `src/claude_worktree/messages.py` with `ErrorMessages` class
  - Impact: Consistent error messages across codebase, better UX
  - File: `src/claude_worktree/messages.py` (new)
  - Testing: All tests passing with standardized messages
  - Merged: 2025-11-03

### User Experience Improvements

- [x] **First-run shell completion prompt** ✅ (Pending PR)
  - ~~Problem: Users may not discover shell completion feature~~
  - Solution: Automatically prompt users on first run to enable shell completion
  - Implementation:
    - Detects if completion is already installed for current shell (bash/zsh/fish)
    - Prompts: "Would you like to enable tab completion for cw commands?"
    - If yes: Runs `cw shell-setup` automatically
    - Stores preference in config (`shell_completion.prompted`, `shell_completion.installed`)
    - Smart skipping: No prompt if stdin is not a TTY or in CI/test environments
  - Files modified:
    - `src/claude_worktree/config.py`: Added `shell_completion` config section
    - `src/claude_worktree/cli.py`: Added detection logic and prompt_completion_setup()
    - `tests/test_config.py`: Added tests for config tracking
  - Testing: All 245 tests pass
  - Impact: Better onboarding experience, increased feature discovery

- [x] **Smart `cw new` with worktree detection** ✅ (Pending PR)
  - ~~Problem: Running `cw new branch-name` when worktree already exists doesn't provide helpful guidance~~
  - Solution: Intelligent detection and user prompting for better workflow
  - Implementation:
    - **Detect existing worktree**: Checks both normalized and `refs/heads/` prefixed branch names
    - **Interactive mode** (when stdin is TTY):
      - Existing worktree detected: Prompt "Resume work in this worktree instead?"
        - If yes: Automatically switches to `cw resume <branch>`
        - If no: Suggests alternative branch names (`<branch>-v2`, `<branch>-alt`)
      - Existing branch without worktree: Prompt "Create worktree from existing branch?"
        - If yes: Creates worktree from existing branch (uses `git worktree add` without `-b`)
        - If no: Suggests alternative actions (rename branch, delete existing branch)
    - **Non-interactive mode** (scripts/tests):
      - Existing worktree: Fails with helpful error message suggesting `cw resume`
      - Existing branch: Automatically creates worktree from existing branch
  - Files modified:
    - `src/claude_worktree/core.py`: Enhanced `create_worktree()` function
    - `tests/test_core.py`: Added 2 new tests
      - `test_create_worktree_existing_worktree_non_interactive`
      - `test_create_worktree_existing_branch_non_interactive`
  - Testing: All 244 tests pass
  - Impact: Prevents user confusion, provides helpful guidance, improves workflow efficiency

### Platform Support

- [x] **Windows shell completion support** ✅ v0.10.16
  - ~~Problem: Shell completion currently only works on macOS/Linux (bash/zsh/fish)~~
  - Solution: Documented PowerShell completion support (already available via Typer)
  - Implementation: Typer already supports PowerShell completion via `cw --install-completion powershell`
  - Documentation updated:
    - README.md: Added PowerShell completion instructions
    - docs/configuration.md: Added comprehensive Windows PowerShell guide
  - Testing: PowerShell 5.1+ and PowerShell Core 7+ supported
  - Impact: Windows developers can now use full tab completion features
  - Note: Command Prompt does not support tab completion (PowerShell only)

- [x] **Windows support for `cw-cd` shell function** ✅ v0.10.16
  - ~~Problem: `cw-cd` shell function only works on Unix shells (bash/zsh/fish)~~
  - Solution: Added PowerShell function equivalent for Windows
  - Implementation:
    - Added `cw.ps1` PowerShell script in `shell_functions/`
    - Updated `cli.py` to support `cw _shell-function powershell|pwsh`
    - Implemented `cw-cd` function with tab completion for PowerShell
  - Features implemented:
    - ✅ `cw-cd <branch>` - Change directory to worktree by branch name
    - ✅ Tab completion for branch names using `Register-ArgumentCompleter`
    - ✅ Error handling for non-existent worktrees
  - Documentation updated:
    - README.md: Added PowerShell installation instructions
    - docs/configuration.md: Added comprehensive PowerShell guide
    - cli.py: Updated help text and examples
  - Impact: Full feature parity for Windows users
  - Files modified:
    - `src/claude_worktree/shell_functions/cw.ps1` (new)
    - `src/claude_worktree/cli.py` (updated)
    - `README.md` (updated)
    - `docs/configuration.md` (updated)
  - Testing: PowerShell 5.1+ and PowerShell Core 7+ supported

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
  - Test `resolve_worktree_target()` with various inputs (branch name, refs/heads/branch, None, invalid)
  - Test `normalize_branch_name()` edge cases
  - Test `get_worktree_metadata()` with missing/invalid metadata
  - Ensure existing tests still pass after refactoring

- [ ] **Add tests for AI conflict resolution workflow**
  - Mock git conflicts
  - Test AI launch with conflict context

- [ ] **Increase test coverage to >90%**
  - Current coverage: Unknown (run pytest --cov to check)
  - Focus on edge cases in core.py
  - Add integration tests for common workflows

## Known Issues

No currently known issues.

---

## Code Review Summary (2025-10-31)

### Analysis Results
- **Total issues found**: 7 (1 high priority, 2 medium, 4 low)
- **Potential code reduction**: ~150-200 lines through deduplication
- **Test status**: ✅ ruff and mypy checks passing
- **Overall code quality**: Good (well-typed, documented, tested)

### Positive Aspects
- ✅ Consistent type hints throughout
- ✅ Well-structured exception hierarchy
- ✅ Comprehensive docstrings
- ✅ Modern tooling (ruff, mypy, pytest)
- ✅ Good test infrastructure

### Refactoring Impact
- **Phase 1 (Immediate)**: Fix default config, add worktree resolution helper
- **Phase 2 (Refactoring)**: Add utility functions, clean imports
- **Phase 3 (Polish)**: Standardize messages, increase test coverage

---

## Contributing

When adding new items to this TODO:
1. Choose appropriate priority level (High/Medium/Low)
2. Provide clear description of the feature or fix
3. Include implementation details, file locations, and use cases when relevant
4. Add related testing requirements to Testing section
5. Mark items as complete with ✅ and version number when implemented
6. Move known issues to "Known Issues" section until resolved
