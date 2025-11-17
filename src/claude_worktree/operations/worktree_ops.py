"""Core worktree lifecycle operations."""

import os
import sys
import time
from pathlib import Path

from ..config import load_config
from ..console import get_console
from ..constants import CONFIG_KEY_BASE_BRANCH, CONFIG_KEY_BASE_PATH, default_worktree_path
from ..exceptions import (
    GitError,
    InvalidBranchError,
    MergeError,
    RebaseError,
    WorktreeNotFoundError,
)
from ..git_utils import (
    branch_exists,
    find_worktree_by_branch,
    get_config,
    get_current_branch,
    get_repo_root,
    git_command,
    has_command,
    parse_worktrees,
    remove_worktree_safe,
    set_config,
    unset_config,
)
from ..shared_files import share_files
from .ai_tools import launch_ai_tool, resume_worktree
from .display import get_worktree_status
from .git_ops import _is_branch_merged_via_gh
from .helpers import get_worktree_metadata, resolve_worktree_target

console = get_console()


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
    import sys

    import typer

    repo = get_repo_root()

    # Validate branch name
    from ..git_utils import find_worktree_by_branch, get_branch_name_error, is_valid_branch_name

    if not is_valid_branch_name(branch_name, repo):
        error_msg = get_branch_name_error(branch_name)
        raise InvalidBranchError(
            f"Invalid branch name: {error_msg}\n"
            f"Hint: Use alphanumeric characters, hyphens, and slashes. "
            f"Avoid special characters like emojis, backslashes, or control characters."
        )

    # Check if worktree already exists for this branch
    # Try both normalized name and refs/heads/ prefixed version
    existing_worktree = find_worktree_by_branch(repo, branch_name)
    if not existing_worktree:
        existing_worktree = find_worktree_by_branch(repo, f"refs/heads/{branch_name}")

    if existing_worktree:
        console.print(
            f"\n[bold yellow]! Worktree already exists[/bold yellow]\n"
            f"Branch '[cyan]{branch_name}[/cyan]' already has a worktree at:\n"
            f"  [blue]{existing_worktree}[/blue]\n"
        )

        # Only prompt if stdin is a TTY (not in scripts/tests)
        if sys.stdin.isatty():
            try:
                response = typer.confirm("Resume work in this worktree instead?", default=True)
                if response:
                    # User wants to resume - call resume_worktree
                    console.print(
                        f"\n[dim]Switching to resume mode for '[cyan]{branch_name}[/cyan]'...[/dim]\n"
                    )
                    resume_worktree(
                        worktree=branch_name,
                        bg=bg,
                        iterm=iterm,
                        iterm_tab=iterm_tab,
                        tmux_session=tmux_session,
                    )
                    return existing_worktree
                else:
                    # User declined - suggest alternatives
                    console.print(
                        f"\n[yellow]Tip:[/yellow] Try a different branch name or use:\n"
                        f"  [cyan]cw new {branch_name}-v2[/cyan]\n"
                        f"  [cyan]cw new {branch_name}-alt[/cyan]\n"
                    )
                    raise typer.Abort()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Operation cancelled[/yellow]")
                raise typer.Abort()
        else:
            # Non-interactive mode - fail with helpful message
            raise InvalidBranchError(
                f"Worktree for branch '{branch_name}' already exists at {existing_worktree}.\n"
                f"Use 'cw resume {branch_name}' to continue work, or choose a different branch name."
            )

    # Check if branch exists without worktree
    # (But skip this check if we already found an existing worktree above)
    branch_already_exists = False
    if branch_exists(branch_name, repo) and not existing_worktree:
        console.print(
            f"\n[bold yellow]! Branch already exists[/bold yellow]\n"
            f"Branch '[cyan]{branch_name}[/cyan]' already exists but has no worktree.\n"
        )

        # Only prompt if stdin is a TTY
        if sys.stdin.isatty():
            try:
                response = typer.confirm("Create worktree from this existing branch?", default=True)
                if response:
                    # Create from existing branch
                    console.print(
                        f"\n[dim]Creating worktree from existing branch '[cyan]{branch_name}[/cyan]'...[/dim]\n"
                    )
                    branch_already_exists = True
                else:
                    # User declined - suggest alternatives
                    console.print(
                        f"\n[yellow]Tip:[/yellow] To use a different branch name:\n"
                        f"  [cyan]cw new {branch_name}-v2[/cyan]\n"
                        f"\nOr delete the existing branch first:\n"
                        f"  [cyan]git branch -d {branch_name}[/cyan]  (if fully merged)\n"
                        f"  [cyan]git branch -D {branch_name}[/cyan]  (force delete)\n"
                    )
                    raise typer.Abort()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Operation cancelled[/yellow]")
                raise typer.Abort()
        else:
            # Non-interactive mode - proceed to create worktree from existing branch
            console.print(
                f"[dim]Creating worktree from existing branch '[cyan]{branch_name}[/cyan]'...[/dim]\n"
            )
            branch_already_exists = True

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

    # If branch already exists, create worktree without -b flag
    if branch_already_exists:
        git_command("worktree", "add", str(worktree_path), branch_name, repo=repo)
    else:
        git_command(
            "worktree", "add", "-b", branch_name, str(worktree_path), base_branch, repo=repo
        )

    # Store metadata
    set_config(CONFIG_KEY_BASE_BRANCH.format(branch_name), base_branch, repo=repo)
    set_config(CONFIG_KEY_BASE_PATH.format(branch_name), str(repo), repo=repo)

    console.print("[bold green]*[/bold green] Worktree created successfully\n")

    # Share files (node_modules, .venv, etc.) if enabled
    config = load_config()
    if config.get("worktree", {}).get("auto_share_files", True):
        try:
            share_files(repo, worktree_path)
        except Exception as e:
            # Non-fatal: warn but continue
            console.print(f"[yellow]![/yellow] Warning: Failed to share files: {e}\n")

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
    # Resolve worktree target to (path, branch, repo)
    cwd, feature_branch, worktree_repo = resolve_worktree_target(target)

    # Get metadata - base_path is the actual main repository
    base_branch, base_path = get_worktree_metadata(feature_branch, worktree_repo)
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
            # AI merge: resolve conflicts automatically
            console.print("\n[bold yellow]! Rebase conflicts detected![/bold yellow]\n")
            console.print("[cyan]Conflicted files:[/cyan]")
            for file in conflicted_files:
                console.print(f"  • {file}")
            console.print()

            console.print("\n[cyan]Launching AI to resolve conflicts automatically...[/cyan]\n")

            # Create detailed prompt for AI to actually resolve conflicts
            context = "Resolve the merge conflicts in this repository and complete the rebase.\n\n"
            context += "**Current situation:**\n"
            context += (
                f"- Branch '{feature_branch}' has conflicts when rebasing onto '{rebase_target}'\n"
            )
            context += "- A rebase is currently in progress\n"
            context += f"- {len(conflicted_files)} file(s) have conflicts\n\n"
            context += "**Conflicted files:**\n"
            for file in conflicted_files:
                context += f"- {file}\n"
            context += "\n"
            context += "**Your task:**\n"
            context += "1. Read each conflicted file to understand the conflicts\n"
            context += (
                "2. Resolve the conflicts by choosing the appropriate changes or merging them\n"
            )
            context += "3. Edit the files to remove conflict markers (<<<<<<< ======= >>>>>>>)\n"
            context += "4. Stage ALL resolved files using: `git add <file1> <file2> ...`\n"
            context += "5. Continue the rebase using: `git rebase --continue`\n"
            context += "6. If the rebase completes successfully, report back\n"
            context += "\n"
            context += "**Important:**\n"
            context += "- Make sure to actually execute the git commands, not just suggest them\n"
            context += "- Stage all conflicted files after resolving\n"
            context += "- Complete the entire rebase process\n"

            # Save context to temporary file (for session restoration)
            from ..session_manager import save_context

            save_context(feature_branch, context)

            # Launch AI tool with prompt for automated conflict resolution
            launch_ai_tool(cwd, bg=False, prompt=context)

            console.print("\n[yellow]AI conflict resolution completed.[/yellow]")
            console.print("[yellow]Verify the resolution and re-run if needed.[/yellow]\n")
            console.print("Re-run: [cyan]cw finish[/cyan] to continue\n")
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

    console.print("[bold green]*[/bold green] Rebase successful\n")

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

    console.print(f"[bold green]*[/bold green] Merged {feature_branch} into {base_branch}\n")

    # Push to remote if requested
    if push:
        if not confirm_step(f"Push {base_branch} to origin"):
            console.print("[yellow]Skipping push step...[/yellow]")
        else:
            console.print(f"[yellow]Pushing {base_branch} to origin...[/yellow]")
            try:
                git_command("push", "origin", base_branch, repo=base_path)
                console.print("[bold green]*[/bold green] Pushed to origin\n")
            except GitError as e:
                console.print(f"[yellow]![/yellow] Push failed: {e}\n")

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

    remove_worktree_safe(worktree_to_remove, repo=repo, force=True)
    git_command("branch", "-D", feature_branch, repo=repo)

    # Remove metadata
    unset_config(CONFIG_KEY_BASE_BRANCH.format(feature_branch), repo=repo)
    unset_config(CONFIG_KEY_BASE_PATH.format(feature_branch), repo=repo)

    console.print("[bold green]* Cleanup complete![/bold green]\n")


