"""AI tool integration operations for claude-worktree."""

import os
import shlex
import subprocess
import sys
import warnings
from pathlib import Path

from ..config import (
    get_ai_tool_command,
    get_ai_tool_merge_command,
    get_ai_tool_resume_command,
    load_config,
    parse_term_option,
)
from ..console import get_console
from ..constants import CONFIG_KEY_BASE_BRANCH, MAX_SESSION_NAME_LENGTH, LaunchMethod
from ..exceptions import GitError, WorktreeNotFoundError
from ..git_utils import (
    find_worktree_by_branch,
    get_config,
    get_current_branch,
    get_repo_root,
    has_command,
)
from ..hooks import run_hooks
from .helpers import resolve_worktree_target

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


def _generate_session_name(path: Path, branch_name: str | None = None) -> str:
    """Generate session name from path with length limit.

    Uses the configured session prefix (default: "cw") combined with directory name.

    Limits:
    - tmux: 255 chars (official limit)
    - Zellij: ~40-60 chars (Unix socket path must be < 108 bytes)
    - WezTerm: No limit

    We use 50 chars as a safe default for Zellij compatibility.

    Args:
        path: Worktree path
        branch_name: Optional branch name (not used currently, reserved for future)

    Returns:
        Generated session name, truncated if necessary
    """
    config = load_config()
    prefix = config.get("launch", {}).get("session_prefix", "cw")
    name = f"{prefix}-{path.name}"

    if len(name) > MAX_SESSION_NAME_LENGTH:
        name = name[:MAX_SESSION_NAME_LENGTH]
    return name


# =============================================================================
# iTerm Launchers (macOS only)
# =============================================================================


def _launch_iterm_window(path: Path, command: str, ai_tool_name: str) -> None:
    """Launch AI tool in new iTerm window."""
    if sys.platform != "darwin":
        raise GitError("--term iterm-window only works on macOS")

    script = f"""
    osascript <<'APPLESCRIPT'
    tell application "iTerm"
      activate
      set newWindow to (create window with default profile)
      tell current session of newWindow
        write text "cd {shlex.quote(str(path))} && {command}"
      end tell
    end tell
APPLESCRIPT
    """
    subprocess.run(["bash", "-lc", script], check=True)
    console.print(f"[bold green]*[/bold green] {ai_tool_name} running in new iTerm window\n")


def _launch_iterm_tab(path: Path, command: str, ai_tool_name: str) -> None:
    """Launch AI tool in new iTerm tab."""
    if sys.platform != "darwin":
        raise GitError("--term iterm-tab only works on macOS")

    script = f"""
    osascript <<'APPLESCRIPT'
    tell application "iTerm"
      activate
      tell current window
        create tab with default profile
        tell current session
          write text "cd {shlex.quote(str(path))} && {command}"
        end tell
      end tell
    end tell
APPLESCRIPT
    """
    subprocess.run(["bash", "-lc", script], check=True)
    console.print(f"[bold green]*[/bold green] {ai_tool_name} running in new iTerm tab\n")


def _launch_iterm_pane(path: Path, command: str, ai_tool_name: str, horizontal: bool = True) -> None:
    """Launch AI tool in iTerm split pane."""
    if sys.platform != "darwin":
        raise GitError("--term iterm-pane-* only works on macOS")

    direction = "horizontally" if horizontal else "vertically"
    script = f"""
    osascript <<'APPLESCRIPT'
    tell application "iTerm"
      activate
      tell current session of current window
        split {direction} with default profile
      end tell
      tell last session of current tab of current window
        write text "cd {shlex.quote(str(path))} && {command}"
      end tell
    end tell
APPLESCRIPT
    """
    subprocess.run(["bash", "-lc", script], check=True)
    pane_type = "horizontal" if horizontal else "vertical"
    console.print(f"[bold green]*[/bold green] {ai_tool_name} running in iTerm {pane_type} pane\n")


# =============================================================================
# tmux Launchers
# =============================================================================


