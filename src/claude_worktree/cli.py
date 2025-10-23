"""Typer-based CLI interface for claude-worktree."""

from pathlib import Path

import typer
from rich.console import Console

from . import __version__
from .config import (
    ConfigError,
    reset_config,
    set_ai_tool,
    set_config_value,
    show_config,
    use_preset,
)
from .config import (
    list_presets as list_ai_presets,
)
from .core import (
    create_worktree,
    delete_worktree,
    finish_worktree,
    list_worktrees,
    prune_worktrees,
    resume_worktree,
    show_status,
)
from .exceptions import ClaudeWorktreeError
from .git_utils import get_repo_root, parse_worktrees
from .update import check_for_updates

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


def complete_preset_names() -> list[str]:
    """Autocomplete function for AI tool preset names."""
    from .config import AI_TOOL_PRESETS

    return sorted(AI_TOOL_PRESETS.keys())


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
    # Check for updates on first run of the day
    check_for_updates(auto=True)


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


@app.command()
def finish(
    target: str | None = typer.Argument(
        None,
        help="Worktree branch to finish (optional, defaults to current directory)",
        autocompletion=complete_worktree_branches,
    ),
    push: bool = typer.Option(
        False,
        "--push",
        help="Push base branch to origin after merge",
    ),
) -> None:
    """
    Finish work on a worktree.

    Performs the following steps:
    1. Rebases feature branch onto base branch
    2. Fast-forward merges into base branch
    3. Removes the worktree
    4. Deletes the feature branch
    5. Optionally pushes to remote with --push

    Can be run from any directory by specifying the worktree branch name,
    or from within a feature worktree without arguments.

    Example:
        cw finish                  # Finish current worktree
        cw finish fix-auth         # Finish fix-auth worktree from anywhere
        cw finish feature-api --push  # Finish and push to remote
    """
    try:
        finish_worktree(target=target, push=push)
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
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


@app.command()
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
        worktree_path = find_worktree_by_branch(repo, branch)
        if not worktree_path:
            worktree_path = find_worktree_by_branch(repo, f"refs/heads/{branch}")

        if not worktree_path:
            print(f"Error: No worktree found for branch '{branch}'", file=sys.stderr)
            raise typer.Exit(code=1)

        # Output only the path (for shell function consumption)
        print(worktree_path)
    except ClaudeWorktreeError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)


@app.command(name="_shell-function", hidden=True)
def shell_function(
    shell: str = typer.Argument(
        ...,
        help="Shell type (bash, zsh, or fish)",
    ),
) -> None:
    """
    [Internal] Output shell function for sourcing.

    This is an internal command that outputs the shell function code
    for the specified shell. Users can source it to enable cw-cd function.

    Example:
        source <(cw _shell-function bash)
        cw _shell-function fish | source
    """
    import sys

    shell = shell.lower()
    valid_shells = ["bash", "zsh", "fish"]

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
        else:
            shell_file = "cw.fish"

        # Use importlib.resources to read the file from the package
        try:
            # Python 3.9+
            from importlib.resources import files

            shell_functions = files("claude_worktree").joinpath("shell_functions")
            script_content = (shell_functions / shell_file).read_text()
        except (ImportError, AttributeError):
            # Python 3.8 fallback
            import importlib.resources as pkg_resources

            script_content = pkg_resources.read_text("claude_worktree.shell_functions", shell_file)

        # Output the shell function script
        print(script_content)
    except Exception as e:
        print(f"Error: Failed to read shell function: {e}", file=sys.stderr)
        raise typer.Exit(code=1)


# Configuration commands
config_app = typer.Typer(
    name="config",
    help="Manage configuration settings",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config")


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
            console.print(f"[bold green]✓[/bold green] AI tool set to: {value}")
        else:
            set_config_value(key, value)
            console.print(f"[bold green]✓[/bold green] {key} = {value}")
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
        console.print(f"[bold green]✓[/bold green] Using preset: {preset}")
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
        console.print("[bold green]✓[/bold green] Configuration reset to defaults")
    except (ClaudeWorktreeError, ConfigError) as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