def delete_worktree(
    target: str | None = None,
    keep_branch: bool = False,
    delete_remote: bool = False,
    no_force: bool = False,
) -> None:
    """
    Delete a worktree by branch name or path.

    Args:
        target: Branch name or worktree path (optional, defaults to current directory)
        keep_branch: Keep the branch, only remove worktree
        delete_remote: Also delete remote branch
        no_force: Don't use --force flag

    Raises:
        WorktreeNotFoundError: If worktree not found
        GitError: If git operations fail
    """
    repo = get_repo_root()

    # If target is None, use current directory
    if target is None:
        target = str(Path.cwd())

    # Determine if target is path or branch
    target_path = Path(target)
    if target_path.exists():
        # Target is a path
        worktree_path = str(target_path.resolve())
        # Find branch for this worktree
        branch_name: str | None = None
        for br, path in parse_worktrees(repo):
            # Use samefile() for cross-platform path comparison
            try:
                if Path(worktree_path).samefile(path):
                    if br != "(detached)":
                        # Normalize branch name: remove refs/heads/ prefix
                        branch_name = br[11:] if br.startswith("refs/heads/") else br
                    break
            except (OSError, ValueError):
                # Fallback to resolved path comparison if samefile() fails
                if path.resolve() == Path(worktree_path):
                    if br != "(detached)":
                        branch_name = br[11:] if br.startswith("refs/heads/") else br
                    break
        if branch_name is None and not keep_branch:
            console.print(
                "[yellow]![/yellow] Worktree is detached or branch not found. "
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

    # Get main repo path from metadata if available (more reliable than get_repo_root when in worktree)
    if branch_name:
        base_path_str = get_config(CONFIG_KEY_BASE_PATH.format(branch_name), repo)
        if base_path_str:
            repo = Path(base_path_str)

    # Safety check: don't delete main repository
    try:
        if Path(worktree_path).samefile(repo):
            raise GitError("Cannot delete main repository worktree")
    except (OSError, ValueError):
        # Fallback if samefile() fails
        if Path(worktree_path).resolve() == repo.resolve():
            raise GitError("Cannot delete main repository worktree")

    # Windows workaround: change to main repo directory before deleting if we're in the worktree
    cwd = Path.cwd().resolve()
    worktree_to_delete = Path(worktree_path).resolve()
    try:
        is_in_worktree = cwd.samefile(worktree_to_delete)
    except (OSError, ValueError):
        is_in_worktree = cwd == worktree_to_delete

    if is_in_worktree:
        os.chdir(repo)

    # Remove worktree
    console.print(f"[yellow]Removing worktree: {worktree_path}[/yellow]")
    remove_worktree_safe(worktree_path, repo=repo, force=not no_force)
    console.print("[bold green]*[/bold green] Worktree removed\n")

    # Delete branch if requested
    if branch_name and not keep_branch:
        console.print(f"[yellow]Deleting local branch: {branch_name}[/yellow]")
        git_command("branch", "-D", branch_name, repo=repo)

        # Remove metadata
        unset_config(CONFIG_KEY_BASE_BRANCH.format(branch_name), repo=repo)
        unset_config(CONFIG_KEY_BASE_PATH.format(branch_name), repo=repo)

        console.print("[bold green]*[/bold green] Local branch and metadata removed\n")

        # Delete remote branch if requested
        if delete_remote:
            console.print(f"[yellow]Deleting remote branch: origin/{branch_name}[/yellow]")
            try:
                git_command("push", "origin", f":{branch_name}", repo=repo)
                console.print("[bold green]*[/bold green] Remote branch deleted\n")
            except GitError as e:
                console.print(f"[yellow]![/yellow] Remote branch deletion failed: {e}\n")


def _topological_sort_worktrees(
    worktrees: list[tuple[str, Path]], repo: Path
) -> list[tuple[str, Path]]:
    """
    Sort worktrees by dependency order using topological sort.

    Worktrees that serve as base branches for other worktrees are sorted first.

    Args:
        worktrees: List of (branch_name, path) tuples
        repo: Repository path

    Returns:
        Sorted list of (branch_name, path) tuples in dependency order
    """
    # Build dependency graph: {branch: [branches_that_depend_on_it]}
    graph: dict[str, list[str]] = {branch: [] for branch, _ in worktrees}
    in_degree: dict[str, int] = {branch: 0 for branch, _ in worktrees}
    worktree_map: dict[str, Path] = dict(worktrees)

    # Collect all branch names (including non-worktree branches that might be bases)
    all_branches = set(graph.keys())

    # Build the dependency graph
    for branch, _ in worktrees:
        base_branch = get_config(CONFIG_KEY_BASE_BRANCH.format(branch), repo)
        if base_branch:
            # If base_branch is another worktree, add dependency
            if base_branch in graph:
                graph[base_branch].append(branch)
                in_degree[branch] += 1
            # If base_branch is not a worktree (e.g., main, develop), add it
            elif base_branch not in all_branches:
                all_branches.add(base_branch)
                graph[base_branch] = []

    # Kahn's algorithm for topological sort
    queue = [branch for branch, degree in in_degree.items() if degree == 0]
    sorted_branches = []

    while queue:
        # Sort alphabetically for deterministic order
        queue.sort()
        current = queue.pop(0)
        sorted_branches.append(current)

        # Process dependents
        if current in graph:
            for dependent in graph[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

    # Check for cycles
    if len(sorted_branches) != len(worktrees):
        # Cycle detected - return original order with warning
        console.print(
            "[yellow]Warning: Circular dependency detected in worktree base branches. "
            "Syncing in original order.[/yellow]\n"
        )
        return worktrees

    # Return sorted worktrees (only those that are actual worktrees)
    return [(branch, worktree_map[branch]) for branch in sorted_branches if branch in worktree_map]


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
        # Collect all worktrees (including main repository)
        all_worktrees_list = parse_worktrees(repo)
        if not all_worktrees_list:
            console.print("[yellow]No worktrees found[/yellow]\n")
            return

        # Collect worktrees (exclude detached only)
        worktrees_to_sync = []
        for branch, path in all_worktrees_list:
            # Skip detached worktrees
            if branch == "(detached)":
                continue

            # Normalize branch name
            branch_name = branch[11:] if branch.startswith("refs/heads/") else branch
            worktrees_to_sync.append((branch_name, path))

        # Sort by dependency order (topological sort)
        worktrees_to_sync = _topological_sort_worktrees(worktrees_to_sync, repo)
    elif target or not all_worktrees:
        # Sync specific worktree by branch name or current worktree
        worktree_path, branch_name, _ = resolve_worktree_target(target)
        worktrees_to_sync = [(branch_name, worktree_path)]

    # Fetch from all remotes first
    console.print("[yellow]Fetching updates from remote...[/yellow]")
    fetch_result = git_command("fetch", "--all", "--prune", repo=repo, check=False)
    if fetch_result.returncode != 0:
        console.print("[yellow]![/yellow] Fetch failed or no remote configured\n")

    if fetch_only:
        console.print("[bold green]*[/bold green] Fetch complete\n")
        return

    # Sync each worktree
    for branch, worktree_path in worktrees_to_sync:
        # Get base branch from metadata (if exists)
        base_branch = get_config(CONFIG_KEY_BASE_BRANCH.format(branch), repo)

        # If no metadata (e.g., main repository), use origin/{branch} as fallback
        if not base_branch:
            # Check if origin/{branch} exists
            if fetch_result.returncode == 0:
                check_result = git_command(
                    "rev-parse",
                    "--verify",
                    f"origin/{branch}",
                    repo=worktree_path,
                    check=False,
                    capture=True,
                )
                if check_result.returncode == 0:
                    # Use origin/{branch} as base
                    console.print("\n[bold cyan]Syncing worktree:[/bold cyan]")
                    console.print(f"  Branch:  [green]{branch}[/green]")
                    console.print(f"  Path:    [blue]{worktree_path}[/blue]\n")

                    console.print(f"[yellow]Rebasing {branch} onto origin/{branch}...[/yellow]")
                    try:
                        git_command("rebase", f"origin/{branch}", repo=worktree_path)
                        console.print("[bold green]*[/bold green] Rebase successful")
                        continue
                    except GitError:
                        # Rebase failed - check for conflicts and handle with AI merge
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

                        # Handle AI merge if requested
                        if conflicted_files and ai_merge:
                            console.print(
                                "\n[bold yellow]! Rebase conflicts detected![/bold yellow]\n"
                            )
                            console.print("[cyan]Conflicted files:[/cyan]")
                            for file in conflicted_files:
                                console.print(f"  • {file}")
                            console.print()

                            console.print(
                                "\n[cyan]Launching AI to resolve conflicts automatically...[/cyan]\n"
                            )

                            # Create detailed prompt for AI to actually resolve conflicts
                            context = "Resolve the merge conflicts in this repository and complete the rebase.\n\n"
                            context += "**Current situation:**\n"
                            context += f"- Branch '{branch}' has conflicts when rebasing onto 'origin/{branch}'\n"
                            context += "- A rebase is currently in progress\n"
                            context += f"- {len(conflicted_files)} file(s) have conflicts\n\n"
                            context += "**Conflicted files:**\n"
                            for file in conflicted_files:
                                context += f"- {file}\n"
                            context += "\n"
                            context += "**Your task:**\n"
                            context += "1. Read each conflicted file to understand the conflicts\n"
                            context += "2. Resolve the conflicts by choosing the appropriate changes or merging them\n"
                            context += "3. Edit the files to remove conflict markers (<<<<<<< ======= >>>>>>>)\n"
                            context += (
                                "4. Stage ALL resolved files using: `git add <file1> <file2> ...`\n"
                            )
                            context += "5. Continue the rebase using: `git rebase --continue`\n"
                            context += "6. If the rebase completes successfully, report back\n"
                            context += "\n"
                            context += "**Important:**\n"
                            context += "- Make sure to actually execute the git commands, not just suggest them\n"
                            context += "- Stage all conflicted files after resolving\n"
                            context += "- Complete the entire rebase process\n"

                            from ..session_manager import save_context

                            save_context(branch, context)
                            # Launch AI tool with prompt for automated conflict resolution
                            launch_ai_tool(worktree_path, bg=False, prompt=context)

                            console.print("\n[yellow]AI conflict resolution completed.[/yellow]")
                            console.print(
                                "[yellow]Verify the resolution and re-run sync if needed.[/yellow]\n"
                            )
                            if all_worktrees:
                                console.print(
                                    "Re-run: [cyan]cw sync --all --ai-merge[/cyan] to continue syncing remaining worktrees\n"
                                )
                            else:
                                console.print("Re-run: [cyan]cw sync[/cyan] if needed\n")
                            sys.exit(0)

                        # Abort rebase and report error
                        git_command("rebase", "--abort", repo=worktree_path, check=False)
                        error_msg = (
                            f"Rebase failed:\n  cd {worktree_path}\n  git rebase origin/{branch}"
                        )
                        if conflicted_files:
                            error_msg += f"\n\nConflicted files ({len(conflicted_files)}):"
                            for file in conflicted_files:
                                error_msg += f"\n  • {file}"
                            if not ai_merge:
                                error_msg += "\n\nTip: Use --ai-merge flag to get AI assistance"

                        if all_worktrees:
                            console.print(f"[bold red]x[/bold red] {error_msg}")
                            console.print("[yellow]Continuing with remaining worktrees...[/yellow]")
                            continue
                        else:
                            raise RebaseError(error_msg)
                else:
                    # No origin/{branch}, skip
                    console.print(
                        f"\n[dim]Skipping {branch}: No metadata and no origin/{branch} found[/dim]\n"
                    )
                    continue
            else:
                # Fetch failed, can't determine remote
                console.print(
                    f"\n[yellow]![/yellow] Skipping {branch}: "
                    f"No metadata (not created with 'cw new') and fetch failed\n"
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
            console.print("[bold green]*[/bold green] Rebase successful")
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

            if conflicted_files and ai_merge:
                # AI merge: resolve conflicts automatically
                console.print("\n[bold yellow]! Rebase conflicts detected![/bold yellow]\n")
                console.print("[cyan]Conflicted files:[/cyan]")
                for file in conflicted_files:
                    console.print(f"  • {file}")
                console.print()

                console.print("\n[cyan]Launching AI to resolve conflicts automatically...[/cyan]\n")

                # Create detailed prompt for AI to actually resolve conflicts
                context = (
                    "Resolve the merge conflicts in this repository and complete the rebase.\n\n"
                )
                context += "**Current situation:**\n"
                context += (
                    f"- Branch '{branch}' has conflicts when rebasing onto '{rebase_target}'\n"
                )
                context += "- A rebase is currently in progress\n"
                context += f"- {len(conflicted_files)} file(s) have conflicts\n\n"
                context += "**Conflicted files:**\n"
                for file in conflicted_files:
                    context += f"- {file}\n"
                context += "\n"
                context += "**Your task:**\n"
                context += "1. Read each conflicted file to understand the conflicts\n"
                context += (
                    "2. Resolve the conflicts by choosing the appropriate changes or merging them\n"
                )
                context += (
                    "3. Edit the files to remove conflict markers (<<<<<<< ======= >>>>>>>)\n"
                )
                context += "4. Stage ALL resolved files using: `git add <file1> <file2> ...`\n"
                context += "5. Continue the rebase using: `git rebase --continue`\n"
                context += "6. If the rebase completes successfully, report back\n"
                context += "\n"
                context += "**Important:**\n"
                context += (
                    "- Make sure to actually execute the git commands, not just suggest them\n"
                )
                context += "- Stage all conflicted files after resolving\n"
                context += "- Complete the entire rebase process\n"

                # Save context to temporary file (for session restoration)
                from ..session_manager import save_context

                save_context(branch, context)

                # Launch AI tool with prompt for automated conflict resolution
                launch_ai_tool(worktree_path, bg=False, prompt=context)

                console.print("\n[yellow]AI conflict resolution completed.[/yellow]")
                console.print("[yellow]Verify the resolution and re-run sync if needed.[/yellow]\n")
                if all_worktrees:
                    console.print(
                        "Re-run: [cyan]cw sync --all --ai-merge[/cyan] to continue syncing remaining worktrees\n"
                    )
                else:
                    console.print("Re-run: [cyan]cw sync[/cyan] if needed\n")
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
                console.print(f"[bold red]x[/bold red] {error_msg}")
                console.print("[yellow]Continuing with remaining worktrees...[/yellow]")
                continue
            else:
                raise RebaseError(error_msg)

    console.print("\n[bold green]* Sync complete![/bold green]\n")


def clean_worktrees(
    merged: bool = False,
    older_than: int | None = None,
    interactive: bool = False,
    dry_run: bool = False,
) -> None:
    """
    Batch cleanup of worktrees based on various criteria.

    Automatically runs 'git worktree prune' after cleanup to remove stale
    administrative data.

    Args:
        merged: Delete worktrees for branches already merged to base
        older_than: Delete worktrees older than N days
        interactive: Interactive selection UI
        dry_run: Show what would be deleted without actually deleting

    Raises:
        GitError: If git operations fail
    """

    repo = get_repo_root()
    worktrees_to_delete: list[tuple[str, str, str]] = []
    gh_unavailable_branches: list[str] = []  # Track branches that need gh CLI
    has_gh = has_command("gh")

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

        # Check if merged
        if merged:
            base_branch = get_config(CONFIG_KEY_BASE_BRANCH.format(branch_name), repo)
            if base_branch:
                # Strategy 1: Check if branch is merged via git (works for merge commits)
                is_merged_git = False
                try:
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
                        is_merged_git = True
                        should_delete = True
                        reasons.append(f"merged into {base_branch}")
                except GitError:
                    pass

                # Strategy 2: If not detected by git, try GitHub CLI (works for squash/rebase)
                if not is_merged_git:
                    gh_result = _is_branch_merged_via_gh(branch_name, base_branch, repo)
                    if gh_result is True:
                        should_delete = True
                        reasons.append(f"merged into {base_branch} (detected via GitHub PR)")
                    elif gh_result is None:
                        # gh CLI not available - check if remote branch exists
                        try:
                            remote_check = git_command(
                                "ls-remote",
                                "--heads",
                                "origin",
                                branch_name,
                                repo=repo,
                                capture=True,
                                check=False,
                            )
                            # If remote branch doesn't exist, it might be merged and deleted
                            if remote_check.returncode == 0 and not remote_check.stdout.strip():
                                gh_unavailable_branches.append(branch_name)
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
    if not merged and older_than is None and not interactive:
        console.print(
            "[bold red]Error:[/bold red] Please specify at least one cleanup criterion:\n"
            "  --merged, --older-than, or -i/--interactive"
        )
        return

    # If nothing to delete
    if not worktrees_to_delete and not interactive:
        console.print("[bold green]*[/bold green] No worktrees match the cleanup criteria\n")

        # Show warning if there are branches with deleted remotes but no gh CLI
        if gh_unavailable_branches and not has_gh:
            console.print(
                "\n[yellow]! Warning:[/yellow] Found worktrees with deleted remote branches:\n"
            )
            for branch in gh_unavailable_branches:
                console.print(f"  • {branch}")
            console.print(
                "\n[dim]These branches may have been merged via squash/rebase merge.[/dim]"
            )
            console.print(
                "[dim]Install GitHub CLI (gh) to automatically detect squash/rebase merges:[/dim]"
            )
            console.print("[dim]  https://cli.github.com/[/dim]\n")

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
            console.print(f"[bold green]*[/bold green] Deleted {branch}")
            deleted_count += 1
        except Exception as e:
            console.print(f"[bold red]x[/bold red] Failed to delete {branch}: {e}")

    console.print(
        f"\n[bold green]* Cleanup complete! Deleted {deleted_count} worktree(s)[/bold green]\n"
    )

    # Automatically prune stale worktree administrative data
    if not dry_run:
        console.print("[dim]Pruning stale worktree metadata...[/dim]")
        try:
            git_command("worktree", "prune", repo=repo)
            console.print("[dim]* Prune complete[/dim]\n")
        except GitError as e:
            console.print(f"[dim yellow]Warning: Failed to prune: {e}[/dim yellow]\n")
