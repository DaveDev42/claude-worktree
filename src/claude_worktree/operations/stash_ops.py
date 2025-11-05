"""Stash operations for claude-worktree."""

from pathlib import Path

from ..console import get_console
from ..exceptions import GitError, InvalidBranchError, WorktreeNotFoundError
from ..git_utils import find_worktree_by_branch, get_current_branch, get_repo_root, git_command

console = get_console()


def stash_save(message: str | None = None) -> None:
    """
    Save changes in current worktree to stash.

    Args:
        message: Optional message to describe the stash

    Raises:
        InvalidBranchError: If not in a git repository or branch cannot be determined
        GitError: If stash operation fails
    """
    cwd = Path.cwd()

    try:
        branch_name = get_current_branch(cwd)
    except InvalidBranchError:
        raise InvalidBranchError("Cannot determine current branch")

    # Create stash message with branch prefix
    stash_msg = f"[{branch_name}] {message}" if message else f"[{branch_name}] WIP"

    # Check if there are changes to stash
    status_result = git_command("status", "--porcelain", repo=cwd, capture=True)
    if not status_result.stdout.strip():
        console.print("[yellow]![/yellow] No changes to stash\n")
        return

    # Create stash (include untracked files)
    console.print(f"[yellow]Stashing changes in {branch_name}...[/yellow]")
    git_command("stash", "push", "--include-untracked", "-m", stash_msg, repo=cwd)
    console.print(f"[bold green]*[/bold green] Stashed changes: {stash_msg}\n")


def stash_list() -> None:
    """
    List all stashes organized by worktree/branch.

    Raises:
        GitError: If git operations fail
    """
    repo = get_repo_root()

    # Get all stashes
    result = git_command("stash", "list", repo=repo, capture=True)
    if not result.stdout.strip():
        console.print("[yellow]No stashes found[/yellow]\n")
        return

    console.print("\n[bold cyan]Stashes by worktree:[/bold cyan]\n")

    # Parse stashes and group by branch
    stashes_by_branch: dict[str, list[tuple[str, str, str]]] = {}

    for line in result.stdout.strip().splitlines():
        # Format: stash@{N}: On <branch>: [<branch>] <message>
        # or: stash@{N}: WIP on <branch>: <hash> <commit-message>
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue

        stash_ref = parts[0].strip()  # e.g., "stash@{0}"
        stash_info = parts[1].strip()  # e.g., "On feature-branch" or "WIP on feature-branch"
        stash_msg = parts[2].strip()  # The actual message

        # Try to extract branch from message if it has our format [branch-name]
        branch_name = "unknown"
        if stash_msg.startswith("[") and "]" in stash_msg:
            branch_name = stash_msg[1 : stash_msg.index("]")]
            stash_msg = stash_msg[stash_msg.index("]") + 1 :].strip()
        elif "On " in stash_info:
            # Extract from "On branch-name" format
            branch_name = stash_info.split("On ")[1].strip()
        elif "WIP on " in stash_info:
            # Extract from "WIP on branch-name" format
            branch_name = stash_info.split("WIP on ")[1].strip()

        if branch_name not in stashes_by_branch:
            stashes_by_branch[branch_name] = []
        stashes_by_branch[branch_name].append((stash_ref, stash_info, stash_msg))

    # Display stashes grouped by branch
    for branch, stashes in sorted(stashes_by_branch.items()):
        console.print(f"[bold green]{branch}[/bold green]:")
        for stash_ref, _stash_info, stash_msg in stashes:
            console.print(f"  {stash_ref}: {stash_msg}")
        console.print()


def stash_apply(target_branch: str, stash_ref: str = "stash@{0}") -> None:
    """
    Apply a stash to a different worktree.

    Args:
        target_branch: Branch name of worktree to apply stash to
        stash_ref: Stash reference (default: stash@{0} - most recent)

    Raises:
        WorktreeNotFoundError: If target worktree not found
        GitError: If stash apply fails
    """
    repo = get_repo_root()

    # Find the target worktree
    worktree_path_result = find_worktree_by_branch(repo, target_branch)
    if not worktree_path_result:
        worktree_path_result = find_worktree_by_branch(repo, f"refs/heads/{target_branch}")
    if not worktree_path_result:
        raise WorktreeNotFoundError(
            f"No worktree found for branch '{target_branch}'. "
            f"Use 'cw list' to see available worktrees."
        )

    worktree_path = worktree_path_result

    # Verify the stash exists
    verify_result = git_command("stash", "list", repo=repo, capture=True, check=False)
    if stash_ref not in verify_result.stdout:
        raise GitError(
            f"Stash '{stash_ref}' not found. Use 'cw stash list' to see available stashes."
        )

    console.print(f"\n[yellow]Applying {stash_ref} to {target_branch}...[/yellow]")

    try:
        # Apply the stash to the target worktree
        git_command("stash", "apply", stash_ref, repo=worktree_path)
        console.print(f"[bold green]*[/bold green] Stash applied to {target_branch}\n")
        console.print(f"[dim]Worktree path: {worktree_path}[/dim]\n")
    except GitError as e:
        console.print(f"[bold red]x[/bold red] Failed to apply stash: {e}\n")
        console.print(
            "[yellow]Tip:[/yellow] There may be conflicts. Check the worktree and resolve manually.\n"
        )
        raise
