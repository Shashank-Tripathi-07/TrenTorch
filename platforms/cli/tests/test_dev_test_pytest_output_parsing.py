"""
MC/DC coverage for the rest of dev/test.py's compound decisions: the
live-stream pytest-output classification inside _run_pytest (CI mode,
Popen-based), the non-CI summary-line detection, and the TREN_PROFILE
debug-timing print gates inside _run_inline_tests. test_dev_test_build_gate.py
already covers the Step-1 build gate in the same file.
"""

import subprocess
from pathlib import Path

import pytest

from platforms.cli.cli_platform.dev.export import DevExportCommand
from platforms.cli.cli_platform.dev.test import DevTestCommand
from platforms.cli.core.config import CLIConfig
from platforms.cli.processes.module_workflow.workflow import ModuleWorkflowCommand

TRENTORCH_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def command():
    return DevTestCommand(CLIConfig.from_project_root(TRENTORCH_ROOT))


class _FakeProcess:
    """Stands in for subprocess.Popen in CI-mode streaming: stdout is a
    plain list of lines (no real process), .wait() and .returncode are
    controllable directly."""

    def __init__(self, lines, returncode):
        self.stdout = iter(lines)
        self.returncode = returncode

    def wait(self, timeout=None):
        return self.returncode


def _run_ci_pytest(monkeypatch, capsys, lines, returncode=0):
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: _FakeProcess(lines, returncode))
    cmd = DevTestCommand(CLIConfig.from_project_root(TRENTORCH_ROOT))
    cmd._run_pytest(TRENTORCH_ROOT, "platforms/cli", "unit", verbose=False, ci_mode=True)
    return capsys.readouterr().out


# ---------------------------------------------------------------------------
# CI-mode streaming: "::" in line and (PASSED or FAILED or ERROR or SKIPPED)
# ---------------------------------------------------------------------------


def test_double_colon_and_passed_is_recognized_and_counted(monkeypatch, capsys):
    """Baseline: '::' present, ' PASSED' present -> counted, printed with a checkmark."""
    out = _run_ci_pytest(monkeypatch, capsys, ["tests/x.py::test_a PASSED"])
    assert "✓ test_a" in out


def test_no_double_colon_is_never_treated_as_a_result_line(monkeypatch, capsys):
    """'::' absent -> not treated as a result line regardless of the
    status word being present. Paired with the baseline: only '::'
    differs, isolating that condition."""
    out = _run_ci_pytest(monkeypatch, capsys, ["a stray PASSED mention, no path separator"])
    assert "✓" not in out and "✗" not in out


def test_double_colon_with_failed_is_counted_as_failed(monkeypatch, capsys):
    """Isolates the FAILED branch of the 4-way or."""
    out = _run_ci_pytest(monkeypatch, capsys, ["tests/x.py::test_b FAILED"], returncode=1)
    assert "✗ test_b" in out


def test_double_colon_with_error_is_counted_as_failed(monkeypatch, capsys):
    """Isolates the ERROR branch of the 4-way or."""
    out = _run_ci_pytest(monkeypatch, capsys, ["tests/x.py::test_c ERROR"], returncode=1)
    assert "! test_c" in out


def test_double_colon_with_skipped_is_counted_but_not_failed(monkeypatch, capsys):
    """Isolates the SKIPPED branch of the 4-way or."""
    out = _run_ci_pytest(monkeypatch, capsys, ["tests/x.py::test_d SKIPPED"])
    assert "- test_d" in out


def test_double_colon_with_no_status_word_is_not_a_result_line(monkeypatch, capsys):
    """'::' present but none of the four status words -> not a result
    line, falls through to the later elif chain instead. Paired with the
    baseline: only the status word's presence differs."""
    out = _run_ci_pytest(monkeypatch, capsys, ["tests/x.py::test_e COLLECTED"])
    assert "test_e" not in out


# ---------------------------------------------------------------------------
# CI-mode streaming: import-error debug line
#   "ImportError" in line or "ModuleNotFoundError" in line or "No module named" in line
# ---------------------------------------------------------------------------


def test_importerror_keyword_is_shown_for_debugging(monkeypatch, capsys):
    out = _run_ci_pytest(monkeypatch, capsys, ["ImportError: cannot import name 'Foo'"])
    assert ">>> ImportError: cannot import name 'Foo'" in out


def test_modulenotfounderror_keyword_is_shown(monkeypatch, capsys):
    """Isolates the second branch of the 3-way or."""
    out = _run_ci_pytest(monkeypatch, capsys, ["ModuleNotFoundError: no module named 'bar'"])
    assert ">>>" in out


def test_no_module_named_phrase_is_shown(monkeypatch, capsys):
    """Isolates the third branch of the 3-way or (the phrase, without
    either exception class name literally appearing)."""
    out = _run_ci_pytest(monkeypatch, capsys, ["No module named baz"])
    assert ">>> No module named baz" in out


def test_unrelated_line_is_not_shown_as_an_import_error(monkeypatch, capsys):
    """None of the three phrases present -> not shown via this branch.
    Paired with the tests above: only the phrase's presence differs."""
    out = _run_ci_pytest(monkeypatch, capsys, ["a perfectly ordinary log line"])
    assert ">>>" not in out


# ---------------------------------------------------------------------------
# CI-mode streaming: traceback-line detection, then its own nested filter
#   line.startswith("E ") or line.startswith("    ")
#   -> "import" in line.lower() or "module" in line.lower() or "not found" in line.lower()
# ---------------------------------------------------------------------------


