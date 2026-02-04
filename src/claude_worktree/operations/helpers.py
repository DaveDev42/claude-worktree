"""Helper functions shared across operations modules."""

from pathlib import Path

from ..console import get_console
from ..constants import CONFIG_KEY_BASE_BRANCH, CONFIG_KEY_BASE_PATH
from ..exceptions import GitError, InvalidBranchError, WorktreeNotFoundError
from ..git_utils import (
    find_worktree_by_intended_branch,
    find_worktree_by_name,
    get_config,
    get_current_branch,
    get_main_repo_root,
    get_repo_root,
    is_non_interactive,
    parse_worktrees,
)


def _prompt_worktree_disambiguation(
    target: str,
    branch_path: Path,
    worktree_path: Path,
    action: str | None = None,
) -> str:
    """Prompt user to choose between branch and worktree name match.

    Args:
        target: The target string that matched both
        branch_path: Path to worktree found via branch name lookup
        worktree_path: Path to worktree found via directory name lookup
        action: Optional action verb for the prompt (e.g., "delete", "resume")

    Returns:
        "branch" or "worktree" depending on user choice
    """
    console = get_console()
    console.print(f"\n[yellow]Multiple matches found for '{target}':[/yellow]")
    console.print(f"  [1] Branch '{target}' → {branch_path}")
    console.print(f"  [2] Worktree '{worktree_path.name}' → {worktree_path}")
    console.print()

    prompt = f"Which one do you want to {action}? [1/2]: " if action else "Which one? [1/2]: "
    while True:
        choice = console.input(prompt).strip()
        if choice == "1":
            return "branch"
        elif choice == "2":
            return "worktree"
        console.print("[red]Please enter 1 or 2[/red]")


def _get_branch_for_worktree(repo: Path, worktree_path: Path) -> str | None:
    """Get the intended branch name for a worktree path.

    Args:
        repo: Repository path
        worktree_path: Path to the worktree

    Returns:
        Branch name (without refs/heads/ prefix) or None if detached
    """
    for branch, path in parse_worktrees(repo):
        try:
            if path.samefile(worktree_path):
                if branch.startswith("refs/heads/"):
                    return branch[11:]
                return branch if branch != "(detached)" else None
        except (OSError, ValueError):
            if path.resolve() == worktree_path.resolve():
                if branch.startswith("refs/heads/"):
                    return branch[11:]
                return branch if branch != "(detached)" else None
    return None


def _resolve_dual_match(
    target: str,
    branch_match: Path | None,
    worktree_match: Path | None,
    main_repo: Path,
) -> tuple[Path, str]:
    """Resolve dual match with disambiguation if needed.

    Args:
        target: Original target string
        branch_match: Path found via branch lookup (or None)
        worktree_match: Path found via worktree name lookup (or None)
        main_repo: Main repository path

    Returns:
        tuple[Path, str]: (worktree_path, branch_name)

    Raises:
        WorktreeNotFoundError: If no match found or ambiguous in non-interactive mode
    """
    if branch_match and worktree_match:
        try:
            same_worktree = branch_match.samefile(worktree_match)
        except (OSError, ValueError):
            same_worktree = branch_match.resolve() == worktree_match.resolve()

        if same_worktree:
            return branch_match, target
        else:
            if is_non_interactive():
                raise WorktreeNotFoundError(
                    f"Ambiguous target '{target}' matches both a branch and a worktree name.\n"
                    f"  Branch '{target}' → {branch_match}\n"
                    f"  Worktree '{worktree_match.name}' → {worktree_match}\n"
                    "Use --branch (-b) or --worktree (-w) flag to specify which one."
                )
            choice = _prompt_worktree_disambiguation(target, branch_match, worktree_match)
            if choice == "branch":
                return branch_match, target
            else:
                branch_name = _get_branch_for_worktree(main_repo, worktree_match)
                return worktree_match, branch_name or target
    elif branch_match:
        return branch_match, target
    elif worktree_match:
        branch_name = _get_branch_for_worktree(main_repo, worktree_match)
        return worktree_match, branch_name or target
    else:
        raise WorktreeNotFoundError(
            f"No worktree found for '{target}'. "
            "Try: full path, branch name (--branch), or worktree name (--worktree)."
        )


