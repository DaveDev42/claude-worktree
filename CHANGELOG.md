# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.8.2] - 2025-10-24

### Fixed
- **GitHub Actions publish workflow**: Fixed workflow to trigger on tag pushes
  - Changed trigger from `release: types: [published]` to `push: tags: v*`
  - Workflow now automatically publishes to PyPI when version tags are pushed
  - GitHub Releases are now created automatically with changelog notes
  - Resolves issue where releases weren't published to PyPI since v0.6.1

## [0.8.1] - 2025-10-24

### Improved
- **Enhanced shell completion**: Added autocompletion for better user experience
  - `cw config use-preset <TAB>`: Now autocompletes preset names (claude, codex, happy, happy-codex, happy-yolo, no-op)
  - `cw _path <TAB>`: Now autocompletes worktree branch names (internal command used by shell functions)
  - Updated preset documentation to reflect current available presets

## [0.8.0] - 2025-10-24

### Removed
- **Deprecated `cw attach` command**: Removed after deprecation period
  - The command was deprecated in v0.4.0 and has now been fully removed
  - Use `cw resume` instead for better context management and session restoration
  - Breaking change: `cw attach` will no longer work

## [0.7.0] - 2025-10-24

### Changed
- **Refactored AI tool launch control**: Removed `--no-ai`/`--no-claude` flags in favor of preset-based approach
  - Old approach: `cw new my-feature --no-ai`
  - New approach: `cw config use-preset no-op && cw new my-feature`
  - More consistent with overall configuration design
  - Added `no-op` preset (empty array) for disabling AI tool launching

### Breaking Changes
- **Removed `--no-ai` and `--no-claude` command-line flags** from all commands (`cw new`, `cw resume`, `cw attach`)
  - Migration: Use `cw config use-preset no-op` to disable AI tool launching
  - Affects users who relied on these flags in scripts or workflows
- **Simplified Happy presets to 3 variants**: Removed model-specific presets
  - Removed: `happy-sonnet`, `happy-opus`, `happy-haiku` (added in 0.6.2)
  - Kept: `happy`, `happy-codex`, `happy-yolo`
  - Migration: Use `happy` preset and configure model via Happy's own flags

### Added
- **New `no-op` preset**: Explicitly disable AI tool launching via configuration
  - `cw config use-preset no-op`
  - Cleaner than using empty string or dummy commands
- **Happy-yolo preset**: `happy` with `--permission-mode bypassPermissions` for faster iteration
- **Updated Happy-codex preset**: Now includes `--permission-mode bypassPermissions` flag

### Documentation
- Added comprehensive pre-commit hook workflow to CLAUDE.md
  - Proper sequence: commit → check hook modifications → amend if needed → push
  - Prevents force push conflicts from code formatting hooks

## [0.6.2] - 2025-10-24

### Fixed
- **Happy-CLI preset commands**: Corrected Happy-CLI integration
  - Removed incorrect `--backend` option (not supported by Happy)
  - Renamed `happy-claude` → `happy` (Claude Code is the default mode)
  - Fixed `happy-codex` to use correct subcommand syntax: `happy codex`

### Added
- **New Happy presets with model selection**:
  - `happy-sonnet`: Happy with Sonnet model (`happy -m sonnet`)
  - `happy-opus`: Happy with Opus model (`happy -m opus`)
  - `happy-haiku`: Happy with Haiku model (`happy -m haiku`)

### Documentation
- Added comprehensive Happy-CLI integration guide to README
  - Installation instructions
  - Quick start guide
  - Model selection examples
  - Codex mode usage
  - Advanced configuration options
- Added custom AI tool configuration examples
- Updated CLAUDE.md with corrected preset information
- Improved preset usage documentation

### Changed
- **Breaking**: Removed `happy-claude` preset (use `happy` instead)
  - Note: This preset was non-functional in previous versions, so impact is minimal

## [0.6.1] - 2025-10-24

### Fixed
- **`uv tool upgrade` command fix**: Removed unsupported `--refresh` flag from `uv tool upgrade` command
  - `uv tool upgrade` doesn't support `--refresh` option
  - The command now works correctly: `uv tool upgrade claude-worktree`
  - `uv pip install --upgrade` still uses `--refresh` which is supported

