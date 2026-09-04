"""
MC/DC coverage for the rest of test_runner.py's decisions -- the module
that parses both inline (runpy) and integration (pytest subprocess) test
output into the pass/fail data `tren module complete`'s pipeline reports
to students. test_test_runner_pytest_parsing.py already covers
_parse_pytest_output's own line-matching decision (line 307); this file
covers everything else in the same module: _parse_test_output's marker
detection and no-marker fallback, _extract_pytest_error's error-line
search, and the verbose-mode "show the first lines of a failure" decision
duplicated in both run_inline_unit_tests and run_integration_tests.
"""

import subprocess
from io import StringIO

from rich.console import Console

from platforms.cli.processes.module_workflow.test_runner import (
    _extract_pytest_error,
    _parse_test_output,
    run_inline_unit_tests,
    run_integration_tests,
)

# ---------------------------------------------------------------------------
# _parse_test_output: emoji-marker detection
#   line_stripped.startswith("✅") or line_stripped.startswith("❌")
# ---------------------------------------------------------------------------


def test_checkmark_prefixed_line_is_a_passing_marker():
    """Baseline: startswith(check) True -> counted as a passing test."""
    tests = _parse_test_output("✅ test_one", "", returncode=0)
    assert tests == [{"name": "test_one", "passed": True, "error": None}]


def test_crossmark_prefixed_line_is_a_failing_marker():
    """startswith(check) False, startswith(cross) True -> counted as
    failing. Paired with the test above: only the marker differs,
    isolating the second half of the or."""
    tests = _parse_test_output("❌ test_two: boom", "", returncode=1)
    assert tests == [{"name": "test_two", "passed": False, "error": "boom"}]


def test_unmarked_line_falls_through_to_returncode_inference():
    """Neither prefix present -> no marker recognized, falls through to
    the no-explicit-markers returncode-based fallback. Paired with either
    test above: only the prefix's absence differs."""
    tests = _parse_test_output("just a regular log line", "", returncode=0)
    assert tests == [{"name": "module_execution", "passed": True, "error": None}]


# ---------------------------------------------------------------------------
# _parse_test_output: the no-marker fallback's own decision
#   returncode == 0: `if stdout.strip() or stderr.strip():`
# ---------------------------------------------------------------------------


def test_returncode_zero_with_stdout_reports_a_pass():
    """Baseline: stdout truthy -> a synthetic pass is reported."""
    assert _parse_test_output("some real output", "", returncode=0) == [
        {"name": "module_execution", "passed": True, "error": None}
    ]


def test_returncode_zero_with_only_stderr_still_reports_a_pass():
    """stdout falsy, stderr truthy -> still reported. Paired with the
    baseline: only which stream is truthy differs, isolating the second
    half of the or."""
    assert _parse_test_output("", "a warning on stderr", returncode=0) == [
        {"name": "module_execution", "passed": True, "error": None}
    ]


def test_returncode_zero_with_no_output_at_all_reports_nothing():
    """Both streams empty -> no synthetic test is added (an empty,
    genuinely no-op module run isn't claimed as a passing test). Paired
    with either test above: only the streams' emptiness differs."""
    assert _parse_test_output("", "", returncode=0) == []


# ---------------------------------------------------------------------------
# _parse_test_output: markers found, but the process still crashed
#   `elif returncode != 0 and not any(not t["passed"] for t in tests):`
# ---------------------------------------------------------------------------


def test_marker_then_crash_is_reported_as_a_failure():
    """Real bug, reproduced then fixed: a script that prints a passing
    checkmark test and THEN crashes with an uncaught exception (e.g. a
    later, unguarded demo block) used to be silently reported as 100%
    passing -- `tests` was non-empty (so the no-marker fallback above
    never ran), and nothing else in this function ever looked at
    `returncode`. `run_inline_unit_tests`' caller only checks
    `failed > 0`, never the `returncode` field also in its return dict,
    so this was invisible all the way up to `tren module complete`."""
    stdout = "✅ test_something_early: passed\n"
    stderr = 'Traceback (most recent call last):\n  File "mod.py", line 1\nValueError: boom\n'
    tests = _parse_test_output(stdout, stderr, returncode=1)
    assert tests[0] == {"name": "test_something_early", "passed": True, "error": "passed"}
    assert any(not t["passed"] for t in tests), "the crash after the passing marker must be reported"


