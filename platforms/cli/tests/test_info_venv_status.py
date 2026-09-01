"""
MC/DC coverage for info.py's own copy of the venv-detection decision
(_gather_system_info's in_venv) and InfoCommand.run's venv_exists and
in_venv display decision. Same shape already proven in
test_status_analyzer_environment.py and test_main_venv_guard.py; kept
concise here since it's a genuine, separate copy of the same logic in a
different file, not because the pattern itself needs re-litigating.
"""

import os
import sys
from io import StringIO

from rich.console import Console

from platforms.cli.cli_platform.system.info import InfoCommand, _gather_system_info
from platforms.cli.core.config import CLIConfig

# ---------------------------------------------------------------------------
# in_venv = VIRTUAL_ENV is not None or (base_prefix != prefix) or real_prefix
# ---------------------------------------------------------------------------


def test_virtual_env_var_alone_reports_active(tmp_path, monkeypatch):
    monkeypatch.setenv("VIRTUAL_ENV", str(tmp_path))
    monkeypatch.setattr(sys, "prefix", "/same")
    monkeypatch.setattr(sys, "base_prefix", "/same")
    monkeypatch.delattr(sys, "real_prefix", raising=False)
    info = _gather_system_info(tmp_path)
    assert info["venv_active"] is True


def test_differing_prefixes_alone_reports_active(monkeypatch, tmp_path):
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.setattr(sys, "prefix", "/venv")
    monkeypatch.setattr(sys, "base_prefix", "/system")
    monkeypatch.delattr(sys, "real_prefix", raising=False)
    info = _gather_system_info(tmp_path)
    assert info["venv_active"] is True


def test_none_of_the_three_signals_reports_inactive(monkeypatch, tmp_path):
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.setattr(sys, "prefix", "/same")
    monkeypatch.setattr(sys, "base_prefix", "/same")
    monkeypatch.delattr(sys, "real_prefix", raising=False)
    info = _gather_system_info(tmp_path)
    assert info["venv_active"] is False


# ---------------------------------------------------------------------------
# InfoCommand.run: venv_exists and in_venv
# ---------------------------------------------------------------------------


def _run_info(tmp_path, monkeypatch, *, venv_exists, in_venv):
    fake_venv = tmp_path / ".venv"
    if venv_exists:
        fake_venv.mkdir()

    import platforms.cli.commands.base as base_module

    monkeypatch.setattr(base_module, "get_venv_path", lambda: fake_venv)
    monkeypatch.setattr(
        "platforms.cli.cli_platform.system.info._gather_system_info",
        lambda venv_path: {
            "python_version": "3.x",
            "platform": "test",
            "tinytorch_version": "test",
            "numpy_version": "test",
            "venv_active": in_venv,
        },
    )

    cmd = InfoCommand(CLIConfig.from_project_root(tmp_path))
    buf = StringIO()
    cmd.console = Console(file=buf, width=200, no_color=True)
    monkeypatch.setattr(
        os, "environ", {**os.environ, "VIRTUAL_ENV": str(fake_venv)} if in_venv else os.environ
    )
    cmd.run(type("Args", (), {"json": False})())
    return buf.getvalue()


def test_venv_exists_and_active_shows_ok_status(tmp_path, monkeypatch):
    """Baseline: venv_exists True, in_venv True -> OK."""
    out = _run_info(tmp_path, monkeypatch, venv_exists=True, in_venv=True)
    assert "OK" in out


def test_venv_exists_but_not_active_shows_not_activated(tmp_path, monkeypatch):
    """venv_exists True, in_venv False -> Not Activated. Paired with the
    baseline: only in_venv differs, isolating that half of the and."""
    out = _run_info(tmp_path, monkeypatch, venv_exists=True, in_venv=False)
    assert "Not Activated" in out


def test_no_venv_directory_shows_not_found(tmp_path, monkeypatch):
    """venv_exists False -> Not Found regardless of in_venv. Paired with
    the baseline: only venv_exists differs, isolating that half."""
    out = _run_info(tmp_path, monkeypatch, venv_exists=False, in_venv=True)
    assert "Not Found" in out