## [0.6.0] - 2025-10-24

### Added
- **Shell function for worktree navigation**: New `cw-cd` shell function for quick directory navigation to worktrees
  - Enables `cw cd <branch>` to jump directly to a worktree directory
  - Supports bash and fish shells
  - Installed automatically or manually with `cw config install-shell-function`

## [0.5.0] - 2025-10-24

### Added
- **iTerm2 tab support**: New `--iterm-tab` flag for `cw new`, `cw resume`, and `cw attach` commands
  - Opens AI tool in a new iTerm2 tab instead of a new window
  - Available on macOS with iTerm2 installed
  - Comprehensive test coverage for iTerm tab functionality

## [0.4.0] - 2025-10-24

### Added
- **Multi-AI tool support**: Full configuration system for different AI coding assistants
  - Support for Claude Code (default), Codex, Happy (with Claude or Codex backend), and custom commands
  - New `cw config` commands: `show`, `set`, `use-preset`, `list-presets`, `reset`
  - Environment variable override: `CW_AI_TOOL`
  - AI tool presets for quick configuration
- **Session context restoration**: New `cw resume` command for resuming AI work with conversation history
  - Automatically restores previous AI session state
  - Optional branch argument to switch worktrees before resuming
  - Session storage in `~/.config/claude-worktree/sessions/<branch>/`
  - Support for background, iTerm, and tmux launch modes
- **Remote worktree completion**: New `target` argument for `cw finish` command
  - Complete work on a different worktree from current directory
  - Useful for managing multiple worktrees

### Changed
- **Renamed AI-tool-specific terminology**: All Claude-specific functions and flags renamed for tool agnostic use
  - `--no-claude` deprecated in favor of `--no-ai`
  - Help text updated to use generic AI tool terminology
- **Deprecated `cw attach` command**: Use `cw resume` instead for better context management
  - `cw attach` now shows deprecation warning and redirects to `cw resume`
  - Will be removed in v2.0

### Documentation
- Added comprehensive documentation for `cw resume` with session restoration
- Updated CLAUDE.md with mandatory local testing requirements before commits
- Added TODO.md for tracking planned features

### Development
- Added test report summary to GitHub Actions
- Improved test suite with fixes for help text and color code handling
- Better editable install documentation for modern Python (PEP 668)

## [0.3.2] - 2025-10-22

### Fixed
- **Cache-busting for upgrade consistency**: Added cache bypass flags to prevent version inconsistency
  - Added `--refresh` flag to `uv tool/pip upgrade` commands
  - Added `--no-cache-dir` flag to `pip upgrade` command
  - Added cache-busting headers to PyPI API calls
  - Ensures users get the exact version detected during update check
  - Prevents issues from CDN propagation delays and local caching

## [0.3.1] - 2025-10-22

### Fixed
- **Improved upgrade command**: Better detection of upgrade status and output display
- **License badge**: Fixed README badge to show BSD-3-Clause instead of MIT

### Removed
- Removed obsolete RELEASING.md file

## [0.3.0] - 2025-10-22

### Changed
- **Expanded worktree status types**: Now shows more informative status indicators in `cw list`:
  - `active` (bold green) - Currently in this worktree directory
  - `clean` (green) - No uncommitted changes
  - `modified` (yellow) - Has uncommitted changes
  - `stale` (red) - Directory deleted but admin data remains (affected by `cw prune`)
- **Improved status display**: Status column now uses color coding for better visibility

## [0.2.2] - 2025-10-22

### Fixed
- **Fixed `uv tool install` support**: Now correctly detects and upgrades packages installed via `uv tool`
- **Improved upgrade command output**: Shows current and latest versions before attempting upgrade
- **Better error handling**: Clear messages for unknown installation methods and source installs

### Added
- Support for `uv tool upgrade` command for uv-tool installations
- Friendly guidance for editable/source installations
- Detailed version information in `cw upgrade` command

## [0.2.1] - 2025-10-22

### Changed
- Test release for auto-update functionality verification

## [0.2.0] - 2025-10-22