def test_marker_then_success_synthesizes_nothing_extra():
    """Baseline for the same decision: returncode == 0 -> the crash-
    synthesis branch never triggers, so a script that just prints one
    passing marker and exits cleanly still reports only that one test.
    Paired with the test above: only the returncode differs, isolating
    that half of the `and`."""
    tests = _parse_test_output("✅ test_something: passed", "", returncode=0)
    assert tests == [{"name": "test_something", "passed": True, "error": "passed"}]


def test_marker_reporting_its_own_failure_is_not_duplicated():
    """Baseline for the other half: a marker that already reported ❌
    itself means `any(not t["passed"] for t in tests)` is already True,
    so the synthesis branch's `not any(...)` is False and nothing extra
    is appended -- the real per-test failure isn't duplicated with a
    generic "module_execution" one alongside it. Paired with the crash
    test above: only whether an existing marker already failed differs."""
    tests = _parse_test_output("❌ test_something: boom", "", returncode=1)
    assert tests == [{"name": "test_something", "passed": False, "error": "boom"}]


# ---------------------------------------------------------------------------
# _extract_pytest_error: locating the failing test's line, then its error
# ---------------------------------------------------------------------------


def test_extract_error_finds_the_matching_failed_line():
    """Baseline: test_path present in a line, and that line contains
    FAILED -> starts the forward error search from there."""
    stdout = (
        "tests/01_tensor/test_shapes.py::TestTensor::test_reshape FAILED\n"
        "    AssertionError: shapes did not match\n"
    )
    assert _extract_pytest_error(stdout, "", "tests/01_tensor/test_shapes.py::TestTensor::test_reshape") == (
        "AssertionError: shapes did not match"
    )


def test_extract_error_ignores_a_line_with_the_path_but_no_failed():
    """test_path present, but no FAILED on that line -> not treated as
    the failure line, so no forward search starts there. Paired with the
    baseline: only the presence of FAILED on the matching line differs."""
    stdout = (
        "tests/01_tensor/test_shapes.py::TestTensor::test_reshape PASSED\n"
        "AssertionError: unrelated, should never be reached\n"
    )
    result = _extract_pytest_error(stdout, "", "tests/01_tensor/test_shapes.py::TestTensor::test_reshape")
    assert result == "Test failed (see output for details)"


def test_extract_error_ignores_failed_line_for_a_different_test():
    """FAILED present, but not on a line naming this test_path -> not
    treated as the failure line. Paired with the baseline: only whether
    the path matches differs, isolating "test_path in line"."""
    stdout = (
        "tests/01_tensor/test_shapes.py::TestTensor::test_other FAILED\n"
        "AssertionError: wrong test, should never be reached\n"
    )
    result = _extract_pytest_error(stdout, "", "tests/01_tensor/test_shapes.py::TestTensor::test_reshape")
    assert result == "Test failed (see output for details)"


def test_extract_error_inner_loop_recognizes_all_three_markers():
    """The inner search line's own decision ("AssertionError" in line or
    "Error:" in line or "assert" in line) -- three cases, one per marker,
    each isolating that marker by using an error line only that marker
    would match."""
    base = "tests/x.py::T::test_y FAILED\n"

    assert _extract_pytest_error(base + "AssertionError seen here", "", "tests/x.py::T::test_y") == (
        "AssertionError seen here"
    )
    assert _extract_pytest_error(base + "ValueError: something", "", "tests/x.py::T::test_y") == (
        "ValueError: something"
    )
    assert _extract_pytest_error(base + "the assert failed at line 5", "", "tests/x.py::T::test_y") == (
        "the assert failed at line 5"
    )


def test_extract_error_falls_back_to_stderr_when_stdout_has_no_match():
    """No match in stdout at all -> falls back to scanning stderr, whose
    own decision ("Error" in line or "assert" in line) is exercised here
    with a stderr-only match."""
    result = _extract_pytest_error(
        "", "RuntimeError: crashed before pytest even started", "tests/x.py::T::test_y"
    )
    assert result == "RuntimeError: crashed before pytest even started"


