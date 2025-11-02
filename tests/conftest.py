"""Shared pytest fixtures for claude-worktree tests."""

import subprocess
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_config_globally(tmp_path: Path, monkeypatch) -> None:
    """Isolate config directory for all tests to prevent modifying user's config.

    This prevents tests from modifying the user's actual config file at
    ~/.config/claude-worktree/config.json by redirecting config operations
    to a temporary directory.

    Also disables AI tool launching by setting CW_AI_TOOL="".
    """
    # Isolate config directory to tmp_path
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows

    # Disable AI tool launching
    monkeypatch.setenv("CW_AI_TOOL", "")


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
    # Ensure the default branch is named 'main' (git init may create 'master' in some environments)
    subprocess.run(
        ["git", "branch", "-M", "main"],
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
    """Disable AI tool launching for tests."""
    # Mock get_ai_tool_command to return empty array (no-op)
    from claude_worktree import config

    def mock_get_ai_tool_command():
        return []

    monkeypatch.setattr(config, "get_ai_tool_command", mock_get_ai_tool_command)
