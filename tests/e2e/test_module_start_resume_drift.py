"""
Regression test for issue #142: `tren module start`/`resume` could get
permanently stuck if data/modules/ and user_data/progress.json drift apart.

Reproduction (from the issue):
    tren module start 01                       # creates data/modules/01_tensor/, marks "01" as started
    tren system reset --keep-progress --force   # wipes data/modules/, leaves started_modules=["01"] untouched
    tren module start 01                        # used to refuse: "already started"
    tren module resume 01                       # used to accept, then fail deep inside open_jupyter()

The fix makes both `start` and `resume` check whether the notebook file
actually exists on disk before trusting the `started_modules` flag, and
self-heal by recreating it from data/src/ when it's missing.

Run with:
    pytest tests/e2e/test_module_start_resume_drift.py -v -m module_flow
"""

import json
import shutil
import sys
from pathlib import Path

import pytest

from tests.e2e.test_user_journey import run_tren

PROJECT_ROOT = Path(__file__).parent.parent.parent
MODULE_DIR = PROJECT_ROOT / "data" / "modules" / "01_tensor"
NOTEBOOK_FILE = MODULE_DIR / "tensor.ipynb"


@pytest.fixture
def clean_module_01_state():
    """Back up and restore progress.json and data/modules/01_tensor/
    around the test, so this test's simulated drift doesn't leak into
    a real student's saved state or other tests.
    """
    progress_file = PROJECT_ROOT / "user_data" / "progress.json"
    backup_progress = PROJECT_ROOT / "user_data" / "progress.json.drift_test_backup"
    had_progress = progress_file.exists()
    if had_progress:
        shutil.copy(progress_file, backup_progress)

    module_dir_backup = PROJECT_ROOT / "data" / "modules" / "01_tensor.drift_test_backup"
    had_module_dir = MODULE_DIR.exists()
    if had_module_dir:
        shutil.move(str(MODULE_DIR), str(module_dir_backup))

    try:
        yield
    finally:
        if MODULE_DIR.exists():
            shutil.rmtree(MODULE_DIR)
        if had_module_dir:
            shutil.move(str(module_dir_backup), str(MODULE_DIR))

        if had_progress:
            shutil.copy(backup_progress, progress_file)
            backup_progress.unlink()
        elif progress_file.exists():
            progress_file.unlink()


@pytest.mark.module_flow
class TestModuleStartResumeDrift:
    def test_start_self_heals_when_notebook_missing(self, clean_module_01_state):
        """`start_module()` should recreate a missing notebook instead of
        refusing forever with 'already started'."""
        # Start module 01 for the first time (--no-jupyter: don't actually
        # open a browser/Jupyter server in CI).
        code, stdout, stderr = run_tren(["module", "start", "01", "--no-jupyter"])
        assert code == 0, f"initial start failed: {stdout}\n{stderr}"
        assert NOTEBOOK_FILE.exists(), "start_module() should have created the notebook"

        # Simulate `tren system reset --keep-progress --force`: wipe
        # data/modules/, leave user_data/progress.json's started_modules
        # untouched.
        shutil.rmtree(MODULE_DIR)
        assert not NOTEBOOK_FILE.exists()

        # Before the fix: this returned 1 with "already started", forever.
        code, stdout, stderr = run_tren(["module", "start", "01", "--no-jupyter"])
        combined = stdout + stderr
        assert code == 0, f"start did not self-heal after drift: {combined}"
        assert NOTEBOOK_FILE.exists(), "start_module() should have recreated the missing notebook"

    def test_resume_self_heals_when_notebook_missing(self, clean_module_01_state):
        """`resume_module()` should recreate a missing notebook instead of
        failing deep inside open_jupyter() with a generic error."""
        code, stdout, stderr = run_tren(["module", "start", "01", "--no-jupyter"])
        assert code == 0, f"initial start failed: {stdout}\n{stderr}"
        assert NOTEBOOK_FILE.exists()

        # Simulate the same drift as above.
        shutil.rmtree(MODULE_DIR)
        assert not NOTEBOOK_FILE.exists()

        # Before the fix: resume accepted (started_modules still has "01"),
        # then failed inside open_jupyter() with a generic, unhelpful error.
        # --no-jupyter isn't a resume flag, so this call will still attempt
        # to open Jupyter; we only assert on the self-heal step (the
        # notebook must exist again) and that it isn't the old dead-end
        # message, rather than requiring a real Jupyter server in CI.
        code, stdout, stderr = run_tren(["module", "resume", "01"], timeout=30)
        combined = stdout + stderr
        assert "notebook is missing" in combined.lower() or "restored" in combined.lower(), (
            f"resume did not report self-healing the missing notebook: {combined}"
        )
        assert NOTEBOOK_FILE.exists(), "resume_module() should have recreated the missing notebook"
        assert "module directory not found" not in combined.lower(), (
            "resume should self-heal before ever reaching open_jupyter()'s generic dead-end message"
        )