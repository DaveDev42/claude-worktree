"""Tests for .cwshare file sharing functionality."""

from pathlib import Path

from claude_worktree.shared_files import parse_cwshare, share_files


def test_parse_cwshare_basic(tmp_path: Path) -> None:
    """Test parsing basic .cwshare file."""
    cwshare = tmp_path / ".cwshare"
    cwshare.write_text(".env\n.env.local\nconfig/local.json\n")

    paths = parse_cwshare(tmp_path)
    assert paths == [".env", ".env.local", "config/local.json"]


def test_parse_cwshare_with_comments(tmp_path: Path) -> None:
    """Test parsing .cwshare file with comments."""
    cwshare = tmp_path / ".cwshare"
    cwshare.write_text("""# This is a comment
.env
# Another comment
.env.local
""")

    paths = parse_cwshare(tmp_path)
    assert paths == [".env", ".env.local"]


def test_parse_cwshare_with_empty_lines(tmp_path: Path) -> None:
    """Test parsing .cwshare file with empty lines."""
    cwshare = tmp_path / ".cwshare"
    cwshare.write_text("""
.env

.env.local

""")

    paths = parse_cwshare(tmp_path)
    assert paths == [".env", ".env.local"]


def test_parse_cwshare_with_whitespace(tmp_path: Path) -> None:
    """Test parsing .cwshare file with leading/trailing whitespace."""
    cwshare = tmp_path / ".cwshare"
    cwshare.write_text("  .env  \n\t.env.local\t\n")

    paths = parse_cwshare(tmp_path)
    assert paths == [".env", ".env.local"]


def test_parse_cwshare_not_exists(tmp_path: Path) -> None:
    """Test parsing when .cwshare file doesn't exist."""
    paths = parse_cwshare(tmp_path)
    assert paths == []


def test_parse_cwshare_empty_file(tmp_path: Path) -> None:
    """Test parsing empty .cwshare file."""
    cwshare = tmp_path / ".cwshare"
    cwshare.write_text("")

    paths = parse_cwshare(tmp_path)
    assert paths == []


def test_share_files_copies_files(tmp_path: Path) -> None:
    """Test that share_files copies specified files."""
    # Setup source repo
    source_repo = tmp_path / "source"
    source_repo.mkdir()
    (source_repo / ".cwshare").write_text(".env\n.env.local\n")
    (source_repo / ".env").write_text("SECRET=value1")
    (source_repo / ".env.local").write_text("SECRET=value2")

    # Create target worktree
    target_worktree = tmp_path / "target"
    target_worktree.mkdir()

    # Share files
    share_files(source_repo, target_worktree)

    # Verify files were copied
    assert (target_worktree / ".env").exists()
    assert (target_worktree / ".env.local").exists()
    assert (target_worktree / ".env").read_text() == "SECRET=value1"
    assert (target_worktree / ".env.local").read_text() == "SECRET=value2"

    # Verify they are copies, not symlinks
    assert not (target_worktree / ".env").is_symlink()
    assert not (target_worktree / ".env.local").is_symlink()


def test_share_files_copies_directories(tmp_path: Path) -> None:
    """Test that share_files copies directories."""
    # Setup source repo
    source_repo = tmp_path / "source"
    source_repo.mkdir()
    (source_repo / ".cwshare").write_text("config\n")
    config_dir = source_repo / "config"
    config_dir.mkdir()
    (config_dir / "local.json").write_text('{"key": "value"}')
    (config_dir / "secrets.json").write_text('{"secret": "hidden"}')

    # Create target worktree
    target_worktree = tmp_path / "target"
    target_worktree.mkdir()

    # Share files
    share_files(source_repo, target_worktree)

    # Verify directory and contents were copied
    target_config = target_worktree / "config"
    assert target_config.exists()
    assert target_config.is_dir()
    assert not target_config.is_symlink()
    assert (target_config / "local.json").read_text() == '{"key": "value"}'
    assert (target_config / "secrets.json").read_text() == '{"secret": "hidden"}'


