"""Core business logic for claude-worktree operations."""

import os
import shlex
import subprocess
import sys
from pathlib import Path

from rich.console import Console

from .config import get_ai_tool_command
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
    bg: bool = False,
    iterm: bool = False,
    iterm_tab: bool = False,
    tmux_session: str | None = None,
) -> Path:
    """
    Create a new worktree with a feature branch.

    Args:
        branch_name: Name for the new branch (user-specified, no timestamp)
        base_branch: Base branch to branch from (defaults to current branch)
        path: Custom path for worktree (defaults to ../<repo>-<branch>)
        no_cd: Don't change directory after creation
        bg: Launch AI tool in background
        iterm: Launch AI tool in new iTerm window (macOS only)
        iterm_tab: Launch AI tool in new iTerm tab (macOS only)
        tmux_session: Launch AI tool in new tmux session

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

    # Launch AI tool (if configured)
    launch_ai_tool(
        worktree_path, bg=bg, iterm=iterm, iterm_tab=iterm_tab, tmux_session=tmux_session
    )

    return worktree_path


def finish_worktree(
    target: str | None = None,
    push: bool = False,
    interactive: bool = False,
    dry_run: bool = False,
    ai_merge: bool = False,
) -> None:
    """
    Finish work on a worktree: rebase, merge, and cleanup.

    Args:
        target: Branch name of worktree to finish (optional, defaults to current directory)
        push: Push base branch to origin after merge
        interactive: Pause for confirmation before each step
        dry_run: Preview merge without executing
        ai_merge: Launch AI tool to help resolve conflicts if rebase fails

    Raises:
        GitError: If git operations fail
        RebaseError: If rebase fails
        MergeError: If merge fails
        WorktreeNotFoundError: If worktree not found
        InvalidBranchError: If branch is invalid
    """
    # Determine the worktree to work on
    if target:
        # Target branch specified - find its worktree path
        repo = get_repo_root()
        worktree_path_result = find_worktree_by_branch(repo, target)
        if not worktree_path_result:
            worktree_path_result = find_worktree_by_branch(repo, f"refs/heads/{target}")
        if not worktree_path_result:
            raise WorktreeNotFoundError(
                f"No worktree found for branch '{target}'. "
                f"Use 'cw list' to see available worktrees."
            )
        cwd = worktree_path_result
        # Normalize branch name
        feature_branch = target[11:] if target.startswith("refs/heads/") else target
    else:
        # No target specified - use current directory
        cwd = Path.cwd()
        try:
            feature_branch = get_current_branch(cwd)
        except InvalidBranchError:
            raise InvalidBranchError("Cannot determine current branch")

    # Get repo root from the worktree we're working on
    if target:
        # When target is specified, cwd is the worktree path we found
        # Need to get repo root from that worktree
        worktree_repo = get_repo_root(cwd)
    else:
        # When no target, use current directory's repo root
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

    # Dry-run mode: preview operations without executing
    if dry_run:
        console.print("[bold yellow]DRY RUN MODE - No changes will be made[/bold yellow]\n")
        console.print("[bold]The following operations would be performed:[/bold]\n")
        console.print("  1. [cyan]Fetch[/cyan] updates from remote")
        console.print(f"  2. [cyan]Rebase[/cyan] {feature_branch} onto {base_branch}")
        console.print(f"  3. [cyan]Switch[/cyan] to {base_branch} in base repository")
        console.print(f"  4. [cyan]Merge[/cyan] {feature_branch} into {base_branch} (fast-forward)")
        if push:
            console.print(f"  5. [cyan]Push[/cyan] {base_branch} to origin")
            console.print(f"  6. [cyan]Remove[/cyan] worktree at {cwd}")
            console.print(f"  7. [cyan]Delete[/cyan] local branch {feature_branch}")
            console.print("  8. [cyan]Clean up[/cyan] metadata")
        else:
            console.print(f"  5. [cyan]Remove[/cyan] worktree at {cwd}")
            console.print(f"  6. [cyan]Delete[/cyan] local branch {feature_branch}")
            console.print("  7. [cyan]Clean up[/cyan] metadata")
        console.print("\n[dim]Run without --dry-run to execute these operations.[/dim]\n")
        return

    # Helper function for interactive prompts
    def confirm_step(step_name: str) -> bool:
        """Prompt user to confirm a step in interactive mode."""
        if not interactive:
            return True
        console.print(f"\n[bold yellow]Next step: {step_name}[/bold yellow]")
        response = input("Continue? [Y/n/q]: ").strip().lower()
        if response in ["q", "quit"]:
            console.print("[yellow]Aborting...[/yellow]")
            sys.exit(1)
        return response in ["", "y", "yes"]

    # Rebase feature on base
    if not confirm_step(f"Rebase {feature_branch} onto {base_branch}"):
        console.print("[yellow]Skipping rebase step...[/yellow]")
        return

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
        # Rebase failed - check if there are conflicts
        conflicts_result = git_command(
            "diff", "--name-only", "--diff-filter=U", repo=cwd, capture=True, check=False
        )
        conflicted_files = (
            conflicts_result.stdout.strip().splitlines() if conflicts_result.returncode == 0 else []
        )

        if conflicted_files and ai_merge:
            # Offer AI assistance for conflict resolution
            console.print("\n[bold yellow]⚠ Rebase conflicts detected![/bold yellow]\n")
            console.print("[cyan]Conflicted files:[/cyan]")
            for file in conflicted_files:
                console.print(f"  • {file}")
            console.print()

            from rich.prompt import Confirm

            if Confirm.ask("Would you like AI to help resolve these conflicts?", default=True):
                console.print("\n[cyan]Launching AI tool with conflict context...[/cyan]\n")

                # Create context message for AI
                context = "# Merge Conflict Resolution\n\n"
                context += f"Branch '{feature_branch}' has conflicts when rebasing onto '{rebase_target}'.\n\n"
                context += f"Conflicted files ({len(conflicted_files)}):\n"
                for file in conflicted_files:
                    context += f"  - {file}\n"
                context += "\n"
                context += "Please help resolve these conflicts. For each file:\n"
                context += "1. Review the conflict markers (<<<<<<< ======= >>>>>>>)\n"
                context += "2. Choose or merge the appropriate changes\n"
                context += "3. Remove the conflict markers\n"
                context += "4. Stage the resolved files with: git add <file>\n"
                context += "5. Continue the rebase with: git rebase --continue\n"

                # Save context to temporary file
                from .session_manager import save_context

                save_context(feature_branch, context)

                # Launch AI tool in the worktree
                launch_ai_tool(cwd, bg=False)

                console.print("\n[yellow]After resolving conflicts with AI:[/yellow]")
                console.print("  1. Stage resolved files: [cyan]git add <files>[/cyan]")
                console.print("  2. Continue rebase: [cyan]git rebase --continue[/cyan]")
                console.print("  3. Re-run: [cyan]cw finish[/cyan]\n")
                sys.exit(0)

        # Abort the rebase
        git_command("rebase", "--abort", repo=cwd, check=False)
        error_msg = f"Rebase failed. Please resolve conflicts manually:\n  cd {cwd}\n  git rebase {rebase_target}"
        if conflicted_files:
            error_msg += f"\n\nConflicted files ({len(conflicted_files)}):"
            for file in conflicted_files:
                error_msg += f"\n  • {file}"
            error_msg += "\n\nTip: Use --ai-merge flag to get AI assistance with conflicts"
        raise RebaseError(error_msg)

    console.print("[bold green]✓[/bold green] Rebase successful\n")

    # Verify base path exists
    if not base_path.exists():
        raise WorktreeNotFoundError(f"Base repository not found at: {base_path}")

    # Fast-forward merge into base
    if not confirm_step(f"Merge {feature_branch} into {base_branch}"):
        console.print("[yellow]Skipping merge step...[/yellow]")
        return

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
        if not confirm_step(f"Push {base_branch} to origin"):
            console.print("[yellow]Skipping push step...[/yellow]")
        else:
            console.print(f"[yellow]Pushing {base_branch} to origin...[/yellow]")
            try:
                git_command("push", "origin", base_branch, repo=base_path)
                console.print("[bold green]✓[/bold green] Pushed to origin\n")
            except GitError as e:
                console.print(f"[yellow]⚠[/yellow] Push failed: {e}\n")

    # Cleanup: remove worktree and branch
    if not confirm_step(f"Clean up worktree and delete branch {feature_branch}"):
        console.print("[yellow]Skipping cleanup step...[/yellow]")
        return

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
            if path.resolve() == Path(worktree_path):
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
        worktree_path = str(worktree_path_result)
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


def sync_worktree(
    target: str | None = None,
    all_worktrees: bool = False,
    fetch_only: bool = False,
    ai_merge: bool = False,
) -> None:
    """
    Synchronize worktree(s) with base branch changes.

    Args:
        target: Branch name of worktree to sync (optional, defaults to current directory)
        all_worktrees: Sync all worktrees
        fetch_only: Only fetch updates without rebasing
        ai_merge: Launch AI tool to help resolve conflicts if rebase fails

    Raises:
        WorktreeNotFoundError: If worktree not found
        GitError: If git operations fail
        RebaseError: If rebase fails
    """
    repo = get_repo_root()

    # Determine which worktrees to sync
    if all_worktrees:
        # Sync all worktrees
        worktrees_to_sync = []
        for branch, path in parse_worktrees(repo):
            # Skip main repository and detached worktrees
            if path.resolve() == repo.resolve() or branch == "(detached)":
                continue
            # Normalize branch name
            branch_name = branch[11:] if branch.startswith("refs/heads/") else branch
            worktrees_to_sync.append((branch_name, path))
    elif target:
        # Sync specific worktree by branch name
        worktree_path_result = find_worktree_by_branch(repo, target)
        if not worktree_path_result:
            worktree_path_result = find_worktree_by_branch(repo, f"refs/heads/{target}")
        if not worktree_path_result:
            raise WorktreeNotFoundError(
                f"No worktree found for branch '{target}'. "
                f"Use 'cw list' to see available worktrees."
            )
        branch_name = target[11:] if target.startswith("refs/heads/") else target
        worktrees_to_sync = [(branch_name, worktree_path_result)]
    else:
        # Sync current worktree
        cwd = Path.cwd()
        try:
            branch_name = get_current_branch(cwd)
        except InvalidBranchError:
            raise InvalidBranchError("Cannot determine current branch")
        worktrees_to_sync = [(branch_name, cwd)]

    # Fetch from all remotes first
    console.print("[yellow]Fetching updates from remote...[/yellow]")
    fetch_result = git_command("fetch", "--all", "--prune", repo=repo, check=False)
    if fetch_result.returncode != 0:
        console.print("[yellow]⚠[/yellow] Fetch failed or no remote configured\n")

    if fetch_only:
        console.print("[bold green]✓[/bold green] Fetch complete\n")
        return

    # Sync each worktree
    for branch, worktree_path in worktrees_to_sync:
        # Get base branch from metadata
        base_branch = get_config(CONFIG_KEY_BASE_BRANCH.format(branch), repo)
        if not base_branch:
            console.print(
                f"\n[yellow]⚠[/yellow] Skipping {branch}: "
                f"No base branch metadata (not created with 'cw new')\n"
            )
            continue

        console.print("\n[bold cyan]Syncing worktree:[/bold cyan]")
        console.print(f"  Feature: [green]{branch}[/green]")
        console.print(f"  Base:    [green]{base_branch}[/green]")
        console.print(f"  Path:    [blue]{worktree_path}[/blue]\n")

        # Determine rebase target (prefer origin/base if available)
        rebase_target = base_branch
        if fetch_result.returncode == 0:
            check_result = git_command(
                "rev-parse",
                "--verify",
                f"origin/{base_branch}",
                repo=worktree_path,
                check=False,
                capture=True,
            )
            if check_result.returncode == 0:
                rebase_target = f"origin/{base_branch}"

        # Rebase feature branch onto base
        console.print(f"[yellow]Rebasing {branch} onto {rebase_target}...[/yellow]")

        try:
            git_command("rebase", rebase_target, repo=worktree_path)
            console.print("[bold green]✓[/bold green] Rebase successful")
        except GitError:
            # Rebase failed - check if there are conflicts
            conflicts_result = git_command(
                "diff",
                "--name-only",
                "--diff-filter=U",
                repo=worktree_path,
                capture=True,
                check=False,
            )
            conflicted_files = (
                conflicts_result.stdout.strip().splitlines()
                if conflicts_result.returncode == 0
                else []
            )

            if conflicted_files and ai_merge and not all_worktrees:
                # Offer AI assistance for conflict resolution
                console.print("\n[bold yellow]⚠ Rebase conflicts detected![/bold yellow]\n")
                console.print("[cyan]Conflicted files:[/cyan]")
                for file in conflicted_files:
                    console.print(f"  • {file}")
                console.print()

                from rich.prompt import Confirm

                if Confirm.ask("Would you like AI to help resolve these conflicts?", default=True):
                    console.print("\n[cyan]Launching AI tool with conflict context...[/cyan]\n")

                    # Create context message for AI
                    context = "# Sync Rebase Conflict Resolution\n\n"
                    context += (
                        f"Branch '{branch}' has conflicts when rebasing onto '{rebase_target}'.\n\n"
                    )
                    context += f"Conflicted files ({len(conflicted_files)}):\n"
                    for file in conflicted_files:
                        context += f"  - {file}\n"
                    context += "\n"
                    context += "Please help resolve these conflicts. For each file:\n"
                    context += "1. Review the conflict markers (<<<<<<< ======= >>>>>>>)\n"
                    context += "2. Choose or merge the appropriate changes\n"
                    context += "3. Remove the conflict markers\n"
                    context += "4. Stage the resolved files with: git add <file>\n"
                    context += "5. Continue the rebase with: git rebase --continue\n"

                    # Save context to temporary file
                    from .session_manager import save_context

                    save_context(branch, context)

                    # Launch AI tool in the worktree
                    launch_ai_tool(worktree_path, bg=False)

                    console.print("\n[yellow]After resolving conflicts with AI:[/yellow]")
                    console.print("  1. Stage resolved files: [cyan]git add <files>[/cyan]")
                    console.print("  2. Continue rebase: [cyan]git rebase --continue[/cyan]")
                    console.print("  3. Re-run: [cyan]cw sync[/cyan]\n")
                    sys.exit(0)

            # Abort the rebase
            git_command("rebase", "--abort", repo=worktree_path, check=False)
            error_msg = f"Rebase failed. Please resolve conflicts manually:\n  cd {worktree_path}\n  git rebase {rebase_target}"
            if conflicted_files:
                error_msg += f"\n\nConflicted files ({len(conflicted_files)}):"
                for file in conflicted_files:
                    error_msg += f"\n  • {file}"
                if not ai_merge:
                    error_msg += "\n\nTip: Use --ai-merge flag to get AI assistance with conflicts"

            if all_worktrees:
                console.print(f"[bold red]✗[/bold red] {error_msg}")
                console.print("[yellow]Continuing with remaining worktrees...[/yellow]")
                continue
            else:
                raise RebaseError(error_msg)

    console.print("\n[bold green]✓ Sync complete![/bold green]\n")


def clean_worktrees(
    merged: bool = False,
    stale: bool = False,
    older_than: int | None = None,
    interactive: bool = False,
    dry_run: bool = False,
) -> None:
    """
    Batch cleanup of worktrees based on various criteria.

    Args:
        merged: Delete worktrees for branches already merged to base
        stale: Delete worktrees with 'stale' status
        older_than: Delete worktrees older than N days
        interactive: Interactive selection UI
        dry_run: Show what would be deleted without actually deleting

    Raises:
        GitError: If git operations fail
    """
    import time

    repo = get_repo_root()
    worktrees_to_delete: list[tuple[str, str, str]] = []

    # Collect worktrees matching criteria
    for branch, path in parse_worktrees(repo):
        # Skip main repository
        if path.resolve() == repo.resolve():
            continue

        # Skip detached worktrees
        if branch == "(detached)":
            continue

        # Normalize branch name
        branch_name = branch[11:] if branch.startswith("refs/heads/") else branch

        should_delete = False
        reasons = []

        # Check stale status
        if stale:
            status = get_worktree_status(str(path), repo)
            if status == "stale":
                should_delete = True
                reasons.append("stale (directory missing)")

        # Check if merged
        if merged:
            base_branch = get_config(CONFIG_KEY_BASE_BRANCH.format(branch_name), repo)
            if base_branch:
                # Check if branch is merged into base
                try:
                    # Use git branch --merged to check
                    result = git_command(
                        "branch",
                        "--merged",
                        base_branch,
                        "--format=%(refname:short)",
                        repo=repo,
                        capture=True,
                    )
                    merged_branches = result.stdout.strip().splitlines()
                    if branch_name in merged_branches:
                        should_delete = True
                        reasons.append(f"merged into {base_branch}")
                except GitError:
                    pass

        # Check age
        if older_than is not None and path.exists():
            try:
                # Get last modification time of the worktree directory
                mtime = path.stat().st_mtime
                age_days = (time.time() - mtime) / (24 * 3600)
                if age_days > older_than:
                    should_delete = True
                    reasons.append(f"older than {older_than} days ({age_days:.1f} days)")
            except OSError:
                pass

        if should_delete:
            reason_str = ", ".join(reasons)
            worktrees_to_delete.append((branch_name, str(path), reason_str))

    # If no criteria specified, show error
    if not merged and not stale and older_than is None and not interactive:
        console.print(
            "[bold red]Error:[/bold red] Please specify at least one cleanup criterion:\n"
            "  --merged, --stale, --older-than, or -i/--interactive"
        )
        return

    # If nothing to delete
    if not worktrees_to_delete and not interactive:
        console.print("[bold green]✓[/bold green] No worktrees match the cleanup criteria\n")
        return

    # Interactive mode: let user select which ones to delete
    if interactive:
        console.print("[bold cyan]Available worktrees:[/bold cyan]\n")
        all_worktrees: list[tuple[str, str, str]] = []
        for branch, path in parse_worktrees(repo):
            if path.resolve() == repo.resolve() or branch == "(detached)":
                continue
            branch_name = branch[11:] if branch.startswith("refs/heads/") else branch
            status = get_worktree_status(str(path), repo)
            all_worktrees.append((branch_name, str(path), status))
            console.print(f"  [{status:8}] {branch_name:<30} {path}")

        console.print()
        console.print("Enter branch names to delete (space-separated), or 'all' for all:")
        user_input = input("> ").strip()

        if user_input.lower() == "all":
            worktrees_to_delete = [(b, p, "user selected") for b, p, _ in all_worktrees]
        else:
            selected = user_input.split()
            worktrees_to_delete = [
                (b, p, "user selected") for b, p, _ in all_worktrees if b in selected
            ]

        if not worktrees_to_delete:
            console.print("[yellow]No worktrees selected for deletion[/yellow]")
            return

    # Show what will be deleted
    console.print(
        f"\n[bold yellow]{'DRY RUN: ' if dry_run else ''}Worktrees to delete:[/bold yellow]\n"
    )
    for branch, worktree_path, reason in worktrees_to_delete:
        console.print(f"  • {branch:<30} ({reason})")
        console.print(f"    Path: {worktree_path}")

    console.print()

    if dry_run:
        console.print(f"[bold cyan]Would delete {len(worktrees_to_delete)} worktree(s)[/bold cyan]")
        console.print("Run without --dry-run to actually delete them")
        return

    # Confirm deletion (unless in non-interactive mode with specific criteria)
    if interactive or len(worktrees_to_delete) > 3:
        console.print(f"[bold red]Delete {len(worktrees_to_delete)} worktree(s)?[/bold red]")
        confirm = input("Type 'yes' to confirm: ").strip().lower()
        if confirm != "yes":
            console.print("[yellow]Deletion cancelled[/yellow]")
            return

    # Delete worktrees
    console.print()
    deleted_count = 0
    for branch, _path, _ in worktrees_to_delete:
        console.print(f"[yellow]Deleting {branch}...[/yellow]")
        try:
            # Use delete_worktree function
            delete_worktree(target=branch, keep_branch=False, delete_remote=False, no_force=False)
            console.print(f"[bold green]✓[/bold green] Deleted {branch}")
            deleted_count += 1
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Failed to delete {branch}: {e}")

    console.print(
        f"\n[bold green]✓ Cleanup complete! Deleted {deleted_count} worktree(s)[/bold green]\n"
    )


def doctor() -> None:
    """
    Perform health check on all worktrees.

    Checks:
    - Git version compatibility
    - Worktree accessibility
    - Uncommitted changes
    - Worktrees behind base branch
    - Existing merge conflicts
    - Cleanup recommendations
    """
    import subprocess

    from packaging.version import parse

    repo = get_repo_root()
    console.print("\n[bold cyan]🏥 claude-worktree Health Check[/bold cyan]\n")

    issues_found = 0
    warnings_found = 0

    # 1. Check Git version
    console.print("[bold]1. Checking Git version...[/bold]")
    try:
        result = subprocess.run(
            ["git", "--version"], capture_output=True, text=True, check=True, timeout=5
        )
        version_output = result.stdout.strip()
        # Extract version number (e.g., "git version 2.39.0" or "git version 2.50.1 (Apple Git-155)")
        # Take the third word which is always the version number
        parts = version_output.split()
        if len(parts) >= 3:
            version_str = parts[2]
        else:
            version_str = parts[-1]
        git_version = parse(version_str)
        min_version = parse("2.31.0")

        if git_version >= min_version:
            console.print(f"   [green]✓[/green] Git version {version_str} (minimum: 2.31.0)")
        else:
            console.print(f"   [red]✗[/red] Git version {version_str} is too old (minimum: 2.31.0)")
            issues_found += 1
    except Exception as e:
        console.print(f"   [red]✗[/red] Could not detect Git version: {e}")
        issues_found += 1

    console.print()

    # 2. Check all worktrees
    console.print("[bold]2. Checking worktree accessibility...[/bold]")
    worktrees: list[tuple[str, Path, str]] = []
    stale_count = 0
    for branch, path in parse_worktrees(repo):
        # Skip main repository
        if path.resolve() == repo.resolve():
            continue
        if branch == "(detached)":
            continue

        branch_name = branch[11:] if branch.startswith("refs/heads/") else branch
        status = get_worktree_status(str(path), repo)
        worktrees.append((branch_name, path, status))

        if status == "stale":
            stale_count += 1
            console.print(f"   [red]✗[/red] {branch_name}: Stale (directory missing)")
            issues_found += 1

    if stale_count == 0:
        console.print(f"   [green]✓[/green] All {len(worktrees)} worktrees are accessible")
    else:
        console.print(
            f"   [yellow]⚠[/yellow] {stale_count} stale worktree(s) found (use 'cw prune')"
        )

    console.print()

    # 3. Check for uncommitted changes
    console.print("[bold]3. Checking for uncommitted changes...[/bold]")
    dirty_worktrees: list[tuple[str, Path]] = []
    for branch_name, path, status in worktrees:
        if status in ["modified", "active"]:
            # Check if there are actual uncommitted changes
            try:
                diff_result = git_command(
                    "status",
                    "--porcelain",
                    repo=path,
                    capture=True,
                    check=False,
                )
                if diff_result.returncode == 0 and diff_result.stdout.strip():
                    dirty_worktrees.append((branch_name, path))
            except Exception:
                pass

    if dirty_worktrees:
        console.print(
            f"   [yellow]⚠[/yellow] {len(dirty_worktrees)} worktree(s) with uncommitted changes:"
        )
        for branch_name, _path in dirty_worktrees:
            console.print(f"      • {branch_name}")
        warnings_found += 1
    else:
        console.print("   [green]✓[/green] No uncommitted changes")

    console.print()

    # 4. Check if worktrees are behind base branch
    console.print("[bold]4. Checking if worktrees are behind base branch...[/bold]")
    behind_worktrees: list[tuple[str, str, str]] = []
    for branch_name, path, status in worktrees:
        if status == "stale":
            continue

        # Get base branch metadata
        base_branch = get_config(CONFIG_KEY_BASE_BRANCH.format(branch_name), repo)
        if not base_branch:
            continue

        try:
            # Fetch to get latest remote refs
            git_command("fetch", "--all", "--prune", repo=path, check=False)

            # Check if branch is behind origin/base
            merge_base_result = git_command(
                "merge-base",
                branch_name,
                f"origin/{base_branch}",
                repo=path,
                capture=True,
                check=False,
            )
            if merge_base_result.returncode != 0:
                continue

            merge_base = merge_base_result.stdout.strip()

            # Get current commit of base branch
            base_commit_result = git_command(
                "rev-parse",
                f"origin/{base_branch}",
                repo=path,
                capture=True,
                check=False,
            )
            if base_commit_result.returncode != 0:
                continue

            base_commit = base_commit_result.stdout.strip()

            # If merge base != base commit, then we're behind
            if merge_base != base_commit:
                # Count commits behind
                behind_count_result = git_command(
                    "rev-list",
                    "--count",
                    f"{branch_name}..origin/{base_branch}",
                    repo=path,
                    capture=True,
                    check=False,
                )
                if behind_count_result.returncode == 0:
                    behind_count = behind_count_result.stdout.strip()
                    behind_worktrees.append((branch_name, base_branch, behind_count))
        except Exception:
            pass

    if behind_worktrees:
        console.print(
            f"   [yellow]⚠[/yellow] {len(behind_worktrees)} worktree(s) behind base branch:"
        )
        for branch_name, base_branch, count in behind_worktrees:
            console.print(f"      • {branch_name}: {count} commit(s) behind {base_branch}")
        console.print("   [dim]Tip: Use 'cw sync --all' to update all worktrees[/dim]")
        warnings_found += 1
    else:
        console.print("   [green]✓[/green] All worktrees are up-to-date with base")

    console.print()

    # 5. Check for existing merge conflicts
    console.print("[bold]5. Checking for merge conflicts...[/bold]")
    conflicted_worktrees: list[tuple[str, list[str]]] = []
    for branch_name, path, status in worktrees:
        if status == "stale":
            continue

        try:
            # Check for unmerged files (conflicts)
            conflicts_result = git_command(
                "diff",
                "--name-only",
                "--diff-filter=U",
                repo=path,
                capture=True,
                check=False,
            )
            if conflicts_result.returncode == 0 and conflicts_result.stdout.strip():
                conflicted_files = conflicts_result.stdout.strip().splitlines()
                conflicted_worktrees.append((branch_name, conflicted_files))
        except Exception:
            pass

    if conflicted_worktrees:
        console.print(
            f"   [red]✗[/red] {len(conflicted_worktrees)} worktree(s) with merge conflicts:"
        )
        for branch_name, files in conflicted_worktrees:
            console.print(f"      • {branch_name}: {len(files)} conflicted file(s)")
        console.print("   [dim]Tip: Use 'cw finish --ai-merge' for AI-assisted resolution[/dim]")
        issues_found += 1
    else:
        console.print("   [green]✓[/green] No merge conflicts detected")

    console.print()

    # Summary
    console.print("[bold cyan]Summary:[/bold cyan]")
    if issues_found == 0 and warnings_found == 0:
        console.print("[bold green]✓ Everything looks healthy![/bold green]\n")
    else:
        if issues_found > 0:
            console.print(f"[bold red]✗ {issues_found} issue(s) found[/bold red]")
        if warnings_found > 0:
            console.print(f"[bold yellow]⚠ {warnings_found} warning(s) found[/bold yellow]")
        console.print()

    # Recommendations
    if stale_count > 0:
        console.print("[bold]Recommendations:[/bold]")
        console.print("  • Run [cyan]cw prune[/cyan] to clean up stale worktrees")
    if behind_worktrees:
        if not stale_count:
            console.print("[bold]Recommendations:[/bold]")
        console.print("  • Run [cyan]cw sync --all[/cyan] to update all worktrees")
    if conflicted_worktrees:
        if not stale_count and not behind_worktrees:
            console.print("[bold]Recommendations:[/bold]")
        console.print("  • Resolve conflicts in conflicted worktrees")
        console.print("  • Use [cyan]cw finish --ai-merge[/cyan] for AI assistance")

    if stale_count > 0 or behind_worktrees or conflicted_worktrees:
        console.print()


def diff_worktrees(branch1: str, branch2: str, summary: bool = False, files: bool = False) -> None:
    """
    Compare two worktrees or branches.

    Args:
        branch1: First branch name
        branch2: Second branch name
        summary: Show diff statistics only
        files: Show changed files only

    Raises:
        InvalidBranchError: If branches don't exist
        GitError: If git operations fail
    """
    repo = get_repo_root()

    # Verify both branches exist
    if not branch_exists(branch1, repo):
        raise InvalidBranchError(f"Branch '{branch1}' not found")
    if not branch_exists(branch2, repo):
        raise InvalidBranchError(f"Branch '{branch2}' not found")

    console.print("\n[bold cyan]Comparing branches:[/bold cyan]")
    console.print(f"  {branch1} [yellow]...[/yellow] {branch2}\n")

    # Choose diff format based on flags
    if files:
        # Show only changed files
        result = git_command(
            "diff",
            "--name-status",
            branch1,
            branch2,
            repo=repo,
            capture=True,
        )
        console.print("[bold]Changed files:[/bold]\n")
        if result.stdout.strip():
            for line in result.stdout.strip().splitlines():
                # Format: M  file.txt (Modified)
                # Format: A  file.txt (Added)
                # Format: D  file.txt (Deleted)
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    status_char, filename = parts
                    status_color = {
                        "M": "yellow",
                        "A": "green",
                        "D": "red",
                        "R": "cyan",  # Renamed
                        "C": "cyan",  # Copied
                    }.get(status_char[0], "white")
                    status_name = {
                        "M": "Modified",
                        "A": "Added",
                        "D": "Deleted",
                        "R": "Renamed",
                        "C": "Copied",
                    }.get(status_char[0], "Changed")
                    console.print(
                        f"  [{status_color}]{status_char}[/{status_color}]  {filename} ({status_name})"
                    )
        else:
            console.print("  [dim]No differences found[/dim]")
    elif summary:
        # Show diff statistics
        result = git_command(
            "diff",
            "--stat",
            branch1,
            branch2,
            repo=repo,
            capture=True,
        )
        console.print("[bold]Diff summary:[/bold]\n")
        if result.stdout.strip():
            console.print(result.stdout)
        else:
            console.print("  [dim]No differences found[/dim]")
    else:
        # Show full diff
        result = git_command(
            "diff",
            branch1,
            branch2,
            repo=repo,
            capture=True,
        )
        if result.stdout.strip():
            console.print(result.stdout)
        else:
            console.print("[dim]No differences found[/dim]\n")


def get_worktree_status(path: str, repo: Path) -> str:
    """
    Determine the status of a worktree.

    Args:
        path: Absolute path to the worktree directory
        repo: Repository root path

    Returns:
        Status string: "stale", "active", "modified", or "clean"
    """
    path_obj = Path(path)

    # Check if directory exists
    if not path_obj.exists():
        return "stale"

    # Check if currently in this worktree
    cwd = str(Path.cwd())
    if cwd.startswith(path):
        return "active"

    # Check for uncommitted changes
    try:
        result = git_command("status", "--porcelain", repo=path_obj, capture=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            return "modified"
    except Exception:
        # If we can't check status, assume clean
        pass

    return "clean"


def list_worktrees() -> None:
    """List all worktrees for the current repository."""
    repo = get_repo_root()
    worktrees = parse_worktrees(repo)

    console.print(f"\n[bold cyan]Worktrees for repository:[/bold cyan] {repo}\n")

    # Calculate maximum branch name length for dynamic column width
    max_branch_len = max((len(branch) for branch, _ in worktrees), default=20)
    # Cap at reasonable maximum but allow for long names
    col_width = min(max(max_branch_len + 2, 35), 60)

    console.print(f"{'BRANCH':<{col_width}} {'STATUS':<10} PATH")
    console.print("-" * (col_width + 50))

    # Status color mapping
    status_colors = {
        "active": "bold green",
        "clean": "green",
        "modified": "yellow",
        "stale": "red",
    }

    for branch, path in worktrees:
        status = get_worktree_status(str(path), repo)
        rel_path = os.path.relpath(str(path), repo)
        color = status_colors.get(status, "white")
        console.print(f"{branch:<{col_width}} [{color}]{status:<10}[/{color}] {rel_path}")

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


def launch_ai_tool(
    path: Path,
    bg: bool = False,
    iterm: bool = False,
    iterm_tab: bool = False,
    tmux_session: str | None = None,
) -> None:
    """
    Launch AI coding assistant in the specified directory.

    Args:
        path: Directory to launch AI tool in
        bg: Launch in background
        iterm: Launch in new iTerm window (macOS only)
        iterm_tab: Launch in new iTerm tab (macOS only)
        tmux_session: Launch in new tmux session
    """
    # Get configured AI tool command
    ai_cmd_parts = get_ai_tool_command()

    # Skip if no AI tool configured (empty array means no-op)
    if not ai_cmd_parts:
        return

    ai_tool_name = ai_cmd_parts[0]

    # Check if the command exists
    if not has_command(ai_tool_name):
        console.print(
            f"[yellow]⚠[/yellow] {ai_tool_name} not detected. "
            f"Install it or update your config with 'cw config set ai-tool <tool>'.\n"
        )
        return

    # Build command - add --dangerously-skip-permissions for Claude only
    cmd_parts = ai_cmd_parts.copy()
    if ai_tool_name == "claude":
        cmd_parts.append("--dangerously-skip-permissions")

    cmd = " ".join(shlex.quote(part) for part in cmd_parts)

    if tmux_session:
        if not has_command("tmux"):
            raise GitError("tmux not installed. Remove --tmux option or install tmux.")
        subprocess.run(
            ["tmux", "new-session", "-ds", tmux_session, "bash", "-lc", cmd],
            cwd=str(path),
        )
        console.print(
            f"[bold green]✓[/bold green] {ai_tool_name} running in tmux session '{tmux_session}'\n"
        )
        return

    if iterm_tab:
        if sys.platform != "darwin":
            raise GitError("--iterm-tab option only works on macOS")
        script = f"""
        osascript <<'APPLESCRIPT'
        tell application "iTerm"
          activate
          tell current window
            create tab with default profile
            tell current session
              write text "cd {shlex.quote(str(path))} && {cmd}"
            end tell
          end tell
        end tell
