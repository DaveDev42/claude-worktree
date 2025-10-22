# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/DaveDev42/claude-worktree/compare/v0.1.4...HEAD
[0.1.4]: https://github.com/DaveDev42/claude-worktree/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/DaveDev42/claude-worktree/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/DaveDev42/claude-worktree/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/DaveDev42/claude-worktree/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/DaveDev42/claude-worktree/releases/tag/v0.1.0
