# Claude Worktree Commands

Execute claude-worktree (cw) commands to manage git worktrees with AI assistance.

## Usage

/cw <subcommand> [arguments]

## Available Commands

**Worktree Management:**
- `new <branch>` - Create new worktree with branch name
- `resume [branch]` - Resume AI work in worktree (with context restoration)
- `list` - Show all worktrees
- `status` - Show current worktree metadata
- `delete <branch>` - Delete worktree and branch

**Completion Workflows:**
- `pr [branch]` - Create GitHub pull request (leaves worktree intact)
- `merge [branch]` - Merge to base branch and cleanup

**Maintenance:**
- `sync [branch]` - Sync with base branch changes
- `clean` - Batch cleanup of worktrees
- `doctor` - Health check on all worktrees

## Examples

```bash
/cw new feature-api          # Create new worktree
/cw list                     # Show all worktrees
/cw resume fix-auth          # Resume work with context
/cw pr                       # Create pull request
/cw merge --push             # Merge and push
/cw delete old-feature       # Delete worktree
```

## Notes

- Works with Happy, Claude Code, and Codex
- Session context is automatically saved/restored
- Use `cw --help` in terminal for full documentation

---

Execute the claude-worktree command:

```bash
cw $ARGUMENTS
```

After execution, explain what happened and show relevant output or next steps.
