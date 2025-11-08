"""Git operations for pull requests and merging."""

import subprocess
import tempfile
from pathlib import Path

from ..config import get_ai_tool_command
from ..console import get_console
from ..exceptions import GitError, RebaseError
from ..git_utils import git_command, has_command
from ..helpers import get_worktree_metadata, resolve_worktree_target

console = get_console()


def _generate_pr_description_with_ai(
    feature_branch: str, base_branch: str, cwd: Path
) -> tuple[str | None, str | None]:
    """
    Generate PR title and body using AI tool by analyzing commit history.

    Args:
        feature_branch: Feature branch name
        base_branch: Base branch name
        cwd: Working directory (worktree path)

    Returns:
        Tuple of (title, body) or (None, None) if AI tool not configured or fails
    """
    # Get AI tool command
    ai_command = get_ai_tool_command()

    # Check if AI tool is configured (not "no-op")
    if not ai_command or ai_command[0] == "echo":
        return None, None

    try:
        # Get commit log for the feature branch (commits not in base)
        log_result = git_command(
            "log",
            f"{base_branch}..{feature_branch}",
            "--pretty=format:Commit: %h%nAuthor: %an%nDate: %ad%nMessage: %s%n%b%n---",
            "--date=short",
            repo=cwd,
            capture=True,
        )

        commits_log = log_result.stdout.strip()

        if not commits_log:
            # No commits to analyze
            return None, None

        # Get diff stats
        diff_stats_result = git_command(
            "diff",
            "--stat",
            f"{base_branch}...{feature_branch}",
            repo=cwd,
            capture=True,
        )
        diff_stats = diff_stats_result.stdout.strip()

        # Create prompt for AI
        prompt = f"""Analyze the following git commits and generate a pull request title and description.

Branch: {feature_branch} -> {base_branch}

Commits:
{commits_log}

Diff Statistics:
{diff_stats}

Please provide:
1. A concise PR title (one line, following conventional commit format if applicable)
2. A detailed PR description with:
   - Summary of changes (2-3 sentences)
   - Test plan (bullet points)

Format your response EXACTLY as:
TITLE: <your title here>
BODY:
<your body here>
"""

        # Write prompt to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            prompt_file = Path(f.name)
            f.write(prompt)

        try:
            # Run AI tool with the prompt
            console.print("[yellow]Generating PR description with AI...[/yellow]")

            # Read prompt content from file
            # Note: AI tools like claude/happy accept prompt as positional argument, not via --prompt flag
            with open(prompt_file) as f:
                prompt_text = f.read()

            # Construct AI command with prompt as positional argument
            ai_cmd = ai_command + [prompt_text]

            result = subprocess.run(
                ai_cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=60,  # 60 second timeout
                check=False,
            )

            if result.returncode != 0:
                console.print(
                    f"[yellow]![/yellow] AI tool failed (exit code {result.returncode})\n"
                )
                return None, None

            # Parse output
            output = result.stdout.strip()

            # Extract TITLE and BODY
            title = None
            body = None

            if "TITLE:" in output:
                lines = output.split("\n")
                for i, line in enumerate(lines):
                    if line.startswith("TITLE:"):
                        title = line.replace("TITLE:", "").strip()
                    elif line.startswith("BODY:"):
                        # Everything after BODY: is the body
                        body = "\n".join(lines[i + 1 :]).strip()
                        break

            if title and body:
                console.print("[bold green]*[/bold green] AI generated PR description\n")
                console.print(f"[dim]Title:[/dim] {title}")
                console.print(f"[dim]Body preview:[/dim] {body[:100]}...\n")
                return title, body
            else:
                console.print("[yellow]![/yellow] Could not parse AI output\n")
                return None, None

        finally:
            # Clean up temporary file
            prompt_file.unlink(missing_ok=True)

    except subprocess.TimeoutExpired:
        console.print("[yellow]![/yellow] AI tool timed out\n")
        return None, None
    except Exception as e:
        console.print(f"[yellow]![/yellow] AI generation failed: {e}\n")
        return None, None


