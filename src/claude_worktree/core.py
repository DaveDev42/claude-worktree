"""Core business logic for claude-worktree operations."""

import os
import shlex
import subprocess
import sys
from pathlib import Path

from rich.console import Console

from .constants import CONFIG_KEY_BASE_BRANCH, CONFIG_KEY_BASE_PATH, default_worktree_path
from .exceptions import (
    GitError,
    InvalidBranchError,
    MergeError,
    RebaseError,
    WorktreeNotFoundError,
)
from .git_utils import (
    branch_exists,
    find_worktree_by_branch,
    get_config,
    get_current_branch,
    get_repo_root,
    git_command,
    has_command,
    parse_worktrees,
    set_config,
    unset_config,
)

console = Console()


def create_worktree(
    branch_name: str,
    base_branch: str | None = None,
    path: Path | None = None,
    no_cd: bool = False,
    no_claude: bool = False,
    bg: bool = False,
    iterm: bool = False,
    tmux_session: str | None = None,
) -> Path:
    """
    Create a new worktree with a feature branch.

    Args:
        branch_name: Name for the new branch (user-specified, no timestamp)
        base_branch: Base branch to branch from (defaults to current branch)
        path: Custom path for worktree (defaults to ../<repo>-<branch>)
        no_cd: Don't change directory after creation
        no_claude: Don't launch Claude Code
        bg: Launch Claude in background
        iterm: Launch Claude in new iTerm window (macOS only)
        tmux_session: Launch Claude in new tmux session

    Returns:
        Path to the created worktree

    Raises:
        GitError: If git operations fail
        InvalidBranchError: If base branch is invalid
    """
    repo = get_repo_root()

    # Validate branch name
    from .git_utils import get_branch_name_error, is_valid_branch_name

    if not is_valid_branch_name(branch_name, repo):
        error_msg = get_branch_name_error(branch_name)
        raise InvalidBranchError(
            f"Invalid branch name: {error_msg}\n"
            f"Hint: Use alphanumeric characters, hyphens, and slashes. "
            f"Avoid special characters like emojis, backslashes, or control characters."
        )

    # Determine base branch
    if base_branch is None:
        try:
            base_branch = get_current_branch(repo)
        except InvalidBranchError:
            raise InvalidBranchError(
                "Cannot determine base branch. Specify with --base or checkout a branch first."
            )

    # Verify base branch exists
    if not branch_exists(base_branch, repo):
        raise InvalidBranchError(f"Base branch '{base_branch}' not found")

    # Determine worktree path
    if path is None:
        worktree_path = default_worktree_path(repo, branch_name)
    else:
        worktree_path = path.resolve()

    console.print("\n[bold cyan]Creating new worktree:[/bold cyan]")
    console.print(f"  Base branch: [green]{base_branch}[/green]")
    console.print(f"  New branch:  [green]{branch_name}[/green]")
    console.print(f"  Path:        [blue]{worktree_path}[/blue]\n")

    # Create worktree
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    git_command("fetch", "--all", "--prune", repo=repo)
    git_command("worktree", "add", "-b", branch_name, str(worktree_path), base_branch, repo=repo)

    # Store metadata
    set_config(CONFIG_KEY_BASE_BRANCH.format(branch_name), base_branch, repo=repo)
    set_config(CONFIG_KEY_BASE_PATH.format(branch_name), str(repo), repo=repo)

    console.print("[bold green]✓[/bold green] Worktree created successfully\n")

    # Change directory
    if not no_cd:
        os.chdir(worktree_path)
        console.print(f"Changed directory to: {worktree_path}")

    # Launch Claude Code
    if not no_claude:
        launch_claude(worktree_path, bg=bg, iterm=iterm, tmux_session=tmux_session)

    return worktree_path