APPLESCRIPT
        """
        subprocess.run(["bash", "-lc", script], check=True)
        console.print(f"[bold green]✓[/bold green] {ai_tool_name} running in new iTerm tab\n")
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
        console.print(f"[bold green]✓[/bold green] {ai_tool_name} running in new iTerm window\n")
        return

    if bg:
        subprocess.Popen(["bash", "-lc", cmd], cwd=str(path))
        console.print(f"[bold green]✓[/bold green] {ai_tool_name} running in background\n")
    else:
        console.print(f"[cyan]Starting {ai_tool_name} (Ctrl+C to exit)...[/cyan]\n")
        subprocess.run(["bash", "-lc", cmd], cwd=str(path), check=False)


def resume_worktree(
    worktree: str | None = None,
    bg: bool = False,
    iterm: bool = False,
    iterm_tab: bool = False,
    tmux_session: str | None = None,
) -> None:
    """
    Resume AI work in a worktree with context restoration.

    Args:
        worktree: Branch name of worktree to resume (optional, defaults to current directory)
        bg: Launch AI tool in background
        iterm: Launch AI tool in new iTerm window (macOS only)
        iterm_tab: Launch AI tool in new iTerm tab (macOS only)
        tmux_session: Launch AI tool in new tmux session

    Raises:
        WorktreeNotFoundError: If worktree not found
        GitError: If git operations fail
    """
    from . import session_manager

    # Determine target directory
    if worktree:
        # Branch name specified - find its worktree path and change to it
        repo = get_repo_root()
        worktree_path_result = find_worktree_by_branch(repo, f"refs/heads/{worktree}")
        if not worktree_path_result:
            worktree_path_result = find_worktree_by_branch(repo, worktree)

        if not worktree_path_result:
            raise WorktreeNotFoundError(
                f"No worktree found for branch '{worktree}'. "
                f"Use 'cw list' to see available worktrees."
            )

        worktree_path = worktree_path_result
        os.chdir(worktree_path)
        console.print(f"[dim]Switched to worktree: {worktree_path}[/dim]\n")

        # Get branch name for session lookup
        try:
            branch_name = get_current_branch(worktree_path)
        except InvalidBranchError:
            raise InvalidBranchError(f"Cannot determine branch for worktree: {worktree_path}")
    else:
        # No branch specified - use current directory
        worktree_path = Path.cwd()
        try:
            branch_name = get_current_branch(worktree_path)
        except InvalidBranchError:
            raise InvalidBranchError("Cannot determine current branch")

    # Check for existing session
    if session_manager.session_exists(branch_name):
        console.print(f"[green]✓[/green] Found session for branch: [bold]{branch_name}[/bold]")

        # Load session metadata
        metadata = session_manager.load_session_metadata(branch_name)
        if metadata:
            console.print(f"[dim]  AI tool: {metadata.get('ai_tool', 'unknown')}[/dim]")
            console.print(f"[dim]  Last updated: {metadata.get('updated_at', 'unknown')}[/dim]")

        # Load context if available
        context = session_manager.load_context(branch_name)
        if context:
            console.print("\n[cyan]Previous context:[/cyan]")
            console.print(f"[dim]{context}[/dim]")

        console.print()
    else:
        console.print(
            f"[yellow]ℹ[/yellow] No previous session found for branch: [bold]{branch_name}[/bold]"
        )
        console.print()

    # Save session metadata and launch AI tool (if configured)
    ai_cmd = get_ai_tool_command()
    if ai_cmd:
        ai_tool_name = ai_cmd[0]
        session_manager.save_session_metadata(branch_name, ai_tool_name, str(worktree_path))
        console.print(f"[cyan]Resuming {ai_tool_name} in:[/cyan] {worktree_path}\n")
        launch_ai_tool(
            worktree_path, bg=bg, iterm=iterm, iterm_tab=iterm_tab, tmux_session=tmux_session
        )


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
        console.print("[yellow]⚠[/yellow] No changes to stash\n")
        return

    # Create stash (include untracked files)
    console.print(f"[yellow]Stashing changes in {branch_name}...[/yellow]")
    git_command("stash", "push", "--include-untracked", "-m", stash_msg, repo=cwd)
    console.print(f"[bold green]✓[/bold green] Stashed changes: {stash_msg}\n")


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
        console.print(f"[bold green]✓[/bold green] Stash applied to {target_branch}\n")
        console.print(f"[dim]Worktree path: {worktree_path}[/dim]\n")
    except GitError as e:
        console.print(f"[bold red]✗[/bold red] Failed to apply stash: {e}\n")
        console.print(
            "[yellow]Tip:[/yellow] There may be conflicts. Check the worktree and resolve manually.\n"
        )
        raise


def show_tree() -> None:
    """
    Display worktree hierarchy in a visual tree format.

    Shows:
    - Base repository at the root
    - All feature worktrees as branches
    - Status indicators for each worktree
    - Current/active worktree highlighting
    """
    repo = get_repo_root()
    worktrees = parse_worktrees(repo)
    cwd = Path.cwd()

    console.print(f"\n[bold cyan]{repo.name}/[/bold cyan] (base repository)")
    console.print(f"[dim]{repo}[/dim]\n")

    # Separate main repo from feature worktrees
    feature_worktrees = []
    for branch, path in worktrees:
        # Skip main repository
        if path.resolve() == repo.resolve():
            continue
        # Skip detached worktrees
        if branch == "(detached)":
            continue

        branch_name = branch[11:] if branch.startswith("refs/heads/") else branch
        status = get_worktree_status(str(path), repo)
        is_current = str(cwd).startswith(str(path))
        feature_worktrees.append((branch_name, path, status, is_current))

    if not feature_worktrees:
        console.print("[dim]  (no feature worktrees)[/dim]\n")
        return

    # Status icons
    status_icons = {
        "active": "●",  # current worktree
        "clean": "○",  # clean
        "modified": "◉",  # has changes
        "stale": "✗",  # directory missing
    }

    # Status colors
    status_colors = {
        "active": "bold green",
        "clean": "green",
        "modified": "yellow",
        "stale": "red",
    }

    # Sort by branch name for consistent display
    feature_worktrees.sort(key=lambda x: x[0])

    # Draw tree
    for i, (branch_name, path, status, is_current) in enumerate(feature_worktrees):
        is_last = i == len(feature_worktrees) - 1
        prefix = "└── " if is_last else "├── "

        # Status icon and color
        icon = status_icons.get(status, "○")
        color = status_colors.get(status, "white")

        # Highlight current worktree
        if is_current:
            branch_display = f"[bold {color}]★ {branch_name}[/bold {color}]"
        else:
            branch_display = f"[{color}]{branch_name}[/{color}]"

        # Show branch with status
        console.print(f"{prefix}[{color}]{icon}[/{color}] {branch_display}")

        # Show path (relative if possible, absolute otherwise)
        try:
            rel_path = path.relative_to(repo.parent)
            path_display = f"../{rel_path}"
        except ValueError:
            path_display = str(path)

        continuation = "    " if is_last else "│   "
        console.print(f"{continuation}[dim]{path_display}[/dim]")

    # Legend
    console.print("\n[bold]Legend:[/bold]")
    console.print(f"  [{status_colors['active']}]●[/{status_colors['active']}] active (current)")
    console.print(f"  [{status_colors['clean']}]○[/{status_colors['clean']}] clean")
    console.print(f"  [{status_colors['modified']}]◉[/{status_colors['modified']}] modified")
    console.print(f"  [{status_colors['stale']}]✗[/{status_colors['stale']}] stale")
    console.print("  [bold green]★[/bold green] currently active worktree\n")


def show_stats() -> None:
    """
    Display usage analytics for worktrees.

    Shows:
    - Total worktrees count
    - Active development time per worktree
    - Worktree age statistics
    - Status distribution
    """
    import time

    repo = get_repo_root()
    worktrees = parse_worktrees(repo)

    # Collect worktree data
    worktree_data: list[tuple[str, Path, str, float, int]] = []
    for branch, path in worktrees:
        # Skip main repository
        if path.resolve() == repo.resolve():
            continue
        # Skip detached worktrees
        if branch == "(detached)":
            continue

        branch_name = branch[11:] if branch.startswith("refs/heads/") else branch
        status = get_worktree_status(str(path), repo)

        # Get creation time (directory mtime)
        try:
            if path.exists():
                creation_time = path.stat().st_mtime
                age_days = (time.time() - creation_time) / (24 * 3600)

                # Count commits in this worktree
                try:
                    commit_count_result = git_command(
                        "rev-list", "--count", branch_name, repo=path, capture=True, check=False
                    )
                    commit_count = (
                        int(commit_count_result.stdout.strip())
                        if commit_count_result.returncode == 0
                        else 0
                    )
                except Exception:
                    commit_count = 0
            else:
                creation_time = 0.0
                age_days = 0.0
                commit_count = 0

            worktree_data.append((branch_name, path, status, age_days, commit_count))
        except Exception:
            continue

    if not worktree_data:
        console.print("\n[yellow]No feature worktrees found[/yellow]\n")
        return

    console.print("\n[bold cyan]📊 Worktree Statistics[/bold cyan]\n")

    # Overall statistics
    total_count = len(worktree_data)
    status_counts = {"clean": 0, "modified": 0, "active": 0, "stale": 0}
    for _, _, status, _, _ in worktree_data:
        status_counts[status] = status_counts.get(status, 0) + 1

    console.print("[bold]Overview:[/bold]")
    console.print(f"  Total worktrees: {total_count}")
    console.print(
        f"  Status: [green]{status_counts.get('clean', 0)} clean[/green], "
        f"[yellow]{status_counts.get('modified', 0)} modified[/yellow], "
        f"[bold green]{status_counts.get('active', 0)} active[/bold green], "
        f"[red]{status_counts.get('stale', 0)} stale[/red]"
    )
    console.print()

    # Age statistics
    ages = [age for _, _, _, age, _ in worktree_data if age > 0]
    if ages:
        avg_age = sum(ages) / len(ages)
        oldest_age = max(ages)
        newest_age = min(ages)

        console.print("[bold]Age Statistics:[/bold]")
        console.print(f"  Average age: {avg_age:.1f} days")
        console.print(f"  Oldest: {oldest_age:.1f} days")
        console.print(f"  Newest: {newest_age:.1f} days")
        console.print()

    # Commit statistics
    commits = [count for _, _, _, _, count in worktree_data if count > 0]
    if commits:
        total_commits = sum(commits)
        avg_commits = total_commits / len(commits)
        max_commits = max(commits)

        console.print("[bold]Commit Statistics:[/bold]")
        console.print(f"  Total commits across all worktrees: {total_commits}")
        console.print(f"  Average commits per worktree: {avg_commits:.1f}")
        console.print(f"  Most commits in a worktree: {max_commits}")
        console.print()

    # Top worktrees by age
    console.print("[bold]Oldest Worktrees:[/bold]")
    sorted_by_age = sorted(worktree_data, key=lambda x: x[3], reverse=True)[:5]
    for branch_name, _path, status, age_days, _ in sorted_by_age:
        if age_days > 0:
            status_icon = {"clean": "○", "modified": "◉", "active": "●", "stale": "✗"}.get(
                status, "○"
            )
            status_color = {
                "clean": "green",
                "modified": "yellow",
                "active": "bold green",
                "stale": "red",
            }.get(status, "white")
            age_str = format_age(age_days)
            console.print(
                f"  [{status_color}]{status_icon}[/{status_color}] {branch_name:<30} {age_str}"
            )
    console.print()

    # Most active worktrees by commit count
    console.print("[bold]Most Active Worktrees (by commits):[/bold]")
    sorted_by_commits = sorted(worktree_data, key=lambda x: x[4], reverse=True)[:5]
    for branch_name, _path, status, _age_days, commit_count in sorted_by_commits:
        if commit_count > 0:
            status_icon = {"clean": "○", "modified": "◉", "active": "●", "stale": "✗"}.get(
                status, "○"
            )
            status_color = {
                "clean": "green",
                "modified": "yellow",
                "active": "bold green",
                "stale": "red",
            }.get(status, "white")
            console.print(
                f"  [{status_color}]{status_icon}[/{status_color}] {branch_name:<30} {commit_count} commits"
            )
    console.print()


def format_age(age_days: float) -> str:
    """Format age in days to human-readable string."""
    if age_days < 1:
        hours = int(age_days * 24)
        return f"{hours}h ago" if hours > 0 else "just now"
    elif age_days < 7:
        return f"{int(age_days)}d ago"
    elif age_days < 30:
        weeks = int(age_days / 7)
        return f"{weeks}w ago"
    elif age_days < 365:
        months = int(age_days / 30)
        return f"{months}mo ago"
    else:
        years = int(age_days / 365)
        return f"{years}y ago"


def change_base_branch(
    new_base: str,
    target: str | None = None,
    interactive: bool = False,
    dry_run: bool = False,
) -> None:
    """
    Change the base branch for a worktree and rebase onto it.

    Args:
        new_base: New base branch name
        target: Branch name of worktree (optional, defaults to current directory)
        interactive: Use interactive rebase
        dry_run: Preview changes without executing

    Raises:
        WorktreeNotFoundError: If worktree not found
        InvalidBranchError: If base branch is invalid
        RebaseError: If rebase fails
        GitError: If git operations fail
    """
    # Determine the worktree to work on
    if target:
        # Target branch specified - find its worktree path
        repo = get_repo_root()
        worktree_path_result = find_worktree_by_branch(repo, target)
        if not worktree_path_result:
            worktree_path_result = find_worktree_by_branch(repo, f"refs/heads/{target}")
        if not worktree_path_result:
            raise WorktreeNotFoundError(
                f"No worktree found for branch '{target}'. "
                f"Use 'cw list' to see available worktrees."
            )
        worktree_path = worktree_path_result
        # Normalize branch name
        feature_branch = target[11:] if target.startswith("refs/heads/") else target
    else:
        # No target specified - use current directory
        worktree_path = Path.cwd()
        try:
            feature_branch = get_current_branch(worktree_path)
        except InvalidBranchError:
            raise InvalidBranchError("Cannot determine current branch")

    # Get repo root
    repo = get_repo_root(worktree_path)

    # Get current base branch metadata
    current_base = get_config(CONFIG_KEY_BASE_BRANCH.format(feature_branch), repo)
    if not current_base:
        raise GitError(
            f"No base branch metadata found for '{feature_branch}'. "
            "Was this worktree created with 'cw new'?"
        )

    # Verify new base branch exists
    if not branch_exists(new_base, repo):
        raise InvalidBranchError(f"Base branch '{new_base}' not found")

    console.print("\n[bold cyan]Changing base branch:[/bold cyan]")
    console.print(f"  Worktree:    [green]{feature_branch}[/green]")
    console.print(f"  Current base: [yellow]{current_base}[/yellow]")
    console.print(f"  New base:     [green]{new_base}[/green]")
    console.print(f"  Path:         [blue]{worktree_path}[/blue]\n")

    # Dry-run mode: preview operations without executing
    if dry_run:
        console.print("[bold yellow]DRY RUN MODE - No changes will be made[/bold yellow]\n")
        console.print("[bold]The following operations would be performed:[/bold]\n")
        console.print("  1. [cyan]Fetch[/cyan] updates from remote")
        console.print(f"  2. [cyan]Rebase[/cyan] {feature_branch} onto {new_base}")
        console.print(f"  3. [cyan]Update[/cyan] base branch metadata: {current_base} → {new_base}")
        console.print("\n[dim]Run without --dry-run to execute these operations.[/dim]\n")
        return

    # Fetch from remote
    console.print("[yellow]Fetching updates from remote...[/yellow]")
    fetch_result = git_command("fetch", "--all", "--prune", repo=repo, check=False)

    # Determine rebase target (prefer origin/new_base if available)
    rebase_target = new_base
    if fetch_result.returncode == 0:
        # Check if origin/new_base exists
        check_result = git_command(
            "rev-parse",
            "--verify",
            f"origin/{new_base}",
            repo=worktree_path,
            check=False,
            capture=True,
        )
        if check_result.returncode == 0:
            rebase_target = f"origin/{new_base}"

    console.print(f"[yellow]Rebasing {feature_branch} onto {rebase_target}...[/yellow]")

    # Build rebase command
    rebase_args = ["rebase"]
    if interactive:
        rebase_args.append("--interactive")
    rebase_args.append(rebase_target)

    try:
        git_command(*rebase_args, repo=worktree_path)
    except GitError:
        # Rebase failed - check if there are conflicts
        conflicts_result = git_command(
            "diff", "--name-only", "--diff-filter=U", repo=worktree_path, capture=True, check=False
        )
        conflicted_files = (
            conflicts_result.stdout.strip().splitlines() if conflicts_result.returncode == 0 else []
        )

        # Abort the rebase
        git_command("rebase", "--abort", repo=worktree_path, check=False)
        error_msg = f"Rebase failed. Please resolve conflicts manually:\n  cd {worktree_path}\n  git rebase {rebase_target}"
        if conflicted_files:
            error_msg += f"\n\nConflicted files ({len(conflicted_files)}):"
            for file in conflicted_files:
                error_msg += f"\n  • {file}"
            error_msg += (
                "\n\nAfter resolving conflicts, run 'cw change-base' again to update metadata."
            )
        raise RebaseError(error_msg)

    console.print("[bold green]✓[/bold green] Rebase successful\n")

    # Update base branch metadata
    console.print("[yellow]Updating base branch metadata...[/yellow]")
    set_config(CONFIG_KEY_BASE_BRANCH.format(feature_branch), new_base, repo=repo)
    console.print("[bold green]✓[/bold green] Base branch metadata updated\n")

    console.print(f"[bold green]✓ Base branch changed to '{new_base}'![/bold green]\n")


def export_config(output_file: Path | None = None) -> None:
    """
    Export worktree configuration and metadata to a file.

    Args:
        output_file: Path to export file (default: cw-export-<timestamp>.json)

    Raises:
        GitError: If git operations fail
    """
    import json
    from datetime import datetime

    from .config import load_config

    repo = get_repo_root()

    # Collect export data
    from typing import Any

    export_data: dict[str, Any] = {
        "export_version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "repository": str(repo),
        "config": load_config(),
        "worktrees": [],
    }

    # Collect worktree metadata
    for branch, path in parse_worktrees(repo):
        # Skip main repository
        if path.resolve() == repo.resolve():
            continue
        # Skip detached worktrees
        if branch == "(detached)":
            continue

        branch_name = branch[11:] if branch.startswith("refs/heads/") else branch

        # Get metadata for this worktree
        base_branch = get_config(CONFIG_KEY_BASE_BRANCH.format(branch_name), repo)
        base_path = get_config(CONFIG_KEY_BASE_PATH.format(branch_name), repo)

        worktree_info = {
            "branch": branch_name,
            "base_branch": base_branch,
            "base_path": base_path,
            "path": str(path),
            "status": get_worktree_status(str(path), repo),
        }

        export_data["worktrees"].append(worktree_info)

    # Determine output file
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_file = Path(f"cw-export-{timestamp}.json")

    # Write export file
    console.print(f"\n[yellow]Exporting configuration to:[/yellow] {output_file}")
    try:
        with open(output_file, "w") as f:
            json.dump(export_data, f, indent=2)
        console.print("[bold green]✓[/bold green] Export complete!\n")
        console.print("[bold]Exported:[/bold]")
        console.print(f"  • {len(export_data['worktrees'])} worktree(s)")
        console.print("  • Configuration settings")
        console.print(
            "\n[dim]Transfer this file to another machine and use 'cw import' to restore.[/dim]\n"
        )
    except OSError as e:
        raise GitError(f"Failed to write export file: {e}")


def import_config(import_file: Path, apply: bool = False) -> None:
    """
    Import worktree configuration and metadata from a file.

    Args:
        import_file: Path to import file
        apply: Apply imported configuration (default: preview only)

    Raises:
        GitError: If import fails
    """
    import json

    from .config import save_config

    if not import_file.exists():
        raise GitError(f"Import file not found: {import_file}")

    # Load import data
    console.print(f"\n[yellow]Loading import file:[/yellow] {import_file}\n")
    try:
        with open(import_file) as f:
            import_data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise GitError(f"Failed to read import file: {e}")

    # Validate format
    if "export_version" not in import_data:
        raise GitError("Invalid export file format")

    # Show import preview
    console.print("[bold cyan]Import Preview:[/bold cyan]\n")
    console.print(f"[bold]Exported from:[/bold] {import_data.get('repository', 'unknown')}")
    console.print(f"[bold]Exported at:[/bold] {import_data.get('exported_at', 'unknown')}")
    console.print(f"[bold]Worktrees:[/bold] {len(import_data.get('worktrees', []))}\n")

    if import_data.get("worktrees"):
        console.print("[bold]Worktrees to import:[/bold]")
        for wt in import_data["worktrees"]:
            console.print(f"  • {wt.get('branch', 'unknown')}")
            console.print(f"    Base: {wt.get('base_branch', 'unknown')}")
            console.print(f"    Original path: {wt.get('path', 'unknown')}")
            console.print()

    if not apply:
        console.print(
            "[bold yellow]Preview mode:[/bold yellow] No changes made. "
            "Use --apply to import configuration.\n"
        )
        return

    # Apply import
    console.print("[bold yellow]Applying import...[/bold yellow]\n")

    repo = get_repo_root()
    imported_count = 0

    # Import global configuration
    if "config" in import_data and import_data["config"]:
        console.print("[yellow]Importing global configuration...[/yellow]")
        try:
            save_config(import_data["config"])
            console.print("[bold green]✓[/bold green] Configuration imported\n")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Configuration import failed: {e}\n")

    # Import worktree metadata
    console.print("[yellow]Importing worktree metadata...[/yellow]\n")
    for wt in import_data.get("worktrees", []):
        branch = wt.get("branch")
        base_branch = wt.get("base_branch")

        if not branch or not base_branch:
            console.print("[yellow]⚠[/yellow] Skipping invalid worktree entry\n")
            continue

        # Check if branch exists locally
        if not branch_exists(branch, repo):
            console.print(
                f"[yellow]⚠[/yellow] Branch '{branch}' not found locally. "
                f"Create it with 'cw new {branch} --base {base_branch}'"
            )
            continue

        # Set metadata for this branch
        try:
            set_config(CONFIG_KEY_BASE_BRANCH.format(branch), base_branch, repo=repo)
            set_config(CONFIG_KEY_BASE_PATH.format(branch), str(repo), repo=repo)
            console.print(f"[bold green]✓[/bold green] Imported metadata for: {branch}")
            imported_count += 1
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Failed to import {branch}: {e}")

    console.print(
        f"\n[bold green]✓ Import complete! Imported {imported_count} worktree(s)[/bold green]\n"
    )
    console.print(
        "[dim]Note: This only imports metadata. "
        "Create actual worktrees with 'cw new' if they don't exist.[/dim]\n"
    )