def create_pr_worktree(
    target: str | None = None,
    push: bool = True,
    title: str | None = None,
    body: str | None = None,
    draft: bool = False,
) -> None:
    """
    Create a GitHub Pull Request for the worktree without merging or cleaning up.

    Args:
        target: Branch name of worktree (optional, defaults to current directory)
        push: Push to remote before creating PR (default: True)
        title: PR title (optional, will use default from gh)
        body: PR body (optional, will use default from gh)
        draft: Create as draft PR

    Raises:
        GitError: If git operations fail
        RebaseError: If rebase fails
        WorktreeNotFoundError: If worktree not found
        InvalidBranchError: If branch is invalid
    """
    # Check if gh CLI is available
    if not has_command("gh"):
        raise GitError(
            "GitHub CLI (gh) is required to create pull requests.\n"
            "Install it from: https://cli.github.com/"
        )

    # Resolve worktree target to (path, branch, repo)
    cwd, feature_branch, worktree_repo = resolve_worktree_target(target)

    # Get metadata - base_path is the actual main repository
    base_branch, base_path = get_worktree_metadata(feature_branch, worktree_repo)
    repo = base_path

    console.print("\n[bold cyan]Creating Pull Request:[/bold cyan]")
    console.print(f"  Feature:     [green]{feature_branch}[/green]")
    console.print(f"  Base:        [green]{base_branch}[/green]")
    console.print(f"  Repo:        [blue]{repo}[/blue]\n")

    # Fetch updates from remote
    console.print("[yellow]Fetching updates from remote...[/yellow]")
    fetch_result = git_command("fetch", "--all", "--prune", repo=repo, check=False)

    # Check if origin remote exists and has the branch
    rebase_target = base_branch
    if fetch_result.returncode == 0:
        # Check if origin/base_branch exists
        check_result = git_command(
            "rev-parse", "--verify", f"origin/{base_branch}", repo=cwd, check=False, capture=True
        )
        if check_result.returncode == 0:
            rebase_target = f"origin/{base_branch}"

    # Rebase feature on base
    console.print(f"[yellow]Rebasing {feature_branch} onto {rebase_target}...[/yellow]")

    try:
        git_command("rebase", rebase_target, repo=cwd)
    except GitError:
        # Rebase failed - check if there are conflicts
        conflicts_result = git_command(
            "diff", "--name-only", "--diff-filter=U", repo=cwd, capture=True, check=False
        )
        conflicted_files = (
            conflicts_result.stdout.strip().splitlines() if conflicts_result.returncode == 0 else []
        )

        # Abort the rebase
        git_command("rebase", "--abort", repo=cwd, check=False)
        error_msg = f"Rebase failed. Please resolve conflicts manually:\n  cd {cwd}\n  git rebase {rebase_target}"
        if conflicted_files:
            error_msg += f"\n\nConflicted files ({len(conflicted_files)}):"
            for file in conflicted_files:
                error_msg += f"\n  • {file}"
        raise RebaseError(error_msg)

    console.print("[bold green]*[/bold green] Rebase successful\n")

    # Push to remote if requested
    if push:
        console.print(f"[yellow]Pushing {feature_branch} to origin...[/yellow]")
        try:
            # Push with -u to set upstream
            git_command("push", "-u", "origin", feature_branch, repo=cwd)
            console.print("[bold green]*[/bold green] Pushed to origin\n")
        except GitError as e:
            console.print(f"[yellow]![/yellow] Push failed: {e}\n")
            raise

    # Create pull request
    console.print("[yellow]Creating pull request...[/yellow]")

    pr_args = ["gh", "pr", "create", "--base", base_branch]

    # Determine title and body
    if title:
        # User provided title/body explicitly
        pr_args.extend(["--title", title])
        if body:
            pr_args.extend(["--body", body])
    else:
        # No title/body provided - try AI generation
        ai_title, ai_body = _generate_pr_description_with_ai(feature_branch, base_branch, cwd)

        if ai_title and ai_body:
            # AI generation succeeded
            pr_args.extend(["--title", ai_title])
            pr_args.extend(["--body", ai_body])
        else:
            # AI not configured or failed
            ai_command = get_ai_tool_command()
            if ai_command and ai_command[0] != "echo":
                # AI tool is configured but failed
                raise GitError(
                    "AI tool is configured but failed to generate PR description.\n"
                    "Please either:\n"
                    "  1. Provide --title and --body explicitly\n"
                    "  2. Fix your AI tool configuration\n"
                    "  3. Use 'cw config use-preset no-op' to disable AI generation"
                )
            else:
                # No AI tool configured - use --fill as fallback
                pr_args.append("--fill")

    if draft:
        pr_args.append("--draft")

    try:
        # Run gh pr create in the worktree directory
        result = subprocess.run(
            pr_args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=True,
        )
        pr_url = result.stdout.strip()
        console.print("[bold green]*[/bold green] Pull request created!\n")
        console.print(f"[bold]PR URL:[/bold] {pr_url}\n")
        console.print(
            "[dim]Note: Worktree is still active. Use 'cw delete' to remove it after PR is merged.[/dim]\n"
        )
    except subprocess.CalledProcessError as e:
        error_msg = f"Failed to create pull request: {e.stderr}"
        raise GitError(error_msg)


def merge_worktree(
    target: str | None = None,
    push: bool = False,
    interactive: bool = False,
    dry_run: bool = False,
) -> None:
    """
    Complete work on a worktree: rebase, merge to base branch, and cleanup.

    This is the new name for the finish command. It performs a direct merge
    to the base branch without creating a pull request.

    Args:
        target: Branch name of worktree to finish (optional, defaults to current directory)
        push: Push base branch to origin after merge
        interactive: Pause for confirmation before each step
        dry_run: Preview merge without executing

    Raises:
        GitError: If git operations fail
        RebaseError: If rebase fails
        MergeError: If merge fails
        WorktreeNotFoundError: If worktree not found
        InvalidBranchError: If branch is invalid
    """
    # Import here to avoid circular dependency
    from .worktree_ops import finish_worktree

    # This is essentially the same as the old finish_worktree function
    # Just call finish_worktree with the same arguments
    finish_worktree(target=target, push=push, interactive=interactive, dry_run=dry_run)


def _is_branch_merged_via_gh(branch_name: str, base_branch: str, repo: Path) -> bool | None:
    """
    Check if a branch is merged via GitHub CLI (detects squash/rebase merges).

    Args:
        branch_name: Feature branch name
        base_branch: Base branch name
        repo: Repository root path

    Returns:
        True if merged via GitHub PR, False if not merged, None if gh CLI unavailable
    """
    import subprocess

    # Check if gh CLI is available
    if not has_command("gh"):
        return None

    try:
        # Check if there's a PR for this branch and if it's merged
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--head",
                branch_name,
                "--base",
                base_branch,
                "--state",
                "merged",
                "--json",
                "number",
                "--jq",
                "length",
            ],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )

        # If there are merged PRs for this branch, it's merged
        if result.returncode == 0 and result.stdout.strip():
            count = int(result.stdout.strip())
            return count > 0

        return False

    except (ValueError, subprocess.SubprocessError):
        # If gh command fails, return None (unavailable)
        return None
