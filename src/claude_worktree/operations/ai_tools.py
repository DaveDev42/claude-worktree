"""AI tool integration operations for claude-worktree."""

import os
import shlex
import subprocess
import sys
from pathlib import Path

from ..config import get_ai_tool_command, get_ai_tool_merge_command, get_ai_tool_resume_command
from ..console import get_console
from ..exceptions import GitError, WorktreeNotFoundError
from ..git_utils import find_worktree_by_branch, get_current_branch, get_repo_root, has_command
from ..helpers import resolve_worktree_target

console = get_console()


def _run_command_in_shell(
    cmd: str,
    cwd: str | Path,
    background: bool = False,
    check: bool = False,
) -> subprocess.CompletedProcess | subprocess.Popen:
    """
    Run a command in the appropriate shell for the current platform.

    On Windows: Uses shell=True to avoid WSL bash issues
    On Unix/macOS: Uses bash -lc for login shell behavior

    Args:
        cmd: Command string to execute
        cwd: Working directory
        background: If True, run in background (Popen), else run synchronously (run)
        check: If True, raise exception on non-zero exit (only for run)

    Returns:
        CompletedProcess if background=False, Popen if background=True
    """
    if sys.platform == "win32":
        # On Windows, use shell=True to let Windows handle shell selection
        # This avoids the WSL bash issue where subprocess resolves to WSL's bash
        # instead of MSYS2/Git Bash, causing node.exe to not be found
        if background:
            return subprocess.Popen(cmd, cwd=str(cwd), shell=True)
        else:
            return subprocess.run(cmd, cwd=str(cwd), shell=True, check=check)
    else:
        # On Unix/macOS, use bash -lc for login shell behavior
        if background:
            return subprocess.Popen(["bash", "-lc", cmd], cwd=str(cwd))
        else:
            return subprocess.run(["bash", "-lc", cmd], cwd=str(cwd), check=check)


def launch_ai_tool(
    path: Path,
    bg: bool = False,
    iterm: bool = False,
    iterm_tab: bool = False,
    tmux_session: str | None = None,
    resume: bool = False,
    prompt: str | None = None,
) -> None:
    """
    Launch AI coding assistant in the specified directory.

    Args:
        path: Directory to launch AI tool in
        bg: Launch in background
        iterm: Launch in new iTerm window (macOS only)
        iterm_tab: Launch in new iTerm tab (macOS only)
        tmux_session: Launch in new tmux session
        resume: Use resume command (adds --resume flag)
        prompt: Initial prompt to send to AI tool (for automated tasks)
    """
    # Get configured AI tool command
    # - If prompt is provided (AI merge): use merge command with preset-specific flags
    # - If resume flag: use resume command
    # - Otherwise: use regular command
    if prompt:
        ai_cmd_parts = get_ai_tool_merge_command(prompt)
    elif resume:
        ai_cmd_parts = get_ai_tool_resume_command()
    else:
        ai_cmd_parts = get_ai_tool_command()

    # Skip if no AI tool configured (empty array means no-op)
    if not ai_cmd_parts:
        return

    ai_tool_name = ai_cmd_parts[0]

    # Check if the command exists
    if not has_command(ai_tool_name):
        console.print(
            f"[yellow]![/yellow] {ai_tool_name} not detected. "
            f"Install it or update your config with 'cw config set ai-tool <tool>'.\n"
        )
        return

    # Build command - only add --dangerously-skip-permissions if not already present
    # (for backward compatibility with non-merge commands)
    cmd_parts = ai_cmd_parts.copy()
    if (
        not prompt
        and ai_tool_name == "claude"
        and "--dangerously-skip-permissions" not in cmd_parts
    ):
        cmd_parts.append("--dangerously-skip-permissions")

    cmd = " ".join(shlex.quote(part) for part in cmd_parts)

    if tmux_session:
        if not has_command("tmux"):
            raise GitError("tmux not installed. Remove --tmux option or install tmux.")
        subprocess.run(
            ["tmux", "new-session", "-ds", tmux_session, "bash", "-lc", cmd],
            cwd=str(path),
        )
        console.print(
            f"[bold green]*[/bold green] {ai_tool_name} running in tmux session '{tmux_session}'\n"
        )
        return

    if iterm_tab:
        if sys.platform != "darwin":
            raise GitError("--iterm-tab option only works on macOS")
        script = f"""
        osascript <<'APPLESCRIPT'
        tell application "iTerm"
          activate
          tell current window
            create tab with default profile
            tell current session
              write text "cd {shlex.quote(str(path))} && {cmd}"
            end tell
          end tell
        end tell
APPLESCRIPT
        """
        subprocess.run(["bash", "-lc", script], check=True)
        console.print(f"[bold green]*[/bold green] {ai_tool_name} running in new iTerm tab\n")
        return

    if iterm:
        if sys.platform != "darwin":
            raise GitError("--iterm option only works on macOS")
        script = f"""
        osascript <<'APPLESCRIPT'
        tell application "iTerm"
          activate
          set newWindow to (create window with default profile)
          tell current session of newWindow
            write text "cd {shlex.quote(str(path))} && {cmd}"
          end tell
        end tell
APPLESCRIPT
        """
        subprocess.run(["bash", "-lc", script], check=True)
        console.print(f"[bold green]*[/bold green] {ai_tool_name} running in new iTerm window\n")
        return

    if bg:
        _run_command_in_shell(cmd, path, background=True)
        console.print(f"[bold green]*[/bold green] {ai_tool_name} running in background\n")
    else:
        console.print(f"[cyan]Starting {ai_tool_name} (Ctrl+C to exit)...[/cyan]\n")
        _run_command_in_shell(cmd, path, background=False, check=False)


