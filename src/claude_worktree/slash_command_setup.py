"""Slash command setup for Happy, Claude Code, and Codex."""

import shutil
from pathlib import Path

import typer

from .config import load_config, save_config
from .console import get_console

console = get_console()


def detect_ai_tools() -> dict[str, bool]:
    """Detect which AI coding tools are installed.

    Returns:
        Dict with tool names and their installation status
        Example: {"happy": True, "claude": True, "codex": False}
    """
    tools = {
        "happy": shutil.which("happy") is not None,
        "claude": shutil.which("claude") is not None,
        "codex": shutil.which("codex") is not None,
    }

    return tools


def get_installed_ai_tools() -> list[str]:
    """Get list of installed AI tool names.

    Returns:
        List of installed tool names (e.g., ["happy", "claude"])
    """
    tools = detect_ai_tools()
    return [name for name, installed in tools.items() if installed]


def is_slash_command_installed() -> bool:
    """Check if /cw slash command is installed.

    Returns:
        True if at least one of the slash command files exists:
        - ~/.claude/commands/cw.md (Claude Code, Happy)
        - ~/.codex/prompts/cw.md (Codex)
    """
    claude_file = Path.home() / ".claude" / "commands" / "cw.md"
    codex_file = Path.home() / ".codex" / "prompts" / "cw.md"
    return claude_file.exists() or codex_file.exists()


def can_use_slash_commands() -> bool:
    """Check if Claude Code is installed (supports slash commands).

    Happy and Codex use the same slash command directories as Claude Code,
    so we only need to check for Claude Code installation.

    Returns:
        True if Claude Code is installed
    """
    return shutil.which("claude") is not None


def install_slash_command() -> bool:
    """Install /cw slash commands to appropriate directories.

    Installs both the main command and subcommands:
    - ~/.claude/commands/cw.md (main command)
    - ~/.claude/commands/cw/*.md (subcommands: new, list, resume, etc.)
    - ~/.codex/prompts/cw.md (main command for Codex)
    - ~/.codex/prompts/cw/*.md (subcommands for Codex)

    Returns:
        True if at least one installation succeeded, False if all failed
    """
    installed_tools = detect_ai_tools()
    success_count = 0
    total_attempts = 0

    # Read bundled command files from package
    try:
        # Python 3.9+
        from importlib.resources import files

        slash_commands_dir = files("claude_worktree").joinpath("slash_commands")

        # Get main command file
        main_command_content = (slash_commands_dir / "cw.md").read_text()

        # Get all subcommand files from cw/ subdirectory
        subcommands = {}
        cw_subdir = slash_commands_dir / "cw"
        for file_path in cw_subdir.iterdir():
            if file_path.name.endswith(".md"):
                subcommands[file_path.name] = file_path.read_text()

    except (ImportError, AttributeError):
        # Python 3.8 fallback
        import importlib.resources as pkg_resources

        main_command_content = pkg_resources.read_text("claude_worktree.slash_commands", "cw.md")
        # Subcommands support requires Python 3.9+
        subcommands = {}

    # Install for Claude Code / Happy (shared directory)
    if installed_tools.get("claude") or installed_tools.get("happy"):
        total_attempts += 1
        claude_dir = Path.home() / ".claude" / "commands"
        claude_cw_dir = claude_dir / "cw"

        try:
            # Install main command
            claude_dir.mkdir(parents=True, exist_ok=True)
            (claude_dir / "cw.md").write_text(main_command_content)

            # Install subcommands
            claude_cw_dir.mkdir(parents=True, exist_ok=True)
            for filename, content in subcommands.items():
                (claude_cw_dir / filename).write_text(content)

            console.print(
                f"[bold green]*[/bold green] Installed for Claude Code/Happy: {claude_dir / 'cw.md'} + {len(subcommands)} subcommands"
            )
            success_count += 1
        except Exception as e:
            console.print(f"[bold red]x[/bold red] Failed to install for Claude Code/Happy: {e}")

    # Install for Codex (separate directory)
    if installed_tools.get("codex"):
        total_attempts += 1
        codex_dir = Path.home() / ".codex" / "prompts"
        codex_cw_dir = codex_dir / "cw"

        try:
            # Install main command
            codex_dir.mkdir(parents=True, exist_ok=True)
            (codex_dir / "cw.md").write_text(main_command_content)

            # Install subcommands
            codex_cw_dir.mkdir(parents=True, exist_ok=True)
            for filename, content in subcommands.items():
                (codex_cw_dir / filename).write_text(content)

            console.print(
                f"[bold green]*[/bold green] Installed for Codex: {codex_dir / 'cw.md'} + {len(subcommands)} subcommands"
            )
            success_count += 1
        except Exception as e:
            console.print(f"[bold red]x[/bold red] Failed to install for Codex: {e}")

    if success_count > 0:
        console.print("\n[bold]Available commands in your AI session:[/bold]")
        console.print("  Main: [cyan]/cw[/cyan] <subcommand> [args]")
        console.print("  Or use specific commands:")
        console.print("    [cyan]/cw:new[/cyan] feature-name")
        console.print("    [cyan]/cw:list[/cyan]")
        console.print("    [cyan]/cw:resume[/cyan] fix-auth")
        console.print(
            "    [cyan]/cw:pr[/cyan], [cyan]/cw:merge[/cyan], [cyan]/cw:status[/cyan], [cyan]/cw:delete[/cyan]"
        )
        console.print("\n[dim]Restart your AI tool session to activate the commands.[/dim]")
        return True
    else:
        console.print("\n[bold red]Error:[/bold red] Failed to install slash command")
        console.print("\n[yellow]Manual installation:[/yellow]")
        console.print("  Claude Code/Happy: ~/.claude/commands/cw.md")
        console.print("  Codex: ~/.codex/prompts/cw.md")
        console.print(
            "  Template: https://github.com/DaveDev42/claude-worktree/blob/main/src/claude_worktree/slash_commands/cw.md"
        )
        return False


