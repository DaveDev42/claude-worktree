# Release Guide

This document describes how to release a new version of claude-worktree to PyPI.

## Prerequisites

1. Ensure you have maintainer access to the GitHub repository
2. PyPI Trusted Publishing is configured (see setup below)
3. All tests are passing on main branch
4. CHANGELOG.md is up to date

## PyPI Trusted Publishing Setup (One-time)

Before the first release, configure PyPI Trusted Publishing:

1. Go to PyPI project settings: https://pypi.org/manage/project/claude-worktree/settings/
2. Navigate to "Publishing" section
3. Add a new publisher with these settings:
   - PyPI Project Name: `claude-worktree`
   - Owner: `DaveDev42`
   - Repository name: `claude-worktree`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`

## Release Process

### 1. Update Version

Update version in `pyproject.toml`:

```toml
[project]
version = "X.Y.Z"
```

### 2. Update CHANGELOG.md

Move items from `[Unreleased]` to a new version section:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- Feature descriptions

### Changed
- Change descriptions

### Fixed
- Bug fix descriptions
```

Update the version links at the bottom:

```markdown
[Unreleased]: https://github.com/DaveDev42/claude-worktree/compare/vX.Y.Z...HEAD
[X.Y.Z]: https://github.com/DaveDev42/claude-worktree/releases/tag/vX.Y.Z
```

### 3. Commit Changes

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "Bump version to X.Y.Z"
git push origin main
```

### 4. Create and Push Tag

```bash
git tag -a vX.Y.Z -m "Release version X.Y.Z"
git push origin vX.Y.Z
```

### 5. Create GitHub Release

1. Go to: https://github.com/DaveDev42/claude-worktree/releases/new
2. Select the tag you just created: `vX.Y.Z`
3. Release title: `vX.Y.Z`
4. Use `.github/RELEASE_TEMPLATE.md` as a starting point
5. Copy relevant sections from CHANGELOG.md
6. Click "Publish release"

### 6. Automated Publishing

Once the GitHub Release is published:

1. GitHub Actions workflow `.github/workflows/publish.yml` automatically triggers
2. The workflow:
   - Builds source distribution and wheel
   - Verifies package with twine
   - Publishes to PyPI using Trusted Publishing
   - Uploads distribution files to GitHub Release

3. Monitor the workflow: https://github.com/DaveDev42/claude-worktree/actions

### 7. Verify Release

After the workflow completes:

1. Check PyPI: https://pypi.org/project/claude-worktree/
2. Test installation in clean environment:
   ```bash
   uv tool install claude-worktree==X.Y.Z
   cw --version
   ```

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes
- **MINOR** (X.Y.0): New features, backwards compatible
- **PATCH** (X.Y.Z): Bug fixes, backwards compatible

## Rollback Procedure

If a release has critical issues:

1. **DO NOT** delete the PyPI release (it's permanent)
2. Create a new patch version with fixes
3. Publish the fixed version following normal process
4. Update GitHub Release notes to mark the problematic version

## Manual Publishing (Emergency Only)

If automated publishing fails:

1. Build locally:
   ```bash
   uv build
   twine check dist/*
   ```

2. Upload to PyPI (requires API token):
   ```bash
   twine upload dist/*
   ```

## Troubleshooting

### Workflow fails with "not configured for trusted publishing"

- Ensure PyPI Trusted Publishing is configured correctly
- Check workflow environment name matches PyPI settings
- Verify repository and owner names match exactly

### Package already exists on PyPI

- You cannot overwrite existing versions
- Increment version number and try again
- PyPI does not allow deleting and re-uploading same version

### Tests failing in release workflow

- Fix issues on main branch first
- Delete the git tag: `git tag -d vX.Y.Z && git push origin :vX.Y.Z`
- Delete the GitHub Release
- Fix and retry release process
