"""Arrow-key TUI selector for interactive worktree selection."""

from __future__ import annotations

import os
import sys


def arrow_select(
    items: list[tuple[str, str]],
    title: str = "Select worktree:",
    default_index: int = 0,
) -> str | None:
    """Arrow-key selector that renders on stderr and returns selected value.

    Args:
        items: List of (label, value) tuples to display.
        title: Title shown above the list.
        default_index: Initially highlighted item index.

    Returns:
        The value of the selected item, or None if cancelled.
    """
    if not items:
        return None

    if not sys.stderr.isatty():
        return None

    default_index = max(0, min(default_index, len(items) - 1))

    try:
        return _arrow_select_unix(items, title, default_index)
    except ImportError:
        pass

    try:
        return _arrow_select_windows(items, title, default_index)
    except ImportError:
        pass

    return _arrow_select_fallback(items, title, default_index)


def _get_terminal_width() -> int:
    """Get terminal width, defaulting to 80."""
    try:
        return os.get_terminal_size(sys.stderr.fileno()).columns
    except (OSError, ValueError):
        return 80


def _write_stderr(s: str) -> None:
    """Write raw bytes to stderr, bypassing buffered text wrapper."""
    os.write(sys.stderr.fileno(), s.encode())


def _truncate(text: str, width: int) -> str:
    """Truncate text to fit within terminal width."""
    # Strip ANSI escapes to measure visible length
    import re

    visible = re.sub(r"\x1b\[[^m]*m", "", text)
    if len(visible) <= width:
        return text
    # Truncate: find where to cut by walking both strings
    vis_pos = 0
    cut_pos = 0
    i = 0
    while i < len(text) and vis_pos < width - 1:
        if text[i] == "\x1b":
            # Skip ANSI sequence
            j = i + 1
            while j < len(text) and text[j] != "m":
                j += 1
            i = j + 1
        else:
            vis_pos += 1
            i += 1
        cut_pos = i
    return text[:cut_pos] + "\x1b[0m"


def _render(
    items: list[tuple[str, str]],
    title: str,
    selected: int,
    total_lines: int,
    *,
    first_render: bool = False,
) -> None:
    """Render the selector list on stderr using ANSI escape codes."""
    width = _get_terminal_width()

    if not first_render:
        # Restore cursor to saved position
        _write_stderr("\x1b[u")

    # Save cursor position at the start of our render area
    _write_stderr("\x1b[s")

    # Title
    line = f"  \x1b[1m{title}\x1b[0m"
    _write_stderr(f"\x1b[2K{_truncate(line, width)}\r\n")
    # Blank line
    _write_stderr("\x1b[2K\r\n")

    for i, (label, value) in enumerate(items):
        _write_stderr("\x1b[2K")  # clear line
        if i == selected:
            line = f"  \x1b[1;7m > {label} \x1b[0m  \x1b[2m{value}\x1b[0m"
        else:
            line = f"    {label}  \x1b[2m{value}\x1b[0m"
        _write_stderr(f"{_truncate(line, width)}\r\n")

    # Clear any leftover lines below (in case of previous longer render)
    for _ in range(2):
        _write_stderr("\x1b[2K\r\n")
    # Move back up to just after our items
    _write_stderr("\x1b[2A")


def _cleanup(total_lines: int) -> None:
    """Erase the rendered selector from stderr."""
    # Restore to saved position
    _write_stderr("\x1b[u")
    for _ in range(total_lines + 2):  # +2 for extra cleared lines
        _write_stderr("\x1b[2K\r\n")
    _write_stderr("\x1b[u")