def _launch_tmux_session(
    path: Path, command: str, ai_tool_name: str, session_name: str | None = None
) -> None:
    """Launch AI tool in new tmux session."""
    if not has_command("tmux"):
        raise GitError("tmux not installed. Install from https://tmux.github.io/")

    if session_name is None:
        session_name = _generate_session_name(path)

    # Create new session with working directory set
    # -d: detached, -s: session name, -c: start directory
    subprocess.run(
        ["tmux", "new-session", "-d", "-s", session_name, "-c", str(path)],
        check=True,
    )
    # Send the AI command to the session
    subprocess.run(
        ["tmux", "send-keys", "-t", session_name, command, "Enter"],
        check=True,
    )
    # Attach to the session
    subprocess.run(["tmux", "attach-session", "-t", session_name], check=True)
    console.print(f"[bold green]*[/bold green] {ai_tool_name} ran in tmux session '{session_name}'\n")


def _launch_tmux_window(path: Path, command: str, ai_tool_name: str) -> None:
    """Launch AI tool in new tmux window (within current session)."""
    if not os.environ.get("TMUX"):
        raise GitError("--term tmux-window requires running inside a tmux session")

    # -c: start directory for new window
    subprocess.run(
        ["tmux", "new-window", "-c", str(path), "bash", "-lc", command],
        check=True,
    )
    console.print(f"[bold green]*[/bold green] {ai_tool_name} running in new tmux window\n")


def _launch_tmux_pane(
    path: Path, command: str, ai_tool_name: str, horizontal: bool = True
) -> None:
    """Launch AI tool in tmux split pane."""
    if not os.environ.get("TMUX"):
        raise GitError("--term tmux-pane-* requires running inside a tmux session")

    # -h: horizontal split, -v: vertical split, -c: start directory
    split_flag = "-h" if horizontal else "-v"
    subprocess.run(
        ["tmux", "split-window", split_flag, "-c", str(path), "bash", "-lc", command],
        check=True,
    )
    pane_type = "horizontal" if horizontal else "vertical"
    console.print(f"[bold green]*[/bold green] {ai_tool_name} running in tmux {pane_type} pane\n")


# =============================================================================
# Zellij Launchers
# =============================================================================


def _launch_zellij_session(
    path: Path, command: str, ai_tool_name: str, session_name: str | None = None
) -> None:
    """Launch AI tool in new Zellij session."""
    if not has_command("zellij"):
        raise GitError("zellij not installed. Install from https://zellij.dev/")

    if session_name is None:
        session_name = _generate_session_name(path)

    # -s: session name, run command directly
    subprocess.run(
        ["zellij", "-s", session_name, "--", "bash", "-lc", command],
        cwd=path,
        check=True,
    )
    console.print(f"[bold green]*[/bold green] {ai_tool_name} ran in Zellij session '{session_name}'\n")


def _launch_zellij_tab(path: Path, command: str, ai_tool_name: str) -> None:
    """Launch AI tool in new Zellij tab."""
    if not os.environ.get("ZELLIJ"):
        raise GitError("--term zellij-tab requires running inside a Zellij session")

    subprocess.run(
        ["zellij", "action", "new-tab", "--cwd", str(path), "--", "bash", "-lc", command],
        check=True,
    )
    console.print(f"[bold green]*[/bold green] {ai_tool_name} running in new Zellij tab\n")


def _launch_zellij_pane(
    path: Path, command: str, ai_tool_name: str, horizontal: bool = True
) -> None:
    """Launch AI tool in Zellij split pane."""
    if not os.environ.get("ZELLIJ"):
        raise GitError("--term zellij-pane-* requires running inside a Zellij session")

    # right = horizontal split, down = vertical split
    direction = "right" if horizontal else "down"
    subprocess.run(
        ["zellij", "action", "new-pane", "-d", direction, "--cwd", str(path),
         "--", "bash", "-lc", command],
        check=True,
    )
    pane_type = "horizontal" if horizontal else "vertical"
    console.print(f"[bold green]*[/bold green] {ai_tool_name} running in Zellij {pane_type} pane\n")


# =============================================================================
# WezTerm Launchers
# =============================================================================


