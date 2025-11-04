# Create Pull Request

Create a GitHub pull request for the current worktree's branch.

## Usage

/cw:pr [branch] [options]

## Arguments

- `branch` - Branch to create PR for (optional, defaults to current)

## Options

- `--title <text>` - PR title (default: auto-generated)
- `--body <text>` - PR description
- `--draft` - Create as draft PR
- `--no-push` - Skip pushing to remote

## Examples

```bash
/cw:pr
/cw:pr fix-auth --title "Fix authentication bug"
/cw:pr --draft --body "Work in progress"
```

## What This Does

1. Rebases feature branch onto base branch
2. Pushes branch to remote (unless --no-push)
3. Creates GitHub PR using `gh` CLI
4. Leaves worktree intact for further work

**Note:** Worktree is NOT deleted - use `/cw:merge` if you want to merge and cleanup.

---

Execute the command:

```bash
cw pr $ARGUMENTS
```

After execution, show the PR URL and explain the next steps (review, merge, etc.).