def _read_key(fd: int) -> str:
    """Read a single keypress from fd, handling escape sequences."""
    ch = os.read(fd, 1)
    if not ch:
        raise EOFError

    if ch == b"\x1b":
        # Could be an escape sequence — peek with a short timeout
        import select

        readable, _, _ = select.select([fd], [], [], 0.05)
        if not readable:
            # Bare Escape key
            return "esc"
        seq1 = os.read(fd, 1)
        if seq1 == b"[":
            seq2 = os.read(fd, 1)
            if seq2 == b"A":
                return "up"
            if seq2 == b"B":
                return "down"
            # Consume any remaining bytes of unknown sequence
            return "unknown"
        return "unknown"

    if ch == b"\r" or ch == b"\n":
        return "enter"
    if ch == b"\x03":
        return "ctrl-c"
    if ch == b"q":
        return "q"
    if ch in (b"1", b"2", b"3", b"4", b"5", b"6", b"7", b"8", b"9"):
        return ch.decode()

    return "unknown"


def _arrow_select_unix(
    items: list[tuple[str, str]],
    title: str,
    default_index: int,
) -> str | None:
    """Unix implementation using termios/tty."""
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    selected = default_index
    total_lines = len(items) + 2  # title + blank + items

    # Hide cursor
    _write_stderr("\x1b[?25l")

    try:
        tty.setraw(fd)
        _render(items, title, selected, total_lines, first_render=True)

        while True:
            key = _read_key(fd)

            if key == "enter":
                _cleanup(total_lines)
                return items[selected][1]

            if key in ("ctrl-c", "q", "esc"):
                _cleanup(total_lines)
                return None

            if key == "up":
                selected = (selected - 1) % len(items)
                _render(items, title, selected, total_lines)
            elif key == "down":
                selected = (selected + 1) % len(items)
                _render(items, title, selected, total_lines)
            elif key in "123456789":
                idx = int(key) - 1
                if 0 <= idx < len(items):
                    _cleanup(total_lines)
                    return items[idx][1]

    except (KeyboardInterrupt, EOFError):
        _cleanup(total_lines)
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        # Show cursor
        _write_stderr("\x1b[?25h")


def _arrow_select_windows(
    items: list[tuple[str, str]],
    title: str,
    default_index: int,
) -> str | None:
    """Windows implementation using msvcrt."""
    import msvcrt

    selected = default_index
    total_lines = len(items) + 2

    _write_stderr("\x1b[?25l")

    try:
        _render(items, title, selected, total_lines, first_render=True)

        while True:
            ch = msvcrt.getwch()  # type: ignore[attr-defined]

            if ch == "\r":
                _cleanup(total_lines)
                return items[selected][1]

            if ch == "\x03" or ch == "q":
                _cleanup(total_lines)
                return None

            if ch == "\x00" or ch == "\xe0":
                # Special key prefix on Windows
                key = msvcrt.getwch()  # type: ignore[attr-defined]
                if key == "H":  # Up arrow
                    selected = (selected - 1) % len(items)
                    _render(items, title, selected, total_lines)
                elif key == "P":  # Down arrow
                    selected = (selected + 1) % len(items)
                    _render(items, title, selected, total_lines)

            elif ch in "123456789":
                idx = int(ch) - 1
                if 0 <= idx < len(items):
                    _cleanup(total_lines)
                    return items[idx][1]

    except (KeyboardInterrupt, EOFError):
        _cleanup(total_lines)
        return None
    finally:
        _write_stderr("\x1b[?25h")


def _arrow_select_fallback(
    items: list[tuple[str, str]],
    title: str,
    default_index: int,
) -> str | None:
    """Fallback: numbered list with text input."""
    out = sys.stderr

    out.write(f"\n  {title}\n\n")
    for i, (label, value) in enumerate(items):
        marker = ">" if i == default_index else " "
        out.write(f"  {marker} [{i + 1}] {label}  {value}\n")
    out.write("\n")
    out.flush()

    try:
        out.write(f"Select [1-{len(items)}]: ")
        out.flush()
        choice = sys.stdin.readline().strip()
        if not choice:
            return items[default_index][1]
        idx = int(choice) - 1
        if 0 <= idx < len(items):
            return items[idx][1]
    except (ValueError, KeyboardInterrupt, EOFError):
        pass

    return None