def _launch_wezterm_window(path: Path, command: str, ai_tool_name: str) -> None:
    """Launch AI tool in new WezTerm window."""
    if not has_command("wezterm"):
        raise GitError("wezterm not installed. Install from https://wezterm.org/")

    subprocess.run(
        ["wezterm", "cli", "spawn", "--new-window", "--cwd", str(path),
         "--", "bash", "-lc", command],
        check=True,
    )
    console.print(f"[bold green]*[/bold green] {ai_tool_name} running in new WezTerm window\n")


def _launch_wezterm_tab(path: Path, command: str, ai_tool_name: str) -> None:
    """Launch AI tool in new WezTerm tab."""
    if not has_command("wezterm"):
        raise GitError("wezterm not installed. Install from https://wezterm.org/")

    subprocess.run(
        ["wezterm", "cli", "spawn", "--cwd", str(path), "--", "bash", "-lc", command],
        check=True,
    )
    console.print(f"[bold green]*[/bold green] {ai_tool_name} running in new WezTerm tab\n")


def _launch_wezterm_pane(
    path: Path, command: str, ai_tool_name: str, horizontal: bool = True
) -> None:
    """Launch AI tool in WezTerm split pane."""
    if not has_command("wezterm"):
        raise GitError("wezterm not installed. Install from https://wezterm.org/")

    # --horizontal: split horizontally (side by side)
    # --bottom: split vertically (top/bottom)
    split_flag = "--horizontal" if horizontal else "--bottom"
    subprocess.run(
        ["wezterm", "cli", "split-pane", split_flag, "--cwd", str(path),
         "--", "bash", "-lc", command],
        check=True,
    )
    pane_type = "horizontal" if horizontal else "vertical"
    console.print(f"[bold green]*[/bold green] {ai_tool_name} running in WezTerm {pane_type} pane\n")


# =============================================================================
# Main Launch Function
# =============================================================================


def launch_ai_tool(
    path: Path,
    term: str | None = None,
    resume: bool = False,
    prompt: str | None = None,
    # Deprecated parameters (for backward compatibility)
    bg: bool = False,
    iterm: bool = False,
    iterm_tab: bool = False,
    tmux_session: str | None = None,
) -> None:
    """
    Launch AI coding assistant in the specified directory.

    Args:
        path: Directory to launch AI tool in
        term: Terminal launch method (e.g., "i-t", "t:mysession", "z-p-h")
        resume: Use resume command (adds --resume flag)
        prompt: Initial prompt to send to AI tool (for automated tasks)
        bg: [DEPRECATED] Use term="bg" instead
        iterm: [DEPRECATED] Use term="iterm-window" or term="i-w" instead
        iterm_tab: [DEPRECATED] Use term="iterm-tab" or term="i-t" instead
        tmux_session: [DEPRECATED] Use term="tmux" or term="t:session_name" instead
    """
    # Handle deprecated parameters
    if bg:
        warnings.warn("--bg is deprecated. Use --term bg instead", DeprecationWarning, stacklevel=2)
        term = "bg"
    elif iterm:
        warnings.warn(
            "--iterm is deprecated. Use --term i-w instead", DeprecationWarning, stacklevel=2
        )
        term = "iterm-window"
    elif iterm_tab:
        warnings.warn(
            "--iterm-tab is deprecated. Use --term i-t instead", DeprecationWarning, stacklevel=2
        )
        term = "iterm-tab"
    elif tmux_session:
        warnings.warn(
            "--tmux is deprecated. Use --term t or --term t:name instead",
            DeprecationWarning,
            stacklevel=2,
        )
        term = f"tmux:{tmux_session}"

    # Parse terminal option
    method, session_name = parse_term_option(term)

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

    # Dispatch to appropriate launcher
    match method:
        case LaunchMethod.FOREGROUND:
            console.print(f"[cyan]Starting {ai_tool_name} (Ctrl+C to exit)...[/cyan]\n")
            _run_command_in_shell(cmd, path, background=False, check=False)
        case LaunchMethod.BACKGROUND:
            _run_command_in_shell(cmd, path, background=True)
            console.print(f"[bold green]*[/bold green] {ai_tool_name} running in background\n")
        # iTerm
        case LaunchMethod.ITERM_WINDOW:
            _launch_iterm_window(path, cmd, ai_tool_name)
        case LaunchMethod.ITERM_TAB:
            _launch_iterm_tab(path, cmd, ai_tool_name)
        case LaunchMethod.ITERM_PANE_H:
            _launch_iterm_pane(path, cmd, ai_tool_name, horizontal=True)
        case LaunchMethod.ITERM_PANE_V:
            _launch_iterm_pane(path, cmd, ai_tool_name, horizontal=False)
        # tmux
        case LaunchMethod.TMUX:
            _launch_tmux_session(path, cmd, ai_tool_name, session_name)
        case LaunchMethod.TMUX_WINDOW:
            _launch_tmux_window(path, cmd, ai_tool_name)
        case LaunchMethod.TMUX_PANE_H:
            _launch_tmux_pane(path, cmd, ai_tool_name, horizontal=True)
        case LaunchMethod.TMUX_PANE_V:
            _launch_tmux_pane(path, cmd, ai_tool_name, horizontal=False)
        # Zellij
        case LaunchMethod.ZELLIJ:
            _launch_zellij_session(path, cmd, ai_tool_name, session_name)
        case LaunchMethod.ZELLIJ_TAB:
            _launch_zellij_tab(path, cmd, ai_tool_name)
        case LaunchMethod.ZELLIJ_PANE_H:
            _launch_zellij_pane(path, cmd, ai_tool_name, horizontal=True)
        case LaunchMethod.ZELLIJ_PANE_V:
            _launch_zellij_pane(path, cmd, ai_tool_name, horizontal=False)
        # WezTerm
        case LaunchMethod.WEZTERM_WINDOW:
            _launch_wezterm_window(path, cmd, ai_tool_name)
        case LaunchMethod.WEZTERM_TAB:
            _launch_wezterm_tab(path, cmd, ai_tool_name)
        case LaunchMethod.WEZTERM_PANE_H:
            _launch_wezterm_pane(path, cmd, ai_tool_name, horizontal=True)
        case LaunchMethod.WEZTERM_PANE_V:
            _launch_wezterm_pane(path, cmd, ai_tool_name, horizontal=False)