def finish_worktree(push: bool = False) -> None:
    """
    Finish work on current worktree: rebase, merge, and cleanup.

    Args:
        push: Push base branch to origin after merge

    Raises:
        GitError: If git operations fail
        RebaseError: If rebase fails
        MergeError: If merge fails
        WorktreeNotFoundError: If base worktree not found
    """
    cwd = Path.cwd()

    try:
        feature_branch = get_current_branch(cwd)
    except InvalidBranchError:
        raise InvalidBranchError("Cannot determine current branch")

    # Get repo root from current worktree (might be the worktree itself)
    worktree_repo = get_repo_root()

    # Get metadata - base_path is the actual main repository
    base_branch = get_config(CONFIG_KEY_BASE_BRANCH.format(feature_branch), worktree_repo)
    base_path_str = get_config(CONFIG_KEY_BASE_PATH.format(feature_branch), worktree_repo)

    if not base_branch or not base_path_str:
        raise GitError(
            f"Missing metadata for branch '{feature_branch}'. "
            "Was this worktree created with 'cw new'?"
        )

    # base_path is the actual main repository root
    base_path = Path(base_path_str)
    repo = base_path

    console.print("\n[bold cyan]Finishing worktree:[/bold cyan]")
    console.print(f"  Feature:     [green]{feature_branch}[/green]")
    console.print(f"  Base:        [green]{base_branch}[/green]")
    console.print(f"  Repo:        [blue]{repo}[/blue]\n")

    # Rebase feature on base
    # Try to fetch from origin if it exists
    fetch_result = git_command("fetch", "--all", "--prune", repo=repo, check=False)

    # Check if origin remote exists and has the branch
    rebase_target = base_branch
    if fetch_result.returncode == 0:
        # Check if origin/base_branch exists
        check_result = git_command(
            "rev-parse", "--verify", f"origin/{base_branch}", repo=cwd, check=False, capture=True
        )
        if check_result.returncode == 0:
            rebase_target = f"origin/{base_branch}"

    console.print(f"[yellow]Rebasing {feature_branch} onto {rebase_target}...[/yellow]")

    try:
        git_command("rebase", rebase_target, repo=cwd)
    except GitError:
        # Abort the rebase
        git_command("rebase", "--abort", repo=cwd, check=False)
        raise RebaseError(
            f"Rebase failed. Please resolve conflicts manually:\n"
            f"  cd {cwd}\n"
            f"  git rebase {rebase_target}"
        )

    console.print("[bold green]✓[/bold green] Rebase successful\n")

    # Verify base path exists
    if not base_path.exists():
        raise WorktreeNotFoundError(f"Base repository not found at: {base_path}")

    # Fast-forward merge into base
    console.print(f"[yellow]Merging {feature_branch} into {base_branch}...[/yellow]")
    git_command("fetch", "--all", "--prune", repo=base_path, check=False)

    # Switch to base branch if needed
    try:
        current_base_branch = get_current_branch(base_path)
        if current_base_branch != base_branch:
            console.print(f"Switching base worktree to '{base_branch}'")
            git_command("switch", base_branch, repo=base_path)
    except InvalidBranchError:
        git_command("switch", base_branch, repo=base_path)

    # Perform fast-forward merge
    try:
        git_command("merge", "--ff-only", feature_branch, repo=base_path)
    except GitError:
        raise MergeError(
            f"Fast-forward merge failed. Manual intervention required:\n"
            f"  cd {base_path}\n"
            f"  git merge {feature_branch}"
        )

    console.print(f"[bold green]✓[/bold green] Merged {feature_branch} into {base_branch}\n")

    # Push to remote if requested
    if push:
        console.print(f"[yellow]Pushing {base_branch} to origin...[/yellow]")
        try:
            git_command("push", "origin", base_branch, repo=base_path)
            console.print("[bold green]✓[/bold green] Pushed to origin\n")
        except GitError as e:
            console.print(f"[yellow]⚠[/yellow] Push failed: {e}\n")

    # Cleanup: remove worktree and branch
    console.print("[yellow]Cleaning up worktree and branch...[/yellow]")

    # Store current worktree path before removal
    worktree_to_remove = str(cwd)

    # Change to base repo before removing current worktree
    # (can't run git commands from a removed directory)
    os.chdir(repo)

    git_command("worktree", "remove", worktree_to_remove, "--force", repo=repo)
    git_command("branch", "-D", feature_branch, repo=repo)

    # Remove metadata
    unset_config(CONFIG_KEY_BASE_BRANCH.format(feature_branch), repo=repo)
    unset_config(CONFIG_KEY_BASE_PATH.format(feature_branch), repo=repo)

    console.print("[bold green]✓ Cleanup complete![/bold green]\n")