def resume_worktree(
    worktree: str | None = None,
    bg: bool = False,
    iterm: bool = False,
    iterm_tab: bool = False,
    tmux_session: str | None = None,
) -> None:
    """
    Resume AI work in a worktree with context restoration.

    Args:
        worktree: Branch name of worktree to resume (optional, defaults to current directory)
        bg: Launch AI tool in background
        iterm: Launch AI tool in new iTerm window (macOS only)
        iterm_tab: Launch AI tool in new iTerm tab (macOS only)
        tmux_session: Launch AI tool in new tmux session

    Raises:
        WorktreeNotFoundError: If worktree not found
        GitError: If git operations fail
    """
    from .. import session_manager

    # Resolve worktree target to (path, branch, repo)
    worktree_path, branch_name, _ = resolve_worktree_target(worktree)

    # Change directory if worktree was specified
    if worktree:
        os.chdir(worktree_path)
        console.print(f"[dim]Switched to worktree: {worktree_path}[/dim]\n")

    # Check for existing session
    has_session = session_manager.session_exists(branch_name)
    if has_session:
        console.print(f"[green]*[/green] Found session for branch: [bold]{branch_name}[/bold]")

        # Load session metadata
        metadata = session_manager.load_session_metadata(branch_name)
        if metadata:
            console.print(f"[dim]  AI tool: {metadata.get('ai_tool', 'unknown')}[/dim]")
            console.print(f"[dim]  Last updated: {metadata.get('updated_at', 'unknown')}[/dim]")

        # Load context if available
        context = session_manager.load_context(branch_name)
        if context:
            console.print("\n[cyan]Previous context:[/cyan]")
            console.print(f"[dim]{context}[/dim]")

        console.print()
    else:
        console.print(
            f"[yellow]ℹ[/yellow] No previous session found for branch: [bold]{branch_name}[/bold]"
        )
        console.print("[dim]Starting fresh session...[/dim]\n")

    # Save session metadata and launch AI tool (if configured)
    # Use resume flag only if session history exists
    ai_cmd = get_ai_tool_resume_command() if has_session else get_ai_tool_command()
    if ai_cmd:
        ai_tool_name = ai_cmd[0]
        session_manager.save_session_metadata(branch_name, ai_tool_name, str(worktree_path))
        if has_session:
            console.print(f"[cyan]Resuming {ai_tool_name} in:[/cyan] {worktree_path}\n")
        else:
            console.print(f"[cyan]Starting {ai_tool_name} in:[/cyan] {worktree_path}\n")
        launch_ai_tool(
            worktree_path,
            bg=bg,
            iterm=iterm,
            iterm_tab=iterm_tab,
            tmux_session=tmux_session,
            resume=has_session,  # Only use resume if session exists
        )


def shell_worktree(
    worktree: str | None = None,
    command: list[str] | None = None,
) -> None:
    """
    Open an interactive shell or execute a command in a worktree.

    Args:
        worktree: Branch name of worktree to shell into (optional, uses current dir)
        command: Command to execute (optional, opens interactive shell if None)

    Raises:
        WorktreeNotFoundError: If worktree doesn't exist
        GitError: If git operations fail
    """
    repo = get_repo_root()

    # Determine target worktree path
    if worktree:
        # Find worktree by branch name
        worktree_path = find_worktree_by_branch(repo, worktree)
        if not worktree_path:
            worktree_path = find_worktree_by_branch(repo, f"refs/heads/{worktree}")

        if not worktree_path:
            raise WorktreeNotFoundError(f"No worktree found for branch '{worktree}'")

        target_path = Path(worktree_path)
    else:
        # Use current directory
        target_path = Path.cwd()

        # Verify we're in a worktree
        try:
            current_branch = get_current_branch(target_path)
            if not current_branch:
                raise WorktreeNotFoundError("Not in a git worktree. Please specify a branch name.")
        except GitError:
            raise WorktreeNotFoundError("Not in a git repository or worktree.")

    # Verify target path exists
    if not target_path.exists():
        raise WorktreeNotFoundError(f"Worktree directory does not exist: {target_path}")

    # Execute command or open interactive shell
    if command:
        # Execute the provided command in the worktree
        console.print(f"[cyan]Executing in {target_path}:[/cyan] {' '.join(command)}\n")
        try:
            result = subprocess.run(
                command,
                cwd=target_path,
                check=False,  # Don't raise exception, let command exit code pass through
            )
            sys.exit(result.returncode)
        except Exception as e:
            console.print(f"[bold red]Error executing command:[/bold red] {e}")
            sys.exit(1)
    else:
        # Open interactive shell
        branch_name = worktree if worktree else get_current_branch(target_path)
        console.print(
            f"[bold cyan]Opening shell in worktree:[/bold cyan] {branch_name}\n"
            f"[dim]Path: {target_path}[/dim]\n"
            f"[dim]Type 'exit' to return[/dim]\n"
        )

        # Determine shell to use
        shell = os.environ.get("SHELL", "/bin/bash")

        try:
            subprocess.run([shell], cwd=target_path, check=False)
        except Exception as e:
            console.print(f"[bold red]Error opening shell:[/bold red] {e}")
            sys.exit(1)
