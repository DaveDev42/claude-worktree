# Resume AI Session

Resume AI work in a worktree with automatic context restoration.

## Usage

/cw:resume [branch] [options]

## Arguments

- `branch` - Branch/worktree to resume (optional, defaults to current)

## Options

- `--bg` - Launch in background
- `--iterm` - Launch in new iTerm2 window (macOS)
- `--iterm-tab` - Launch in new iTerm2 tab (macOS)
- `--tmux <name>` - Launch in tmux session

## Examples

```bash
/cw:resume fix-auth
/cw:resume feature-api --iterm-tab
/cw:resume --bg
```

## What This Does

1. Switches to the specified worktree (if branch argument provided)
2. Restores previous AI session history from ~/.config/claude-worktree/sessions/
3. Launches your configured AI tool with restored context
4. You can continue conversations from where you left off

---

Execute the command:

```bash
cw resume $ARGUMENTS
```

After execution, confirm that the AI session was launched and explain how the user can access it.