def delete_worktree(
    target: str,
    keep_branch: bool = False,
    delete_remote: bool = False,
    no_force: bool = False,
) -> None:
    """
    Delete a worktree by branch name or path.

    Args:
        target: Branch name or worktree path
        keep_branch: Keep the branch, only remove worktree
        delete_remote: Also delete remote branch
        no_force: Don't use --force flag

    Raises:
        WorktreeNotFoundError: If worktree not found
        GitError: If git operations fail
    """
    repo = get_repo_root()

    # Determine if target is path or branch
    target_path = Path(target)
    if target_path.exists():
        # Target is a path
        worktree_path = str(target_path.resolve())
        # Find branch for this worktree
        branch_name: str | None = None
        for br, path in parse_worktrees(repo):
            if str(Path(path).resolve()) == worktree_path:
                if br != "(detached)":
                    # Normalize branch name: remove refs/heads/ prefix
                    branch_name = br[11:] if br.startswith("refs/heads/") else br
                break
        if branch_name is None and not keep_branch:
            console.print(
                "[yellow]⚠[/yellow] Worktree is detached or branch not found. "
                "Branch deletion will be skipped.\n"
            )
    else:
        # Target is a branch name
        branch_name = target
        # Try with and without refs/heads/ prefix
        worktree_path_result = find_worktree_by_branch(repo, branch_name)
        if not worktree_path_result:
            worktree_path_result = find_worktree_by_branch(repo, f"refs/heads/{branch_name}")
        if not worktree_path_result:
            raise WorktreeNotFoundError(
                f"No worktree found for branch '{branch_name}'. Try specifying the path directly."
            )
        worktree_path = worktree_path_result
        # Normalize branch_name to simple name without refs/heads/
        if branch_name.startswith("refs/heads/"):
            branch_name = branch_name[11:]

    # Safety check: don't delete main repository
    if Path(worktree_path).resolve() == repo.resolve():
        raise GitError("Cannot delete main repository worktree")

    # Remove worktree
    console.print(f"[yellow]Removing worktree: {worktree_path}[/yellow]")
    rm_args = ["worktree", "remove", worktree_path]
    if not no_force:
        rm_args.append("--force")
    git_command(*rm_args, repo=repo)
    console.print("[bold green]✓[/bold green] Worktree removed\n")

    # Delete branch if requested
    if branch_name and not keep_branch:
        console.print(f"[yellow]Deleting local branch: {branch_name}[/yellow]")
        git_command("branch", "-D", branch_name, repo=repo)

        # Remove metadata
        unset_config(CONFIG_KEY_BASE_BRANCH.format(branch_name), repo=repo)
        unset_config(CONFIG_KEY_BASE_PATH.format(branch_name), repo=repo)

        console.print("[bold green]✓[/bold green] Local branch and metadata removed\n")

        # Delete remote branch if requested
        if delete_remote:
            console.print(f"[yellow]Deleting remote branch: origin/{branch_name}[/yellow]")
            try:
                git_command("push", "origin", f":{branch_name}", repo=repo)
                console.print("[bold green]✓[/bold green] Remote branch deleted\n")
            except GitError as e:
                console.print(f"[yellow]⚠[/yellow] Remote branch deletion failed: {e}\n")


