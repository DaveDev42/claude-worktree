"""Typer-based CLI interface for claude-worktree."""

from pathlib import Path

import typer
from rich.console import Console

from . import __version__
from .core import (
    attach_claude,
    create_worktree,
    delete_worktree,
    finish_worktree,
    list_worktrees,
    prune_worktrees,
    show_status,
)
from .exceptions import ClaudeWorktreeError
from .git_utils import get_repo_root, parse_worktrees

app = typer.Typer(
    name="cw",
    help="Claude Code × git worktree helper CLI",
    no_args_is_help=True,
    add_completion=True,
)
console = Console()


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"claude-worktree version {__version__}")
        raise typer.Exit()


def complete_worktree_branches() -> list[str]:
    """Autocomplete function for worktree branch names."""
    try:
        repo = get_repo_root()
        worktrees = parse_worktrees(repo)
        # Return branch names without refs/heads/ prefix
        branches = []
        for branch, _ in worktrees:
            if branch.startswith("refs/heads/"):
                branches.append(branch[11:])  # Remove refs/heads/
            elif branch != "(detached)":
                branches.append(branch)
        return branches
    except Exception:
        return []


def complete_all_branches() -> list[str]:
    """Autocomplete function for all git branches."""
    try:
        from .git_utils import git_command

        repo = get_repo_root()
        result = git_command("branch", "--format=%(refname:short)", repo=repo, capture=True)
        branches = result.stdout.strip().splitlines()
        return branches
    except Exception:
        return []


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Claude Code × git worktree helper CLI."""
    pass


@app.command()
def new(
    branch_name: str = typer.Argument(
        ..., help="Name for the new branch (e.g., 'fix-auth', 'feature-api')"
    ),
    base: str | None = typer.Option(
        None,
        "--base",
        "-b",
        help="Base branch to branch from (default: current branch)",
        autocompletion=complete_all_branches,
    ),
    path: Path | None = typer.Option(
        None,
        "--path",
        "-p",
        help="Custom path for worktree (default: ../<repo>-<branch>)",
        exists=False,
    ),
    no_cd: bool = typer.Option(
        False,
        "--no-cd",
        help="Don't change directory after creation",
    ),
    no_claude: bool = typer.Option(
        False,
        "--no-claude",
        help="Don't launch Claude Code",
    ),
    bg: bool = typer.Option(
        False,
        "--bg",
        help="Launch Claude in background",
    ),
    iterm: bool = typer.Option(
        False,
        "--iterm",
        help="Launch Claude in new iTerm window (macOS only)",
    ),
    tmux: str | None = typer.Option(
        None,
        "--tmux",
        help="Launch Claude in new tmux session with given name",
    ),
) -> None:
    """
    Create a new worktree with a feature branch.

    Creates a new git worktree at ../<repo>-<branch_name> by default,
    or at a custom path if specified. Automatically launches Claude Code
    in the new worktree unless --no-claude is specified.

    Example:
        cw new fix-auth
        cw new feature-api --base develop
        cw new hotfix-bug --path /tmp/my-hotfix
    """
    try:
        create_worktree(
            branch_name=branch_name,
            base_branch=base,
            path=path,
            no_cd=no_cd,
            no_claude=no_claude,
            bg=bg,
            iterm=iterm,
            tmux_session=tmux,
        )
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def finish(
    push: bool = typer.Option(
        False,
        "--push",
        help="Push base branch to origin after merge",
    ),
) -> None:
    """
    Finish work on current worktree.

    Performs the following steps:
    1. Rebases feature branch onto base branch
    2. Fast-forward merges into base branch
    3. Removes the worktree
    4. Deletes the feature branch
    5. Optionally pushes to remote with --push

    Must be run from within a feature worktree created with 'cw new'.
    """
    try:
        finish_worktree(push=push)
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def attach(
    worktree: str | None = typer.Argument(
        None,
        help="Worktree branch to attach to (optional, defaults to current directory)",
        autocompletion=complete_worktree_branches,
    ),
    bg: bool = typer.Option(
        False,
        "--bg",
        help="Launch Claude in background",
    ),
    iterm: bool = typer.Option(
        False,
        "--iterm",
        help="Launch Claude in new iTerm window (macOS only)",
    ),
    tmux: str | None = typer.Option(
        None,
        "--tmux",
        help="Launch Claude in new tmux session with given name",
    ),
) -> None:
    """
    Reattach Claude Code to a worktree.

    Launches Claude Code in the specified worktree or current directory.
    Useful if you closed the Claude session and want to restart it.

    Example:
        cw attach                  # Attach to current directory
        cw attach fix-auth         # Attach to fix-auth worktree
        cw attach feature-api --iterm  # Attach in new iTerm window
    """
    try:
        # If worktree specified, find its path and attach there
        if worktree:
            import os

            from .git_utils import find_worktree_by_branch

            repo = get_repo_root()
            # Try with refs/heads/ prefix first
            worktree_path = find_worktree_by_branch(repo, f"refs/heads/{worktree}")
            # If not found, try without prefix
            if not worktree_path:
                worktree_path = find_worktree_by_branch(repo, worktree)

            if not worktree_path:
                console.print(f"[bold red]Error:[/bold red] Worktree '{worktree}' not found")
                raise typer.Exit(code=1)

            # Change to worktree directory and attach
            os.chdir(worktree_path)
            console.print(f"[dim]Attaching to worktree at: {worktree_path}[/dim]")

        attach_claude(bg=bg, iterm=iterm, tmux_session=tmux)
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(name="list")
def list_cmd() -> None:
    """
    List all worktrees in the current repository.

    Shows all worktrees with their branch names, status, and paths.
    """
    try:
        list_worktrees()
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def status() -> None:
    """
    Show status of current worktree and list all worktrees.

    Displays metadata for the current worktree (feature branch, base branch)
    and lists all worktrees in the repository.
    """
    try:
        show_status()
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def prune() -> None:
    """
    Prune stale worktree administrative data.

    Removes worktree metadata for directories that no longer exist.
    Equivalent to 'git worktree prune'.
    """
    try:
        prune_worktrees()
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def delete(
    target: str = typer.Argument(
        ...,
        help="Branch name or worktree path to delete",
        autocompletion=complete_worktree_branches,
    ),
    keep_branch: bool = typer.Option(
        False,
        "--keep-branch",
        help="Keep the branch, only remove worktree",
    ),
    delete_remote: bool = typer.Option(
        False,
        "--delete-remote",
        help="Also delete remote branch on origin",
    ),
    no_force: bool = typer.Option(
        False,
        "--no-force",
        help="Don't use --force flag (fails if worktree has changes)",
    ),
) -> None:
    """
    Delete a worktree by branch name or path.

    By default, removes both the worktree and the local branch.
    Use --keep-branch to preserve the branch, or --delete-remote
    to also remove the branch from the remote repository.

    Example:
        cw delete fix-auth
        cw delete ../myproject-fix-auth
        cw delete old-feature --delete-remote
    """
    try:
        delete_worktree(
            target=target,
            keep_branch=keep_branch,
            delete_remote=delete_remote,
            no_force=no_force,
        )
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
