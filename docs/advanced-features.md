# Advanced Features

This guide covers advanced `claude-worktree` features for power users.

## Backup & Restore

Create complete backups of your worktrees with full git history and uncommitted changes.

### Creating Backups

```bash
# Backup current worktree
cw backup create

# Backup specific worktree by branch name
cw backup create fix-auth

# Backup all worktrees
cw backup create --all

# Custom backup location
cw backup create -o ~/my-backups
cw backup create --output /external/drive/backups
```

**What's included in backups:**
- Complete git bundle with full commit history
- Uncommitted changes (as patch files)
- Worktree metadata (branch name, base branch, paths)
- Backup timestamp for organization

**Default backup location:** `~/.config/claude-worktree/backups/`

### Listing Backups

```bash
# List all backups
cw backup list

# List backups for specific branch
cw backup list fix-auth
```

Output shows:
- Branch name
- Backup timestamp
- Creation date/time
- Indicator for uncommitted changes

### Restoring from Backup

```bash
# Restore latest backup for a branch
cw backup restore fix-auth

# Restore specific backup by timestamp
cw backup restore fix-auth --id 20250129-143052

# Restore to custom path
cw backup restore fix-auth --path /tmp/my-restore
```

**Restore process:**
1. Clones from git bundle (full history restored)
2. Checks out the branch
3. Restores worktree metadata
4. Applies uncommitted changes if they exist

### Use Cases

#### Before Risky Operations

```bash
# Backup before major refactoring
cw backup create my-feature

# ... make changes ...

# If something goes wrong:
cw backup restore my-feature
```

#### Archive Completed Work

```bash
# Backup before cleanup
cw backup create old-feature
cw merge old-feature --push

# Can restore later if needed
cw backup restore old-feature
```

#### Transfer Work Between Machines

```bash
# Machine 1
cw backup create feature-x -o ~/Dropbox/backups

# Machine 2
cp ~/Dropbox/backups/feature-x/20250129-143052 ~/.config/claude-worktree/backups/
cw backup restore feature-x
```

#### Disaster Recovery

```bash
# Regular backup schedule
cw backup create --all  # Backup all worktrees

# After disk failure or accidental deletion
cw backup list
cw backup restore important-feature --id 20250128-120000
```

#### Experimentation with Safety Net

```bash
# Backup stable state
cw backup create experiment

# Try risky changes
# ... changes didn't work out ...

# Restore to stable state
cw delete experiment
cw backup restore experiment
```

## Stash Management

Worktree-aware stashing makes it easy to move work-in-progress between worktrees.

### Saving Stashes

```bash
# Save changes in current worktree
cw stash save

# Save with message
cw stash save "work in progress"
```

Stashes are automatically prefixed with the worktree branch name for organization.

### Listing Stashes

```bash
cw stash list
```

Output is organized by worktree, making it easy to see which stashes belong to which feature.

### Applying Stashes

```bash
# Apply latest stash for a branch
cw stash apply fix-auth

# Apply specific stash to different worktree
cw stash apply feature-api --stash stash@{1}
```

This allows you to move uncommitted work between worktrees without committing.

### Workflow Example

```bash
# Working on feature-a, need to switch to urgent bug fix
cd myproject-feature-a
cw stash save "Half-done refactoring"

# Work on bug fix
cw resume fix-urgent-bug
# Fix bug...
cw merge fix-urgent-bug --push

# Return to original work
cw resume feature-a
cw stash list  # See all stashes by worktree
cw stash apply feature-a
```

## Synchronization

Keep worktrees in sync with their base branches.

### Basic Sync

```bash
# Sync current worktree
cw sync

# Sync specific worktree
cw sync fix-auth

# Sync all worktrees
cw sync --all
```

**What it does:**
1. Fetches latest changes from remote
2. Rebases feature branch onto updated base branch

### Fetch-Only Mode

```bash
# Only fetch, don't rebase
cw sync --fetch-only
```

Useful when you want to see what's changed without modifying your branch.

### AI-Assisted Conflict Resolution

```bash
# Get AI help with rebase conflicts
cw sync --ai-merge
```

When rebase conflicts occur, the AI tool helps you resolve them.

### Use Cases

#### Long-Running Feature Branch

```bash
# Start feature from develop branch
cw new big-refactor --base develop

# Work for a few days...
# Meanwhile, develop branch gets updates

# Stay synchronized with develop
cw sync big-refactor

# Check if you're behind
cw doctor
```

#### Team Collaboration