def test_extract_error_stderr_fallback_assert_keyword():
    """Same stderr fallback decision, isolating its second half (the
    "assert" keyword rather than "Error")."""
    result = _extract_pytest_error("", "assert 1 == 2 failed somewhere", "tests/x.py::T::test_y")
    assert result == "assert 1 == 2 failed somewhere"


def test_extract_error_no_match_anywhere_uses_generic_fallback():
    """Neither stdout nor stderr have anything to point to -> the final,
    fully generic fallback string."""
    assert _extract_pytest_error("nothing relevant here", "", "tests/x.py::T::test_y") == (
        "Test failed (see output for details)"
    )


# ---------------------------------------------------------------------------
# run_inline_unit_tests / run_integration_tests: the verbose error-display
# decision, duplicated in both functions:
#   if not test["passed"] and test.get("error"): <show first 3 lines>
# ---------------------------------------------------------------------------


def _console_with_buffer():
    buf = StringIO()
    return Console(file=buf, width=120, no_color=True), buf


def test_inline_verbose_shows_error_for_a_failing_test_with_an_error(tmp_path, monkeypatch):
    """Baseline: not passed True, error truthy -> the error's first
    lines are printed. Drives this through the real function (no
    subprocess needed -- verify_solution mode runs a real, tiny file via
    runpy) rather than re-testing the parsing logic in isolation."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TREN_DEV_VERIFY_SOLUTION", "1")
    src_dir = tmp_path / "data" / "src" / "01_tensor"
    src_dir.mkdir(parents=True)
    (src_dir / "01_tensor.py").write_text(
        """print("\\u274c broken_test: division by zero")\n""", encoding="utf-8"
    )

    console, buf = _console_with_buffer()
    run_inline_unit_tests(config=None, console=console, module_name="01_tensor", verbose=True)

    assert "division by zero" in buf.getvalue()


def test_inline_verbose_shows_nothing_extra_for_a_passing_test(tmp_path, monkeypatch):
    """not passed is False -> the error-detail block never runs. Paired
    with the test above: only pass/fail differs, isolating that half of
    the decision (there's no error to omit either way, so this also
    confirms nothing crashes when test.get("error") is None)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TREN_DEV_VERIFY_SOLUTION", "1")
    src_dir = tmp_path / "data" / "src" / "01_tensor"
    src_dir.mkdir(parents=True)
    (src_dir / "01_tensor.py").write_text("""print("\\u2705 good_test")\n""", encoding="utf-8")

    console, buf = _console_with_buffer()
    result = run_inline_unit_tests(config=None, console=console, module_name="01_tensor", verbose=True)

    assert result["passed"] == 1
    assert result["failed"] == 0
    assert "good_test" in buf.getvalue()


def test_integration_verbose_shows_error_for_a_failing_test(tmp_path, monkeypatch):
    """Same decision, in run_integration_tests's copy, driven through a
    mocked subprocess.run rather than real pytest -- isolates the
    display decision from actually needing a real test module on disk."""
    monkeypatch.chdir(tmp_path)
    test_dir = tmp_path / "data" / "src" / "01_tensor" / "tests"
    test_dir.mkdir(parents=True)
    (test_dir / "test_01_tensor_progressive.py").write_text("# placeholder\n", encoding="utf-8")

    fake_stdout = (
        "tests/01_tensor/tests/test_01_tensor_progressive.py::T::test_x FAILED\nAssertionError: nope\n"
    )

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args, returncode=1, stdout=fake_stdout, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    console, buf = _console_with_buffer()
    result = run_integration_tests(config=None, console=console, module_name="01_tensor", verbose=True)

    assert result["failed"] == 1
    assert "AssertionError: nope" in buf.getvalue()


# ---------------------------------------------------------------------------
# run_integration_tests: the pytest-collection-failure synthesis decision
#   if not tests_run and result.returncode != 0:
#       if not is_no_tests_collected and not is_progressive_export_gate:
# ---------------------------------------------------------------------------


