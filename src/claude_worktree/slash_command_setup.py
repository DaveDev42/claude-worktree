"""Slash command setup for Happy, Claude Code, and Codex."""

import os
import shutil
import sys
from pathlib import Path

import typer
from rich.console import Console

from .config import load_config, save_config

console = Console()


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
    """Check if any AI tool that supports slash commands is installed.

    Returns:
        True if at least one of happy/claude/codex is installed
    """
    return any(detect_ai_tools().values())


def install_slash_command() -> bool:
    """Install /cw slash command to appropriate directories.

    Installs to:
    - ~/.claude/commands/cw.md (for Claude Code and Happy)
    - ~/.codex/prompts/cw.md (for Codex)

    Returns:
        True if at least one installation succeeded, False if all failed
    """
    installed_tools = detect_ai_tools()
    success_count = 0
    total_attempts = 0

    # Read bundled command file from package
    try:
        # Python 3.9+
        from importlib.resources import files

        slash_commands_dir = files("claude_worktree").joinpath("slash_commands")
        command_content = (slash_commands_dir / "cw.md").read_text()
    except (ImportError, AttributeError):
        # Python 3.8 fallback
        import importlib.resources as pkg_resources

        command_content = pkg_resources.read_text("claude_worktree.slash_commands", "cw.md")

    # Install for Claude Code / Happy (shared directory)
    if installed_tools.get("claude") or installed_tools.get("happy"):
        total_attempts += 1
        claude_dir = Path.home() / ".claude" / "commands"
        claude_file = claude_dir / "cw.md"

        try:
            claude_dir.mkdir(parents=True, exist_ok=True)
            claude_file.write_text(command_content)
            console.print(
                f"[bold green]✓[/bold green] Installed for Claude Code/Happy: {claude_file}"
            )
            success_count += 1
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Failed to install for Claude Code/Happy: {e}")

    # Install for Codex (separate directory)
    if installed_tools.get("codex"):
        total_attempts += 1
        codex_dir = Path.home() / ".codex" / "prompts"
        codex_file = codex_dir / "cw.md"

        try:
            codex_dir.mkdir(parents=True, exist_ok=True)
            codex_file.write_text(command_content)
            console.print(f"[bold green]✓[/bold green] Installed for Codex: {codex_file}")
            success_count += 1
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Failed to install for Codex: {e}")

    if success_count > 0:
        console.print("\n[bold]Usage in your AI session:[/bold]")
        console.print("  [cyan]/cw new feature-name[/cyan]")
        console.print("  [cyan]/cw list[/cyan]")
        console.print("  [cyan]/cw resume fix-auth[/cyan]")
        console.print("\n[dim]Restart your AI tool session to activate the command.[/dim]")
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
    1. Checks if we're in a TTY (skip in scripts/tests)
    2. Checks if user was already prompted (skip if yes)
    3. Detects installed AI tools
    4. Asks user if they want to install slash command
    5. Updates config with user's choice
    """
    # Don't prompt if stdin is not a TTY
    if not sys.stdin.isatty():
        return

    # Don't prompt in CI/test environment
    if os.environ.get("CI") or os.environ.get("PYTEST_CURRENT_TEST"):
        return

    config = load_config()

    # Check if we've already prompted
    if config.get("slash_commands", {}).get("prompted", False):
        return

    # Check if any AI tool is installed
    installed_tools = get_installed_ai_tools()
    if not installed_tools:
        # No AI tools installed, mark as prompted and skip
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

    # Format tool names nicely
    tools_str = ", ".join(installed_tools)

    # Prompt user
    console.print("\n[bold cyan]💡 Claude Code Slash Command Setup[/bold cyan]")
    console.print(f"\nDetected AI tools: [bold]{tools_str}[/bold]")
    console.print("\nWould you like to enable [cyan]/cw[/cyan] commands in your AI sessions?")
    console.print("This lets you run worktree commands directly from Happy/Claude/Codex:\n")
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
