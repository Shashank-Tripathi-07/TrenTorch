"""
MC/DC coverage for HealthCommand's venv-status decision (venv_exists and
in_venv), the kernel-issue-recording decision, and _check_jupyter_kernel's
own registered-kernel decision.
"""

import subprocess
import sys
from io import StringIO

from rich.console import Console

import platforms.cli.commands.base as base_module
from platforms.cli.cli_platform.system.health import HealthCommand
from platforms.cli.core.config import CLIConfig

# ---------------------------------------------------------------------------
# venv_exists and in_venv
# ---------------------------------------------------------------------------


def _run_health(tmp_path, monkeypatch, *, venv_exists, in_venv):
    fake_venv = tmp_path / ".venv"
    if venv_exists:
        fake_venv.mkdir()
    monkeypatch.setattr(base_module, "get_venv_path", lambda: fake_venv)

    if in_venv:
        monkeypatch.setenv("VIRTUAL_ENV", str(fake_venv))
    else:
        monkeypatch.delenv("VIRTUAL_ENV", raising=False)
        monkeypatch.setattr(sys, "prefix", "/fake/same")
        monkeypatch.setattr(sys, "base_prefix", "/fake/same")
        monkeypatch.delattr(sys, "real_prefix", raising=False)

    cmd = HealthCommand(CLIConfig.from_project_root(tmp_path))
    monkeypatch.setattr(cmd, "_check_jupyter_kernel", lambda: ("[dim]○ Skipped[/dim]", "test"))
    monkeypatch.setattr(cmd, "_get_kernel_python", lambda: None)
    buf = StringIO()
    cmd.console = Console(file=buf, width=300, no_color=True)
    cmd.run(None)
    return buf.getvalue()


def test_venv_exists_and_active_shows_ok(tmp_path, monkeypatch):
    """Baseline: venv_exists True, in_venv True -> OK."""
    out = _run_health(tmp_path, monkeypatch, venv_exists=True, in_venv=True)
    assert "Virtual Environment" in out and "OK" in out


def test_venv_exists_but_not_active_shows_not_activated(tmp_path, monkeypatch):
    """venv_exists True, in_venv False -> "Not Activated", not OK.
    Paired with the baseline: only in_venv differs, isolating that half
    of the and."""
    out = _run_health(tmp_path, monkeypatch, venv_exists=True, in_venv=False)
    # The fixed-width Status column can wrap "Not Activated" onto two
    # lines, so check both fragments rather than one exact substring.
    assert "Not" in out and "Activated" in out
    assert "exists but is not activated" in out


def test_no_venv_directory_shows_missing_regardless_of_env_vars(tmp_path, monkeypatch):
    """venv_exists False -> "Missing", regardless of in_venv (the elif
    chain's final else). Paired with the baseline: only venv_exists
    differs, isolating that half of the and."""
    out = _run_health(tmp_path, monkeypatch, venv_exists=False, in_venv=True)
    assert "Missing" in out


def test_real_prefix_alone_also_counts_as_in_venv(tmp_path, monkeypatch):
    """in_venv's own third disjunct (hasattr(sys, "real_prefix")),
    isolated on its own -- the _run_health helper's in_venv=True path
    only ever set VIRTUAL_ENV, never exercised this atom independently."""
    fake_venv = tmp_path / ".venv"
    fake_venv.mkdir()
    monkeypatch.setattr(base_module, "get_venv_path", lambda: fake_venv)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.setattr(sys, "prefix", "/fake/same")
    monkeypatch.setattr(sys, "base_prefix", "/fake/same")
    monkeypatch.setattr(sys, "real_prefix", "/fake/old-venv", raising=False)

    cmd = HealthCommand(CLIConfig.from_project_root(tmp_path))
    monkeypatch.setattr(cmd, "_check_jupyter_kernel", lambda: ("[dim]○ Skipped[/dim]", "test"))
    monkeypatch.setattr(cmd, "_get_kernel_python", lambda: None)
    buf = StringIO()
    cmd.console = Console(file=buf, width=300, no_color=True)
    cmd.run(None)

    assert "Virtual Environment" in buf.getvalue() and "OK" in buf.getvalue()


