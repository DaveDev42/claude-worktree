# Claude Worktree - Project Guide for Claude Code

**IMPORTANT - Internal Document Policy:**
This file (CLAUDE.md) is strictly for AI assistant guidance and internal development purposes. **NEVER reference or mention this file in:**
- GitHub issues, pull requests, or comments
- External documentation or user-facing content
- Communication with external contributors or users

When communicating externally, always reference user-facing documentation:
- **README.md** - Quick-start guide and overview
- **docs/commands.md** - Command reference
- **docs/configuration.md** - Configuration guide
- **docs/advanced-features.md** - Advanced workflows
- **TROUBLESHOOTING.md** - Common issues and solutions

## Project Overview

**claude-worktree** is a CLI tool that seamlessly integrates git worktree with AI coding assistants to streamline feature development workflows. It allows developers to quickly create isolated worktrees for feature branches, work with their preferred AI tool (Claude Code, Codex, Happy, or custom) in those environments, and cleanly merge changes back to the base branch.

## Core Concept

Instead of switching branches in a single working directory, `claude-worktree` creates separate directories (worktrees) for each feature branch. This allows:
- Multiple features to be worked on simultaneously
- Clean isolation between different tasks
- Automatic AI coding assistant session management per feature (configurable per user)
- Safe merge workflows with automatic cleanup

## Project Structure

```
claude-worktree/
├── src/claude_worktree/          # Main package
│   ├── __init__.py               # Package initialization
│   ├── __main__.py               # Entry point for `python -m claude_worktree`
│   ├── cli.py                    # Typer-based CLI definitions
│   ├── core.py                   # Core business logic (commands implementation)
│   ├── config.py                 # Configuration management
│   ├── git_utils.py              # Git operations wrapper
│   ├── session_manager.py        # AI session backup/restore
│   ├── exceptions.py             # Custom exception classes
│   └── constants.py              # Constants and default values
├── tests/                        # Test suite
│   ├── test_core.py
│   ├── test_config.py
│   ├── test_git_utils.py
│   ├── test_cli.py
│   ├── test_session_manager.py
│   └── conftest.py               # pytest fixtures
├── docs/                         # User documentation
│   ├── commands.md               # Complete command reference
│   ├── configuration.md          # Configuration guide
│   └── advanced-features.md      # Advanced features and workflows
├── .github/workflows/
│   ├── test.yml                  # CI: Run tests on push/PR
│   └── publish.yml               # CD: Publish to PyPI on release
├── pyproject.toml                # Project metadata, dependencies (uv format)
├── README.md                     # User quick-start guide (concise)
├── TROUBLESHOOTING.md            # Common issues and solutions
├── TODO.md                       # Planned features and improvements
├── CHANGELOG.md                  # Release history
├── CLAUDE.md                     # This file (for AI assistants)
├── LICENSE                       # MIT License
└── .gitignore
```

### Documentation Structure

**README.md** - Quick-start guide for new users (~285 lines)
- What is claude-worktree?
- Quick installation and basic usage
- Key features overview
- Links to detailed documentation