```bash
# Create feature and share
cw new team-feature
git push -u origin team-feature

# Team member pulls your worktree
cw new team-feature --base origin/team-feature

# Sync with latest changes from team
cw sync team-feature

# Or sync all your worktrees
cw sync --all
```

## Batch Cleanup

Clean up multiple worktrees based on various criteria.

### Cleanup by Status

```bash
# Delete merged worktrees
cw clean --merged

# Delete stale worktrees (deleted directories)
cw clean --stale
```

### Cleanup by Age

```bash
# Delete worktrees older than 30 days
cw clean --older-than 30

# Delete worktrees older than a week
cw clean --older-than 7
```

### Interactive Cleanup

```bash
# Interactive selection
cw clean -i
```

Shows a UI for selecting which worktrees to delete.

### Preview Mode

```bash
# Preview what would be deleted
cw clean --merged --dry-run
cw clean --older-than 30 --dry-run
```

Always shows what would be deleted without actually removing anything.

### Combine Criteria

```bash
# Delete merged worktrees older than 7 days
cw clean --merged --older-than 7

# Preview complex cleanup
cw clean --merged --stale --older-than 14 --dry-run
```

### Workflow Example

```bash
# Create experimental worktrees
cw new experiment-approach-a
cw new experiment-approach-b
cw new experiment-approach-c

# After testing, keep only what works
cw delete experiment-approach-a
cw delete experiment-approach-b
cw merge experiment-approach-c --push  # Keep the winner

# Or use batch cleanup
cw clean --merged           # Remove already-merged features
cw clean --older-than 7     # Remove week-old experiments
cw clean --stale            # Remove deleted directories
```

## Health Monitoring

Comprehensive health checks for all worktrees.

### Running Health Checks

```bash
cw doctor
```

**Performs these checks:**
- Git version compatibility (minimum 2.31.0)
- Worktree accessibility (detects stale worktrees)
- Uncommitted changes detection
- Worktrees behind base branch
- Existing merge conflicts
- Cleanup recommendations

### Interpreting Results

The doctor command provides:
- ✅ Green checks for healthy worktrees
- ⚠️ Yellow warnings for potential issues
- ❌ Red errors for problems requiring attention
- 💡 Recommendations for cleanup and optimization

### Example Output

```
Checking Git version... ✅ Git 2.35.0
Checking worktrees...
  - main: ✅ clean
  - feature-api: ⚠️ 5 commits behind main
  - fix-bug-123: ✅ clean
  - old-feature: ❌ stale (directory deleted)

Recommendations:
  - Run 'cw sync feature-api' to update with base branch
  - Run 'cw prune' to clean up stale worktree data
```

## Branch Management

### Changing Base Branch

Sometimes you realize after creating a worktree that you should have based it on a different branch.

```bash
# Change base for current worktree
cw change-base master

# Change base for specific worktree
cw change-base develop -t fix-auth

# Interactive rebase
cw change-base main -i

# Preview changes
cw change-base master --dry-run
```

**What it does:**
1. Rebases your feature branch onto the new base
2. Updates worktree metadata to track new base

### Example Workflow

```bash
# Oops! Should have based this on develop, not main
cw change-base develop

# Now the worktree tracks develop as its base branch
cw status
```

## Visualization & Analysis

### Worktree Hierarchy

```bash
cw tree
```

Displays ASCII tree showing:
- Base repository at root
- Feature worktrees as branches
- Status indicators (clean, modified, stale)
- Current worktree highlighting

**Example output:**
```
myproject/
├─ main (clean)
├─ feature-api (active) *
├─ fix-bug-123 (modified)
└─ refactor-db (clean)
```

### Statistics

```bash
cw stats
```

Shows comprehensive analytics:
- Total worktrees count and status distribution
- Age statistics (average, oldest, newest)
- Commit activity across worktrees
- Top 5 oldest worktrees
- Top 5 most active worktrees by commit count

### Branch Comparison

```bash
# Full diff between branches
cw diff main feature-api

# Show diff statistics only
cw diff main feature-api --summary

# Show changed files list
cw diff main feature-api --files
```

**Example output (summary):**
```
Comparing main...feature-api
Files changed: 15
Insertions: +234
Deletions: -67
```

## CI/CD Integration

Use `claude-worktree` in continuous integration pipelines.

### Example CI Pipeline

