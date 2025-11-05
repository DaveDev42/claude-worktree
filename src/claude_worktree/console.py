"""Console factory for centralized Rich console configuration.

This module provides a single point of configuration for all Rich Console
instances used throughout the application. This ensures consistent behavior
across all platforms, especially for Windows compatibility.
"""

from rich.console import Console


def get_console() -> Console:
    """Get a configured Rich Console instance.

    Returns a Console instance with Windows-compatible settings:
    - legacy_windows=False: Uses modern Windows terminal features when available

    Note: While legacy_windows=False helps, we still use ASCII characters (*, !, x, ->)
    instead of Unicode symbols (✓, ⚠, ✗, →) to ensure compatibility with Windows
    cp1252 encoding on older systems.

    Returns:
        Console: A configured Rich Console instance
    """
    return Console(legacy_windows=False)
