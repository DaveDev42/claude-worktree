"""Operations package - organized worktree operations."""

# Worktree lifecycle operations
# AI tool integration
from .ai_tools import launch_ai_tool, resume_worktree, shell_worktree

# Backup/restore operations
from .backup_ops import backup_worktree, get_backups_dir, list_backups, restore_worktree

# Configuration operations
from .config_ops import change_base_branch, export_config, import_config

# Diagnostics
from .diagnostics import doctor

# Display/information operations
from .display import (
    diff_worktrees,
    get_worktree_status,
    list_worktrees,
    show_stats,
    show_status,
    show_tree,
)

# Git operations (PR/merge)
from .git_ops import create_pr_worktree, merge_worktree

# Stash operations
from .stash_ops import stash_apply, stash_list, stash_save
from .worktree_ops import (
    clean_worktrees,
    create_worktree,
    delete_worktree,
    finish_worktree,
    sync_worktree,
)

__all__ = [
    # Worktree operations
    "create_worktree",
    "finish_worktree",
    "delete_worktree",
    "sync_worktree",
    "clean_worktrees",
    # Git operations
    "create_pr_worktree",
    "merge_worktree",
    # AI tools
    "launch_ai_tool",
    "resume_worktree",
    "shell_worktree",
    # Stash
    "stash_save",
    "stash_list",
    "stash_apply",
    # Backup
    "backup_worktree",
    "get_backups_dir",
    "list_backups",
    "restore_worktree",
    # Config
    "export_config",
    "import_config",
    "change_base_branch",
    # Display
    "get_worktree_status",
    "list_worktrees",
    "show_status",
    "show_tree",
    "show_stats",
    "diff_worktrees",
    # Diagnostics
    "doctor",
]