### Added
- **Self auto-update functionality**: Automatically checks for updates on first run each day
- **`cw upgrade` command**: Manually upgrade to the latest version
- Smart installer detection (pipx, pip, or uv)
- Update check caching to avoid unnecessary network requests
- Graceful handling of network failures during update checks

### Dependencies
- Added `httpx>=0.27.0` for HTTP requests to PyPI
- Added `packaging>=24.0` for version comparison

## [0.1.4] - 2025-10-22

### Changed
- **License changed from MIT to BSD-3-Clause**

## [0.1.3] - 2025-10-22

### Changed
- **Single source of truth for version**: Now `pyproject.toml` is the only place where version is defined
- `__init__.py` now dynamically reads version from package metadata using `importlib.metadata`
- This eliminates version management overhead and prevents version mismatches

## [0.1.2] - 2025-10-22

### Fixed
- Fixed version string in `__init__.py` to match package version (was stuck at 0.1.0)

## [0.1.1] - 2025-10-22

### Fixed
- Fixed GitHub Actions workflow to properly handle asset uploads with `--clobber` flag
- This prevents workflow failures when re-running releases with existing assets

### Changed
- Renamed workflow from "Publish to PyPI" to "Publish" for simplicity

## [0.1.0] - 2025-01-22

### Added
- Initial release of claude-worktree CLI tool
- `cw new` command to create worktrees with automatic Claude Code integration
- `cw finish` command to rebase, merge, and cleanup worktrees
- `cw attach` command to reattach Claude Code to current worktree
- `cw list` command to display all worktrees with status
- `cw status` command to show current worktree information
- `cw delete` command to remove worktrees with optional branch/remote cleanup
- `cw prune` command to clean up stale worktree metadata
- Automatic shell completion for bash/zsh/fish
- Rich terminal output with colored status indicators
- Type-safe implementation with full mypy strict mode compliance
- Comprehensive test suite with 47 tests achieving 79% coverage
- Pre-commit hooks for code quality (ruff, mypy, basic git checks)
- GitHub Actions CI/CD pipeline testing on Ubuntu and macOS
- Support for Python 3.11 and 3.12

### Features
- Clean worktree naming: `../<repo>-<branch>` (no timestamps)
- Metadata storage via git config for tracking base branches
- Claude Code integration with multiple launch modes:
  - Background mode
  - iTerm window (macOS)
  - tmux session
- Automatic rebase and fast-forward merge workflow
- Origin remote detection and smart rebase target selection
- Protection against deleting main repository
- Support for custom worktree paths
- Optional remote branch deletion

### Documentation
- Comprehensive README with usage examples and troubleshooting
- CLAUDE.md for AI assistant context
- Inline documentation with detailed docstrings
- Type hints throughout codebase

[Unreleased]: https://github.com/DaveDev42/claude-worktree/compare/v0.8.2...HEAD
[0.8.2]: https://github.com/DaveDev42/claude-worktree/compare/v0.8.1...v0.8.2
[0.8.1]: https://github.com/DaveDev42/claude-worktree/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/DaveDev42/claude-worktree/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/DaveDev42/claude-worktree/compare/v0.6.2...v0.7.0
[0.6.2]: https://github.com/DaveDev42/claude-worktree/compare/v0.6.1...v0.6.2
[0.6.1]: https://github.com/DaveDev42/claude-worktree/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/DaveDev42/claude-worktree/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/DaveDev42/claude-worktree/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/DaveDev42/claude-worktree/compare/v0.3.2...v0.4.0
[0.3.2]: https://github.com/DaveDev42/claude-worktree/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/DaveDev42/claude-worktree/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/DaveDev42/claude-worktree/compare/v0.2.2...v0.3.0
[0.2.2]: https://github.com/DaveDev42/claude-worktree/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/DaveDev42/claude-worktree/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/DaveDev42/claude-worktree/compare/v0.1.4...v0.2.0
[0.1.4]: https://github.com/DaveDev42/claude-worktree/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/DaveDev42/claude-worktree/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/DaveDev42/claude-worktree/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/DaveDev42/claude-worktree/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/DaveDev42/claude-worktree/releases/tag/v0.1.0