def resume_worktree(
    worktree: str | None = None,
    term: str | None = None,
    lookup_mode: str | None = None,
    # Deprecated parameters (for backward compatibility)
    bg: bool = False,
    iterm: bool = False,
    iterm_tab: bool = False,
    tmux_session: str | None = None,
) -> None:
    """
    Resume AI work in a worktree with context restoration.

    Args:
        worktree: Branch name or worktree directory name (optional, defaults to current directory)
        term: Terminal launch method (e.g., "i-t", "t:mysession", "z-p-h")
        lookup_mode: "branch", "worktree", or None (try both)
        bg: [DEPRECATED] Use term="bg" instead
        iterm: [DEPRECATED] Use term="iterm-window" or term="i-w" instead
        iterm_tab: [DEPRECATED] Use term="iterm-tab" or term="i-t" instead
        tmux_session: [DEPRECATED] Use term="tmux" or term="t:session_name" instead

    Raises:
        WorktreeNotFoundError: If worktree not found
        GitError: If git operations fail
    """
    from .. import session_manager

    # Resolve worktree target to (path, branch, repo)
    worktree_path, branch_name, worktree_repo = resolve_worktree_target(worktree, lookup_mode)

    # Get base branch for hook context
    base_branch = get_config(CONFIG_KEY_BASE_BRANCH.format(branch_name), worktree_repo) or ""

    # Run pre-resume hooks (can abort operation)
    hook_context = {
        "branch": branch_name,
        "base_branch": base_branch,
        "worktree_path": str(worktree_path),
        "repo_path": str(worktree_repo),
        "event": "resume.pre",
        "operation": "resume",
    }
    run_hooks("resume.pre", hook_context, cwd=worktree_path)

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
            term=term,
            resume=has_session,  # Only use resume if session exists
            # Deprecated parameters passed through
            bg=bg,
            iterm=iterm,
            iterm_tab=iterm_tab,
            tmux_session=tmux_session,
        )

        # Run post-resume hooks (non-blocking)
        hook_context["event"] = "resume.post"
        run_hooks("resume.post", hook_context, cwd=worktree_path)


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