# ---------------------------------------------------------------------------
# "❌" in kernel_status or "⚠️" in kernel_status
# ---------------------------------------------------------------------------


def _run_health_with_kernel_status(tmp_path, monkeypatch, kernel_status):
    monkeypatch.setattr(base_module, "get_venv_path", lambda: tmp_path / ".venv")
    (tmp_path / ".venv").mkdir()
    monkeypatch.setenv("VIRTUAL_ENV", str(tmp_path / ".venv"))

    cmd = HealthCommand(CLIConfig.from_project_root(tmp_path))
    monkeypatch.setattr(cmd, "_check_jupyter_kernel", lambda: (kernel_status, "detail text"))
    monkeypatch.setattr(cmd, "_get_kernel_python", lambda: None)
    buf = StringIO()
    cmd.console = Console(file=buf, width=300, no_color=True)
    cmd.run(None)
    return buf.getvalue()


def test_failed_kernel_status_is_recorded_as_an_issue(tmp_path, monkeypatch):
    """Baseline: "❌" present -> recorded as an issue (shown in the
    action-items summary)."""
    out = _run_health_with_kernel_status(tmp_path, monkeypatch, "[red]❌ Not found[/red]")
    assert "• detail text" in out


def test_warning_kernel_status_is_recorded_as_an_issue(tmp_path, monkeypatch):
    """Isolates the second half of the or: "⚠️" present, "❌" absent."""
    out = _run_health_with_kernel_status(tmp_path, monkeypatch, "[yellow]⚠️  Mismatch[/yellow]")
    assert "• detail text" in out


def test_ok_kernel_status_is_not_recorded_as_an_issue(tmp_path, monkeypatch):
    """Neither symbol present -> not recorded as an issue. Paired with
    the tests above: only the symbol's presence differs, isolating that
    condition."""
    out = _run_health_with_kernel_status(tmp_path, monkeypatch, "[green]✅ Registered[/green]")
    assert "• detail text" not in out


# ---------------------------------------------------------------------------
# _check_jupyter_kernel: result.returncode == 0 and "tinytorch" in result.stdout
# ---------------------------------------------------------------------------


def _check_jupyter_kernel(tmp_path, monkeypatch, *, returncode, stdout):
    def fake_run(cmd_args, **kwargs):
        return subprocess.CompletedProcess(cmd_args, returncode=returncode, stdout=stdout, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    cmd = HealthCommand(CLIConfig.from_project_root(tmp_path))
    return cmd._check_jupyter_kernel()


def test_kernelspec_success_with_tinytorch_registered(tmp_path, monkeypatch):
    """Baseline: returncode == 0 True, "tinytorch" in stdout True ->
    registered."""
    status, detail = _check_jupyter_kernel(tmp_path, monkeypatch, returncode=0, stdout="python3\ntinytorch\n")
    assert "Registered" in status


def test_kernelspec_success_without_tinytorch(tmp_path, monkeypatch):
    """returncode == 0 True, "tinytorch" in stdout False -> the and is
    False, falls to the "no tinytorch kernel" branch. Paired with the
    baseline: only whether tinytorch is listed differs, isolating that
    half of the and."""
    status, detail = _check_jupyter_kernel(tmp_path, monkeypatch, returncode=0, stdout="python3\n")
    assert "Registered" not in status
    assert "install --user --name tinytorch" in detail


def test_kernelspec_command_itself_fails(tmp_path, monkeypatch):
    """returncode == 0 is False -> the and is False regardless of
    stdout content. Paired with the baseline: only returncode differs,
    isolating that half of the and."""
    status, detail = _check_jupyter_kernel(tmp_path, monkeypatch, returncode=1, stdout="tinytorch\n")
    assert "Registered" not in status
