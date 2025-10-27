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
    ai_merge: bool = typer.Option(
        False,
        "--ai-merge",
        help="Launch AI tool to help resolve conflicts if rebase fails",
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

    Use --interactive/-i to confirm each step before execution.
    Use --dry-run to preview what would happen without actually executing.
    Use --ai-merge to get AI assistance with conflict resolution if rebase fails.

    Example:
        cw finish                     # Finish current worktree
        cw finish fix-auth            # Finish fix-auth worktree from anywhere
        cw finish feature-api --push  # Finish and push to remote
        cw finish -i                  # Interactive mode with confirmations
        cw finish --dry-run           # Preview merge steps
        cw finish --ai-merge          # Get AI help with conflicts
    """
    try:
        finish_worktree(
            target=target, push=push, interactive=interactive, dry_run=dry_run, ai_merge=ai_merge
        )
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
def clean(
    merged: bool = typer.Option(
        False,
        "--merged",
        help="Delete worktrees for branches already merged to base",
    ),
    stale: bool = typer.Option(
        False,
        "--stale",
        help="Delete worktrees with 'stale' status",
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

    Example:
        cw clean --merged           # Delete merged worktrees
        cw clean --stale            # Delete stale worktrees
        cw clean --older-than 30    # Delete worktrees older than 30 days
        cw clean -i                 # Interactive selection
        cw clean --merged --dry-run # Preview merged worktrees
    """
    try:
        from .core import clean_worktrees

        clean_worktrees(
            merged=merged,
            stale=stale,
            older_than=older_than,
            interactive=interactive,
            dry_run=dry_run,
        )
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
) -> None:
    """
    Synchronize worktree(s) with base branch changes.

    Fetches latest changes from the remote and rebases the feature branch
    onto the updated base branch. Useful for long-running feature branches
    that need to stay up-to-date with the base branch.

    Example:
        cw sync                    # Sync current worktree
        cw sync fix-auth           # Sync specific worktree
        cw sync --all              # Sync all worktrees
        cw sync --fetch-only       # Only fetch, don't rebase
    """
    try:
        from .core import sync_worktree

        sync_worktree(target=target, all_worktrees=all_worktrees, fetch_only=fetch_only)
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
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
        from .core import doctor as run_doctor

        run_doctor()
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
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
        from .core import diff_worktrees

        diff_worktrees(branch1=branch1, branch2=branch2, summary=summary, files=files)
    except ClaudeWorktreeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


# Template commands
template_app = typer.Typer(
    name="template",
    help="Manage worktree templates",
    no_args_is_help=True,
)
app.add_typer(template_app, name="template")


@template_app.command(name="create")
def template_create(
    name: str = typer.Argument(..., help="Template name"),
    source: str = typer.Argument(".", help="Source path (defaults to current directory)"),
    description: str | None = typer.Option(
        None, "--description", "-d", help="Template description"
    ),
) -> None:
    """
    Create a new template from a worktree.

    Copies files from the source directory (excluding .git and common build directories)
    to create a reusable template for future worktrees.

    Example:
        cw template create my-python-setup      # From current directory
        cw template create my-setup ./feature   # From specific path
        cw template create my-setup . -d "My project template"
    """
    try:
        from .template_manager import create_template

        source_path = Path(source).resolve()
        create_template(name=name, source_path=source_path, description=description)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@template_app.command(name="list")
def template_list() -> None:
    """
    List all available templates.

    Shows template names, descriptions, and file counts.

    Example:
        cw template list
    """
    try:
        from .template_manager import show_all_templates

        show_all_templates()
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@template_app.command(name="show")
def template_show(
    name: str = typer.Argument(..., help="Template name"),
) -> None:
    """
    Show detailed information about a template.

    Example:
        cw template show my-setup
    """
    try:
        from .template_manager import show_template_info

        show_template_info(name=name)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@template_app.command(name="delete")
def template_delete(
    name: str = typer.Argument(..., help="Template name"),
) -> None:
    """
    Delete a template.

    Example:
        cw template delete my-setup
    """
    try:
        from .template_manager import delete_template

        delete_template(name=name)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@template_app.command(name="apply")
def template_apply(
    name: str = typer.Argument(..., help="Template name"),
    target: str = typer.Argument(".", help="Target path (defaults to current directory)"),
) -> None:
    """
    Apply a template to a directory.

    Copies template files to the target directory, skipping existing files.

    Example:
        cw template apply my-setup             # To current directory
        cw template apply my-setup ../feature  # To specific path
    """
    try:
        from .template_manager import apply_template

        target_path = Path(target).resolve()
        apply_template(name=name, target_path=target_path)
    except Exception as e:
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


@app.command()
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
    Print the path to a worktree's directory.

    This command prints the worktree path to stdout. Since a CLI tool cannot
    directly change your shell's directory, use the cw-cd shell function for
    actual directory navigation.

    To install the shell function:
        bash/zsh: source <(cw _shell-function bash)
        fish:     cw _shell-function fish | source

    Then use: cw-cd <branch>

    Example:
        cw cd fix-auth          # Show path and installation hint
        cw cd fix-auth --print  # Print path only (for scripting)
    """

    from .git_utils import find_worktree_by_branch, get_repo_root

    try:
        repo = get_repo_root()
        # Try to find worktree by branch name
        worktree_path = find_worktree_by_branch(repo, branch)
        if not worktree_path:
            worktree_path = find_worktree_by_branch(repo, f"refs/heads/{branch}")

        if not worktree_path:
            console.print(f"[bold red]Error:[/bold red] No worktree found for branch '{branch}'")
            raise typer.Exit(code=1)

        if print_only:
            # Script-friendly output: path only
            print(worktree_path)
        else:
            # User-friendly output: path + helpful message
            console.print(f"[bold cyan]Worktree path:[/bold cyan] {worktree_path}")
            console.print()
            console.print(
                "[dim]To navigate directly to worktrees, install the cw-cd shell function:[/dim]"
            )
            console.print("[dim]  bash/zsh:[/dim] source <(cw _shell-function bash)")
            console.print("[dim]  fish:    [/dim] cw _shell-function fish | source")
            console.print()
            console.print(f"[dim]Then use:[/dim] cw-cd {branch}")
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