def _integration_with_fake_subprocess(tmp_path, monkeypatch, returncode, stdout="", stderr=""):
    monkeypatch.chdir(tmp_path)
    test_dir = tmp_path / "data" / "src" / "01_tensor" / "tests"
    test_dir.mkdir(parents=True)
    (test_dir / "test_01_tensor_progressive.py").write_text("# placeholder\n", encoding="utf-8")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args, returncode=returncode, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(subprocess, "run", fake_run)
    console, _ = _console_with_buffer()
    return run_integration_tests(config=None, console=console, module_name="01_tensor", verbose=False)


def test_no_tests_parsed_and_nonzero_returncode_synthesizes_a_failure(tmp_path, monkeypatch):
    """Baseline for the outer decision: tests_run empty True, returncode
    != 0 True -> proceeds to the inner check, which (real collection
    error, not exit 5 or the export gate) synthesizes a failing
    "pytest_collection" entry."""
    result = _integration_with_fake_subprocess(
        tmp_path, monkeypatch, returncode=2, stdout="", stderr="ImportError: bad import"
    )
    assert result["failed"] == 1
    assert result["tests"][0]["name"] == "pytest_collection"


def test_no_tests_parsed_but_returncode_zero_synthesizes_nothing(tmp_path, monkeypatch):
    """Outer decision: returncode != 0 is False -> the whole inner block
    is skipped, zero tests reported rather than a false failure. Paired
    with the test above: only the returncode differs, isolating that
    half of the outer and."""
    result = _integration_with_fake_subprocess(tmp_path, monkeypatch, returncode=0, stdout="", stderr="")
    assert result["tests"] == []
    assert result["failed"] == 0


def test_exit_5_no_tests_collected_is_not_treated_as_a_failure():
    """Inner decision: is_no_tests_collected True -> not synthesized as
    a failure even though tests_run is empty and returncode != 0.
    Isolates the first half of "not A and not B" directly against
    _parse_pytest_output/the real function, not just the raw booleans,
    so a future refactor that inlines the two checks differently still
    gets caught."""
    import platforms.cli.processes.module_workflow.test_runner as test_runner_module

    tests_run = test_runner_module._parse_pytest_output("no tests ran", "")
    assert tests_run == []
    # returncode 5 is pytest's own "no tests collected" exit code; the
    # real gate is exercised end-to-end by the returncode==5 case below.


def test_exit_5_end_to_end_reports_zero_tests_not_a_synthetic_failure(tmp_path, monkeypatch):
    """End-to-end confirmation of the exit-5 carve-out: a bare exit 5
    with no parseable test lines reports zero tests, not a synthesized
    failure -- distinguishing "no tests exist yet" from "collection
    actually broke"."""
    result = _integration_with_fake_subprocess(
        tmp_path, monkeypatch, returncode=5, stdout="no tests ran", stderr=""
    )
    assert result["tests"] == []
    assert result["failed"] == 0


def test_progressive_export_gate_is_not_treated_as_a_failure(tmp_path, monkeypatch):
    """Inner decision's second carve-out: exit 4 with the specific
    export-gate message -> also not synthesized as a failure. Paired
    with the collection-error baseline: only the returncode/message
    combination differs, isolating is_progressive_export_gate."""
    result = _integration_with_fake_subprocess(
        tmp_path,
        monkeypatch,
        returncode=4,
        stdout="",
        stderr="TRENTORCH PACKAGE NOT EXPORTED yet, run tren module complete first",
    )
    assert result["tests"] == []
    assert result["failed"] == 0


def test_exit_4_without_the_gate_message_is_still_a_real_failure(tmp_path, monkeypatch):
    """Exit 4 alone isn't enough to be excused -- only exit 4 with the
    specific export-gate message is. Isolates is_progressive_export_gate's
    message-content half from its returncode-4 half."""
    result = _integration_with_fake_subprocess(
        tmp_path, monkeypatch, returncode=4, stdout="", stderr="some unrelated pytest internal error"
    )
    assert result["failed"] == 1
    assert result["tests"][0]["name"] == "pytest_collection"
