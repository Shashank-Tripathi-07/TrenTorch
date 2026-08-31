"""
MC/DC coverage for ModuleTestCommand.run_integration_tests's test-file
deduplication decision (test_path.exists() and str(test_path) not in
relevant_tests), plus its stderr-display gate (shared with
run_module_pytest's identical copy).
"""

import subprocess
from pathlib import Path

from platforms.cli.core.config import CLIConfig
from platforms.cli.processes.module_workflow.test import ModuleTestCommand

TRENTORCH_ROOT = Path(__file__).resolve().parents[3]


def _run_with_fake_subprocess(monkeypatch, module_number, verbose=False):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="1 passed\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    cmd = ModuleTestCommand(CLIConfig.from_project_root(TRENTORCH_ROOT))
    cmd.run_integration_tests(module_number, verbose=verbose)
    return captured.get("cmd", [])


# ---------------------------------------------------------------------------
# test_path.exists() and str(test_path) not in relevant_tests
# ---------------------------------------------------------------------------


def test_a_file_shared_by_two_modules_is_only_included_once(monkeypatch):
    """Both module 12 and 13 map to test_nlp_pipeline_flow.py in the
    real integration_test_map: by module 13, that file has already been
    added once (from module 12's iteration) -- the "not in
    relevant_tests" half of the and prevents a duplicate on module 13's
    own iteration. A live, in-repo case rather than a synthetic one."""
    cmd = _run_with_fake_subprocess(monkeypatch, "13")

    nlp_entries = [c for c in cmd if str(c).endswith("test_nlp_pipeline_flow.py")]
    assert len(nlp_entries) == 1


def test_a_mapped_file_that_does_not_exist_on_disk_is_skipped(monkeypatch, tmp_path):
    """test_path.exists() False -> not added, regardless of dedup.
    Isolated by pointing config.project_root at an empty tmp_path (no
    tests/integration/*.py files actually exist there), so every mapped
    file for module 3 (test_layers_integration.py) fails the exists()
    check and the run short-circuits to the no-tests-found message."""
    (tmp_path / "tests" / "integration").mkdir(parents=True)
    cmd = ModuleTestCommand(CLIConfig.from_project_root(tmp_path))
    result_ok, message = cmd.run_integration_tests("03", verbose=False)

    assert result_ok is True
    assert "No relevant" in message


def test_each_uniquely_mapped_file_that_exists_is_included(monkeypatch):
    """Baseline for the and: exists() True, not a duplicate (first time
    this path is seen) -> included. test_layers_integration.py is only
    mapped once (module 3), so it appears exactly once regardless of
    dedup, confirming ordinary inclusion still works alongside the
    dedup check exercised above."""
    cmd = _run_with_fake_subprocess(monkeypatch, "05")

    layers_entries = [c for c in cmd if str(c).endswith("test_layers_integration.py")]
    dataloader_entries = [c for c in cmd if str(c).endswith("test_dataloader_integration.py")]
    assert len(layers_entries) == 1
    assert len(dataloader_entries) == 1


# ---------------------------------------------------------------------------
# result.stderr and verbose (shared shape between run_module_pytest and
# run_integration_tests)
# ---------------------------------------------------------------------------


def _run_integration_capturing_output(monkeypatch, capsys, *, verbose, stderr):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr=stderr)

    monkeypatch.setattr(subprocess, "run", fake_run)
    cmd = ModuleTestCommand(CLIConfig.from_project_root(TRENTORCH_ROOT))
    cmd.run_integration_tests("05", verbose=verbose)
    return capsys.readouterr().out


def test_stderr_shown_when_verbose_and_stderr_present(monkeypatch, capsys):
    """Baseline: stderr truthy, verbose True -> stderr printed."""
    out = _run_integration_capturing_output(monkeypatch, capsys, verbose=True, stderr="a warning from pytest")
    assert "a warning from pytest" in out


def test_stderr_hidden_when_not_verbose(monkeypatch, capsys):
    """stderr truthy, verbose False -> not printed. Paired with the
    baseline: only verbose differs, isolating that half of the and."""
    out = _run_integration_capturing_output(
        monkeypatch, capsys, verbose=False, stderr="a warning from pytest"
    )
    assert "a warning from pytest" not in out


def test_nothing_shown_when_stderr_is_empty_even_if_verbose(monkeypatch, capsys):
    """stderr falsy, verbose True -> nothing to print regardless. Paired
    with the baseline: only stderr's presence differs, isolating that
    half of the and."""
    out = _run_integration_capturing_output(monkeypatch, capsys, verbose=True, stderr="")
    assert out.strip() == ""
