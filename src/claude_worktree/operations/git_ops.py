"""Git operations for pull requests and merging."""

import subprocess
from pathlib import Path

from rich.console import Console

from ..exceptions import GitError, RebaseError
from ..git_utils import git_command, has_command
from ..helpers import get_worktree_metadata, resolve_worktree_target

console = Console()


def create_pr_worktree(
    target: str | None = None,
    push: bool = True,
    title: str | None = None,
    body: str | None = None,
    draft: bool = False,
) -> None:
    """
    Create a GitHub Pull Request for the worktree without merging or cleaning up.

    Args:
        target: Branch name of worktree (optional, defaults to current directory)
        push: Push to remote before creating PR (default: True)
        title: PR title (optional, will use default from gh)
        body: PR body (optional, will use default from gh)
        draft: Create as draft PR

    Raises:
        GitError: If git operations fail
        RebaseError: If rebase fails
        WorktreeNotFoundError: If worktree not found
        InvalidBranchError: If branch is invalid
    """
    # Check if gh CLI is available
    if not has_command("gh"):
        raise GitError(
            "GitHub CLI (gh) is required to create pull requests.\n"
            "Install it from: https://cli.github.com/"
        )

    # Resolve worktree target to (path, branch, repo)
    cwd, feature_branch, worktree_repo = resolve_worktree_target(target)

    # Get metadata - base_path is the actual main repository
    base_branch, base_path = get_worktree_metadata(feature_branch, worktree_repo)
    repo = base_path

    console.print("\n[bold cyan]Creating Pull Request:[/bold cyan]")
    console.print(f"  Feature:     [green]{feature_branch}[/green]")
    console.print(f"  Base:        [green]{base_branch}[/green]")
    console.print(f"  Repo:        [blue]{repo}[/blue]\n")

    # Fetch updates from remote
    console.print("[yellow]Fetching updates from remote...[/yellow]")
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

    # Rebase feature on base
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

        # Abort the rebase
        git_command("rebase", "--abort", repo=cwd, check=False)
        error_msg = f"Rebase failed. Please resolve conflicts manually:\n  cd {cwd}\n  git rebase {rebase_target}"
        if conflicted_files:
            error_msg += f"\n\nConflicted files ({len(conflicted_files)}):"
            for file in conflicted_files:
                error_msg += f"\n  • {file}"
        raise RebaseError(error_msg)

    console.print("[bold green]✓[/bold green] Rebase successful\n")

    # Push to remote if requested
    if push:
        console.print(f"[yellow]Pushing {feature_branch} to origin...[/yellow]")
        try:
            # Push with -u to set upstream
            git_command("push", "-u", "origin", feature_branch, repo=cwd)
            console.print("[bold green]✓[/bold green] Pushed to origin\n")
        except GitError as e:
            console.print(f"[yellow]⚠[/yellow] Push failed: {e}\n")
            raise

    # Create pull request
    console.print("[yellow]Creating pull request...[/yellow]")

    pr_args = ["gh", "pr", "create", "--base", base_branch]

    if title:
        pr_args.extend(["--title", title])

    if body:
        pr_args.extend(["--body", body])

    if draft:
        pr_args.append("--draft")

    try:
        # Run gh pr create in the worktree directory
        result = subprocess.run(
            pr_args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=True,
        )
        pr_url = result.stdout.strip()
        console.print("[bold green]✓[/bold green] Pull request created!\n")
        console.print(f"[bold]PR URL:[/bold] {pr_url}\n")
        console.print(
            "[dim]Note: Worktree is still active. Use 'cw delete' to remove it after PR is merged.[/dim]\n"
        )
    except subprocess.CalledProcessError as e:
        error_msg = f"Failed to create pull request: {e.stderr}"
        raise GitError(error_msg)


def merge_worktree(
    target: str | None = None,
    push: bool = False,
    interactive: bool = False,
    dry_run: bool = False,
) -> None:
    """
    Complete work on a worktree: rebase, merge to base branch, and cleanup.

    This is the new name for the finish command. It performs a direct merge
    to the base branch without creating a pull request.

    Args:
        target: Branch name of worktree to finish (optional, defaults to current directory)
        push: Push base branch to origin after merge
        interactive: Pause for confirmation before each step
        dry_run: Preview merge without executing

    Raises:
        GitError: If git operations fail
        RebaseError: If rebase fails
        MergeError: If merge fails
        WorktreeNotFoundError: If worktree not found
        InvalidBranchError: If branch is invalid
    """
    # Import here to avoid circular dependency
    from .worktree_ops import finish_worktree

    # This is essentially the same as the old finish_worktree function
    # Just call finish_worktree with the same arguments
    finish_worktree(target=target, push=push, interactive=interactive, dry_run=dry_run)


def _is_branch_merged_via_gh(branch_name: str, base_branch: str, repo: Path) -> bool | None:
    """
    Check if a branch is merged via GitHub CLI (detects squash/rebase merges).

    Args:
        branch_name: Feature branch name
        base_branch: Base branch name
        repo: Repository root path

    Returns:
        True if merged via GitHub PR, False if not merged, None if gh CLI unavailable
    """
    import subprocess

    # Check if gh CLI is available
    if not has_command("gh"):
        return None

    try:
        # Check if there's a PR for this branch and if it's merged
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--head",
                branch_name,
                "--base",
                base_branch,
                "--state",
                "merged",
                "--json",
                "number",
                "--jq",
                "length",
            ],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )

        # If there are merged PRs for this branch, it's merged
        if result.returncode == 0 and result.stdout.strip():
            count = int(result.stdout.strip())
            return count > 0

        return False

    except (ValueError, subprocess.SubprocessError):
        # If gh command fails, return None (unavailable)
        return None
