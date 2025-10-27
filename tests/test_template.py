"""Tests for template management functionality."""

from pathlib import Path

from claude_worktree.template_manager import (
    apply_template,
    create_template,
    delete_template,
    get_templates_dir,
    list_templates,
    template_exists,
)


def test_get_templates_dir() -> None:
    """Test that templates directory is created."""
    templates_dir = get_templates_dir()
    assert templates_dir.exists()
    assert templates_dir.is_dir()
    assert templates_dir.name == "templates"


def test_list_templates_empty(tmp_path: Path, monkeypatch) -> None:
    """Test listing templates when none exist."""
    # Mock templates directory
    monkeypatch.setattr(
        "claude_worktree.template_manager.get_templates_dir", lambda: tmp_path / "templates"
    )
    (tmp_path / "templates").mkdir()

    templates = list_templates()
    assert templates == []


def test_create_template(tmp_path: Path, monkeypatch) -> None:
    """Test creating a template from a source directory."""
    # Setup source directory
    source = tmp_path / "source"
    source.mkdir()
    (source / "file1.txt").write_text("content1")
    (source / "file2.py").write_text("content2")
    (source / "subdir").mkdir()
    (source / "subdir" / "file3.txt").write_text("content3")

    # Mock templates directory
    templates_dir = tmp_path / "templates"
    monkeypatch.setattr("claude_worktree.template_manager.get_templates_dir", lambda: templates_dir)

    # Create template
    create_template("test-template", source, "Test description")

    # Verify template was created
    template_path = templates_dir / "test-template"
    assert template_path.exists()
    assert (template_path / "file1.txt").exists()
    assert (template_path / "file2.py").exists()
    assert (template_path / "subdir" / "file3.txt").exists()
    assert (template_path / ".template.json").exists()


def test_template_exists(tmp_path: Path, monkeypatch) -> None:
    """Test checking if a template exists."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    monkeypatch.setattr("claude_worktree.template_manager.get_templates_dir", lambda: templates_dir)

    # Create a template directory
    (templates_dir / "existing-template").mkdir()

    assert template_exists("existing-template")
    assert not template_exists("nonexistent-template")


def test_delete_template(tmp_path: Path, monkeypatch) -> None:
    """Test deleting a template."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    template_path = templates_dir / "test-template"
    template_path.mkdir()
    (template_path / "file.txt").write_text("content")

    monkeypatch.setattr("claude_worktree.template_manager.get_templates_dir", lambda: templates_dir)

    # Delete template
    delete_template("test-template")

    # Verify it was deleted
    assert not template_path.exists()


def test_apply_template(tmp_path: Path, monkeypatch) -> None:
    """Test applying a template to a target directory."""
    # Setup template
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    template_path = templates_dir / "test-template"
    template_path.mkdir()
    (template_path / "file1.txt").write_text("content1")
    (template_path / "file2.py").write_text("content2")

    monkeypatch.setattr("claude_worktree.template_manager.get_templates_dir", lambda: templates_dir)

    # Setup target directory
    target = tmp_path / "target"
    target.mkdir()

    # Apply template
    apply_template("test-template", target)

    # Verify files were copied
    assert (target / "file1.txt").exists()
    assert (target / "file2.py").exists()
    assert (target / "file1.txt").read_text() == "content1"
    assert (target / "file2.py").read_text() == "content2"


def test_apply_template_skips_existing(tmp_path: Path, monkeypatch, capsys) -> None:
    """Test that apply_template skips existing files."""
    # Setup template
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    template_path = templates_dir / "test-template"
    template_path.mkdir()
    (template_path / "file1.txt").write_text("template content")

    monkeypatch.setattr("claude_worktree.template_manager.get_templates_dir", lambda: templates_dir)

    # Setup target with existing file
    target = tmp_path / "target"
    target.mkdir()
    (target / "file1.txt").write_text("existing content")

    # Apply template
    apply_template("test-template", target)

    # Verify existing file was not overwritten
    assert (target / "file1.txt").read_text() == "existing content"

    # Check warning message
    captured = capsys.readouterr()
    assert "Skipping existing file" in captured.out


def test_create_template_excludes_git(tmp_path: Path, monkeypatch) -> None:
    """Test that .git directory is excluded from templates."""
    # Setup source with .git directory
    source = tmp_path / "source"
    source.mkdir()
    (source / "file.txt").write_text("content")
    git_dir = source / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("git config")

    templates_dir = tmp_path / "templates"
    monkeypatch.setattr("claude_worktree.template_manager.get_templates_dir", lambda: templates_dir)

    # Create template
    create_template("test-template", source)

    # Verify .git was excluded
    template_path = templates_dir / "test-template"
    assert (template_path / "file.txt").exists()
    assert not (template_path / ".git").exists()