```bash
#!/bin/bash
# In CI pipeline script

# Disable AI tool and auto-updates
export CW_AI_TOOL="echo"  # No-op AI tool
cw config set update.auto_check false

# Create isolated test environment
cw new ci-test-${CI_BUILD_ID} --base ${CI_COMMIT_BRANCH}

# Run tests in worktree
cd ../repo-ci-test-${CI_BUILD_ID}
pytest

# Cleanup
cw delete ci-test-${CI_BUILD_ID}
```

### Best Practices for CI/CD

1. **Disable AI tool:**
   ```bash
   export CW_AI_TOOL="echo"
   ```

2. **Disable auto-updates:**
   ```bash
   cw config set update.auto_check false
   ```

3. **Use unique worktree names:**
   ```bash
   cw new ci-test-${CI_BUILD_ID}
   ```

4. **Always cleanup:**
   ```bash
   cw delete ci-test-${CI_BUILD_ID}
   ```

## Code Review Workflow

Review pull requests in isolated worktrees.

### Example Workflow

```bash
# Fetch PR branch
git fetch origin pull/123/head:pr-123

# Create worktree for review
cw new review-pr-123 --base pr-123

# Review and test changes
cw diff main review-pr-123 --summary
cw diff main review-pr-123 --files

# Run tests in isolated environment
cd ../myproject-review-pr-123
npm test

# Clean up after review
cw delete review-pr-123
```

## Advanced Git Integration

### How Metadata is Stored

`claude-worktree` stores metadata in git config:

```bash
# Stores base branch for feature branches
git config branch.<feature>.worktreeBase <base>

# Stores path to main repository
git config worktree.<feature>.basePath <path>
```

This allows commands like `pr` and `merge` to know:
1. Which branch to rebase onto
2. Where the main repository is located
3. How to safely perform operations

### Inspecting Metadata

```bash
# Show metadata for current worktree
cw status

# Or use git config directly
git config --get branch.<feature>.worktreeBase
git config --get worktree.<feature>.basePath
```

### Manual Metadata Management

In rare cases, you may need to manually update metadata:

```bash
# Update base branch
git config branch.my-feature.worktreeBase develop

# Update base repository path
git config worktree.my-feature.basePath /path/to/main/repo
```

## Best Practices

### 1. Regular Syncing

Keep worktrees updated with base branches:

```bash
# Daily sync
cw sync --all
```

### 2. Periodic Cleanup

Remove old worktrees regularly:

```bash
# Weekly cleanup
cw clean --merged --older-than 7
```

### 3. Health Checks

Run doctor periodically:

```bash
# Before starting new work
cw doctor
```

### 4. Backup Important Work

Backup before risky operations:

```bash
# Before major refactoring
cw backup create my-feature
```

### 5. Consistent Naming

Use descriptive branch names:

```bash
# Good
cw new fix-auth-timeout
cw new feature-user-dashboard

# Avoid
cw new temp
cw new test123
```

### 6. Choose the Right Workflow

**For teams:** Use `cw pr`
```bash
cw pr  # Create pull request
```

**For solo projects:** Use `cw merge`
```bash
cw merge --push  # Direct merge
```

## Performance Tips

### 1. Limit Number of Worktrees

Keep active worktrees under 10 for optimal performance.

### 2. Use `--fetch-only` When Appropriate

```bash
cw sync --fetch-only  # Faster, no rebase
```

### 3. Clean Up Regularly

```bash
cw clean --merged     # Remove merged worktrees
cw prune              # Clean stale data
```

### 4. Use Shallow Clones for Backups

For very large repositories, consider Git's shallow clone features (note: not directly supported by `cw backup` but can be done manually).

## Troubleshooting Advanced Features

### Backup/Restore Issues

**Problem:** "Backup not found"

**Solution:** Check backup location:
```bash
ls ~/.config/claude-worktree/backups/
cw backup list
```

**Problem:** "Restore failed"

**Solution:** Ensure git bundle is valid:
```bash
git bundle verify <bundle-file>
```

### Sync Issues

**Problem:** "Rebase conflicts"

**Solution:** Resolve manually or use AI assistance:
```bash
cw sync --ai-merge
```

**Problem:** "Cannot sync: uncommitted changes"

**Solution:** Commit or stash changes first:
```bash
cw stash save "WIP"
cw sync
cw stash apply <branch>
```

### Clean Issues

**Problem:** "Cannot delete worktree: uncommitted changes"

**Solution:** Use force delete or commit changes:
```bash
git -C <worktree-path> add -A
git -C <worktree-path> commit -m "Save work"
cw delete <branch>
```

For more troubleshooting help, see [TROUBLESHOOTING.md](../TROUBLESHOOTING.md).
