"""
MC/DC coverage for DevTestCommand._run_user_journey's reset-verification
decisions: modules_cleared and core_cleared, each a `not any(...)` over a
directory listing, checked after actually invoking `tren system reset`.
Milestone-running (Step 1) is skipped entirely by emptying MILESTONE_SCRIPTS,
isolating Step 2's reset verification from the rest of this otherwise very
heavy, real-subprocess-per-milestone method.
"""

import subprocess
from argparse import Namespace

import platforms.cli.processes.milestone as milestone_module
from platforms.cli.cli_platform.dev.test import DevTestCommand
from platforms.cli.core.config import CLIConfig


def _verify_reset(tmp_path, monkeypatch, *, reset_returncode, modules_left, core_files_left, progress_left):
    monkeypatch.setattr(milestone_module, "MILESTONE_SCRIPTS", {})

    modules_dir = tmp_path / "data" / "modules"
    core_dir = tmp_path / "data" / "trentorch" / "core"
    user_data_dir = tmp_path / "user_data"
    modules_dir.mkdir(parents=True)
    core_dir.mkdir(parents=True)
    (core_dir / "__init__.py").write_text("", encoding="utf-8")  # always present, never counts

    if modules_left:
        (modules_dir / "01_tensor").mkdir()
    if core_files_left:
        (core_dir / "tensor.py").write_text("", encoding="utf-8")
    if progress_left:
        user_data_dir.mkdir()
        (user_data_dir / "progress.json").write_text("{}", encoding="utf-8")

    (tmp_path / "bin").mkdir()

    def fake_run(cmd_args, **kwargs):
        return subprocess.CompletedProcess(cmd_args, returncode=reset_returncode, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    cmd = DevTestCommand(CLIConfig.from_project_root(tmp_path))
    result = cmd._run_user_journey(tmp_path, Namespace(ci=False))
    return result


# ---------------------------------------------------------------------------
# modules_cleared = not any(item.is_dir() and item.name[:1].isdigit()
#                            for item in modules_dir.iterdir())
# ---------------------------------------------------------------------------


def test_fully_cleared_state_passes_verification(tmp_path, monkeypatch):
    """Baseline: reset succeeds, no digit-prefixed module dirs, no
    stray core files, no progress file -> reset_ok True, overall pass."""
    result = _verify_reset(
        tmp_path,
        monkeypatch,
        reset_returncode=0,
        modules_left=False,
        core_files_left=False,
        progress_left=False,
    )
    assert result.passed is True


def test_leftover_module_directory_fails_verification(tmp_path, monkeypatch):
    """A digit-prefixed module directory still present -> the any() is
    True, modules_cleared False, reset_ok False. Paired with the
    baseline: only the leftover module directory differs, isolating
    that condition from core/progress's independent effects."""
    result = _verify_reset(
        tmp_path,
        monkeypatch,
        reset_returncode=0,
        modules_left=True,
        core_files_left=False,
        progress_left=False,
    )
    assert result.passed is False


def test_leftover_core_file_fails_verification(tmp_path, monkeypatch):
    """A generated core .py file still present (beyond __init__.py) ->
    core_cleared False, reset_ok False. Paired with the baseline: only
    the leftover core file differs, isolating that condition."""
    result = _verify_reset(
        tmp_path,
        monkeypatch,
        reset_returncode=0,
        modules_left=False,
        core_files_left=True,
        progress_left=False,
    )
    assert result.passed is False


def test_leftover_progress_file_fails_verification(tmp_path, monkeypatch):
    """progress.json still present -> progress_cleared False, reset_ok
    False. Paired with the baseline: only the leftover progress file
    differs, isolating that condition."""
    result = _verify_reset(
        tmp_path,
        monkeypatch,
        reset_returncode=0,
        modules_left=False,
        core_files_left=False,
        progress_left=True,
    )
    assert result.passed is False


def test_reset_command_nonzero_exit_fails_verification_even_if_state_looks_clean(tmp_path, monkeypatch):
    """The reset command itself reporting failure (returncode != 0)
    fails verification even when every file-state check looks clean --
    isolating reset_result.returncode's own independent effect within
    the larger "reset_ok = returncode == 0 and modules_cleared and
    core_cleared and progress_cleared" and."""
    result = _verify_reset(
        tmp_path,
        monkeypatch,
        reset_returncode=1,
        modules_left=False,
        core_files_left=False,
        progress_left=False,
    )
    assert result.passed is False