**docs/** - Detailed user documentation
- **commands.md** - Complete command reference with all options and examples
- **configuration.md** - Configuration guide (AI tools, presets, shell setup)
- **advanced-features.md** - Advanced workflows (backup, sync, cleanup, CI/CD)

**TROUBLESHOOTING.md** - Comprehensive troubleshooting guide
- Installation issues
- Git-related problems
- AI tool launch issues
- Platform-specific solutions

**CLAUDE.md** (this file) - Project guide for AI assistants
- Architecture and design decisions
- Development workflow and conventions
- Testing and release procedures
- Code quality guidelines

## Key Features

### 1. Worktree Management
- **`cw new <name>`**: Create new worktree with specified branch name
  - Default path: `../<repo>-<branch>` (e.g., `../myproject-fix-auth/`)
  - Customizable with `--path` option
  - Automatically launches configured AI tool in the new worktree

- **`cw pr [branch]`**: Create GitHub Pull Request (recommended for teams)
  - Rebases feature branch on base branch
  - Pushes to remote
  - Creates PR using GitHub CLI (`gh`)
  - Leaves worktree intact for further work
  - Options: `--title`, `--body`, `--draft`, `--no-push`

- **`cw merge [branch]`**: Direct merge to base branch (for solo development)
  - Rebases feature branch on base branch
  - Fast-forward merges into base branch
  - Cleans up worktree and feature branch
  - Optional `--push` to push to remote
  - Options: `--interactive`, `--dry-run`

- **`cw delete <target>`**: Remove worktree by branch name or path
  - Options: `--keep-branch`, `--delete-remote`

- **`cw list`**: Show all worktrees
- **`cw status`**: Show current worktree metadata

### 2. AI Tool Integration & Session Management
- **`cw resume [branch]`**: Resume AI work in a worktree with context restoration
  - Optional branch argument: switches to specified worktree before resuming
  - **Context restoration**: Automatically restores previous AI session history
  - Seamlessly continue conversations from where you left off
  - Session storage: `~/.config/claude-worktree/sessions/<branch>/`
  - Launch options:
    - `--bg`: Background process
    - `--iterm`: New iTerm2 window (macOS)
    - `--iterm-tab`: New iTerm2 tab (macOS) ✅ Implemented in v0.5.0
    - `--tmux <session>`: New tmux session
  - Supports multiple AI tools:
    - Claude Code (default)
    - Codex
    - Happy (with Claude or Codex backend)
    - Custom commands
  - Note: To skip AI tool launch, use `cw config use-preset no-op`

### 3. Configuration Management
- **`cw config show`**: Display current configuration
- **`cw config set <key> <value>`**: Set configuration value
- **`cw config use-preset <name>`**: Use predefined AI tool preset
  - Available presets:
    - `no-op`: Disable AI tool launching
    - `claude`: Claude Code (default)
    - `codex`: OpenAI Codex
    - `happy`: Happy with Claude Code (mobile-enabled)
    - `happy-codex`: Happy with Codex mode and bypass permissions
    - `happy-yolo`: Happy with YOLO mode (bypass all permissions)
- **`cw config list-presets`**: List available presets
- **`cw config reset`**: Reset to defaults
- Configuration stored in `~/.config/claude-worktree/config.json`
- Environment variable override: `CW_AI_TOOL`

#### Auto-Update Configuration (v0.9.0+)
By default, `claude-worktree` checks for updates once per day. This can be configured:

```bash
# Disable automatic update checks
cw config set update.auto_check false

# Re-enable automatic update checks
cw config set update.auto_check true

# Manual upgrade always works regardless of setting
cw upgrade
```

**When to disable auto-check:**
- Corporate environments with restricted internet access
- Air-gapped systems
- CI/CD pipelines
- Personal preference for manual updates

### 4. Shell Completion
- Typer provides automatic shell completion for bash/zsh/fish
- Install with: `cw --install-completion`

## Technology Stack

- **Python 3.11+**: Core language (minimum version required)
- **uv**: Fast Python package manager
- **Typer**: Modern CLI framework with type hints
- **pytest**: Testing framework
- **GitHub Actions**: CI/CD automation

## Development Workflow Changes from Legacy

### Path Naming (IMPORTANT)
**Before (cw.py):**
- Path: `../.cw_worktrees/<repo>/<topic>-<timestamp>/`
- Branch: `<topic>-<timestamp>` (e.g., `fix-auth-20250122-143052`)

**After (new design):**
- Path: `../<repo>-<branch>/` (e.g., `../myproject-fix-auth/`)
- Branch: User-specified name (e.g., `fix-auth`)
- Cleaner, more predictable naming
- No timestamp clutter

### CLI Framework
**Before:** argparse with manual completion setup
**After:** Typer with:
- Type hints for automatic validation
- Built-in shell completion
- Better help text generation
- Cleaner command definitions

### Error Handling
**Before:** Generic RuntimeError with string messages
**After:** Custom exception hierarchy:
- `ClaudeWorktreeError`: Base exception
- `GitError`: Git operation failures
- `WorktreeNotFoundError`: Missing worktree
- `InvalidBranchError`: Invalid branch state

## Metadata Storage

### Git Config Metadata
The tool stores worktree metadata in git config:
- `branch.<feature>.worktreeBase`: The base branch name
- `worktree.<feature>.basePath`: Path to the base repository

This allows the `pr` and `merge` commands to know:
1. Which branch to rebase onto
2. Where the main repository is located
3. How to perform the merge safely

### AI Session Storage (Planned)
AI session data is stored separately in the user's config directory:

```
~/.config/claude-worktree/
├── config.json              # Tool configuration
└── sessions/                # AI session backups
    ├── fix-auth/
    │   ├── claude-session.json    # Claude Code session data
    │   ├── metadata.json          # Session metadata (timestamps, AI tool type)
    │   └── context.txt            # Additional context (optional)
    └── feature-api/
        └── ... (similar structure)
```

Session restoration workflow:
1. When `cw resume` is called, the session manager checks for existing session data
2. If found, it restores the AI tool's conversation history
3. AI tool continues from the last saved state
4. Sessions are automatically backed up when AI tool exits (planned)

## Git Requirements

- Git 2.31+ (for modern worktree support)
- Repository must be initialized
- Remote origin recommended for fetch/push operations

## Installation Methods

1. **uv (recommended):**
   ```bash
   uv tool install claude-worktree
   ```

2. **pip:**
   ```bash
   pip install claude-worktree
   ```

3. **From source:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/claude-worktree
   cd claude-worktree
   uv pip install -e .
   ```

## Testing Strategy

- **Unit tests**: Test individual functions in isolation
- **Integration tests**: Test full command workflows
- **Mocking**: Mock git commands to avoid filesystem changes
- **Fixtures**: Reusable test repositories

**CRITICAL: Test Policy**
- **NEVER skip or ignore tests** using `@pytest.mark.skip`, `pytest.skip()`, or similar
- **NEVER comment out failing tests**
- **ALWAYS fix the root cause** of test failures
- If a test fails in CI but works locally, investigate the CI environment difference and fix the test or code
- Skipping tests hides bugs and breaks quality assurance
- Every test must have a valid reason to exist; if it doesn't, delete it - don't skip it

## Common Development Tasks

### Running tests
**IMPORTANT: Skip local test runs unless absolutely necessary!**

Tests are automatically run by GitHub Actions on every push and PR. Running tests locally before every commit is time-consuming and redundant.

**When to run tests locally:**
- ✅ Debugging a specific test failure
- ✅ Developing complex new features that require iterative testing
- ✅ Investigating test behavior before committing

**When to skip tests:**
- ❌ Before routine commits (let GitHub Actions handle it)
- ❌ Before creating PRs (CI will catch issues)
- ❌ In release scripts (CI runs comprehensive tests)

```bash
# Only run tests when debugging or developing complex features
uv run pytest

# Run with verbose output (for debugging)
uv run pytest -v

# Run specific test file (for targeted debugging)
uv run pytest tests/test_core.py

# Run with coverage report (for development)
uv run pytest --cov=claude_worktree --cov-report=term
```

**Pre-commit checklist:**
1. ⏭️ **SKIP** `uv run pytest` - GitHub Actions will run tests automatically
2. ✅ Run `ruff check src/ tests/` - no linting errors (pre-commit hook runs this)
3. ✅ Run `mypy src/claude_worktree` - no type errors (pre-commit hook runs this)
4. ✅ Check `git status` for `uv.lock` changes - commit if modified
5. ✅ Verify changes work as expected locally (manual testing)

The pre-commit hooks automatically run ruff and mypy. GitHub Actions will run the full test suite on every push, so you don't need to run pytest locally unless debugging.

### Git commit workflow with pre-commit hooks

**IMPORTANT**: Pre-commit hooks may modify files (e.g., code formatting). Always follow this sequence:

1. **Stage and commit** your changes:
   ```bash
   git add <files>
   git commit -m "Your commit message"
   ```

2. **Check for hook modifications**:
   - Pre-commit hooks will run automatically
   - If hooks modify files, they will be shown as "modified" after commit
   - Check with `git status`

3. **Amend commit if files were modified**:
   ```bash
   git add <modified-files>
   git commit --amend --no-edit
   ```

4. **Push to remote**:
   ```bash
   git push origin main
   # Use --force only if you already pushed and then amended
   git push --force origin main  # (if needed after amend)
   ```

**Example workflow:**
```bash
# Make changes
vim src/claude_worktree/config.py

# Stage and commit
git add src/claude_worktree/config.py
git commit -m "feat: Add new config option"

# Pre-commit hooks run and modify files
# Check status
git status

# If files were modified by hooks, amend the commit
git add src/claude_worktree/config.py  # Add formatted files
git commit --amend --no-edit

# Push
git push origin main
```

### Protected Branch Policy (This Repository)

**IMPORTANT**: This repository has branch protection rules enabled for the `main` branch.

**Workflow constraints:**
- ✅ **Use `cw pr`**: Create pull requests for all changes (recommended workflow)
- ❌ **Direct push blocked**: Cannot push directly to `main` branch
- ❌ **`cw merge --push` will fail**: Local merge works, but push to protected branch is blocked

**Correct workflow for this repository:**
1. Create feature branch with `cw new <feature-name>`
2. Make changes and commit in the worktree
3. **IMPORTANT: Rebase onto latest main before creating PR**
   ```bash
   git fetch origin
   git rebase origin/main
   git push --force-with-lease origin <feature-branch>
   ```
4. Create PR with `cw pr` (rebases, pushes to remote, creates PR)
5. **Keep PR up-to-date**: If main changes after PR creation, rebase again (don't merge!)
   ```bash
   git fetch origin
   git rebase origin/main
   git push --force-with-lease origin <feature-branch>
   ```
6. Merge PR remotely via GitHub web interface
7. Pull latest changes in main repository

**Why this matters:**
- Branch protection ensures all changes go through code review
- CI/CD checks must pass before merging
- Maintains code quality and prevents accidental direct commits to main
- **Clean git history**: Rebase (not merge commits) keeps history linear and readable
- **"PR must be up-to-date" = rebase required**: Don't create merge commits to update PR!

**Note**: The `cw merge` command (without `--push`) still works for local testing, but changes cannot be pushed to the protected `main` branch. Always use `cw pr` for this repository.

### Running the CLI during development

**Option 1: Run with uv (recommended)**
```bash
uv run python -m claude_worktree --help
uv run python -m claude_worktree new my-feature
```

**Option 2: Install in editable mode for dog-fooding**

For testing local changes, install in editable mode so code changes are immediately reflected:

```bash
# Using uv tool (recommended - isolated global installation)
uv tool install -e .
cw --help

# Using uv pip (works without virtual environment)
uv pip install -e .
cw --help

# Using pipx (for isolated global installation)
pipx install -e .
cw --help

# Using regular pip (requires virtual environment due to PEP 668)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
cw --help
```

**Note**: Modern Python (3.11+) restricts global pip installs via PEP 668. Use `uv tool`, `uv pip`, or `pipx` for system-wide installation, or create a virtual environment for regular `pip`.

### Building the package
```bash
uv build
```

### Publishing to PyPI
```bash
uv publish
```

### Release & Versioning Policy

**IMPORTANT**: Version bumps and releases require explicit user approval based on semantic versioning:

- **Patch version (x.x.N)**: Default for all releases unless specified otherwise
  - Bug fixes, minor improvements, documentation updates
  - Can be released automatically when requested
  - Example: `0.10.0 → 0.10.1`

- **Minor version (x.N.0)**: Requires explicit user approval
  - New features, backward-compatible changes
  - Must ask user before bumping
  - Example: `0.10.8 → 0.11.0`

- **Major version (N.0.0)**: Requires explicit user approval
  - Breaking changes, API changes, major redesigns
  - Must ask user before bumping
  - Example: `0.11.5 → 1.0.0`

**Default behavior**: When user requests "release" or "new version" without specifying the version type, ALWAYS use patch version bump.

**Release workflow**:
1. Determine version type (default: patch)
2. Get user approval for minor/major bumps
3. Update version in `pyproject.toml`
4. **MANDATORY: Commit `uv.lock` file**
   - Lock file ensures reproducible builds
   - MUST be included in every release
   - Check `git status` before committing version bump
   - If `uv.lock` is modified, stage it with version bump
5. Commit changes (including uv.lock if modified)
6. Create GitHub release with tag
7. Optionally publish to PyPI (requires explicit request)

**CRITICAL: Lock File Policy**
- **ALWAYS check `uv.lock` status** before every commit
- **NEVER skip `uv.lock` commits** - it's as important as `pyproject.toml`
- If `uv.lock` is modified, it MUST be committed
- Lock file ensures all users get identical dependency versions
- Missing lock file commits break reproducible builds

### Release Workflow (Automated with GitHub Actions)

**IMPORTANT**: This repository uses an automated release workflow. When a PR from `release/*` branch is merged to `main`, it automatically:
1. Creates a git tag (e.g., `v0.10.9`)
2. Triggers CI/CD to build and publish to PyPI
3. Creates a GitHub release

**Step-by-step release process:**

**RECOMMENDED: Use the automated release script** (`scripts/release.py`):

```bash
# Patch release (default: 0.10.20 → 0.10.21)
uv run python scripts/release.py

# Minor release (0.10.21 → 0.11.0)
uv run python scripts/release.py --minor

# Major release (0.11.0 → 1.0.0)
uv run python scripts/release.py --major

# Dry-run to preview changes
uv run python scripts/release.py --dry-run

# Run tests locally (only if needed for debugging)
uv run python scripts/release.py --run-tests
```

The script automatically:
1. ✅ Checks git working tree is clean
2. ✅ Reads current version from `pyproject.toml`
3. ✅ Calculates new version based on semantic versioning
4. ⏭️ Skips tests by default (use `--skip-tests` flag, GitHub Actions will run them)
5. ✅ Updates `pyproject.toml` and `uv.lock`
6. ✅ Creates `release/vX.Y.Z` branch
7. ✅ Commits changes with proper message
8. ✅ Pushes to remote
9. ✅ Creates GitHub PR via `gh` CLI

**Note**: Tests are skipped by default because GitHub Actions will run comprehensive tests on the PR. Only run tests locally if you need to debug a specific issue before creating the release PR.

**Manual release process** (if script unavailable):

1. **Update version** (in main repository):
   ```bash
   # Check git status
   git status

   # Update version in pyproject.toml
   # For patch: 0.10.8 → 0.10.9
   # For minor: 0.10.9 → 0.11.0 (requires user approval)
   # For major: 0.11.0 → 1.0.0 (requires user approval)

   # Commit version bump
   git add pyproject.toml uv.lock  # Include uv.lock if modified
   git commit -m "chore: Bump version to X.Y.Z"
   ```

   **Note**: Skip running tests locally - GitHub Actions will run them when you create the PR.

2. **Create release branch and PR**:
   ```bash
   # Create release branch (MUST start with "release/")
   git checkout -b release/vX.Y.Z

   # Push to remote
   git push origin release/vX.Y.Z

   # Create PR
   gh pr create --title "chore: Release vX.Y.Z" --body "Version bump for [patch/minor/major] release"
   ```

3. **Merge PR** (fully automated):
   - Review and merge PR via GitHub web interface
   - **🤖 Auto-release handles everything:**
     - Reads version from `pyproject.toml`
     - Creates and pushes tag `vX.Y.Z`
     - Runs tests (multiple OS/Python versions)
     - Builds package
     - Publishes to PyPI
     - Creates GitHub release with artifacts
   - Track progress at: https://github.com/DaveDev42/claude-worktree/actions
   - Done! No manual steps required ✨

**Workflow files:**
- `.github/workflows/publish.yml`: Complete release automation (tag → test → build → publish)
- `.github/workflows/publish-manual.yml`: Manual workflow (for tag-based or manual releases)
- `.github/workflows/test.yml`: Runs tests on all PRs

**Manual release (if needed):**
If you need to manually trigger a release:
```bash
# Option 1: Create tag manually to trigger publish.yml
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z

# Option 2: Use workflow dispatch
gh workflow run publish.yml --ref vX.Y.Z
```

**Why this workflow is optimal:**
- ✅ **Zero manual steps** after PR merge
- ✅ **Single workflow** handles everything (no multi-workflow triggering issues)
- ✅ **Consistent** release process every time
- ✅ **Automatic PyPI publishing** via trusted publishing
- ✅ **All CI/CD checks** must pass before publishing
- ✅ **Audit trail** maintained through PRs and workflow logs
- ✅ **No credentials needed** on local machine

## Code Style Guidelines

- Type hints for all function signatures
- Docstrings for public functions (Google style)
- Follow PEP 8 (enforced by ruff)
- Keep functions focused and testable
- Separate business logic from CLI interface

## Future Enhancements (Ideas)

### Completed
- **AI session context restoration** - ✅ Implemented in v0.4.0 with `cw resume`
  - Session storage in `~/.config/claude-worktree/sessions/`
  - Automatic context restoration when resuming work
- **Shell function for worktree navigation** - ✅ Implemented in v0.6.0 as `cw-cd`
  - Quick directory navigation with `cw-cd <branch>`
  - Supports bash, zsh, and fish shells
  - Install with: `source <(cw _shell-function bash)` or `cw _shell-function fish | source`

### Planned
- Interactive mode for command selection
- Git hook integration (auto-backup sessions on exit)
- Multi-session management (switch between different AI conversations)
- Session export/import for team collaboration
- Better conflict resolution guidance

## Troubleshooting

### Common Issues

1. **"Not a git repository"**
   - Run from within a git repository

2. **"Claude CLI not found"**
   - Install Claude Code CLI: https://claude.ai/download

3. **"Rebase failed"**
   - Conflicts detected; resolve manually
   - Tool aborts rebase automatically

4. **Shell completion not working**
   - Run `cw --install-completion`
   - Restart your shell

5. **Session restoration not working**
   - Check session storage directory: `~/.config/claude-worktree/sessions/`
   - Verify AI tool supports session restoration
   - Check session metadata for corruption: `cat ~/.config/claude-worktree/sessions/<branch>/metadata.json`
   - Clear sessions if needed: `rm -rf ~/.config/claude-worktree/sessions/<branch>/`

## Contributing

This is an open-source project. Contributions welcome!
- Report bugs via GitHub Issues
- Submit PRs for features/fixes
- Discuss ideas in GitHub Discussions

## License

MIT License - see LICENSE file
