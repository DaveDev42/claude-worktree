# Merge and Cleanup

Merge feature branch to base branch and clean up the worktree.

## Usage

/cw:merge [branch] [options]

## Arguments

- `branch` - Branch to merge (optional, defaults to current)

## Options

- `--push` - Push merged changes to remote
- `--interactive` - Interactive rebase before merge
- `--dry-run` - Show what would happen without doing it

## Examples

```bash
/cw:merge
/cw:merge fix-auth --push
/cw:merge --interactive --dry-run
```

## What This Does

1. Rebases feature branch onto base branch
2. Fast-forward merges into base branch
3. Optionally pushes to remote (if --push)
4. Deletes worktree
5. Deletes feature branch

**Warning:** This is destructive - worktree and branch will be deleted. Use `/cw:pr` if you want to keep the worktree.

---

Execute the command:

```bash
cw merge $ARGUMENTS
```

After execution, confirm what was merged and cleaned up, and show the current state of the base branch.
