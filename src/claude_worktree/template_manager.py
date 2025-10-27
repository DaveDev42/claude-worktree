"""Template management for worktree configurations."""

import json
import shutil
from pathlib import Path
from typing import Any

from rich.console import Console

from .config import get_config_path
from .exceptions import ClaudeWorktreeError

console = Console()


class TemplateError(ClaudeWorktreeError):
    """Template-related errors."""

    pass


def get_templates_dir() -> Path:
    """Get templates directory path."""
    config_path = get_config_path()
    templates_dir = config_path.parent / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    return templates_dir


def list_templates() -> list[str]:
    """
    List all available templates.

    Returns:
        List of template names
    """
    templates_dir = get_templates_dir()
    return [d.name for d in templates_dir.iterdir() if d.is_dir()]


def template_exists(name: str) -> bool:
    """Check if a template exists."""
    templates_dir = get_templates_dir()
    return (templates_dir / name).exists()


def get_template_path(name: str) -> Path:
    """Get path to a specific template."""
    return get_templates_dir() / name


def create_template(name: str, source_path: Path, description: str | None = None) -> None:
    """
    Create a new template from a worktree.

    Args:
        name: Template name
        source_path: Path to worktree to use as template
        description: Optional template description

    Raises:
        TemplateError: If template already exists or source is invalid
    """
    if template_exists(name):
        raise TemplateError(f"Template '{name}' already exists. Use --force to overwrite.")

    if not source_path.exists():
        raise TemplateError(f"Source path does not exist: {source_path}")

    if not source_path.is_dir():
        raise TemplateError(f"Source path is not a directory: {source_path}")

    template_path = get_template_path(name)
    template_path.mkdir(parents=True, exist_ok=True)

    # Create template metadata
    metadata: dict[str, Any] = {
        "name": name,
        "description": description or f"Template created from {source_path.name}",
        "created_from": str(source_path),
    }

    # Copy template files (exclude .git directory and other common exclusions)
    exclusions = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox", "build", "dist"}

    files_copied = 0
    for item in source_path.iterdir():
        if item.name not in exclusions:
            dest = template_path / item.name
            if item.is_file():
                shutil.copy2(item, dest)
                files_copied += 1
            elif item.is_dir():
                shutil.copytree(item, dest, ignore=shutil.ignore_patterns(*exclusions))
                # Count files recursively
                files_copied += sum(1 for _ in dest.rglob("*") if _.is_file())

    metadata["files_count"] = files_copied

    # Save metadata
    metadata_file = template_path / ".template.json"
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)

    console.print(f"[bold green]✓[/bold green] Template '{name}' created successfully")
    console.print(f"  Files copied: {files_copied}")
    console.print(f"  Location: {template_path}\n")


def delete_template(name: str) -> None:
    """
    Delete a template.

    Args:
        name: Template name

    Raises:
        TemplateError: If template doesn't exist
    """
    if not template_exists(name):
        raise TemplateError(f"Template '{name}' does not exist")

    template_path = get_template_path(name)
    shutil.rmtree(template_path)
    console.print(f"[bold green]✓[/bold green] Template '{name}' deleted\n")


def show_template_info(name: str) -> None:
    """
    Display information about a template.

    Args:
        name: Template name

    Raises:
        TemplateError: If template doesn't exist
    """
    if not template_exists(name):
        raise TemplateError(f"Template '{name}' does not exist")

    template_path = get_template_path(name)
    metadata_file = template_path / ".template.json"

    if metadata_file.exists():
        with open(metadata_file) as f:
            metadata = json.load(f)

        console.print(f"\n[bold cyan]Template: {name}[/bold cyan]\n")
        console.print(f"[bold]Description:[/bold] {metadata.get('description', 'N/A')}")
        console.print(f"[bold]Created from:[/bold] {metadata.get('created_from', 'N/A')}")
        console.print(f"[bold]Files:[/bold] {metadata.get('files_count', 'Unknown')}")
        console.print(f"[bold]Location:[/bold] {template_path}")
    else:
        console.print(f"\n[bold cyan]Template: {name}[/bold cyan]\n")
        console.print("[yellow]⚠[/yellow] No metadata available")
        console.print(f"[bold]Location:[/bold] {template_path}")

    console.print()


def apply_template(name: str, target_path: Path) -> None:
    """
    Apply a template to a target directory.

    Args:
        name: Template name
        target_path: Path to apply template to

    Raises:
        TemplateError: If template doesn't exist or target is invalid
    """
    if not template_exists(name):
        raise TemplateError(f"Template '{name}' does not exist")

    template_path = get_template_path(name)

    if not target_path.exists():
        raise TemplateError(f"Target path does not exist: {target_path}")

    if not target_path.is_dir():
        raise TemplateError(f"Target path is not a directory: {target_path}")

    # Copy template files to target (excluding metadata)
    files_copied = 0
    for item in template_path.iterdir():
        if item.name == ".template.json":
            continue

        dest = target_path / item.name
        if dest.exists():
            console.print(f"[yellow]⚠[/yellow] Skipping existing file: {item.name}")
            continue

        if item.is_file():
            shutil.copy2(item, dest)
            files_copied += 1
        elif item.is_dir():
            shutil.copytree(item, dest)
            files_copied += sum(1 for _ in dest.rglob("*") if _.is_file())

    console.print(f"[bold green]✓[/bold green] Template '{name}' applied successfully")
    console.print(f"  Files copied: {files_copied}\n")


def show_all_templates() -> None:
    """Display all available templates."""
    templates = list_templates()

    if not templates:
        console.print("[yellow]No templates found[/yellow]")
        console.print("Create a template with: [cyan]cw template create <name> <path>[/cyan]\n")
        return

    console.print(f"\n[bold cyan]Available Templates ({len(templates)})[/bold cyan]\n")

    for template_name in sorted(templates):
        template_path = get_template_path(template_name)
        metadata_file = template_path / ".template.json"

        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)
            description = metadata.get("description", "No description")
            files_count = metadata.get("files_count", "?")
        else:
            description = "No description available"
            files_count = "?"

        console.print(f"[bold green]•[/bold green] {template_name}")
        console.print(f"  {description}")
        console.print(f"  [dim]Files: {files_count}[/dim]")
        console.print()
