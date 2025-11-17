"""Typer-based CLI interface for claude-worktree."""

from pathlib import Path

import typer

from . import __version__
from .config import (
    ConfigError,
    add_copy_file,
    list_copy_files,
    load_config,
    remove_copy_file,
    reset_config,
    save_config,
    set_ai_tool,
    set_config_value,
    show_config,
    use_preset,
)
from .config import (
    list_presets as list_ai_presets,
)
from .console import get_console
from .exceptions import ClaudeWorktreeError
from .git_utils import get_repo_root, normalize_branch_name, parse_worktrees
from .operations import (
    backup_worktree,
    change_base_branch,
    create_pr_worktree,
    create_worktree,
    delete_worktree,
    export_config,
    import_config,
    list_backups,
    list_worktrees,
    merge_worktree,
    restore_worktree,
    resume_worktree,
    shell_worktree,
    show_status,
)
from .slash_command_setup import (
    get_installed_ai_tools,
    install_slash_command,
    is_slash_command_installed,
    prompt_slash_command_setup,
)
from .update import check_for_updates

app = typer.Typer(
    name="cw",
    help="Claude Code × git worktree helper CLI",
    no_args_is_help=True,
    add_completion=True,
)
console = get_console()


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
            normalized = normalize_branch_name(branch)
            if normalized and normalized != "(detached)":
                branches.append(normalized)
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


def complete_preset_names() -> list[str]:
    """Autocomplete function for AI tool preset names."""
    from .config import AI_TOOL_PRESETS

    return sorted(AI_TOOL_PRESETS.keys())


def is_completion_installed() -> bool:
    """Check if shell completion appears to be installed."""
    import os
    import sys

    # Detect current shell
    shell_env = os.environ.get("SHELL", "")

    # Check for common shell completion indicators
    if "bash" in shell_env:
        bashrc = Path.home() / ".bashrc"
        if bashrc.exists() and "cw" in bashrc.read_text():
            return True
    elif "zsh" in shell_env:
        zshrc = Path.home() / ".zshrc"
        if zshrc.exists() and "cw" in zshrc.read_text():
            return True
    elif "fish" in shell_env:
        config_fish = Path.home() / ".config" / "fish" / "config.fish"
        if config_fish.exists() and "cw" in config_fish.read_text():
            return True
    elif sys.platform == "win32" or os.environ.get("PSModulePath"):
        # PowerShell - harder to detect, assume not installed
        return False

    # If we can't determine, assume not installed
    return False


def prompt_completion_setup() -> None:
    """Prompt user to install shell completion on first run."""
    # Don't prompt in non-interactive environments (CI, scripts, tests, SSH without TTY, etc.)
    from .git_utils import is_non_interactive

    if is_non_interactive():
        return

    config = load_config()

    # Check if we've already prompted
    if config["shell_completion"]["prompted"]:
        return

    # Check if completion is already installed
    if is_completion_installed():
        # Mark as prompted and installed
        config["shell_completion"]["prompted"] = True
        config["shell_completion"]["installed"] = True
        save_config(config)
        return

    # Prompt user
    console.print("\n[bold cyan]💡 Shell Completion Setup[/bold cyan]")
    console.print("\nWould you like to enable tab completion for cw commands?")
    console.print("This makes it easier to autocomplete branch names and options.\n")

    try:
        response = typer.confirm("Enable shell completion?", default=True)
    except (KeyboardInterrupt, EOFError):
        # User cancelled (Ctrl+C or EOF)
        config["shell_completion"]["prompted"] = True
        config["shell_completion"]["installed"] = False
        save_config(config)
        console.print("\n[dim]You can always set this up later with: cw shell-setup[/dim]\n")
        return

    # Mark as prompted
    config["shell_completion"]["prompted"] = True

    if response:
        # User wants to install - run shell-setup
        config["shell_completion"]["installed"] = True
        save_config(config)
        console.print("")
        shell_setup()
    else:
        # User declined
        config["shell_completion"]["installed"] = False
        save_config(config)
        console.print("\n[dim]You can always set this up later with: cw shell-setup[/dim]\n")


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
    import sys

    # Skip callbacks for internal commands that output machine-readable content
    if len(sys.argv) > 1 and sys.argv[1] in ["_shell-function", "_path"]:
        return

    # Check for updates on first run of the day
    check_for_updates(auto=True)

    # Prompt for shell completion setup on first run
    prompt_completion_setup()

    # Prompt for slash command setup on first run
    prompt_slash_command_setup()


