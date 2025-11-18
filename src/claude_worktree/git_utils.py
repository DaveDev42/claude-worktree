"""Git operations wrapper utilities."""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .exceptions import GitError, InvalidBranchError


def run_command(
    cmd: list[str],
    cwd: Path | None = None,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    """
    Run a shell command.

    Args:
        cmd: Command and arguments as a list
        cwd: Working directory for the command
        check: Raise exception on non-zero exit code
        capture: Capture stdout/stderr

    Returns:
        CompletedProcess instance

    Raises:
        GitError: If command fails and check=True
    """
    kwargs: dict[str, Any] = {}
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.STDOUT
        kwargs["text"] = True

    try:
        result = subprocess.run(cmd, cwd=cwd, check=False, **kwargs)
        if check and result.returncode != 0:
            output = result.stdout if capture else ""
            raise GitError(f"Command failed: {' '.join(cmd)}\n{output}")
        return result
    except FileNotFoundError as e:
        raise GitError(f"Command not found: {cmd[0]}") from e


def git_command(
    *args: str,
    repo: Path | None = None,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    """
    Run a git command.

    Args:
        *args: Git command arguments
        repo: Repository path
        check: Raise exception on non-zero exit code
        capture: Capture stdout/stderr

    Returns:
        CompletedProcess instance

    Raises:
        GitError: If git command fails
    """
    cmd = ["git"] + list(args)
    return run_command(cmd, cwd=repo, check=check, capture=capture)


def get_repo_root(path: Path | None = None) -> Path:
    """
    Get the root directory of the git repository.

    Args:
        path: Optional path to start from (defaults to current directory)

    Returns:
        Path to repository root

    Raises:
        GitError: If not in a git repository
    """
    try:
        result = git_command("rev-parse", "--show-toplevel", repo=path, capture=True)
        return Path(result.stdout.strip())
    except GitError:
        raise GitError("Not in a git repository")


def get_current_branch(repo: Path | None = None) -> str:
    """
    Get the current branch name.

    Args:
        repo: Repository path

    Returns:
        Current branch name

    Raises:
        InvalidBranchError: If in detached HEAD state
    """
    result = git_command("rev-parse", "--abbrev-ref", "HEAD", repo=repo, capture=True)
    branch = result.stdout.strip()
    if branch == "HEAD":
        raise InvalidBranchError("In detached HEAD state")
    return branch


def branch_exists(branch: str, repo: Path | None = None) -> bool:
    """
    Check if a branch exists.

    Args:
        branch: Branch name
        repo: Repository path

    Returns:
        True if branch exists, False otherwise
    """
    result = git_command("rev-parse", "--verify", branch, repo=repo, check=False, capture=True)
    return result.returncode == 0


def get_config(key: str, repo: Path | None = None) -> str | None:
    """
    Get a git config value.

    Args:
        key: Config key
        repo: Repository path

    Returns:
        Config value or None if not found
    """
    result = git_command("config", "--local", "--get", key, repo=repo, check=False, capture=True)
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def set_config(key: str, value: str, repo: Path | None = None) -> None:
    """
    Set a git config value.

    Args:
        key: Config key
        value: Config value
        repo: Repository path
    """
    git_command("config", "--local", key, value, repo=repo)


def unset_config(key: str, repo: Path | None = None) -> None:
    """
    Unset a git config value.

    Args:
        key: Config key
        repo: Repository path
    """
    git_command("config", "--local", "--unset-all", key, repo=repo, check=False)


def normalize_branch_name(branch: str) -> str:
    """
    Normalize branch name by removing refs/heads/ prefix if present.

    Args:
        branch: Branch name (may include refs/heads/ prefix)

    Returns:
        str: Normalized branch name without refs/heads/ prefix

    Examples:
        >>> normalize_branch_name("refs/heads/main")
        "main"
        >>> normalize_branch_name("feature-branch")
        "feature-branch"
    """
    if branch.startswith("refs/heads/"):
        return branch[11:]
    return branch


def parse_worktrees(repo: Path) -> list[tuple[str, Path]]:
    """
    Parse git worktree list output.

    Args:
        repo: Repository path

    Returns:
        List of (branch_or_detached, path) tuples where path is a Path object
    """
    result = git_command("worktree", "list", "--porcelain", repo=repo, capture=True)
    lines = result.stdout.strip().splitlines()

    items: list[tuple[str, Path]] = []
    cur_path: str | None = None
    cur_branch: str | None = None

    for line in lines:
        if line.startswith("worktree "):
            cur_path = line.split(" ", 1)[1]
        elif line.startswith("branch "):
            cur_branch = line.split(" ", 1)[1]
        elif line.strip() == "" and cur_path:
            items.append((cur_branch or "(detached)", Path(cur_path)))
            cur_path, cur_branch = None, None

    if cur_path:
        items.append((cur_branch or "(detached)", Path(cur_path)))

    return items


def find_worktree_by_branch(repo: Path, branch: str) -> Path | None:
    """
    Find worktree path by branch name.

    Args:
        repo: Repository path
        branch: Branch name

    Returns:
        Worktree path as Path object or None if not found
    """
    for br, path in parse_worktrees(repo):
        if br == branch:
            return path
    return None


def has_command(name: str) -> bool:
    """
    Check if a command is available in PATH.

    Args:
        name: Command name

    Returns:
        True if command exists, False otherwise
    """
    from shutil import which

    return bool(which(name))


def is_non_interactive() -> bool:
    """
    Check if running in non-interactive environment.

    Detects non-interactive environments where user input prompts should be skipped:
    - CI/CD environments (GitHub Actions, GitLab CI, Jenkins, etc.)
    - Scripted/automated execution
    - SSH without TTY
    - Explicit non-interactive flag

    Returns:
        True if non-interactive environment detected, False otherwise

    Environment Variables:
        CW_NON_INTERACTIVE: Set to '1' or 'true' to force non-interactive mode
        CI: Common CI environment indicator
        GITHUB_ACTIONS, GITLAB_CI, JENKINS_HOME, etc.: CI-specific variables
    """
    # Check explicit non-interactive flag
    non_interactive_env = os.environ.get("CW_NON_INTERACTIVE", "").lower()
    if non_interactive_env in ("1", "true", "yes"):
        return True

    # Check if stdin is not a TTY (e.g., piped input, redirected stdin)
    if not sys.stdin.isatty():
        return True

    # Check for common CI environment variables
    ci_vars = [
        "CI",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "JENKINS_HOME",
        "CIRCLECI",
        "TRAVIS",
        "BUILDKITE",
        "DRONE",
        "BITBUCKET_PIPELINE",
        "CODEBUILD_BUILD_ID",  # AWS CodeBuild
        "PYTEST_CURRENT_TEST",  # Running in pytest
    ]

    return any(os.environ.get(var) for var in ci_vars)


def is_valid_branch_name(branch_name: str, repo: Path | None = None) -> bool:
    """
    Check if a branch name is valid according to git rules.

    Uses git check-ref-format to validate branch name.
    Git branch name rules:
    - No ASCII control characters
    - No spaces
    - No ~, ^, :, ?, *, [
    - No backslashes
    - No consecutive dots (..)
    - No @{
    - Cannot start or end with /
    - Cannot end with .lock
    - Cannot be @ alone
    - No consecutive slashes (//)

    Args:
        branch_name: Branch name to validate
        repo: Repository path (optional)

    Returns:
        True if valid branch name, False otherwise
    """
    if not branch_name:
        return False

    # Use git check-ref-format for validation
    result = git_command(
        "check-ref-format",
        "--branch",
        branch_name,
        repo=repo,
        check=False,
        capture=True,
    )
    return result.returncode == 0


def get_branch_name_error(branch_name: str) -> str:
    """
    Get descriptive error message for invalid branch name.

    Args:
        branch_name: Invalid branch name

    Returns:
        Human-readable error message
    """
    # Common issues
    if not branch_name:
        return "Branch name cannot be empty"

    if branch_name == "@":
        return "Branch name cannot be '@' alone"

    if branch_name.endswith(".lock"):
        return "Branch name cannot end with '.lock'"

    if branch_name.startswith("/") or branch_name.endswith("/"):
        return "Branch name cannot start or end with '/'"

    if "//" in branch_name:
        return "Branch name cannot contain consecutive slashes '//'"

    if ".." in branch_name:
        return "Branch name cannot contain consecutive dots '..'"

    if "@{" in branch_name:
        return "Branch name cannot contain '@{'"

    # Check for invalid characters
    invalid_chars = set("~^:?*[\\")
    if any(c in branch_name for c in invalid_chars):
        found = [c for c in invalid_chars if c in branch_name]
        return f"Branch name contains invalid characters: {', '.join(repr(c) for c in found)}"

    # Check for control characters and spaces
    if any(ord(c) < 32 or c == " " for c in branch_name):
        return "Branch name cannot contain spaces or control characters"

    # Generic error
    return (
        f"'{branch_name}' is not a valid branch name. See 'git check-ref-format --help' for rules"
    )


def remove_worktree_safe(worktree_path: str | Path, repo: Path, force: bool = True) -> None:
    """
    Remove a git worktree with Windows-safe fallback.

    On Windows, 'git worktree remove' can fail with "Directory not empty" even with --force
    due to file locking or open file handles. This function provides a fallback that:
    1. Tries git worktree remove first
    2. If that fails on Windows, manually removes the directory
    3. Cleans up git's administrative data with 'git worktree prune'

    Args:
        worktree_path: Path to the worktree directory
        repo: Path to the main repository
        force: Use --force flag with git worktree remove

    Raises:
        GitError: If worktree removal fails on all platforms except Windows,
                  or if manual removal fails on Windows
    """
    worktree_path_obj = Path(worktree_path).resolve()
    worktree_str = str(worktree_path_obj)

    # Try git worktree remove first
    rm_args = ["worktree", "remove", worktree_str]
    if force:
        rm_args.append("--force")

    result = git_command(*rm_args, repo=repo, check=False, capture=True)

    if result.returncode == 0:
        # Success via git command
        return

    # Git command failed - check if it's Windows and the specific error
    is_windows = platform.system() == "Windows"
    is_directory_not_empty = "Directory not empty" in (result.stdout or "")

    if is_windows and is_directory_not_empty:
        # Windows-specific workaround: manually remove directory then prune
        try:
            if worktree_path_obj.exists():
                # Use shutil.rmtree with aggressive error handler for Windows
                def handle_remove_error(func: Any, path: str, exc_info: Any) -> None:
                    """
                    Aggressive error handler for Windows directory removal.

                    Handles:
                    - Readonly files
                    - Symlinks (common in node_modules/.bin)
                    - Permission errors
                    """
                    path_obj = Path(path)

                    # Try to remove readonly attribute
                    try:
                        os.chmod(path, 0o777)
                    except Exception:
                        pass  # Ignore if chmod fails

                    # If it's a symlink, try to unlink it directly
                    if path_obj.is_symlink():
                        try:
                            path_obj.unlink()
                            return
                        except Exception:
                            pass

                    # If it's a directory, try rmdir
                    if path_obj.is_dir():
                        try:
                            os.rmdir(path)
                            return
                        except Exception:
                            pass

                    # Try the original function again after chmod
                    try:
                        func(path)
                    except Exception:
                        # If all else fails, ignore the error
                        # The prune command will clean up git's references
                        pass

                shutil.rmtree(worktree_str, onerror=handle_remove_error)

            # Clean up git's administrative data
            git_command("worktree", "prune", repo=repo)

        except Exception as e:
            # If we get here, the directory might still be partially removed
            # Check if it's gone or nearly gone
            if not worktree_path_obj.exists():
                # Directory was removed, just ensure git cleanup
                git_command("worktree", "prune", repo=repo)
                return

            raise GitError(
                f"Failed to remove worktree directory on Windows: {worktree_str}\n"
                f"Error: {e}\n"
                f"Try closing any programs that might have files open in this directory.\n"
                f"If the issue persists, you may need to manually delete the directory:\n"
                f'  rmdir /s /q "{worktree_str}"\n'
                f"Then run: git worktree prune"
            ) from e
    else:
        # Non-Windows platform or different error - propagate the original error
        raise GitError(f"Command failed: {' '.join(rm_args)}\n{result.stdout}")
