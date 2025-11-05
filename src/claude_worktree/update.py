"""Self-update functionality for claude-worktree."""

import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from packaging.version import parse
from rich.prompt import Confirm

from . import __version__
from .console import get_console

console = get_console()

# Cache directory for update check
CACHE_DIR = Path.home() / ".cache" / "claude-worktree"
UPDATE_CHECK_FILE = CACHE_DIR / "update_check.json"


def get_latest_version() -> str | None:
    """
    Fetch the latest version from PyPI.

    Returns:
        Latest version string, or None if failed
    """
    try:
        # Add cache-busting headers to ensure we get the latest version
        headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        }
        response = httpx.get(
            "https://pypi.org/pypi/claude-worktree/json",
            timeout=5.0,
            follow_redirects=True,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()
        version: str = data["info"]["version"]
        return version
    except Exception:
        return None


def load_update_cache() -> dict[str, Any]:
    """
    Load update check cache from disk.

    Returns:
        Cache data dictionary
    """
    if not UPDATE_CHECK_FILE.exists():
        return {}

    try:
        data: dict[str, Any] = json.loads(UPDATE_CHECK_FILE.read_text())
        return data
    except Exception:
        return {}


def save_update_cache(data: dict[str, Any]) -> None:
    """
    Save update check cache to disk.

    Args:
        data: Cache data to save
    """
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        UPDATE_CHECK_FILE.write_text(json.dumps(data, indent=2))
    except Exception:
        pass  # Silently fail if we can't write cache


def should_check_update() -> bool:
    """
    Determine if we should check for updates today.

    Returns:
        True if we should check, False otherwise
    """
    cache = load_update_cache()
    today = str(date.today())

    # Check if we already checked today
    last_check = cache.get("last_check_date")
    if last_check == today:
        # Already checked today, don't check again
        return False

    return True


def mark_update_checked(failed: bool = False) -> None:
    """
    Mark that we checked for updates today.

    Args:
        failed: Whether the check failed
    """
    cache = load_update_cache()
    cache["last_check_date"] = str(date.today())
    cache["last_check_failed"] = failed
    save_update_cache(cache)


def is_newer_version(latest: str, current: str) -> bool:
    """
    Check if latest version is newer than current.

    Args:
        latest: Latest version string
        current: Current version string

    Returns:
        True if latest is newer than current
    """
    try:
        # Handle dev versions
        if current.endswith(".dev"):
            return False
        result: bool = parse(latest) > parse(current)
        return result
    except Exception:
        return False


def detect_installer() -> str | None:
    """
    Detect how claude-worktree was installed.

    Returns:
        'pipx', 'uv-tool', 'uv-pip', 'pip', 'source', or None if unknown
    """
    # Check if running from source (editable install)
    if __version__.endswith(".dev"):
        return "source"

    # Check if installed via pipx
    try:
        result = subprocess.run(
            ["pipx", "list"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0 and "claude-worktree" in result.stdout:
            return "pipx"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Check if installed via uv tool
    try:
        result = subprocess.run(
            ["uv", "tool", "list"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0 and "claude-worktree" in result.stdout:
            return "uv-tool"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Check if uv is available and verify package was installed via uv
    # Don't assume uv-pip just because uv exists - verify the package location
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0:
            # Check if package was actually installed via uv by looking at pip list
            try:
                pip_result = subprocess.run(
                    [sys.executable, "-m", "pip", "show", "claude-worktree"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=5,
                )
                # If pip show works, the package was installed via pip, not uv
                if pip_result.returncode == 0:
                    return "pip"
                # If pip show fails, try uv-pip (package might be in uv's env)
                return "uv-pip"
            except (FileNotFoundError, subprocess.TimeoutExpired):
                return "uv-pip"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Default to pip
    return "pip"


def check_package_available(version: str) -> bool:
    """
    Check if a specific version is available for download from PyPI.

    Args:
        version: Version string to check

    Returns:
        True if the version is downloadable, False otherwise
    """
    try:
        headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        }
        response = httpx.get(
            f"https://pypi.org/pypi/claude-worktree/{version}/json",
            timeout=5.0,
            follow_redirects=True,
            headers=headers,
        )
        is_available: bool = response.status_code == 200
        return is_available
    except Exception:
        return False


def upgrade_package(installer: str | None = None, target_version: str | None = None) -> bool:
    """
    Upgrade claude-worktree to the latest version.

    Args:
        installer: Installation method ('pipx', 'uv-tool', 'uv-pip', 'pip', 'source')
        target_version: Target version to upgrade to (for retry logic)

    Returns:
        True if upgrade succeeded, False otherwise
    """
    if installer is None:
        installer = detect_installer()

    # Handle unknown installation method
    if installer is None:
        console.print("\n[yellow]![/yellow] Could not detect how claude-worktree was installed.")
        console.print("\nPlease upgrade manually using one of these methods:")
        console.print("  [cyan]pip install --upgrade claude-worktree[/cyan]")
        console.print("  [cyan]uv tool upgrade claude-worktree[/cyan]")
        console.print("  [cyan]pipx upgrade claude-worktree[/cyan]\n")
        return False

    # Handle source installations
    if installer == "source":
        console.print(
            "\n[yellow]![/yellow] You appear to be running from source (editable install)."
        )
        console.print("\nTo upgrade, you have two options:")
        console.print("  1. [cyan]git pull[/cyan] in your development directory")
        console.print("  2. Install from PyPI:")
        console.print("     [cyan]pip install --upgrade claude-worktree[/cyan]")
        console.print("     [cyan]uv tool install --upgrade claude-worktree[/cyan]")
        console.print("     [cyan]pipx install --force claude-worktree[/cyan]\n")
        return False

    # If target version is specified, check if it's available
    if target_version:
        console.print(f"[dim]Verifying version {target_version} is available...[/dim]")
        if not check_package_available(target_version):
            console.print(
                f"\n[yellow]![/yellow] Version {target_version} not yet available on PyPI CDN."
            )
            console.print(
                "[dim]This is normal immediately after a release. The CDN may take a few minutes to sync.[/dim]"
            )
            console.print("\n[cyan]Retrying in 30 seconds...[/cyan]")

            import time

            time.sleep(30)

            # Check again
            if not check_package_available(target_version):
                console.print(
                    "\n[yellow]![/yellow] Version still not available. Please try again in a few minutes."
                )
                console.print("[dim]You can manually retry with:[/dim] [cyan]cw upgrade[/cyan]\n")
                return False

            console.print("[green]*[/green] Version is now available!")

    console.print(f"\n[cyan]Upgrading using {installer}...[/cyan]")

    try:
        if installer == "pipx":
            cmd = ["pipx", "upgrade", "claude-worktree"]
        elif installer == "uv-tool":
            # uv tool upgrade automatically checks for latest version
            cmd = ["uv", "tool", "upgrade", "claude-worktree"]
        elif installer == "uv-pip":
            # Use --refresh to bypass cache and --system for non-venv installs
            cmd = ["uv", "pip", "install", "--upgrade", "--refresh", "--system", "claude-worktree"]
        else:  # pip
            # Use --no-cache-dir to bypass cache
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--upgrade",
                "--no-cache-dir",
                "claude-worktree",
            ]

        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
        )

        # Show the output
        if result.stdout:
            console.print(result.stdout)
        if result.stderr:
            console.print(result.stderr)

        if result.returncode == 0:
            # Check if anything was actually upgraded
            output = result.stdout + result.stderr
            if "Nothing to upgrade" in output or "already installed" in output.lower():
                console.print("\n[yellow]![/yellow] Already at the latest version")
                return False

            console.print("[bold green]*[/bold green] Upgrade completed successfully!")
            console.print(f"\nPlease restart {sys.argv[0]} to use the new version.\n")
            return True
        else:
            console.print("[bold red]x[/bold red] Upgrade failed")
            return False

    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]x[/bold red] Upgrade failed: {e}")
        return False
    except FileNotFoundError:
        console.print(f"[bold red]x[/bold red] {installer} not found")
        return False


def check_for_updates(auto: bool = True) -> bool:
    """
    Check for updates and optionally prompt user to upgrade.

    Args:
        auto: If True, only check if it's the first run today and auto-check is enabled.
              If False, always check (for manual upgrade command)

    Returns:
        True if an update is available, False otherwise
    """
    # For auto-check, respect the config setting
    if auto:
        from .config import load_config

        config = load_config()
        if not config.get("update", {}).get("auto_check", True):
            # Auto-check is disabled
            return False

    # Show current version for manual upgrade
    current_version = __version__
    if not auto:
        console.print(f"\n[cyan]Current version:[/cyan] {current_version}")
        console.print("[cyan]Checking for updates...[/cyan]")

    # For auto-check, respect the daily limit
    if auto and not should_check_update():
        return False

    # Try to fetch latest version
    latest_version = get_latest_version()

    if latest_version is None:
        # Network error or PyPI unavailable
        if auto:
            mark_update_checked(failed=True)
        else:
            console.print(
                "[bold red]x[/bold red] Failed to check for updates. Please try again later.\n"
            )
        return False

    # Mark that we successfully checked today
    if auto:
        mark_update_checked(failed=False)

    # Show remote version for manual upgrade
    if not auto:
        console.print(f"[cyan]Latest version:[/cyan]  {latest_version}")

    # Compare versions
    if not is_newer_version(latest_version, current_version):
        if not auto:
            console.print("\n[green]* You are already running the latest version![/green]\n")
        return False

    # New version available!
    console.print("\n[bold yellow]📦 Update available:[/bold yellow]")
    if auto:
        # For auto-check, show both versions
        console.print(f"  Current version: [cyan]{current_version}[/cyan]")
        console.print(f"  Latest version:  [green]{latest_version}[/green]\n")
    else:
        # For manual upgrade, already showed both versions above
        console.print()

    # Check if running in non-interactive environment
    from .git_utils import is_non_interactive

    if is_non_interactive():
        # Non-interactive mode behavior
        if auto:
            # Auto-check in CI/scripts: show notification but don't upgrade
            console.print("[dim]Auto-upgrade skipped in non-interactive environment.[/dim]")
            console.print("[dim]Run 'cw upgrade' manually to update.[/dim]\n")
            return True
        else:
            # Manual upgrade command in CI/scripts: proceed automatically
            console.print(
                "[dim]Running in non-interactive environment, upgrading automatically...[/dim]\n"
            )
            return upgrade_package(target_version=latest_version)

    # Interactive mode: ask user for confirmation
    # For manual upgrade command, always ask
    # For auto-check, ask if user wants to upgrade
    if Confirm.ask("Would you like to upgrade now?"):
        return upgrade_package(target_version=latest_version)

    if auto:
        console.print("\n[dim]Run 'cw upgrade' anytime to update.[/dim]\n")

    return True