@app.command(rich_help_panel="Core Workflow")
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
    bg: bool = typer.Option(
        False,
        "--bg",
        help="Launch AI tool in background",
    ),
    iterm: bool = typer.Option(
        False,
        "--iterm",
        help="Launch AI tool in new iTerm window (macOS only)",
    ),
    iterm_tab: bool = typer.Option(
        False,
        "--iterm-tab",
        help="Launch AI tool in new iTerm tab (macOS only)",
    ),
    tmux: str | None = typer.Option(
        None,
        "--tmux",
        help="Launch AI tool in new tmux session with given name",
    ),
) -> None:
    """
    Create a new worktree with a feature branch.

    Creates a new git worktree at ../<repo>-<branch_name> by default,
    or at a custom path if specified. Automatically launches your configured
    AI tool in the new worktree (unless set to 'no-op' preset).

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
            bg=bg,
            iterm=iterm,
            iterm_tab=iterm_tab,
            tmux_session=tmux,
        )
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(rich_help_panel="Core Workflow")
def pr(
    target: str | None = typer.Argument(
        None,
        help="Worktree branch (optional, defaults to current directory)",
        autocompletion=complete_worktree_branches,
    ),
    no_push: bool = typer.Option(
        False,
        "--no-push",
        help="Don't push to remote before creating PR",
    ),
    title: str | None = typer.Option(
        None,
        "--title",
        "-t",
        help="Pull request title",
    ),
    body: str | None = typer.Option(
        None,
        "--body",
        "-b",
        help="Pull request body",
    ),
    draft: bool = typer.Option(
        False,
        "--draft",
        help="Create as draft PR",
    ),
) -> None:
    """
    Create a GitHub Pull Request without merging or cleaning up the worktree.

    This command:
    1. Rebases feature branch onto base branch
    2. Pushes to remote (unless --no-push)
    3. Creates a pull request using GitHub CLI (gh)
    4. Leaves the worktree intact for further work

    After the PR is merged on GitHub, use 'cw delete <branch>' to clean up.

    Requires: GitHub CLI (gh) - https://cli.github.com/

    Example:
        cw pr                           # Create PR from current worktree
        cw pr fix-auth                  # Create PR for fix-auth branch
        cw pr --title "Fix auth bug"    # Custom PR title
        cw pr --draft                   # Create draft PR
        cw pr --no-push                 # Don't push (for testing)
    """
    try:
        create_pr_worktree(
            target=target,
            push=not no_push,
            title=title,
            body=body,
            draft=draft,
        )
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(rich_help_panel="Core Workflow")
def merge(
    target: str | None = typer.Argument(
        None,
        help="Worktree branch to merge (optional, defaults to current directory)",
        autocompletion=complete_worktree_branches,
    ),
    push: bool = typer.Option(
        False,
        "--push",
        help="Push base branch to origin after merge",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Pause for confirmation before each step",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview merge without executing",
    ),
) -> None:
    """
    Complete work on a worktree by merging directly to base branch.

    This command performs a local merge workflow:
    1. Rebases feature branch onto base branch
    2. Fast-forward merges into base branch
    3. Removes the worktree
    4. Deletes the feature branch
    5. Optionally pushes to remote with --push

    Use this when you want to merge directly without creating a pull request.
    For PR-based workflows, use 'cw pr' instead.

    Example:
        cw merge                     # Merge current worktree
        cw merge fix-auth            # Merge fix-auth branch
        cw merge feature-api --push  # Merge and push to remote
        cw merge -i                  # Interactive mode
        cw merge --dry-run           # Preview merge steps
    """
    try:
        merge_worktree(
            target=target,
            push=push,
            interactive=interactive,
            dry_run=dry_run,
        )
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(rich_help_panel="Core Workflow")
def resume(
    worktree: str | None = typer.Argument(
        None,
        help="Worktree branch to resume (optional, defaults to current directory)",
        autocompletion=complete_worktree_branches,
    ),
    bg: bool = typer.Option(
        False,
        "--bg",
        help="Launch AI tool in background",
    ),
    iterm: bool = typer.Option(
        False,
        "--iterm",
        help="Launch AI tool in new iTerm window (macOS only)",
    ),
    iterm_tab: bool = typer.Option(
        False,
        "--iterm-tab",
        help="Launch AI tool in new iTerm tab (macOS only)",
    ),
    tmux: str | None = typer.Option(
        None,
        "--tmux",
        help="Launch AI tool in new tmux session with given name",
    ),
) -> None:
    """
    Resume AI work in a worktree with context restoration.

    Launches your configured AI tool in the specified worktree or current directory,
    restoring previous session context if available. This is the recommended way
    to continue work on a feature branch.

    Example:
        cw resume                  # Resume in current directory
        cw resume fix-auth         # Resume in fix-auth worktree
        cw resume feature-api --iterm  # Resume in new iTerm window
    """
    try:
        resume_worktree(
            worktree=worktree,
            bg=bg,
            iterm=iterm,
            iterm_tab=iterm_tab,
            tmux_session=tmux,
        )
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(
    rich_help_panel="Core Workflow",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def shell(
    ctx: typer.Context,
    worktree: str | None = typer.Argument(
        None,
        help="Worktree branch to shell into (optional, defaults to current directory)",
        autocompletion=complete_worktree_branches,
    ),
) -> None:
    """
    Open an interactive shell or execute a command in a worktree.

    Without a command, opens an interactive shell in the specified worktree.
    With a command, executes the command in the worktree and exits.

    Example:
        cw shell fix-auth                    # Open interactive shell
        cw shell fix-auth git status         # Execute git status
        cw shell fix-auth npm test           # Run tests
        cw shell ls -la                      # Execute in current worktree
        cw shell                             # Open shell in current worktree
    """
    try:
        # Determine command from extra args
        # ctx.args contains everything after unrecognized args
        command = ctx.args if ctx.args else None

        # If worktree was given as positional arg, check if it's valid
        # If not valid and we have no command yet, treat it as command
        if worktree:
            from .git_utils import find_worktree_by_branch, get_repo_root

            try:
                repo = get_repo_root()
                normalized = normalize_branch_name(worktree)
                wt_path = find_worktree_by_branch(repo, worktree)
                if not wt_path:
                    wt_path = find_worktree_by_branch(repo, f"refs/heads/{normalized}")

                if not wt_path:
                    # Not a valid worktree - treat as command
                    if command:
                        command = [worktree] + command
                    else:
                        command = [worktree]
                    worktree = None
            except Exception:
                # If error checking repo, pass the error up
                pass

        shell_worktree(worktree=worktree, command=command)
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(name="list", rich_help_panel="Worktree Management")
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


@app.command(rich_help_panel="Worktree Management")
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


@app.command(rich_help_panel="Worktree Management")
def clean(
    merged: bool = typer.Option(
        False,
        "--merged",
        help="Delete worktrees for branches already merged to base",
    ),
    older_than: int | None = typer.Option(
        None,
        "--older-than",
        help="Delete worktrees older than N days",
        metavar="DAYS",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Interactive selection UI",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be deleted without actually deleting",
    ),
) -> None:
    """
    Batch cleanup of worktrees.

    Delete multiple worktrees based on various criteria. Use --dry-run
    to preview what would be deleted before actually removing anything.

    Automatically runs 'git worktree prune' after cleanup to remove stale
    administrative data.

    Example:
        cw clean --merged           # Delete merged worktrees
        cw clean --older-than 30    # Delete worktrees older than 30 days
        cw clean -i                 # Interactive selection
        cw clean --merged --dry-run # Preview merged worktrees
    """
    try:
        from .operations import clean_worktrees

        clean_worktrees(
            merged=merged,
            older_than=older_than,
            interactive=interactive,
            dry_run=dry_run,
        )
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(rich_help_panel="Worktree Management")
def delete(
    target: str | None = typer.Argument(
        None,
        help="Branch name or worktree path to delete (optional, defaults to current directory)",
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

    If no target is specified, deletes the current directory's worktree.
    By default, removes both the worktree and the local branch.
    Use --keep-branch to preserve the branch, or --delete-remote
    to also remove the branch from the remote repository.

    Example:
        cw delete                        # Delete current worktree
        cw delete fix-auth               # Delete by branch name
        cw delete ../myproject-fix-auth  # Delete by path
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


@app.command(rich_help_panel="Worktree Management")
def sync(
    target: str | None = typer.Argument(
        None,
        help="Branch to sync (optional, defaults to current directory)",
        autocompletion=complete_worktree_branches,
    ),
    all_worktrees: bool = typer.Option(
        False,
        "--all",
        help="Sync all worktrees",
    ),
    fetch_only: bool = typer.Option(
        False,
        "--fetch-only",
        help="Fetch updates without rebasing",
    ),
    ai_merge: bool = typer.Option(
        False,
        "--ai-merge",
        help="Launch AI tool to help resolve conflicts if rebase fails",
    ),
) -> None:
    """
    Synchronize worktree(s) with base branch changes.

    Fetches latest changes from the remote and rebases the feature branch
    onto the updated base branch. Useful for long-running feature branches
    that need to stay up-to-date with the base branch.

    If rebase conflicts occur, use --ai-merge to get AI assistance with
    conflict resolution. The AI tool will be launched with context about
    the conflicted files.

    Example:
        cw sync                    # Sync current worktree
        cw sync fix-auth           # Sync specific worktree
        cw sync --all              # Sync all worktrees
        cw sync --fetch-only       # Only fetch, don't rebase
        cw sync --ai-merge         # Get AI help with conflicts
    """
    try:
        from .operations import sync_worktree

        sync_worktree(
            target=target, all_worktrees=all_worktrees, fetch_only=fetch_only, ai_merge=ai_merge
        )
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(name="change-base", rich_help_panel="Worktree Management")
def change_base_cmd(
    new_base: str = typer.Argument(
        ...,
        help="New base branch name",
        autocompletion=complete_all_branches,
    ),
    target: str | None = typer.Option(
        None,
        "--target",
        "-t",
        help="Worktree branch to change (optional, defaults to current directory)",
        autocompletion=complete_worktree_branches,
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Use interactive rebase",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview changes without executing",
    ),
) -> None:
    """
    Change the base branch for a worktree and rebase onto it.

    This is useful when you realize after creating a worktree that you should
    have based it on a different branch (e.g., 'master' instead of 'develop').

    The command will:
    1. Fetch latest changes from remote
    2. Rebase the feature branch onto the new base branch
    3. Update the base branch metadata

    If the rebase fails due to conflicts, you'll need to resolve them manually
    and then run this command again to update the metadata.

    Example:
        cw change-base master              # Change current worktree to master
        cw change-base develop -t fix-auth # Change fix-auth to develop
        cw change-base main -i             # Interactive rebase
        cw change-base master --dry-run    # Preview changes
    """
    try:
        change_base_branch(
            new_base=new_base,
            target=target,
            interactive=interactive,
            dry_run=dry_run,
        )
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(rich_help_panel="Inspection & Analysis")
def doctor() -> None:
    """
    Perform health check on all worktrees.

    Checks for common issues and provides recommendations:
    - Git version compatibility (minimum 2.31.0)
    - Worktree accessibility (detects stale worktrees)
    - Uncommitted changes in worktrees
    - Worktrees behind their base branch
    - Existing merge conflicts
    - Cleanup recommendations

    Example:
        cw doctor    # Run full health check
    """
    try:
        from .operations import doctor as run_doctor

        run_doctor()
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(rich_help_panel="Inspection & Analysis")
def diff(
    branch1: str = typer.Argument(
        ...,
        help="First branch name to compare",
        autocompletion=complete_all_branches,
    ),
    branch2: str = typer.Argument(
        ...,
        help="Second branch name to compare",
        autocompletion=complete_all_branches,
    ),
    summary: bool = typer.Option(
        False,
        "--summary",
        "-s",
        help="Show diff statistics only",
    ),
    files: bool = typer.Option(
        False,
        "--files",
        "-f",
        help="Show changed files only",
    ),
) -> None:
    """
    Compare two worktrees or branches.

    Shows the differences between two branches in various formats:
    - Default: Full diff output (like `git diff`)
    - --summary/-s: Diff statistics (files changed, insertions, deletions)
    - --files/-f: List of changed files with status (Modified, Added, Deleted)

    Useful for reviewing changes before merging or understanding differences
    between feature branches.

    Example:
        cw diff main feature-api           # Full diff
        cw diff main feature-api --summary  # Stats only
        cw diff main feature-api --files    # Changed files list
        cw diff fix-auth hotfix-bug -f      # Compare two feature branches
    """
    try:
        from .operations import diff_worktrees

        diff_worktrees(branch1=branch1, branch2=branch2, summary=summary, files=files)
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(rich_help_panel="Inspection & Analysis")
def tree() -> None:
    """
    Display worktree hierarchy in a visual tree format.

    Shows all worktrees in an ASCII tree format with:
    - Base repository at the root
    - Feature worktrees as branches
    - Status indicators (clean, modified, stale)
    - Current worktree highlighting

    Example:
        cw tree
    """
    try:
        from .operations import show_tree

        show_tree()
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(rich_help_panel="Inspection & Analysis")
def stats() -> None:
    """
    Display usage analytics for worktrees.

    Shows comprehensive statistics about your worktrees:
    - Total worktrees count and status distribution
    - Age statistics (average, oldest, newest)
    - Commit activity across worktrees
    - Top 5 oldest worktrees
    - Top 5 most active worktrees by commit count

    Example:
        cw stats
    """
    try:
        from .operations import show_stats

        show_stats()
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(rich_help_panel="Maintenance")
def upgrade() -> None:
    """
    Upgrade claude-worktree to the latest version.

    Checks PyPI for the latest version and upgrades if a newer version
    is available. Automatically detects the installation method (pipx, pip, or uv).

    Example:
        cw upgrade
    """
    try:
        check_for_updates(auto=False)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Upgrade cancelled[/yellow]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(rich_help_panel="Configuration")
def cd(
    branch: str = typer.Argument(
        ...,
        help="Branch name to navigate to",
        autocompletion=complete_worktree_branches,
    ),
    print_only: bool = typer.Option(
        False,
        "--print",
        "-p",
        help="Print path only (for scripting)",
    ),
) -> None:
    """
    Print the path to a worktree's directory and optionally setup cw-cd shell function.

    This command always prints the worktree path to stdout for use in scripts (e.g., cd $(cw cd fix-auth)).
    If the cw-cd shell function is not installed and not in --print mode, prompts to run shell-setup.

    Example:
        cw cd fix-auth          # Print path and offer shell-setup if not installed
        cw cd fix-auth --print  # Print path only (no prompts)
        cd $(cw cd fix-auth)    # Use in scripts
    """
    import os

    from .git_utils import find_worktree_by_branch, get_repo_root, is_non_interactive

    try:
        repo = get_repo_root()
        # Try to find worktree by branch name
        normalized = normalize_branch_name(branch)
        worktree_path = find_worktree_by_branch(repo, branch)
        if not worktree_path:
            worktree_path = find_worktree_by_branch(repo, f"refs/heads/{normalized}")

        if not worktree_path:
            console.print(f"[bold red]Error:[/bold red] No worktree found for branch '{branch}'")
            raise typer.Exit(code=1)

        # Check if cw-cd shell function is installed (only if not in print-only mode and interactive)
        if not print_only and not is_non_interactive():
            # Check shell config files for cw-cd installation
            shell_env = os.environ.get("SHELL", "")
            cw_cd_installed = False

            if "bash" in shell_env:
                bashrc = Path.home() / ".bashrc"
                if bashrc.exists() and "cw _shell-function" in bashrc.read_text():
                    cw_cd_installed = True
            elif "zsh" in shell_env:
                zshrc = Path.home() / ".zshrc"
                if zshrc.exists() and "cw _shell-function" in zshrc.read_text():
                    cw_cd_installed = True
            elif "fish" in shell_env:
                config_fish = Path.home() / ".config" / "fish" / "config.fish"
                if config_fish.exists() and "cw _shell-function" in config_fish.read_text():
                    cw_cd_installed = True

            # If not installed, offer to run shell-setup
            if not cw_cd_installed:
                console.print(f"[bold cyan]Worktree path:[/bold cyan] {worktree_path}\n")
                console.print(
                    "[dim]💡 Tip: Install the cw-cd shell function for easier navigation![/dim]"
                )
                console.print(
                    f"[dim]   With cw-cd installed, you can just type: [cyan]cw-cd {branch}[/cyan][/dim]\n"
                )

                try:
                    response = typer.confirm("Run shell-setup now?", default=False)
                    if response:
                        console.print("")
                        shell_setup()
                        console.print("")
                    else:
                        # User declined
                        console.print(
                            "\n[dim]You can run [cyan]cw shell-setup[/cyan] anytime to install it.[/dim]\n"
                        )
                except (KeyboardInterrupt, EOFError):
                    console.print(
                        "\n[dim]You can run [cyan]cw shell-setup[/cyan] anytime to install it.[/dim]\n"
                    )

        # Always print path to stdout (for scripting)
        print(worktree_path)

    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(name="_path", hidden=True)
def worktree_path(
    branch: str = typer.Argument(
        ...,
        help="Branch name to get worktree path for",
        autocompletion=complete_worktree_branches,
    ),
) -> None:
    """
    [Internal] Get worktree path for a branch.

    This is an internal command used by shell functions.
    Outputs only the worktree path to stdout for machine consumption.

    Example:
        cw _path fix-auth
    """
    import sys

    from .git_utils import find_worktree_by_branch, get_repo_root

    try:
        repo = get_repo_root()
        # Try to find worktree by branch name
        normalized = normalize_branch_name(branch)
        worktree_path = find_worktree_by_branch(repo, branch)
        if not worktree_path:
            worktree_path = find_worktree_by_branch(repo, f"refs/heads/{normalized}")

        if not worktree_path:
            print(f"Error: No worktree found for branch '{branch}'", file=sys.stderr)
            raise typer.Exit(code=1)

        # Output only the path (for shell function consumption)
        print(worktree_path)
    except ClaudeWorktreeError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)


@app.command(name="shell-setup", rich_help_panel="Configuration")
def shell_setup() -> None:
    """
    Interactive shell integration setup (cw-cd function + tab completion).

    Automatically detects your shell and offers to add both:
    - cw-cd function for directory navigation
    - Tab completion for cw commands and branch names

    Adds the configuration to your shell profile (.bashrc, .zshrc, config.fish, or $PROFILE).

    Example:
        cw shell-setup
    """
    import os
    import sys

    # Detect current shell
    shell_name = None
    profile_path = None

    # Check SHELL environment variable (Unix)
    shell_env = os.environ.get("SHELL", "")
    if "bash" in shell_env:
        shell_name = "bash"
        profile_path = Path.home() / ".bashrc"
    elif "zsh" in shell_env:
        shell_name = "zsh"
        profile_path = Path.home() / ".zshrc"
    elif "fish" in shell_env:
        shell_name = "fish"
        profile_path = Path.home() / ".config" / "fish" / "config.fish"
    # Check for PowerShell (Windows or cross-platform)
    elif sys.platform == "win32" or os.environ.get("PSModulePath"):
        shell_name = "powershell"
        # PowerShell profile path varies, we'll provide instructions instead
        profile_path = None

    if not shell_name:
        console.print("[yellow]Could not detect your shell automatically.[/yellow]")
        console.print("\nPlease manually add the cw-cd function to your shell:")
        console.print("\n[bold]bash/zsh:[/bold]")
        console.print("  source <(cw _shell-function bash)")
        console.print("\n[bold]fish:[/bold]")
        console.print("  cw _shell-function fish | source")
        console.print("\n[bold]PowerShell:[/bold]")
        console.print("  cw _shell-function powershell | Out-String | Invoke-Expression")
        raise typer.Exit(code=0)

    console.print(f"[bold cyan]Detected shell:[/bold cyan] {shell_name}\n")

    if shell_name == "powershell":
        # PowerShell: provide instructions instead of auto-install
        console.print(
            "[bold]To enable cw-cd in PowerShell, add the following to your $PROFILE:[/bold]\n"
        )
        console.print(
            "[cyan]cw _shell-function powershell | Out-String | Invoke-Expression[/cyan]\n"
        )
        console.print("To find your PowerShell profile location, run: [cyan]$PROFILE[/cyan]")
        console.print(
            "\nIf the profile file doesn't exist, create it with: [cyan]New-Item -Path $PROFILE -ItemType File -Force[/cyan]"
        )
        raise typer.Exit(code=0)

    # Unix shells: prepare setup lines
    if shell_name == "bash":
        shell_function_line = "source <(cw _shell-function bash)"
    elif shell_name == "zsh":
        shell_function_line = "source <(cw _shell-function zsh)"
    else:  # fish
        shell_function_line = "cw _shell-function fish | source"

    # Check if already installed
    if profile_path and profile_path.exists():
        content = profile_path.read_text()
        if "cw _shell-function" in content or "cw-cd" in content:
            console.print("[green]*[/green] cw-cd function is already installed!\n")
            console.print(f"Found in: [dim]{profile_path}[/dim]")
            raise typer.Exit(code=0)

    # Offer to install
    console.print("[bold]Setup shell integration?[/bold]")
    console.print(f"\nThis will add the following to [cyan]{profile_path}[/cyan]:")

    if shell_name == "zsh":
        # zsh: Show tab completion first, then shell functions
        console.print("\n  [dim]# Tab completion support[/dim]")
        console.print("  [dim]FPATH=$HOME/.zfunc:$FPATH[/dim]")
        console.print("  [dim]autoload -Uz compinit && compinit[/dim]")
        console.print("\n  [dim]# cw-cd function for directory navigation[/dim]")
        console.print(f"  [dim]{shell_function_line}[/dim]")
    elif shell_name == "bash":
        # bash: Show shell functions first, then tab completion
        console.print("\n  [dim]# cw-cd function for directory navigation[/dim]")
        console.print(f"  [dim]{shell_function_line}[/dim]")
        console.print("\n  [dim]# Tab completion support[/dim]")
        console.print('  [dim]eval "$(cw --show-completion bash 2>/dev/null || true)"[/dim]')
    else:
        # other shells: just shell functions
        console.print("\n  [dim]# cw-cd function for directory navigation[/dim]")
        console.print(f"  [dim]{shell_function_line}[/dim]")

    console.print("")

    response = typer.confirm("Add to your shell profile?", default=True)

    if not response:
        console.print("\n[yellow]Setup cancelled.[/yellow]")
        console.print(f"\nTo install manually, add the above lines to {profile_path}")
        raise typer.Exit(code=0)

    if not profile_path:
        console.print("\n[yellow]Could not determine profile path.[/yellow]")
        console.print("\nTo install manually, add the above lines to your shell profile")
        raise typer.Exit(code=1)

    try:
        # Create parent directories if needed
        profile_path.parent.mkdir(parents=True, exist_ok=True)

        # For zsh, also create completion directory and file
        if shell_name == "zsh":
            zfunc_dir = Path.home() / ".zfunc"
            zfunc_dir.mkdir(exist_ok=True)

            # Create completion file
            completion_file = zfunc_dir / "_cw"
            completion_content = """#compdef cw