def test_e_prefixed_line_with_import_keyword_is_shown(monkeypatch, capsys):
    """Outer: startswith('E ') True. Inner: 'import' present True -> shown."""
    out = _run_ci_pytest(monkeypatch, capsys, ["E   import error somewhere"])
    assert ">>> E   import error somewhere" in out


def test_indented_line_with_module_keyword_is_shown(monkeypatch, capsys):
    """Outer: startswith('    ') True (isolating the outer or's second
    half). Inner: 'module' present True."""
    out = _run_ci_pytest(monkeypatch, capsys, ["    the module could not load"])
    assert ">>>" in out


def test_e_prefixed_line_with_not_found_keyword_is_shown(monkeypatch, capsys):
    """Inner or's third branch: 'not found' present, isolated from
    'import'/'module' both being absent."""
    out = _run_ci_pytest(monkeypatch, capsys, ["E   resource not found here"])
    assert ">>>" in out


def test_e_prefixed_line_without_any_inner_keyword_is_not_shown(monkeypatch, capsys):
    """Outer True, but none of the inner keywords present -> not shown.
    Paired with the tests above: only the inner keywords' presence
    differs, isolating the inner decision from the outer one."""
    out = _run_ci_pytest(monkeypatch, capsys, ["E   assert 1 == 2"])
    assert ">>>" not in out


def test_unindented_non_e_line_is_never_checked_for_keywords(monkeypatch, capsys):
    """Outer False (neither prefix) -> the inner check never even runs,
    regardless of keyword content. Paired with the tests above: only the
    outer prefix's presence differs, isolating the outer or."""
    out = _run_ci_pytest(monkeypatch, capsys, ["this mentions import and module but has no prefix"])
    assert ">>>" not in out


# ---------------------------------------------------------------------------
# Non-CI mode: failure-summary line detection
#   "failed" in line.lower() or "error" in line.lower()
# ---------------------------------------------------------------------------


def _run_noci_pytest(monkeypatch, stdout, returncode=1):
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args, returncode=returncode, stdout=stdout, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    cmd = DevTestCommand(CLIConfig.from_project_root(TRENTORCH_ROOT))
    return cmd._run_pytest(TRENTORCH_ROOT, "platforms/cli", "unit", verbose=False, ci_mode=False)


def test_noci_summary_recognizes_failed_keyword(monkeypatch):
    """Baseline: 'failed' present (case-insensitively) -> used as the
    failure summary message."""
    result = _run_noci_pytest(monkeypatch, "2 Failed, 3 passed\n")
    assert "failed" in result.message.lower()


def test_noci_summary_recognizes_error_keyword(monkeypatch):
    """Isolates the second half of the or: 'error' present, 'failed'
    absent."""
    result = _run_noci_pytest(monkeypatch, "1 ERROR during collection\n")
    assert "error" in result.message.lower()


def test_noci_summary_falls_back_when_neither_keyword_present(monkeypatch):
    """Neither keyword present -> summary stays empty (the loop's break
    is never hit). Paired with the tests above: only keyword presence
    differs."""
    result = _run_noci_pytest(monkeypatch, "something went sideways, no recognizable keyword\n")
    assert result.message == "Tests failed"  # the loop's own summary stays empty; this is the outer default


# ---------------------------------------------------------------------------
# _run_inline_tests: the TREN_PROFILE debug-timing print gates
#   ci_mode and os.environ.get("TREN_PROFILE") == "1"
#   ci_mode and _profile_on   (same underlying env var, read once)
# ---------------------------------------------------------------------------


def _run_inline_one_module(monkeypatch, capsys, *, ci_mode, profile_env):
    monkeypatch.setattr(DevExportCommand, "_export_specific_modules", lambda self, modules, console: 0)
    monkeypatch.setattr(ModuleWorkflowCommand, "complete_module", lambda self, num, **kwargs: 0)
    if profile_env is None:
        monkeypatch.delenv("TREN_PROFILE", raising=False)
    else:
        monkeypatch.setenv("TREN_PROFILE", profile_env)

    cmd = DevTestCommand(CLIConfig.from_project_root(TRENTORCH_ROOT))
    cmd._run_inline_tests(TRENTORCH_ROOT, module="01", verbose=False, ci_mode=ci_mode)
    return capsys.readouterr().out


def test_profile_env_set_in_ci_mode_prints_timing(monkeypatch, capsys):
    """Baseline: ci_mode True, TREN_PROFILE=1 True -> both profiling
    print statements fire (export timing and complete-module timing,
    the two separate but identical-condition gates)."""
    out = _run_inline_one_module(monkeypatch, capsys, ci_mode=True, profile_env="1")
    assert "[TREN_PROFILE]" in out


def test_profile_env_unset_in_ci_mode_prints_nothing(monkeypatch, capsys):
    """ci_mode True, TREN_PROFILE unset -> neither gate fires. Paired
    with the baseline: only the env var differs, isolating it from
    ci_mode."""
    out = _run_inline_one_module(monkeypatch, capsys, ci_mode=True, profile_env=None)
    assert "[TREN_PROFILE]" not in out


def test_profile_env_set_but_not_ci_mode_prints_nothing(monkeypatch, capsys):
    """TREN_PROFILE=1, ci_mode False -> neither gate fires even though
    the env var is set, since both prints are inside `if ci_mode:`
    blocks entirely (ci_mode False means the print statements aren't
    even reached to check the env var). Paired with the baseline: only
    ci_mode differs, isolating it from the env var."""
    out = _run_inline_one_module(monkeypatch, capsys, ci_mode=False, profile_env="1")
    assert "[TREN_PROFILE]" not in out
