"""
MC/DC coverage for main.py's own copy of the Windows-detection decision:
_is_windows(platform, os_name) = platform == "win32" or os_name == "nt".

This decision used to be inline (`if sys.platform == "win32" or os.name ==
"nt":`), directly at module import time, which meant the only way to test
it independently of the real host platform was to reload platforms.cli.main
under a monkeypatched sys.platform/os.name -- but that reload re-runs every
import below it, including export_utils.py's module-level Path(...) default
argument, which crashes instantiating the wrong Path flavor on a real
Windows filesystem. Pulling the decision out into its own function makes it
callable directly with fake inputs, with no reload and no crash risk.
"""

from platforms.cli.main import _is_windows


def test_win32_platform_alone_is_windows():
    """Baseline: platform == "win32" True, os_name == "nt" False ->
    Windows."""
    assert _is_windows("win32", "posix") is True


def test_nt_os_name_alone_is_windows():
    """platform == "win32" False, os_name == "nt" True -> Windows.
    Paired with the baseline: only os_name differs, isolating that half
    of the or."""
    assert _is_windows("linux", "nt") is True


def test_neither_signal_is_not_windows():
    """Both False -> not Windows. Paired with the baseline: only
    platform's value differs, isolating that half of the or."""
    assert _is_windows("linux", "posix") is False
