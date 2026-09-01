"""
MC/DC coverage for ModuleTestCommand's two independent copies of the same
result.stderr or result.stdout fallback: run_module_pytest (line ~179) and
run_integration_tests (line ~283). Textually identical, but distinct
methods with distinct setup, so each gets its own isolation pair.
"""

import subprocess
from io import StringIO
from types import SimpleNamespace

from rich.console import Console

from platforms.cli.core.config import CLIConfig
from platforms.cli.processes.module_workflow.test import ModuleTestCommand


def _fake_result(*, returncode, stdout, stderr):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def _command(tmp_path):
    cmd = ModuleTestCommand(CLIConfig.from_project_root(tmp_path))
    cmd.console = Console(file=StringIO(), width=200, no_color=True)
    return cmd


# ---------------------------------------------------------------------------
# run_module_pytest: on failure, return result.stderr or result.stdout
# ---------------------------------------------------------------------------


def test_pytest_failure_with_stderr_returns_stderr(tmp_path, monkeypatch):
    """Baseline: returncode != 0, result.stderr truthy -> stderr
    returned (the or's left side wins)."""
    tests_dir = tmp_path / "data" / "src" / "01_tensor" / "tests"
    tests_dir.mkdir(parents=True)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: _fake_result(returncode=1, stdout="stdout text", stderr="stderr text"),
    )
    cmd = _command(tmp_path)
    ok, message = cmd.run_module_pytest("01_tensor", "01")
    assert ok is False
    assert message == "stderr text"


def test_pytest_failure_with_empty_stderr_falls_back_to_stdout(tmp_path, monkeypatch):
    """result.stderr falsy (empty string) -> falls back to result.stdout.
    Paired with the baseline: only stderr's truthiness differs,
    isolating that half of the or."""
    tests_dir = tmp_path / "data" / "src" / "01_tensor" / "tests"
    tests_dir.mkdir(parents=True)
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: _fake_result(returncode=1, stdout="stdout text", stderr="")
    )
    cmd = _command(tmp_path)
    ok, message = cmd.run_module_pytest("01_tensor", "01")
    assert ok is False
    assert message == "stdout text"


# ---------------------------------------------------------------------------
# run_integration_tests: same fallback pattern, distinct method
# ---------------------------------------------------------------------------


def _setup_integration(tmp_path):
    integration_dir = tmp_path / "tests" / "integration"
    integration_dir.mkdir(parents=True)
    (integration_dir / "test_layers_integration.py").write_text("", encoding="utf-8")


def test_integration_failure_with_stderr_returns_stderr(tmp_path, monkeypatch):
    """Baseline: returncode != 0, result.stderr truthy -> stderr
    returned. A distinct method from run_module_pytest, exercising the
    same or shape independently."""
    _setup_integration(tmp_path)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: _fake_result(returncode=1, stdout="stdout text", stderr="stderr text"),
    )
    cmd = _command(tmp_path)
    ok, message = cmd.run_integration_tests("03")
    assert ok is False
    assert message == "stderr text"


def test_integration_failure_with_empty_stderr_falls_back_to_stdout(tmp_path, monkeypatch):
    """result.stderr falsy -> falls back to result.stdout. Paired with
    the baseline: only stderr's truthiness differs, isolating that half
    of the or, distinct from run_module_pytest's own isolation pair."""
    _setup_integration(tmp_path)
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: _fake_result(returncode=1, stdout="stdout text", stderr="")
    )
    cmd = _command(tmp_path)
    ok, message = cmd.run_integration_tests("03")
    assert ok is False
    assert message == "stdout text"
