"""
TinyTorch CLI Package

A professional command-line interface for the TinyTorch ML system.
Organized with clean separation of concerns and proper error handling.
"""

import sys as _sys
from pathlib import Path as _Path

# trentorch/ lives at data/trentorch/, not the repo root. bin/tren and
# conftest.py both add data/ to sys.path already, but anything importing
# platforms.cli directly (e.g. as a subprocess) bypasses both, so this
# package -- imported by every such invocation -- fixes it here once.
_data_dir = str(_Path(__file__).resolve().parent.parent.parent / "data")
if _data_dir not in _sys.path:
    _sys.path.insert(0, _data_dir)


def _get_version() -> str:
    """Read version from pyproject.toml (single source of truth)."""
    try:
        pyproject_path = _Path(__file__).parent.parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            content = pyproject_path.read_text()
            for line in content.splitlines():
                if line.strip().startswith("version"):
                    return line.split("=")[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "0.0.0-dev"


__version__ = _get_version()
__author__ = "TinyTorch Team"