def list_worktrees() -> None:
    """List all worktrees for the current repository."""
    repo = get_repo_root()
    worktrees = parse_worktrees(repo)

    console.print(f"\n[bold cyan]Worktrees for repository:[/bold cyan] {repo}\n")
    console.print(f"{'BRANCH':<35} {'STATUS':<10} PATH")
    console.print("-" * 80)

    cwd = str(Path.cwd())
    for branch, path in worktrees:
        status = "active" if cwd.startswith(path) else "clean"
        rel_path = os.path.relpath(path, repo)
        console.print(f"{branch[:33]:<35} {status:<10} {rel_path}")

    console.print()


def show_status() -> None:
    """Show status of current worktree and list all worktrees."""
    repo = get_repo_root()

    try:
        branch = get_current_branch(Path.cwd())
        base = get_config(CONFIG_KEY_BASE_BRANCH.format(branch), repo)
        base_path = get_config(CONFIG_KEY_BASE_PATH.format(branch), repo)

        console.print("\n[bold cyan]Current worktree:[/bold cyan]")
        console.print(f"  Feature:  [green]{branch}[/green]")
        console.print(f"  Base:     [green]{base or 'N/A'}[/green]")
        console.print(f"  Base path: [blue]{base_path or 'N/A'}[/blue]\n")
    except (InvalidBranchError, GitError):
        console.print(
            "\n[yellow]Current directory is not a feature worktree "
            "or is the main repository.[/yellow]\n"
        )

    list_worktrees()


def prune_worktrees() -> None:
    """Prune stale worktree administrative data."""
    repo = get_repo_root()
    console.print("[yellow]Pruning stale worktrees...[/yellow]")
    git_command("worktree", "prune", repo=repo)
    console.print("[bold green]✓[/bold green] Prune complete\n")


def launch_claude(
    path: Path,
    bg: bool = False,
    iterm: bool = False,
    tmux_session: str | None = None,
) -> None:
    """
    Launch Claude Code in the specified directory.

    Args:
        path: Directory to launch Claude in
        bg: Launch in background
        iterm: Launch in new iTerm window (macOS only)
        tmux_session: Launch in new tmux session
    """
    if not has_command("claude"):
        console.print("[yellow]⚠[/yellow] Claude CLI not detected. Skipping Claude launch.\n")
        return

    cmd = "claude --dangerously-skip-permissions"

    if tmux_session:
        if not has_command("tmux"):
            raise GitError("tmux not installed. Remove --tmux option or install tmux.")
        subprocess.run(
            ["tmux", "new-session", "-ds", tmux_session, "bash", "-lc", cmd],
            cwd=str(path),
        )
        console.print(
            f"[bold green]✓[/bold green] Claude running in tmux session '{tmux_session}'\n"
        )
        return

    if iterm:
        if sys.platform != "darwin":
            raise GitError("--iterm option only works on macOS")
        script = f"""
        osascript <<'APPLESCRIPT'
        tell application "iTerm"
          activate
          set newWindow to (create window with default profile)
          tell current session of newWindow
            write text "cd {shlex.quote(str(path))} && {cmd}"
          end tell
        end tell
APPLESCRIPT
        """
        subprocess.run(["bash", "-lc", script], check=True)
        console.print("[bold green]✓[/bold green] Claude running in new iTerm window\n")
        return

    if bg:
        subprocess.Popen(["bash", "-lc", cmd], cwd=str(path))
        console.print("[bold green]✓[/bold green] Claude running in background\n")
    else:
        console.print("[cyan]Starting Claude Code (Ctrl+C to exit)...[/cyan]\n")
        subprocess.run(["bash", "-lc", cmd], cwd=str(path), check=False)


def attach_claude(
    bg: bool = False,
    iterm: bool = False,
    tmux_session: str | None = None,
) -> None:
    """
    Reattach Claude Code to the current worktree.

    Args:
        bg: Launch in background
        iterm: Launch in new iTerm window (macOS only)
        tmux_session: Launch in new tmux session
    """
    path = Path.cwd()
    console.print(f"[cyan]Attaching Claude to:[/cyan] {path}\n")
    launch_claude(path, bg=bg, iterm=iterm, tmux_session=tmux_session)
