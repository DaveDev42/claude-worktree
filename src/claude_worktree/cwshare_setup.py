"""Setup prompt for .cwshare file creation."""

from pathlib import Path

import typer

from .console import get_console
from .git_utils import get_config, get_repo_root, is_non_interactive, set_config

console = get_console()

# Common files that users might want to share across worktrees
COMMON_SHARED_FILES = [
    ".env",
    ".env.local",
    ".env.development",
    ".env.test",
    "config/local.json",
    "config/local.yaml",
    "config/local.yml",
    ".vscode/settings.json",
]


def is_cwshare_prompted(repo: Path) -> bool:
    """Check if user has been prompted for .cwshare in this repo.

    Args:
        repo: Repository path

    Returns:
        True if already prompted, False otherwise
    """
    prompted = get_config("cwshare.prompted", repo=repo)
    return prompted == "true"


def mark_cwshare_prompted(repo: Path) -> None:
    """Mark that user has been prompted for .cwshare in this repo.

    Args:
        repo: Repository path
    """
    set_config("cwshare.prompted", "true", repo=repo)


def has_cwshare_file(repo: Path) -> bool:
    """Check if .cwshare file exists in repo.

    Args:
        repo: Repository path

    Returns:
        True if .cwshare exists, False otherwise
    """
    return (repo / ".cwshare").exists()


def detect_common_files(repo: Path) -> list[str]:
    """Detect common files that exist in repo and might be worth sharing.

    Args:
        repo: Repository path

    Returns:
        List of detected file paths
    """
    detected = []
    for file_path in COMMON_SHARED_FILES:
        if (repo / file_path).exists():
            detected.append(file_path)
    return detected


def create_cwshare_template(repo: Path, suggested_files: list[str]) -> None:
    """Create a .cwshare file with template content.

    Args:
        repo: Repository path
        suggested_files: List of files to suggest (will be commented out)
    """
    cwshare_path = repo / ".cwshare"

    template = """# .cwshare - Files to copy to new worktrees
#
# Files listed here will be automatically copied when you run 'cw new'.
# Useful for environment files and local configs not tracked in git.
#
# Format:
#   - One file/directory path per line (relative to repo root)
#   - Lines starting with # are comments
#   - Empty lines are ignored
"""

    if suggested_files:
        template += "#\n# Detected files in this repository (uncomment to enable):\n\n"
        for file in suggested_files:
            template += f"# {file}\n"
    else:
        template += "#\n# No common files detected. Add your own below:\n\n"

    cwshare_path.write_text(template)


def prompt_cwshare_setup() -> None:
    """Prompt user to create .cwshare file on first run in this repo.

    This function:
    1. Checks if we're in a git repository (skip if not)
    2. Checks if we're in non-interactive environment (skip if yes)
    3. Checks if .cwshare already exists (skip if yes, mark as prompted)
    4. Checks if user was already prompted for this repo (skip if yes)
    5. Detects common files and suggests them
    6. Asks user if they want to create .cwshare
    7. Marks repo as prompted regardless of answer
    """
    # Check if in git repo
    try:
        repo = get_repo_root()
    except Exception:
        # Not in a git repo - skip silently
        return

    # Don't prompt in non-interactive environments
    if is_non_interactive():
        return

    # Check if .cwshare already exists
    if has_cwshare_file(repo):
        # File exists - mark as prompted and return
        if not is_cwshare_prompted(repo):
            mark_cwshare_prompted(repo)
        return

    # Check if already prompted for this repo
    if is_cwshare_prompted(repo):
        return

    # Detect common files
    detected_files = detect_common_files(repo)

    # Prompt user
    console.print("\n[bold cyan]💡 .cwshare File Setup[/bold cyan]")
    console.print("\nWould you like to create a [cyan].cwshare[/cyan] file?")
    console.print("This lets you automatically copy files to new worktrees (like .env, configs).\n")

    if detected_files:
        console.print("[bold]Detected files that you might want to share:[/bold]")
        for file in detected_files:
            console.print(f"  [dim]•[/dim] {file}")
        console.print("")

    try:
        response = typer.confirm("Create .cwshare file?", default=True)
    except (KeyboardInterrupt, EOFError):
        # User cancelled
        mark_cwshare_prompted(repo)
        console.print("\n[dim]You can create .cwshare manually anytime.[/dim]\n")
        return

    # Mark as prompted
    mark_cwshare_prompted(repo)

    if response:
        # Create .cwshare file
        create_cwshare_template(repo, detected_files)
        console.print(f"\n[bold green]✓[/bold green] Created {repo / '.cwshare'}")
        console.print("\n[bold]Next steps:[/bold]")
        console.print("  1. Review and edit .cwshare to uncomment files you want to share")
        console.print("  2. Add to git: [cyan]git add .cwshare && git commit[/cyan]")
        console.print("  3. Files will be copied when you run: [cyan]cw new <branch>[/cyan]\n")
    else:
        # User declined
        console.print("\n[dim]You can create .cwshare manually anytime.[/dim]\n")
