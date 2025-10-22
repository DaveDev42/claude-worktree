"""Shared pytest fixtures for claude-worktree tests."""

import subprocess
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def temp_git_repo(tmp_path: Path, monkeypatch) -> Generator[Path, None, None]:
    """Create a temporary git repository for testing."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    # Disable GPG signing for tests
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Create initial commit on main branch
    (repo_path / "README.md").write_text("# Test Repository")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Change to repo directory for tests
    monkeypatch.chdir(repo_path)

    yield repo_path

    # Cleanup: remove all worktrees
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            lines = result.stdout.splitlines()
            worktrees = []
            for line in lines:
                if line.startswith("worktree "):
                    path = line.split(" ", 1)[1]
                    if path != str(repo_path):
                        worktrees.append(path)

            for wt in worktrees:
                subprocess.run(
                    ["git", "worktree", "remove", "--force", wt],
                    cwd=repo_path,
                    capture_output=True,
                    check=False,
                )
    except Exception:
        pass


@pytest.fixture
def disable_claude(monkeypatch) -> None:
    """Disable Claude CLI for tests by making it unavailable."""
    # Mock has_command to return False for 'claude'
    from claude_worktree import core, git_utils

    original_has_command = git_utils.has_command

    def mock_has_command(name: str) -> bool:
        if name == "claude":
            return False
        return original_has_command(name)

    monkeypatch.setattr(git_utils, "has_command", mock_has_command)
    monkeypatch.setattr(core, "has_command", mock_has_command)
