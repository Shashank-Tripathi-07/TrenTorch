"""
MC/DC coverage for the "are we on Windows" decision as it appears in
get_venv_bin_dir, plus the smoke test docs/testing-strategy.md section
4.1 explicitly proposes as missing: "a dedicated smoke test that imports
platforms.cli.main and prints a string containing emoji" -- the fast,
targeted regression test for the real historical UnicodeEncodeError bug
(Windows console legacy codepage crashing on ordinary emoji output).

main.py's own copy of this same `sys.platform == "win32" or os.name ==
"nt"` decision (the module-level stdout/stderr encoding fix) is
deliberately not MC/DC'd via reload here: reloading platforms.cli.main
cascades into re-importing its entire command-class tree, including
export_utils.py's module-level `Path("data") / "src"` default argument,
which is evaluated at import time using Python's own real os.name-based
Path class selection -- monkeypatching os.name to fake "not Windows"
while actually running on a real Windows filesystem makes that
crash with "cannot instantiate PosixPath on your system", a platform
inconsistency in the test technique itself, not in the code under test.
Isolating main.py's copy safely would need refactoring the check into an
importable, directly-callable function first, which is a real code change
beyond this pass's scope, not something to force through a fragile test.
"""

import os
import sys

from platforms.cli.core.virtual_env_manager import get_venv_bin_dir

# ---------------------------------------------------------------------------
# get_venv_bin_dir: sys.platform == "win32" or os.name == "nt"
# ---------------------------------------------------------------------------


def test_win32_platform_alone_selects_scripts_dir(tmp_path, monkeypatch):
    """A=True, B doesn't matter (short-circuits) -> Scripts/."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(os, "name", "posix")  # B False, isolates A alone
    assert get_venv_bin_dir(tmp_path).name == "Scripts"


def test_nt_os_name_alone_selects_scripts_dir(tmp_path, monkeypatch):
    """A=False, B=True -> Scripts/. Paired with the test above: only
    which condition is True differs, isolating B's independent effect."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(os, "name", "nt")
    assert get_venv_bin_dir(tmp_path).name == "Scripts"


def test_neither_windows_signal_selects_bin_dir(tmp_path, monkeypatch):
    """A=False, B=False -> bin/. Paired with either test above: only one
    condition's truth differs, isolating the or's "both false" case."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(os, "name", "posix")
    assert get_venv_bin_dir(tmp_path).name == "bin"


def test_emoji_output_does_not_crash_after_import():
    """The concrete smoke test docs/testing-strategy.md section 4.1
    proposes directly: import platforms.cli.main and print a string
    containing emoji, on whatever platform this actually runs on. On
    Windows this is the real regression test for the historical
    UnicodeEncodeError; on other platforms it's a cheap no-op
    confirmation nothing here is platform-fragile in the other direction."""
    import platforms.cli.main  # noqa: F401

    print("🔥 smoke test: TrenTorch imports and prints emoji cleanly")
