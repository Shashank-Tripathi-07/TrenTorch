"""
Fuzz coverage for dev/test.py's _run_pytest CI-mode live-streaming
test-name extraction, batch 2 of the fuzz-testing survey (issue #72).

Found by fuzzing: `line.split("::")[-1].split()[0]` raised IndexError
whenever the text after the last "::" was empty or all-whitespace (e.g.
"tests/x.py::   PASSED" -- unusual but not something pytest's own output
format actually guarantees never happens, since this only checks "::" is
present anywhere in the line and " PASSED"/" FAILED"/" ERROR"/" SKIPPED"
appears, not that a real test id follows the last "::").

This is caught by _run_pytest's own outer `except Exception`, so it
doesn't crash the CLI -- but it does silently truncate live CI test
streaming mid-run, replacing real test-by-test visibility with a generic
"list index out of range" TestResult failure. Confirmed via mutation
testing (reverting the fix reproduces exactly that truncation) before
fixing.
"""

import subprocess
from pathlib import Path
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

from platforms.cli.cli_platform.dev.test import DevTestCommand
from platforms.cli.core.config import CLIConfig

TRENTORCH_ROOT = Path(__file__).resolve().parents[3]


class _FakeProcess:
    def __init__(self, lines, returncode=0):
        self.stdout = iter(lines)
        self.returncode = returncode

    def wait(self, timeout=None):
        return self.returncode


def _run_ci_pytest(lines):
    """Uses unittest.mock.patch as a context manager (not the monkeypatch
    fixture) so this is safe to call from inside a Hypothesis @given body
    -- monkeypatch is function-scoped and doesn't reset between generated
    examples, which Hypothesis flags as a health-check failure."""
    with patch.object(subprocess, "Popen", lambda *a, **k: _FakeProcess(lines)):
        cmd = DevTestCommand(CLIConfig.from_project_root(TRENTORCH_ROOT))
        return cmd._run_pytest(TRENTORCH_ROOT, "platforms/cli", "unit", verbose=False, ci_mode=True)


def test_line_with_nothing_after_the_last_colons_does_not_crash_streaming(capsys):
    """The concrete regression case: "::" present, " PASSED" present
    (the outer guard only checks these appear *somewhere* in the line,
    not that the marker follows the last "::"), and the text after the
    line's *last* "::" is empty. " PASSED::" satisfies both: the marker
    comes before the trailing "::", so splitting on "::" leaves nothing
    after it. Before the fix, this IndexError'd out of the whole
    streaming loop -- every line after it in the same pytest run went
    unreported, and the TestResult's message became the raw exception
    text instead of a real summary."""
    result = _run_ci_pytest([" PASSED::", "tests/y.py::test_after PASSED"])
    out = capsys.readouterr().out
    assert "list index out of range" not in (result.message or "")
    # The line *after* the malformed one must still have been processed --
    # this is the actual symptom of the bug, not just "didn't raise".
    assert "test_after" in out


@given(st.lists(st.text(), max_size=6))
@settings(max_examples=200)
def test_run_pytest_ci_streaming_never_crashes_on_arbitrary_lines(lines):
    """Broad fuzz: whatever subprocess stdout throws at the live-stream
    parser, _run_pytest itself must return a TestResult (it always did --
    there's an outer except Exception), AND that result's message must
    never be a raw Python exception string leaking an internal parsing
    detail to the user instead of a real test summary. That second
    assertion is the one that actually distinguishes "fixed" from
    "merely doesn't crash the process" -- the bug this file exists for
    was already caught by the outer except before the fix; what it
    didn't do was avoid corrupting the reported outcome."""
    result = _run_ci_pytest(lines)
    assert result is not None
    assert hasattr(result, "passed")
    assert "index out of range" not in (result.message or "")


# Structured strategy that actually contains the markers the parser looks
# for ("::", " PASSED"/" FAILED"/" ERROR"/" SKIPPED"), so fuzzing reaches
# the real test-name-extraction branch instead of only the early-exit path.
# The " PASSED::"-shaped entries are the ones that actually trigger the
# original bug: the marker appears *before* the line's last "::", so
# splitting on "::" leaves nothing after it to extract a name from.
_MARKER_LINE = st.sampled_from(
    [
        "tests/x.py::test_a PASSED",
        "tests/x.py:: PASSED",
        "tests/x.py::   PASSED",
        "::PASSED",
        " PASSED::",
        " FAILED::",
        " ERROR::",
        " SKIPPED::",
        "a::b::c FAILED",
        "no colons here PASSED",
        "tests/x.py::test_b ERROR",
        "tests/x.py::test_c SKIPPED",
    ]
)


@given(st.lists(_MARKER_LINE, max_size=8))
@settings(max_examples=200)
def test_run_pytest_ci_streaming_handles_marker_soup(lines):
    result = _run_ci_pytest(lines)
    assert result is not None
    assert "index out of range" not in (result.message or "")
