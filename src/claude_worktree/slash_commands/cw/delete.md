# Delete Worktree

Remove a worktree and optionally its branch.

## Usage

/cw:delete <target> [options]

## Arguments

- `target` - Branch name or worktree path to delete (required)

## Options

- `--keep-branch` - Keep the feature branch after deleting worktree
- `--delete-remote` - Also delete the remote branch

## Examples

```bash
/cw:delete old-feature
/cw:delete fix-auth --keep-branch
/cw:delete experimental --delete-remote
```

## What This Does

1. Removes the git worktree
2. Deletes the feature branch (unless --keep-branch)
3. Optionally deletes remote branch (if --delete-remote)

**Warning:** This is destructive. Make sure your work is committed/pushed before deleting.

---

Execute the command:

```bash
cw delete $ARGUMENTS
```

After execution, confirm what was deleted and remind the user if any remote cleanup is needed.
