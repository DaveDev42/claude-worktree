"""Tests for stats functionality."""

import subprocess
import time
from pathlib import Path

from claude_worktree.helpers import format_age
from claude_worktree.operations import show_stats


def test_show_stats_no_worktrees(temp_git_repo: Path, monkeypatch, capsys) -> None:
    """Test stats display with no feature worktrees."""
    monkeypatch.chdir(temp_git_repo)

    show_stats()

    captured = capsys.readouterr()
    assert "No feature worktrees found" in captured.out


def test_show_stats_single_worktree(temp_git_repo: Path, monkeypatch, capsys) -> None:
    """Test stats display with a single worktree."""
    monkeypatch.chdir(temp_git_repo)

    # Create a feature worktree
    feature_path = temp_git_repo.parent / "feature"
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature-branch", str(feature_path), "HEAD"],
        cwd=temp_git_repo,
        capture_output=True,
        check=True,
    )

    show_stats()

    captured = capsys.readouterr()
    # Check for statistics sections
    assert "Worktree Statistics" in captured.out or "📊" in captured.out
    assert "Overview:" in captured.out
    assert "Total worktrees: 1" in captured.out
    assert "feature-branch" in captured.out


def test_show_stats_multiple_worktrees(temp_git_repo: Path, monkeypatch, capsys) -> None:
    """Test stats display with multiple worktrees."""
    monkeypatch.chdir(temp_git_repo)

    # Create multiple feature worktrees
    feature1_path = temp_git_repo.parent / "feature1"
    feature2_path = temp_git_repo.parent / "feature2"
    feature3_path = temp_git_repo.parent / "feature3"

    subprocess.run(
        ["git", "worktree", "add", "-b", "feature-1", str(feature1_path), "HEAD"],
        cwd=temp_git_repo,
        capture_output=True,
        check=True,
    )

    subprocess.run(
        ["git", "worktree", "add", "-b", "feature-2", str(feature2_path), "HEAD"],
        cwd=temp_git_repo,
        capture_output=True,
        check=True,
    )

    subprocess.run(
        ["git", "worktree", "add", "-b", "feature-3", str(feature3_path), "HEAD"],
        cwd=temp_git_repo,
        capture_output=True,
        check=True,
    )

    show_stats()

    captured = capsys.readouterr()
    # Should show 3 worktrees
    assert "Total worktrees: 3" in captured.out


def test_show_stats_age_statistics(temp_git_repo: Path, monkeypatch, capsys) -> None:
    """Test that age statistics are displayed."""
    monkeypatch.chdir(temp_git_repo)

    # Create a feature worktree
    feature_path = temp_git_repo.parent / "feature"
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature-branch", str(feature_path), "HEAD"],
        cwd=temp_git_repo,
        capture_output=True,
        check=True,
    )

    show_stats()

    captured = capsys.readouterr()
    # Should show age statistics section
    assert "Age Statistics:" in captured.out
    assert "Average age:" in captured.out
    assert "Oldest:" in captured.out
    assert "Newest:" in captured.out


def test_show_stats_commit_statistics(temp_git_repo: Path, monkeypatch, capsys) -> None:
    """Test that commit statistics are displayed."""
    monkeypatch.chdir(temp_git_repo)

    # Create a feature worktree with commits
    feature_path = temp_git_repo.parent / "feature"
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature-branch", str(feature_path), "HEAD"],
        cwd=temp_git_repo,
        capture_output=True,
        check=True,
    )

    # Make a commit in the feature worktree
    test_file = feature_path / "test.txt"
    test_file.write_text("test")
    subprocess.run(["git", "add", "test.txt"], cwd=feature_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "test commit"], cwd=feature_path, capture_output=True, check=True
    )

    show_stats()

    captured = capsys.readouterr()
    # Should show commit statistics
    assert "Commit Statistics:" in captured.out
    assert "Total commits" in captured.out
    assert "Average commits" in captured.out


