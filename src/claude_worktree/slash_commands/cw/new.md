# Create New Worktree

Create a new git worktree with a feature branch and optionally launch an AI session.

## Usage

/cw:new <branch-name> [options]

## Arguments

- `branch-name` - Name for the new feature branch (required)

## Options

- `--path <path>` - Custom worktree path (default: ../<repo>-<branch>)
- `--no-launch` - Don't launch AI tool after creation
- `--base <branch>` - Base branch to create from (default: main)

## Examples

```bash
/cw:new feature-api
/cw:new fix-auth --base develop
/cw:new experimental --path /tmp/test --no-launch
```

## What This Does

1. Creates a new git worktree at the specified path
2. Creates and checks out a new feature branch
3. Stores metadata (base branch, base path) in git config
4. Optionally launches your configured AI tool in the new worktree

---

Execute the command:

```bash
cw new $ARGUMENTS
```

After execution, explain what worktree was created, where it's located, and what the next steps are.
