"""
Persist the venv's bin directory onto the user's PATH, so `tren` (a
console-script entry point installed into that venv) works from any
terminal, in any directory, without manually activating the venv first.

This deliberately never touches the *current* process's PATH (that would
be pointless -- a child process's env can't reach back into the shell
that spawned it) or an already-open terminal. It only persists the
change for terminals opened after it runs:
  - Windows: writes HKEY_CURRENT_USER\\Environment\\Path via winreg.
    New cmd/PowerShell windows read User PATH fresh from the registry at
    startup; already-open windows are unaffected until reopened.
  - macOS/Linux: appends an `export PATH=...` line, wrapped in a
    recognizable comment marker, to the user's shell rc file (detected
    from $SHELL, falling back to ~/.profile). New shells source that
    file on startup; already-open shells are unaffected until restarted.

Every function here is pure with respect to the real environment except
the two `_persist_*` functions, which are the only ones that touch the
registry or a real file -- kept separate so the decision logic
(already on PATH? which platform?) is unit-testable without mutating
anything real.
"""

import os
import sys
from pathlib import Path

_MARKER_START = "# >>> tren PATH setup >>>"
_MARKER_END = "# <<< tren PATH setup <<<"


def is_windows() -> bool:
    return sys.platform == "win32" or os.name == "nt"


def _normalize(path_str: str) -> str:
    """Normalize a PATH entry for comparison (case-insensitive on
    Windows, trailing-slash-insensitive everywhere)."""
    normalized = str(Path(path_str)) if path_str else ""
    return normalized.lower() if is_windows() else normalized


def is_on_path(bin_dir: Path, path_value: str | None = None) -> bool:
    """Whether bin_dir already appears in the given PATH string (the
    live os.environ["PATH"] by default)."""
    if path_value is None:
        path_value = os.environ.get("PATH", "")
    target = _normalize(str(bin_dir))
    entries = {_normalize(entry) for entry in path_value.split(os.pathsep) if entry}
    return target in entries


def _persist_windows(bin_dir: Path) -> tuple[bool, str]:
    """Prepend bin_dir to the user's persisted PATH via the registry.
    Only new terminals pick this up; the current process's PATH (and
    any already-open terminal) is untouched."""
    try:
        import winreg
    except ImportError:
        return False, "winreg is unavailable (not running on Windows)"

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS) as key:
            try:
                current, value_type = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                current, value_type = "", winreg.REG_EXPAND_SZ

            if is_on_path(bin_dir, current):
                return True, "already on PATH"

            new_value = f"{current};{bin_dir}" if current else str(bin_dir)
            winreg.SetValueEx(key, "Path", 0, value_type, new_value)
        return True, f"added {bin_dir} to your persisted User PATH (new terminals will see it)"
    except OSError as e:
        return False, f"could not update the registry: {e}"


def _detect_shell_rc_file() -> Path:
    """Guess which shell rc file new terminals will source, from $SHELL.
    Falls back to ~/.profile (sourced by most POSIX-compatible shells)
    when $SHELL isn't set or isn't recognized."""
    shell = os.environ.get("SHELL", "")
    home = Path.home()
    if "zsh" in shell:
        return home / ".zshrc"
    if "bash" in shell:
        # .bash_profile takes precedence for login shells on macOS, but
        # .bashrc is what most terminal emulators actually source for
        # new interactive shells on Linux -- .bashrc is the safer
        # single target for "the next terminal I open".
        return home / ".bashrc"
    return home / ".profile"


def _persist_unix(bin_dir: Path, rc_file: Path | None = None) -> tuple[bool, str]:
    """Append an export line to the user's shell rc file, wrapped in a
    marker so re-running `tren setup` never duplicates it."""
    if rc_file is None:
        rc_file = _detect_shell_rc_file()

    existing = rc_file.read_text(encoding="utf-8") if rc_file.exists() else ""
    if _MARKER_START in existing or is_on_path(bin_dir):
        return True, f"already configured in {rc_file}"

    export_line = f'{_MARKER_START}\nexport PATH="{bin_dir}:$PATH"\n{_MARKER_END}\n'
    try:
        with open(rc_file, "a", encoding="utf-8") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write(export_line)
        return True, f"added to {rc_file} (new terminals will see it; run 'source {rc_file}' for this one)"
    except OSError as e:
        return False, f"could not write to {rc_file}: {e}"


def add_bin_dir_to_path(bin_dir: Path) -> tuple[bool, str]:
    """Persist bin_dir onto PATH for future terminals. Returns
    (success, human-readable message) -- never raises."""
    bin_dir = bin_dir.resolve()
    if is_on_path(bin_dir):
        return True, "already on PATH"
    if is_windows():
        return _persist_windows(bin_dir)
    return _persist_unix(bin_dir)