def resolve_worktree_target(
    target: str | None,
    lookup_mode: str | None = None,
) -> tuple[Path, str, Path]:
    """
    Resolve worktree target to (worktree_path, branch_name, worktree_repo).

    Supports:
    - Branch name lookup (via metadata/intended branch)
    - Worktree directory name lookup
    - Disambiguation when both match different worktrees

    Args:
        target: Branch name, worktree directory name, or None (uses current directory)
        lookup_mode: "branch", "worktree", or None (try both)

    Returns:
        tuple[Path, str, Path]: (worktree_path, branch_name, worktree_repo)
            - worktree_path: Path to the worktree directory
            - branch_name: Simple branch name (without refs/heads/ prefix)
            - worktree_repo: Git repository root of the worktree

    Raises:
        WorktreeNotFoundError: If worktree not found for specified target
        InvalidBranchError: If current branch cannot be determined
        GitError: If not in a git repository
    """
    if target is None:
        # No target - use current directory (existing behavior)
        worktree_path = Path.cwd()
        try:
            branch_name = get_current_branch(worktree_path)
        except InvalidBranchError:
            raise InvalidBranchError("Cannot determine current branch")
        worktree_repo = get_repo_root()
        return worktree_path, branch_name, worktree_repo

    # Get main repo for lookups
    main_repo = get_main_repo_root()

    # Dual lookup based on mode
    branch_match: Path | None = None
    worktree_match: Path | None = None

    if lookup_mode == "branch":
        branch_match = find_worktree_by_intended_branch(main_repo, target)
        if not branch_match:
            raise WorktreeNotFoundError(f"No worktree found for branch '{target}'")
    elif lookup_mode == "worktree":
        worktree_match = find_worktree_by_name(main_repo, target)
        if not worktree_match:
            raise WorktreeNotFoundError(f"No worktree found with name '{target}'")
    else:
        # Try both
        branch_match = find_worktree_by_intended_branch(main_repo, target)
        worktree_match = find_worktree_by_name(main_repo, target)

    # Resolve with disambiguation if needed
    worktree_path, branch_name = _resolve_dual_match(
        target, branch_match, worktree_match, main_repo
    )

    worktree_repo = get_repo_root(worktree_path)
    return worktree_path, branch_name, worktree_repo


def get_worktree_metadata(branch: str, repo: Path) -> tuple[str, Path]:
    """
    Get worktree metadata (base branch and base repository path).

    This helper function retrieves the stored metadata for a worktree,
    including the base branch it was created from and the path to the
    base repository.

    If metadata is missing (e.g., branch created manually without 'cw new'),
    it will attempt to infer:
    - base_path: Main repository path from git worktree list
    - base_branch: Common default branches (main, master, develop) or first worktree branch

    Args:
        branch: Feature branch name
        repo: Worktree repository path

    Returns:
        tuple[str, Path]: (base_branch_name, base_repo_path)

    Raises:
        GitError: If metadata cannot be retrieved or inferred

    Example:
        >>> base_branch, base_path = get_worktree_metadata("fix-auth", Path("/path/to/worktree"))
        >>> print(f"Created from: {base_branch}")
        Created from: main
    """
    from ..console import get_console
    from ..git_utils import branch_exists, parse_worktrees

    base_branch = get_config(CONFIG_KEY_BASE_BRANCH.format(branch), repo)
    base_path_str = get_config(CONFIG_KEY_BASE_PATH.format(branch), repo)

    # If metadata exists, use it
    if base_branch and base_path_str:
        base_path = Path(base_path_str)
        return base_branch, base_path

    # Metadata missing - try to infer
    console = get_console()
    console.print(f"\n[yellow]! Metadata missing for branch '{branch}'[/yellow]")
    console.print("[dim]Attempting to infer metadata automatically...[/dim]\n")

    # Step 1: Infer base_path (main repository)
    # Find the main repository by getting the first worktree (which is always the main repo)
    inferred_base_path: Path | None = None
    try:
        worktrees = parse_worktrees(repo)
        if worktrees:
            # The first worktree is always the main repository
            inferred_base_path = worktrees[0][1]
    except Exception:
        pass

    if not inferred_base_path:
        raise GitError(
            f"Cannot infer base repository path for branch '{branch}'. "
            f"Please use 'cw new' to create worktrees."
        )

    # Step 2: Infer base_branch
    # Try common default branch names in order: main, master, develop
    inferred_base_branch: str | None = None
    for candidate in ["main", "master", "develop"]:
        if branch_exists(candidate, inferred_base_path):
            inferred_base_branch = candidate
            break

    # If no common branch found, use the branch of the first worktree (main repo)
    if not inferred_base_branch:
        if worktrees and worktrees[0][0] != "(detached)":
            first_branch = worktrees[0][0]
            # Normalize branch name (remove refs/heads/ prefix)
            inferred_base_branch = (
                first_branch[11:] if first_branch.startswith("refs/heads/") else first_branch
            )

    if not inferred_base_branch:
        raise GitError(
            f"Cannot infer base branch for '{branch}'. "
            f"Please specify manually or use 'cw new' to create worktrees."
        )

    console.print(f"  [dim]Inferred base branch: [cyan]{inferred_base_branch}[/cyan][/dim]")
    console.print(f"  [dim]Inferred base path: [blue]{inferred_base_path}[/blue][/dim]")
    console.print("\n[dim]Tip: Use 'cw new' to create worktrees with proper metadata.[/dim]\n")

    return inferred_base_branch, inferred_base_path
