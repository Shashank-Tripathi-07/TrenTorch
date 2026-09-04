"""Shared pytest fixtures for platforms/cli/tests/."""

import shutil
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


@pytest.fixture
def force_first_run():
    """Deterministically force bare `tren`'s "first run" state for the
    duration of a test, regardless of whatever user_data/ state is left
    over in this checkout from other commands run against it.

    Bare `tren` now launches the TUI directly once user_data/ exists (see
    main.py's --tui shortcut routing), which would hang a subprocess-based
    test waiting on the TUI's interactive event loop. Any test asserting
    on the one-time welcome/quick-start screen instead of the TUI needs
    this fixture so it isn't at the mercy of ambient repo state.
    """
    user_data_dir = _PROJECT_ROOT / "user_data"
    backup_dir = _PROJECT_ROOT / "user_data.test_backup"
    moved_aside = False
    if user_data_dir.exists():
        user_data_dir.rename(backup_dir)
        moved_aside = True

    try:
        yield
    finally:
        # The test run itself creates a fresh user_data/ as its first-run
        # marker; discard it before restoring the real one.
        if user_data_dir.exists():
            shutil.rmtree(user_data_dir)
        if moved_aside:
            backup_dir.rename(user_data_dir)
