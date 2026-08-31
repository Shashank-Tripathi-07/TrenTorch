"""
MC/DC coverage for the rest of status_analyzer.py's compound decisions.
test_status_analyzer_environment.py already covers check_environment's
venv-detection decision.
"""

import subprocess

from platforms.cli.core.status_analyzer import ModuleStatus, TinyTorchStatusAnalyzer

# ---------------------------------------------------------------------------
# ModuleStatus.overall_status: two threshold-and-flag decisions
#   compliance_score >= 0.9 and runs_without_errors  -> EXCELLENT
#   compliance_score >= 0.7 and imports_successfully  -> GOOD
# ---------------------------------------------------------------------------


def _status(compliance_flags: int, **overrides) -> ModuleStatus:
    """compliance_score is computed from how many of 6 boolean
    "has_*" checks are true (docstring elsewhere: a straight fraction),
    so build a status with exactly `compliance_flags` of them set to hit
    a specific score threshold precisely."""
    flags = [
        "has_introduction",
        "has_math_background",
        "has_implementation",
        "has_testing",
        "has_ml_systems_questions",
        "has_summary",
    ]
    kwargs = {flags[i]: True for i in range(compliance_flags)}
    base = {"has_dev_file": True, "imports_successfully": True}
    base.update(kwargs)
    base.update(overrides)
    return ModuleStatus(name="x", path=None, **base)


def test_high_compliance_and_runs_without_errors_is_excellent():
    """Baseline: compliance>=0.9 True, runs_without_errors True ->
    EXCELLENT."""
    status = _status(6, runs_without_errors=True)  # 6/6 = 1.0
    assert status.compliance_score >= 0.9
    assert status.overall_status == "EXCELLENT"


def test_high_compliance_but_errors_falls_through_to_good():
    """compliance>=0.9 True, runs_without_errors False -> not EXCELLENT;
    falls to the next check (compliance>=0.7 and imports_successfully,
    both true here) -> GOOD. Paired with the baseline: only
    runs_without_errors differs, isolating that half of the first and."""
    status = _status(6, runs_without_errors=False)
    assert status.overall_status == "GOOD"


def test_moderate_compliance_with_imports_is_good():
    """First check's compliance threshold is False (0.7-0.89 range) so
    it never reaches runs_without_errors; second check's compliance
    threshold True -> GOOD.

    This second check used to also require `and self.imports_successfully`,
    but that condition can never be False by the time this line runs --
    an earlier `if not self.imports_successfully: return "BROKEN"` guard
    already rules it out -- so it was dead code with no independent
    effect on this decision, fixed (not just tested) while writing this
    file's MC/DC pass turned it up as genuinely untestable-as-compound."""
    status = _status(5, runs_without_errors=True)  # 5/6 ≈ 0.83
    assert 0.7 <= status.compliance_score < 0.9
    assert status.overall_status == "GOOD"


def test_low_compliance_falls_to_partial():
    """compliance below 0.7 (but >= 0.4) -> PARTIAL, the next check
    down. Confirms the boundary the fixed GOOD check now guards
    correctly on its own."""
    status = _status(3, runs_without_errors=True)  # 3/6 = 0.5
    assert 0.4 <= status.compliance_score < 0.7
    assert status.overall_status == "PARTIAL"


# ---------------------------------------------------------------------------
# analyze_module: dev-file discovery loop
#   possible_file and possible_file.exists()
# ---------------------------------------------------------------------------


def test_dev_file_found_at_exact_module_name(tmp_path, monkeypatch):
    """Baseline: possible_file is not None and it exists (the exact
    "<module_name>.py" candidate) -> found there, first in the list."""
    module_dir = tmp_path / "01_tensor"
    module_dir.mkdir()
    (module_dir / "01_tensor.py").write_text("x = 1\n", encoding="utf-8")

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, "SUCCESS", ""))
    analyzer = TinyTorchStatusAnalyzer(repo_path=tmp_path)
    status = analyzer.analyze_module(module_dir)

    assert status.has_dev_file is True


def test_dev_file_none_candidate_is_skipped_without_crashing(tmp_path, monkeypatch):
    """When the module name has no "_", the second candidate expression
    (module_name.split("_", 1)[1]...) itself evaluates to None rather
    than raising -- so "possible_file and ..." short-circuits on None
    cleanly. Confirms that half of the and (the None-check) actually
    matters, not just exists()."""
    module_dir = tmp_path / "orphan"
    module_dir.mkdir()
    (module_dir / "orphan.py").write_text("x = 1\n", encoding="utf-8")

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, "SUCCESS", ""))
    analyzer = TinyTorchStatusAnalyzer(repo_path=tmp_path)
    status = analyzer.analyze_module(module_dir)

    assert status.has_dev_file is True