def prompt_slash_command_setup() -> None:
    """Prompt user to install /cw slash command on first run.

    This function:
    1. Checks if we're in a non-interactive environment (skip in CI/scripts/tests)
    2. Checks if user was already prompted (skip if yes)
    3. Detects installed AI tools
    4. Asks user if they want to install slash command
    5. Updates config with user's choice
    """
    # Don't prompt in non-interactive environments (CI, scripts, tests, SSH without TTY, etc.)
    from .git_utils import is_non_interactive

    if is_non_interactive():
        return

    config = load_config()

    # Check if we've already prompted
    if config.get("slash_commands", {}).get("prompted", False):
        return

    # Check if Claude Code is installed
    if not can_use_slash_commands():
        # Claude Code not installed, mark as prompted and skip
        if "slash_commands" not in config:
            config["slash_commands"] = {}
        config["slash_commands"]["prompted"] = True
        config["slash_commands"]["installed"] = False
        save_config(config)
        return

    # Check if already installed
    if is_slash_command_installed():
        if "slash_commands" not in config:
            config["slash_commands"] = {}
        config["slash_commands"]["prompted"] = True
        config["slash_commands"]["installed"] = True
        save_config(config)
        return

    # Prompt user
    console.print("\n[bold cyan]💡 Claude Code Slash Command Setup[/bold cyan]")
    console.print("\nWould you like to enable [cyan]/cw[/cyan] commands in your AI sessions?")
    console.print("This lets you run worktree commands directly from Claude Code/Happy/Codex:\n")
    console.print("  [dim]/cw new feature-name[/dim]")
    console.print("  [dim]/cw list[/dim]")
    console.print("  [dim]/cw resume fix-auth[/dim]\n")

    try:
        response = typer.confirm("Install /cw slash command?", default=True)
    except (KeyboardInterrupt, EOFError):
        # User cancelled
        if "slash_commands" not in config:
            config["slash_commands"] = {}
        config["slash_commands"]["prompted"] = True
        config["slash_commands"]["installed"] = False
        save_config(config)
        console.print(
            "\n[dim]You can always set this up later with: cw slash-command-setup[/dim]\n"
        )
        return

    # Mark as prompted
    if "slash_commands" not in config:
        config["slash_commands"] = {}
    config["slash_commands"]["prompted"] = True

    if response:
        # Install slash command
        if install_slash_command():
            config["slash_commands"]["installed"] = True
        save_config(config)
    else:
        # User declined
        config["slash_commands"]["installed"] = False
        save_config(config)
        console.print(
            "\n[dim]You can always set this up later with: cw slash-command-setup[/dim]\n"
        )