_cw_completion() {
  eval $(env _TYPER_COMPLETE_ARGS="${words[1,$CURRENT]}" _CW_COMPLETE=complete_zsh cw)
}

compdef _cw_completion cw"""
            completion_file.write_text(completion_content)
            console.print(f"[dim]Created completion file: {completion_file}[/dim]")

        # Append to profile file
        with profile_path.open("a") as f:
            if shell_name == "zsh":
                # For zsh: Add FPATH and compinit FIRST, then shell functions
                # (compdef in shell functions requires compinit to be loaded)
                f.write("\n# claude-worktree tab completion\n")
                f.write("FPATH=$HOME/.zfunc:$FPATH\n")
                f.write("autoload -Uz compinit && compinit\n")
                f.write("\n# claude-worktree shell integration\n")
                f.write(f"{shell_function_line}\n")
            elif shell_name == "bash":
                # For bash: Shell functions first, then completion
                f.write("\n# claude-worktree shell integration\n")
                f.write(f"{shell_function_line}\n")
                f.write("\n# claude-worktree tab completion\n")
                f.write('eval "$(cw --show-completion bash 2>/dev/null || true)"\n')
            else:
                # For other shells (fish): Just shell functions
                f.write("\n# claude-worktree shell integration\n")
                f.write(f"{shell_function_line}\n")

        console.print(f"\n[bold green]*[/bold green] Successfully added to {profile_path}")
        console.print("\n[bold]Next steps:[/bold]")
        console.print(f"  1. Restart your shell or run: [cyan]source {profile_path}[/cyan]")
        console.print("  2. Try directory navigation: [cyan]cw-cd <branch-name>[/cyan]")
        console.print("  3. Try tab completion: [cyan]cw <TAB>[/cyan] or [cyan]cw new <TAB>[/cyan]")

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] Failed to update {profile_path}: {e}")
        console.print(f"\nTo install manually, add the lines shown above to {profile_path}")
        raise typer.Exit(code=1)


@app.command(name="_shell-function", hidden=True)
def shell_function(
    shell: str = typer.Argument(
        ...,
        help="Shell type (bash, zsh, fish, or powershell)",
    ),
) -> None:
    """
    [Internal] Output shell function for sourcing.

    This is an internal command that outputs the shell function code
    for the specified shell. Users can source it to enable cw-cd function.

    Example:
        bash/zsh:   source <(cw _shell-function bash)
        fish:       cw _shell-function fish | source
        PowerShell: cw _shell-function powershell | Out-String | Invoke-Expression
    """
    import sys

    shell = shell.lower()
    valid_shells = ["bash", "zsh", "fish", "powershell", "pwsh"]

    if shell not in valid_shells:
        print(
            f"Error: Invalid shell '{shell}'. Must be one of: {', '.join(valid_shells)}",
            file=sys.stderr,
        )
        raise typer.Exit(code=1)

    try:
        # Read the shell function file
        if shell in ["bash", "zsh"]:
            shell_file = "cw.bash"
        elif shell == "fish":
            shell_file = "cw.fish"
        else:  # powershell or pwsh
            shell_file = "cw.ps1"

        # Use importlib.resources to read the file from the package
        script_content = None
        try:
            # Python 3.9+
            from importlib.resources import files

            shell_functions = files("claude_worktree").joinpath("shell_functions")
            script_content = (shell_functions / shell_file).read_text()
        except (ImportError, AttributeError):
            # Python 3.8 fallback
            import importlib.resources as pkg_resources

            script_content = pkg_resources.read_text("claude_worktree.shell_functions", shell_file)

        if not script_content or not script_content.strip():
            print(f"Error: Shell function file is empty for {shell}", file=sys.stderr)
            raise typer.Exit(code=1)

        # Output the shell function script to stdout only (no extra output)
        sys.stdout.write(script_content)
        sys.stdout.flush()
    except Exception as e:
        print(f"Error: Failed to read shell function: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        raise typer.Exit(code=1)


# Configuration commands
config_app = typer.Typer(
    name="config",
    help="Manage configuration settings",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config", rich_help_panel="Configuration")


@config_app.command()
def show() -> None:
    """
    Show current configuration.

    Displays all configuration settings including the AI tool command,
    launch method, and default base branch.

    Example:
        cw config show
    """
    try:
        output = show_config()
        console.print(output)
    except (ClaudeWorktreeError, ConfigError) as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@config_app.command(name="set")
def set_cmd(
    key: str = typer.Argument(
        ...,
        help="Configuration key (e.g., 'ai-tool', 'git.default_base_branch')",
    ),
    value: str = typer.Argument(
        ...,
        help="Configuration value",
    ),
) -> None:
    """
    Set a configuration value.

    Supports the following keys:
    - ai-tool: Set the AI coding assistant command
    - git.default_base_branch: Set default base branch

    Example:
        cw config set ai-tool claude
        cw config set ai-tool "happy --backend claude"
        cw config set git.default_base_branch develop
    """
    try:
        # Special handling for ai-tool
        if key == "ai-tool":
            # Parse value as command with potential arguments
            parts = value.split()
            command = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            set_ai_tool(command, args)
            console.print(f"[bold green]*[/bold green] AI tool set to: {value}")
        else:
            set_config_value(key, value)
            console.print(f"[bold green]*[/bold green] {key} = {value}")
    except (ClaudeWorktreeError, ConfigError) as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@config_app.command(name="use-preset")
def use_preset_cmd(
    preset: str = typer.Argument(
        ...,
        help="Preset name (e.g., 'claude', 'codex', 'happy', 'happy-codex')",
        autocompletion=complete_preset_names,
    ),
) -> None:
    """
    Use a predefined AI tool preset.

    Available presets:
    - no-op: Disable AI tool launching
    - claude: Claude Code CLI
    - codex: OpenAI Codex
    - happy: Happy with Claude Code mode
    - happy-codex: Happy with Codex mode (bypass permissions)
    - happy-yolo: Happy with bypass permissions (fast iteration)

    Example:
        cw config use-preset claude
        cw config use-preset happy-codex
        cw config use-preset no-op
    """
    try:
        use_preset(preset)
        console.print(f"[bold green]*[/bold green] Using preset: {preset}")
    except (ClaudeWorktreeError, ConfigError) as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@config_app.command(name="list-presets")
def list_presets_cmd() -> None:
    """
    List all available AI tool presets.

    Shows all predefined presets with their corresponding commands.

    Example:
        cw config list-presets
    """
    try:
        output = list_ai_presets()
        console.print(output)
    except (ClaudeWorktreeError, ConfigError) as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@config_app.command()
def reset() -> None:
    """
    Reset configuration to defaults.

    Restores all configuration values to their default settings.

    Example:
        cw config reset
    """
    try:
        reset_config()
        console.print("[bold green]*[/bold green] Configuration reset to defaults")
    except (ClaudeWorktreeError, ConfigError) as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


# Copy files commands (subcommand group)
copy_files_app = typer.Typer(
    name="copy-files",
    help="Manage files to copy to new worktrees",
    no_args_is_help=True,
)
config_app.add_typer(copy_files_app, name="copy-files")


@copy_files_app.command(name="list")
def copy_files_list_cmd() -> None:
    """
    List all files configured to be copied to new worktrees.

    Example:
        cw config copy-files list
    """
    try:
        output = list_copy_files()
        console.print(output)
    except (ClaudeWorktreeError, ConfigError) as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@copy_files_app.command(name="add")
def copy_files_add_cmd(
    file_path: str = typer.Argument(
        ...,
        help="Relative path to file (e.g., '.env', 'config/local.json')",
    ),
) -> None:
    """
    Add a file to be copied to new worktrees.

    This is useful for project-specific configuration files like .env,
    local config files, or other files that should be copied (not symlinked)
    to each new worktree.

    Example:
        cw config copy-files add .env
        cw config copy-files add .env.local
        cw config copy-files add config/local.json
    """
    try:
        add_copy_file(file_path)
        console.print(f"[bold green]*[/bold green] Added to copy list: {file_path}")
    except (ClaudeWorktreeError, ConfigError) as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@copy_files_app.command(name="remove")
def copy_files_remove_cmd(
    file_path: str = typer.Argument(
        ...,
        help="Relative path to file to remove from copy list",
    ),
) -> None:
    """
    Remove a file from the copy list.

    Example:
        cw config copy-files remove .env
    """
    try:
        removed = remove_copy_file(file_path)
        if removed:
            console.print(f"[bold green]*[/bold green] Removed from copy list: {file_path}")
        else:
            console.print(f"[yellow]![/yellow] File not in copy list: {file_path}")
    except (ClaudeWorktreeError, ConfigError) as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(name="slash-command-setup", rich_help_panel="Configuration")
def slash_command_setup_cmd() -> None:
    """
    Install or reinstall /cw slash command for Happy/Claude/Codex.

    Installs the /cw slash command to ~/.claude/commands/ directory,
    making it available in all Happy, Claude Code, and Codex sessions.

    Example:
        cw slash-command-setup
    """
    # Check if AI tools are installed
    installed_tools = get_installed_ai_tools()

    if not installed_tools:
        console.print("[yellow]Warning:[/yellow] No AI tools (happy/claude/codex) detected.")
        console.print("\nSlash commands work with:")
        console.print("  - Happy: https://github.com/happy-coder/happy")
        console.print("  - Claude Code: https://claude.ai/download")
        console.print("  - Codex: https://github.com/codex-ai/codex")
        console.print("\nInstall one of these tools to use /cw commands.")

        if not typer.confirm("\nInstall slash command anyway?", default=False):
            raise typer.Exit(code=0)
    else:
        tools_str = ", ".join(installed_tools)
        console.print(f"[bold cyan]Detected AI tools:[/bold cyan] {tools_str}\n")

    # Check if already installed
    if is_slash_command_installed():
        console.print("[yellow]Slash command is already installed.[/yellow]")
        if not typer.confirm("Reinstall?", default=True):
            raise typer.Exit(code=0)

    # Install
    if install_slash_command():
        # Update config
        config = load_config()
        if "slash_commands" not in config:
            config["slash_commands"] = {}
        config["slash_commands"]["prompted"] = True
        config["slash_commands"]["installed"] = True
        save_config(config)
    else:
        raise typer.Exit(code=1)


# Stash commands
stash_app = typer.Typer(
    name="stash",
    help="Worktree-aware stash management",
    no_args_is_help=True,
)
app.add_typer(stash_app, name="stash", rich_help_panel="Configuration")


@stash_app.command(name="save")
def stash_save_cmd(
    message: str | None = typer.Argument(
        None,
        help="Optional message to describe the stash",
    ),
) -> None:
    """
    Save changes in current worktree to stash.

    Creates a stash with a branch-prefixed message to help organize
    stashes by worktree. If no message is provided, uses "WIP" as default.

    Example:
        cw stash save                  # Stash with default "WIP" message
        cw stash save "work in progress"  # Stash with custom message
    """
    try:
        from .operations import stash_save

        stash_save(message=message)
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@stash_app.command(name="list")
def stash_list_cmd() -> None:
    """
    List all stashes organized by worktree/branch.

    Shows all stashes grouped by the branch they were created from,
    making it easy to see which stashes belong to which worktree.

    Example:
        cw stash list
    """
    try:
        from .operations import stash_list

        stash_list()
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@stash_app.command(name="apply")
def stash_apply_cmd(
    target_branch: str = typer.Argument(
        ...,
        help="Branch name of worktree to apply stash to",
        autocompletion=complete_worktree_branches,
    ),
    stash_ref: str = typer.Option(
        "stash@{0}",
        "--stash",
        "-s",
        help="Stash reference (default: stash@{0} - most recent)",
    ),
) -> None:
    """
    Apply a stash to a different worktree.

    Applies the specified stash (or most recent by default) to the
    target worktree. This allows moving changes between worktrees.

    Example:
        cw stash apply fix-auth              # Apply most recent stash to fix-auth
        cw stash apply feature-api --stash stash@{1}  # Apply specific stash
    """
    try:
        from .operations import stash_apply

        stash_apply(target_branch=target_branch, stash_ref=stash_ref)
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(rich_help_panel="Configuration")
def export(
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (default: cw-export-<timestamp>.json)",
    ),
) -> None:
    """
    Export worktree configuration and metadata to a file.

    Creates a JSON file containing:
    - Global configuration settings (AI tool, default base branch, etc.)
    - Worktree metadata (branch names, base branches, paths, status)

    This allows you to share worktree configurations across machines
    or back up your worktree setup for later restoration.

    Example:
        cw export                          # Export to timestamped file
        cw export -o my-worktrees.json     # Export to specific file
        cw export --output backup.json     # Alternative syntax
    """
    try:
        export_config(output_file=output)
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(name="import", rich_help_panel="Configuration")
def import_cmd(
    import_file: Path = typer.Argument(
        ...,
        help="Path to the configuration file to import",
        exists=True,
    ),
    apply: bool = typer.Option(
        False,
        "--apply",
        help="Apply the imported configuration (default: preview only)",
    ),
) -> None:
    """
    Import worktree configuration and metadata from a file.

    By default, shows a preview of what would be imported without making changes.
    Use --apply to actually apply the imported configuration.

    Preview mode shows:
    - Configuration changes that would be applied
    - Worktrees that would be created/updated
    - Any warnings or conflicts

    Apply mode:
    - Updates global configuration settings
    - Stores worktree metadata for matching branches
    - Does not automatically create worktrees (metadata only)

    Example:
        cw import backup.json              # Preview import
        cw import backup.json --apply      # Apply import
        cw import my-worktrees.json        # Preview from specific file
    """
    try:
        import_config(import_file=import_file, apply=apply)
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


# Backup/Restore commands
backup_app = typer.Typer(
    name="backup",
    help="Backup and restore worktrees",
    no_args_is_help=True,
)
app.add_typer(backup_app, name="backup", rich_help_panel="Backup & Recovery")


@backup_app.command(name="create")
def backup_create(
    branch: str | None = typer.Argument(
        None,
        help="Branch name to backup (default: current worktree)",
        autocompletion=complete_worktree_branches,
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory for backups (default: ~/.config/claude-worktree/backups)",
    ),
    all_worktrees: bool = typer.Option(
        False,
        "--all",
        help="Backup all worktrees",
    ),
) -> None:
    """
    Create backup of worktree(s) using git bundle.

    Backs up the complete git history and uncommitted changes to a timestamped
    directory. Backups can be restored later using 'cw backup restore'.

    Example:
        cw backup create                   # Backup current worktree
        cw backup create fix-auth          # Backup specific worktree
        cw backup create --all             # Backup all worktrees
        cw backup create -o ~/backups      # Custom backup location
    """
    try:
        backup_worktree(branch=branch, output=output, all_worktrees=all_worktrees)
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@backup_app.command(name="list")
def backup_list(
    branch: str | None = typer.Argument(
        None,
        help="Filter by branch name (default: show all)",
        autocompletion=complete_worktree_branches,
    ),
) -> None:
    """
    List available backups.

    Shows all backups organized by branch name with timestamps.

    Example:
        cw backup list              # List all backups
        cw backup list fix-auth     # List backups for specific branch
    """
    try:
        list_backups(branch=branch)
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@backup_app.command(name="restore")
def backup_restore(
    branch: str = typer.Argument(
        ...,
        help="Branch name to restore",
        autocompletion=complete_worktree_branches,
    ),
    backup_id: str | None = typer.Option(
        None,
        "--id",
        help="Backup timestamp to restore (default: latest)",
    ),
    path: Path | None = typer.Option(
        None,
        "--path",
        "-p",
        help="Custom path for restored worktree (default: ../<repo>-<branch>)",
    ),
) -> None:
    """
    Restore worktree from backup.

    Restores a worktree from a previously created backup, including
    the full git history and uncommitted changes if they were backed up.

    Example:
        cw backup restore fix-auth                          # Restore latest backup
        cw backup restore fix-auth --id 20250129-143052     # Restore specific backup
        cw backup restore fix-auth --path /tmp/my-restore   # Custom restore path
    """
    try:
        restore_worktree(branch=branch, backup_id=backup_id, path=path)
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
