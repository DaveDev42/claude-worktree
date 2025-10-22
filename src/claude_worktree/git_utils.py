"""Git operations wrapper utilities."""

import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from .exceptions import GitError, InvalidBranchError


def run_command(
    cmd: List[str],
    cwd: Optional[Path] = None,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess:
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
    kwargs = {}
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
    repo: Optional[Path] = None,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess:
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


def get_repo_root(path: Optional[Path] = None) -> Path:
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


def get_current_branch(repo: Optional[Path] = None) -> str:
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


def branch_exists(branch: str, repo: Optional[Path] = None) -> bool:
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


def get_config(key: str, repo: Optional[Path] = None) -> Optional[str]:
    """
    Get a git config value.

    Args:
        key: Config key
        repo: Repository path

    Returns:
        Config value or None if not found
    """
    result = git_command(
        "config", "--local", "--get", key, repo=repo, check=False, capture=True
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def set_config(key: str, value: str, repo: Optional[Path] = None) -> None:
    """
    Set a git config value.

    Args:
        key: Config key
        value: Config value
        repo: Repository path
    """
    git_command("config", "--local", key, value, repo=repo)


def unset_config(key: str, repo: Optional[Path] = None) -> None:
    """
    Unset a git config value.

    Args:
        key: Config key
        repo: Repository path
    """
    git_command("config", "--local", "--unset-all", key, repo=repo, check=False)


def parse_worktrees(repo: Path) -> List[Tuple[str, str]]:
    """
    Parse git worktree list output.

    Args:
        repo: Repository path

    Returns:
        List of (branch_or_detached, path) tuples
    """
    result = git_command("worktree", "list", "--porcelain", repo=repo, capture=True)
    lines = result.stdout.strip().splitlines()

    items: List[Tuple[str, str]] = []
    cur_path: Optional[str] = None
    cur_branch: Optional[str] = None

    for line in lines:
        if line.startswith("worktree "):
            cur_path = line.split(" ", 1)[1]
        elif line.startswith("branch "):
            cur_branch = line.split(" ", 1)[1]
        elif line.strip() == "" and cur_path:
            items.append((cur_branch or "(detached)", cur_path))
            cur_path, cur_branch = None, None

    if cur_path:
        items.append((cur_branch or "(detached)", cur_path))

    return items


def find_worktree_by_branch(repo: Path, branch: str) -> Optional[str]:
    """
    Find worktree path by branch name.

    Args:
        repo: Repository path
        branch: Branch name

    Returns:
        Worktree path or None if not found
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
