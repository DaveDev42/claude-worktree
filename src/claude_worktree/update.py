"""Self-update functionality for claude-worktree."""

import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from packaging.version import parse
from rich.console import Console
from rich.prompt import Confirm

from . import __version__

console = Console()

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
        response = httpx.get(
            "https://pypi.org/pypi/claude-worktree/json",
            timeout=5.0,
            follow_redirects=True,
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
        'pipx', 'pip', 'uv', or None if unknown
    """
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

    # Check if uv is available
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0:
            return "uv"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Default to pip
    return "pip"


def upgrade_package(installer: str | None = None) -> bool:
    """
    Upgrade claude-worktree to the latest version.

    Args:
        installer: Installation method ('pipx', 'pip', 'uv')

    Returns:
        True if upgrade succeeded, False otherwise
    """
    if installer is None:
        installer = detect_installer()

    console.print(f"\n[cyan]Upgrading using {installer}...[/cyan]")

    try:
        if installer == "pipx":
            cmd = ["pipx", "upgrade", "claude-worktree"]
        elif installer == "uv":
            cmd = ["uv", "pip", "install", "--upgrade", "claude-worktree"]
        else:  # pip
            cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "claude-worktree"]

        result = subprocess.run(
            cmd,
            check=True,
            capture_output=False,
            text=True,
        )

        if result.returncode == 0:
            console.print("[bold green]✓[/bold green] Upgrade completed successfully!")
            console.print(f"\nPlease restart {sys.argv[0]} to use the new version.\n")
            return True
        else:
            console.print("[bold red]✗[/bold red] Upgrade failed")
            return False

    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]✗[/bold red] Upgrade failed: {e}")
        return False
    except FileNotFoundError:
        console.print(f"[bold red]✗[/bold red] {installer} not found")
        return False


def check_for_updates(auto: bool = True) -> bool:
    """
    Check for updates and optionally prompt user to upgrade.

    Args:
        auto: If True, only check if it's the first run today.
              If False, always check (for manual upgrade command)

    Returns:
        True if an update is available, False otherwise
    """
    # For auto-check, respect the daily limit
    if auto and not should_check_update():
        return False

    # Try to fetch latest version
    latest_version = get_latest_version()

    if latest_version is None:
        # Network error or PyPI unavailable
        if auto:
            mark_update_checked(failed=True)
        return False

    # Mark that we successfully checked today
    if auto:
        mark_update_checked(failed=False)

    # Compare versions
    current_version = __version__
    if not is_newer_version(latest_version, current_version):
        if not auto:
            console.print(
                f"\n[green]You are already running the latest version ({current_version})[/green]\n"
            )
        return False

    # New version available!
    console.print("\n[bold yellow]📦 Update available:[/bold yellow]")
    console.print(f"  Current version: [cyan]{current_version}[/cyan]")
    console.print(f"  Latest version:  [green]{latest_version}[/green]\n")

    # For manual upgrade command, always ask
    # For auto-check, ask if user wants to upgrade
    if Confirm.ask("Would you like to upgrade now?"):
        return upgrade_package()

    if auto:
        console.print("\n[dim]Run 'cw upgrade' anytime to update.[/dim]\n")

    return True