def test_show_stats_status_distribution(temp_git_repo: Path, monkeypatch, capsys) -> None:
    """Test that status distribution is shown."""
    monkeypatch.chdir(temp_git_repo)

    # Create clean worktree
    clean_path = temp_git_repo.parent / "clean"
    subprocess.run(
        ["git", "worktree", "add", "-b", "clean-branch", str(clean_path), "HEAD"],
        cwd=temp_git_repo,
        capture_output=True,
        check=True,
    )

    # Create modified worktree
    modified_path = temp_git_repo.parent / "modified"
    subprocess.run(
        ["git", "worktree", "add", "-b", "modified-branch", str(modified_path), "HEAD"],
        cwd=temp_git_repo,
        capture_output=True,
        check=True,
    )
    (modified_path / "test.txt").write_text("modified")

    show_stats()

    captured = capsys.readouterr()
    # Should show status distribution
    assert "Status:" in captured.out
    assert "clean" in captured.out


def test_show_stats_oldest_worktrees(temp_git_repo: Path, monkeypatch, capsys) -> None:
    """Test that oldest worktrees are listed."""
    monkeypatch.chdir(temp_git_repo)

    # Create worktrees
    for i in range(3):
        feature_path = temp_git_repo.parent / f"feature{i}"
        subprocess.run(
            ["git", "worktree", "add", "-b", f"feature-{i}", str(feature_path), "HEAD"],
            cwd=temp_git_repo,
            capture_output=True,
            check=True,
        )
        # Sleep briefly to ensure different timestamps
        time.sleep(0.1)

    show_stats()

    captured = capsys.readouterr()
    # Should show oldest worktrees section
    assert "Oldest Worktrees:" in captured.out


def test_show_stats_most_active_worktrees(temp_git_repo: Path, monkeypatch, capsys) -> None:
    """Test that most active worktrees are listed."""
    monkeypatch.chdir(temp_git_repo)

    # Create worktrees with different commit counts
    for i in range(2):
        feature_path = temp_git_repo.parent / f"feature{i}"
        subprocess.run(
            ["git", "worktree", "add", "-b", f"feature-{i}", str(feature_path), "HEAD"],
            cwd=temp_git_repo,
            capture_output=True,
            check=True,
        )

        # Make commits
        for j in range(i + 1):
            test_file = feature_path / f"test{j}.txt"
            test_file.write_text(f"test {j}")
            subprocess.run(
                ["git", "add", f"test{j}.txt"], cwd=feature_path, capture_output=True, check=True
            )
            subprocess.run(
                ["git", "commit", "-m", f"commit {j}"],
                cwd=feature_path,
                capture_output=True,
                check=True,
            )

    show_stats()

    captured = capsys.readouterr()
    # Should show most active worktrees section
    assert "Most Active Worktrees" in captured.out


def test_format_age_hours() -> None:
    """Test format_age for hours."""
    assert format_age(0.5) == "12h ago"
    assert format_age(0.04) == "just now"  # Less than 1 hour shows as "just now"
    assert format_age(0.0) == "just now"


def test_format_age_days() -> None:
    """Test format_age for days."""
    assert format_age(1.5) == "1d ago"
    assert format_age(3.0) == "3d ago"
    assert format_age(6.9) == "6d ago"


def test_format_age_weeks() -> None:
    """Test format_age for weeks."""
    assert format_age(7.0) == "1w ago"
    assert format_age(14.0) == "2w ago"
    assert format_age(21.0) == "3w ago"


def test_format_age_months() -> None:
    """Test format_age for months."""
    assert format_age(30.0) == "1mo ago"
    assert format_age(60.0) == "2mo ago"
    assert format_age(180.0) == "6mo ago"


def test_format_age_years() -> None:
    """Test format_age for years."""
    assert format_age(365.0) == "1y ago"
    assert format_age(730.0) == "2y ago"