def test_no_matching_dev_file_falls_back_to_any_py_file(tmp_path, monkeypatch):
    """Neither named candidate exists -> falls through to the *.py glob
    fallback. Paired with the baseline: neither candidate's exists()
    check succeeds this time, isolating that half of the and."""
    module_dir = tmp_path / "01_tensor"
    module_dir.mkdir()
    (module_dir / "some_other_name.py").write_text("x = 1\n", encoding="utf-8")

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, "SUCCESS", ""))
    analyzer = TinyTorchStatusAnalyzer(repo_path=tmp_path)
    status = analyzer.analyze_module(module_dir)

    assert status.has_dev_file is True


# ---------------------------------------------------------------------------
# analyze_module: import-error issue recording
#   not status.imports_successfully and result.stderr
# ---------------------------------------------------------------------------


def _analyze_with_fake_subprocess(tmp_path, monkeypatch, stdout, stderr, returncode=0):
    module_dir = tmp_path / "01_tensor"
    module_dir.mkdir()
    (module_dir / "01_tensor.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, returncode, stdout, stderr)
    )
    analyzer = TinyTorchStatusAnalyzer(repo_path=tmp_path)
    return analyzer.analyze_module(module_dir)


def test_import_failure_with_stderr_records_an_issue(tmp_path, monkeypatch):
    """Baseline: imports_successfully False, stderr truthy -> an "Import
    error: ..." issue is recorded."""
    status = _analyze_with_fake_subprocess(
        tmp_path, monkeypatch, stdout="ERROR: boom", stderr="Traceback: real error text"
    )
    assert any("Import error" in issue for issue in status.issues)


def test_import_success_with_stderr_records_no_issue(tmp_path, monkeypatch):
    """imports_successfully True (despite stderr having content, e.g. a
    stray warning) -> no issue recorded. Paired with the baseline: only
    imports_successfully differs, isolating that half of the and."""
    status = _analyze_with_fake_subprocess(
        tmp_path, monkeypatch, stdout="SUCCESS: Module imports and runs", stderr="a harmless warning"
    )
    assert not any("Import error" in issue for issue in status.issues)


def test_import_failure_with_no_stderr_records_no_issue(tmp_path, monkeypatch):
    """imports_successfully False, but stderr empty -> no issue recorded
    (nothing to report). Paired with the first baseline: only stderr's
    presence differs, isolating the other half of the and."""
    status = _analyze_with_fake_subprocess(tmp_path, monkeypatch, stdout="ERROR: boom", stderr="")
    assert not any("Import error" in issue for issue in status.issues)


# ---------------------------------------------------------------------------
# _print_detailed_module_status: code-health symbol
#   module.imports_successfully and module.runs_without_errors
# ---------------------------------------------------------------------------


def _render_code_health(tmp_path, imports_successfully: bool, runs_without_errors: bool) -> str:
    from io import StringIO

    from rich.console import Console

    analyzer = TinyTorchStatusAnalyzer(repo_path=tmp_path)
    analyzer.modules = {
        "01_tensor": ModuleStatus(
            name="01_tensor",
            path=tmp_path,
            has_dev_file=True,
            imports_successfully=imports_successfully,
            runs_without_errors=runs_without_errors,
        )
    }
    buf = StringIO()
    console = Console(file=buf, width=200, no_color=True)
    analyzer._print_detailed_module_status(console)
    return buf.getvalue()


def test_imports_and_runs_cleanly_shows_the_healthy_symbol(tmp_path):
    """Baseline: both True -> the healthiest code-health cell."""
    out = _render_code_health(tmp_path, imports_successfully=True, runs_without_errors=True)
    assert "✅" in out


def test_imports_but_does_not_run_cleanly_shows_a_warning(tmp_path):
    """imports True, runs False -> the middle symbol. Paired with the
    baseline: only runs_without_errors differs, isolating that half of
    the and."""
    out = _render_code_health(tmp_path, imports_successfully=True, runs_without_errors=False)
    assert "⚠️" in out


def test_does_not_import_shows_the_unhealthy_symbol_regardless_of_runs(tmp_path):
    """imports False -> the worst symbol regardless of runs_without_errors
    (never even reaches that check, short-circuited). Paired with the
    baseline: only imports_successfully differs, isolating that half."""
    out = _render_code_health(tmp_path, imports_successfully=False, runs_without_errors=True)
    assert "❌" in out
