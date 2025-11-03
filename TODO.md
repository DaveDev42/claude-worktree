# TODO - claude-worktree

This document tracks planned features, enhancements, and known issues for the claude-worktree project.

## High Priority

### Code Quality & Refactoring

- [ ] **Fix default AI tool configuration** (config.py:40)
  - Current: `"command": "claude-yolo"` (uses dangerous permissions by default)
  - Change to: `"command": "claude"` (safer default) or `"command": "no-op"` (let user choose)
  - File: `src/claude_worktree/config.py`
  - Impact: New users will have safer defaults
  - Related: Issue discovered during code review (2025-10-31)

## Medium Priority

### Code Quality & Refactoring (Critical Improvements)

- [ ] **Extract duplicated worktree resolution logic** (core.py - multiple functions)
  - Problem: Same 30-40 line pattern repeated in 7+ functions (finish_worktree, create_pr_worktree, delete_worktree, sync_worktree, change_base_branch, backup_worktree, resume_worktree)
  - Solution: Create `resolve_worktree_target(target: str | None) -> tuple[Path, str]` helper
  - Impact: Reduce ~150-200 lines of duplicated code, improve maintainability
  - Priority: High impact on code quality
  - File: `src/claude_worktree/core.py`
  - Lines affected: ~152-165, ~418-431, ~619-632, ~701-711, ~1578-1591, ~1822-1831, ~2130-2143
  - Testing: Ensure all affected commands still work correctly

- [ ] **Add branch name normalization utility** (git_utils.py)
  - Problem: `refs/heads/` prefix removal logic duplicated throughout codebase
  - Solution: Add `normalize_branch_name(branch: str) -> str` to git_utils.py
  - Current patterns:
    - `branch_name = target[11:] if target.startswith("refs/heads/") else target`
    - `if branch.startswith("refs/heads/"): branch_name = branch[11:]`
  - Impact: DRY principle, single source of truth for branch name handling
  - File: `src/claude_worktree/git_utils.py`
  - Refactor locations: core.py (10+ occurrences), cli.py (2 occurrences)

- [ ] **Extract worktree metadata retrieval helper** (core.py)
  - Problem: Metadata fetching logic repeated in finish_worktree, create_pr_worktree, merge_worktree
  - Solution: Create `get_worktree_metadata(branch: str, repo: Path) -> tuple[str, Path]` helper
  - Current pattern:
    ```python
    base_branch = get_config(CONFIG_KEY_BASE_BRANCH.format(feature_branch), worktree_repo)
    base_path_str = get_config(CONFIG_KEY_BASE_PATH.format(feature_branch), worktree_repo)
    if not base_branch or not base_path_str:
        raise GitError(f"Missing metadata for branch '{feature_branch}'...")
    ```
  - Impact: Consistent error handling, reduced duplication
  - File: `src/claude_worktree/core.py`
  - Testing: Verify error messages remain consistent

- [ ] **Consolidate duplicate imports** (cli.py:9-19)
  - Problem: Two separate import statements from same module `.config`
  - Solution: Merge into single import block
  - File: `src/claude_worktree/cli.py`
  - Impact: Code cleanliness, minor

- [ ] **Standardize error messages** (core.py)
  - Problem: Inconsistent error message formats for similar situations
  - Current variations:
    - `"No worktree found for branch '{target}'. Use 'cw list' to see available worktrees."`
    - `"No worktree found for branch '{branch}'. Try specifying the path directly."`
  - Solution: Define error message templates/constants
  - Impact: Better user experience, consistency
  - File: `src/claude_worktree/core.py` or new `src/claude_worktree/messages.py`

### User Experience Improvements

- [ ] **First-run shell completion prompt**
  - On first run (or when completion not detected), prompt user to install shell completion
  - Detection: Check if completion is already installed for current shell
  - Prompt: "Would you like to install shell completion for better productivity? (y/n)"
  - If yes: Run `cw --install-completion` automatically
  - Store preference in config to avoid re-prompting
  - Impact: Helps users discover and enable this productivity feature
  - File: `src/claude_worktree/cli.py` or `src/claude_worktree/core.py`

- [ ] **Smart `cw new` with worktree detection**
  - Problem: Running `cw new branch-name` when worktree already exists doesn't provide helpful guidance
  - Solution 1: Detect existing worktree for same branch name
    - Prompt: "Worktree for branch 'feature-x' already exists at '../repo-feature-x'. Resume work instead? (y/n)"
    - If yes: Automatically switch to `cw resume feature-x`
    - If no: Suggest alternative branch name or path
  - Solution 2: Detect existing branch without worktree
    - Prompt: "Branch 'feature-x' already exists. Create worktree from existing branch? (y/n)"
    - If yes: Create worktree from existing branch
    - If no: Suggest different branch name or abort
  - Impact: Better user experience, prevents confusion and mistakes
  - File: `src/claude_worktree/core.py` (create_worktree function)
  - Testing: Add tests for existing worktree/branch detection

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