def test_share_files_nested_path(tmp_path: Path) -> None:
    """Test sharing nested files creates parent directories."""
    # Setup source repo
    source_repo = tmp_path / "source"
    source_repo.mkdir()
    (source_repo / ".cwshare").write_text("config/local/settings.json\n")
    config_dir = source_repo / "config" / "local"
    config_dir.mkdir(parents=True)
    (config_dir / "settings.json").write_text('{"nested": true}')

    # Create target worktree
    target_worktree = tmp_path / "target"
    target_worktree.mkdir()

    # Share files
    share_files(source_repo, target_worktree)

    # Verify nested file was copied with parent directories created
    target_file = target_worktree / "config" / "local" / "settings.json"
    assert target_file.exists()
    assert target_file.read_text() == '{"nested": true}'


def test_share_files_skips_nonexistent_source(tmp_path: Path) -> None:
    """Test that share_files skips files that don't exist in source."""
    # Setup source repo with .cwshare but no actual files
    source_repo = tmp_path / "source"
    source_repo.mkdir()
    (source_repo / ".cwshare").write_text(".env\n.env.local\n")
    # Only create .env, not .env.local
    (source_repo / ".env").write_text("SECRET=value")

    # Create target worktree
    target_worktree = tmp_path / "target"
    target_worktree.mkdir()

    # Share files (should not raise, just skip .env.local)
    share_files(source_repo, target_worktree)

    # Verify .env was copied but .env.local was not
    assert (target_worktree / ".env").exists()
    assert not (target_worktree / ".env.local").exists()


def test_share_files_skips_existing_target(tmp_path: Path) -> None:
    """Test that share_files doesn't overwrite existing files in target."""
    # Setup source repo
    source_repo = tmp_path / "source"
    source_repo.mkdir()
    (source_repo / ".cwshare").write_text(".env\n")
    (source_repo / ".env").write_text("NEW_SECRET=new_value")

    # Create target worktree with existing .env
    target_worktree = tmp_path / "target"
    target_worktree.mkdir()
    (target_worktree / ".env").write_text("OLD_SECRET=old_value")

    # Share files (should skip since .env already exists)
    share_files(source_repo, target_worktree)

    # Verify existing file was NOT overwritten
    assert (target_worktree / ".env").read_text() == "OLD_SECRET=old_value"


def test_share_files_no_cwshare(tmp_path: Path) -> None:
    """Test that share_files does nothing when no .cwshare file exists."""
    # Setup source repo without .cwshare
    source_repo = tmp_path / "source"
    source_repo.mkdir()
    (source_repo / ".env").write_text("SECRET=value")

    # Create target worktree
    target_worktree = tmp_path / "target"
    target_worktree.mkdir()

    # Share files (should do nothing)
    share_files(source_repo, target_worktree)

    # Verify nothing was copied
    assert not (target_worktree / ".env").exists()


def test_share_files_empty_cwshare(tmp_path: Path) -> None:
    """Test that share_files does nothing when .cwshare is empty."""
    # Setup source repo with empty .cwshare
    source_repo = tmp_path / "source"
    source_repo.mkdir()
    (source_repo / ".cwshare").write_text("")
    (source_repo / ".env").write_text("SECRET=value")

    # Create target worktree
    target_worktree = tmp_path / "target"
    target_worktree.mkdir()

    # Share files (should do nothing)
    share_files(source_repo, target_worktree)

    # Verify nothing was copied
    assert not (target_worktree / ".env").exists()


def test_share_files_preserves_symlinks_in_copied_dirs(tmp_path: Path) -> None:
    """Test that symlinks inside copied directories are preserved."""
    # Setup source repo with a directory containing a symlink
    source_repo = tmp_path / "source"
    source_repo.mkdir()
    (source_repo / ".cwshare").write_text("config\n")

    config_dir = source_repo / "config"
    config_dir.mkdir()
    (config_dir / "real_file.json").write_text('{"real": true}')
    # Create a symlink inside the directory
    symlink_path = config_dir / "link_file.json"
    symlink_path.symlink_to(config_dir / "real_file.json")

    # Create target worktree
    target_worktree = tmp_path / "target"
    target_worktree.mkdir()

    # Share files
    share_files(source_repo, target_worktree)

    # Verify the symlink was preserved as a symlink
    target_symlink = target_worktree / "config" / "link_file.json"
    assert target_symlink.is_symlink()
