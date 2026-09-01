"""
MC/DC coverage for PreflightCommand._output_rich's failure-detail
rendering: which failed checks get their stdout/stderr shown, and
whether stdout is shown when stderr already covers it.
"""

from io import StringIO

from rich.console import Console

from platforms.cli.cli_platform.dev.preflight import CheckCategory, CheckResult, CheckStatus, PreflightCommand
from platforms.cli.core.config import CLIConfig


def _render(tmp_path, checks):
    cmd = PreflightCommand(CLIConfig.from_project_root(tmp_path))
    buf = StringIO()
    cmd.console = Console(file=buf, width=120, no_color=True)
    category = CheckCategory(name="Test Category", emoji="🧪", checks=checks)
    cmd._output_rich(
        categories=[category],
        all_passed=False,
        duration=0.0,
        total_passed=0,
        total_failed=len(checks),
        total_warned=0,
        total_checks=len(checks),
        level="full",
        is_ci=False,
        verbose=False,
    )
    return buf.getvalue()


# ---------------------------------------------------------------------------
# check.status == CheckStatus.FAIL and (check.stdout or check.stderr)
# ---------------------------------------------------------------------------


def test_failed_check_with_stdout_shows_failure_detail(tmp_path):
    """Baseline: status FAIL True, stdout truthy -> detail block shown."""
    out = _render(tmp_path, [CheckResult(name="thing", status=CheckStatus.FAIL, stdout="some output")])
    assert "Failed: thing" in out


def test_failed_check_with_neither_stream_shows_nothing_extra(tmp_path):
    """status FAIL True, but stdout and stderr both empty -> "(stdout or
    stderr)" is False, the and is False, no detail block. Paired with
    the baseline: only the streams' emptiness differs, isolating that
    half of the and."""
    out = _render(tmp_path, [CheckResult(name="thing", status=CheckStatus.FAIL)])
    assert "Failed: thing" not in out


def test_passing_check_with_output_shows_nothing_extra(tmp_path):
    """status FAIL is False -> the and is False regardless of stdout/
    stderr content. Paired with the baseline: only status differs,
    isolating that half of the and."""
    out = _render(tmp_path, [CheckResult(name="thing", status=CheckStatus.PASS, stdout="some output")])
    assert "Failed: thing" not in out


# ---------------------------------------------------------------------------
# check.stdout and not check.stderr
# ---------------------------------------------------------------------------


def test_stdout_without_stderr_is_shown_as_output(tmp_path):
    """Baseline: stdout truthy, stderr falsy -> stdout shown under
    "Output (last lines)"."""
    out = _render(
        tmp_path, [CheckResult(name="thing", status=CheckStatus.FAIL, stdout="the real output here")]
    )
    assert "Output (last lines)" in out
    assert "the real output here" in out


def test_stdout_with_stderr_present_is_not_shown_as_output(tmp_path):
    """stdout truthy, stderr also truthy -> "not stderr" is False, the
    and is False -- stderr's own block is shown instead (already covers
    the failure), stdout is skipped to avoid duplicating it. Paired with
    the baseline: only stderr's presence differs, isolating that half of
    the and."""
    out = _render(
        tmp_path,
        [
            CheckResult(
                name="thing", status=CheckStatus.FAIL, stdout="stdout content", stderr="the real error"
            )
        ],
    )
    assert "Output (last lines)" not in out
    assert "Error:" in out
