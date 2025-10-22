# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/DaveDev42/claude-worktree/compare/v0.3.1...HEAD
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
