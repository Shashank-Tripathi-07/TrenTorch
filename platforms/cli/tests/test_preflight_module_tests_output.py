"""
MC/DC coverage for PreflightCommand._check_module_tests's failure-message
extraction: "failed" in line.lower() or "error" in line.lower().
"""

from platforms.cli.cli_platform.dev.preflight import CheckStatus, PreflightCommand
from platforms.cli.core.config import CLIConfig


def _module_tests_check(tmp_path, monkeypatch, stdout):
    (tmp_path / "tests" / "01_tensor").mkdir(parents=True)
    cmd = PreflightCommand(CLIConfig.from_project_root(tmp_path))
    monkeypatch.setattr(cmd, "_run_command", lambda *a, **k: (1, stdout, ""))
    category = cmd._check_module_tests(tmp_path, quick=True, verbose=False)
    return next(c for c in category.checks if c.name == "Module 01 tests")


def test_failed_keyword_is_recognized(tmp_path, monkeypatch):
    """Baseline: 'failed' present (case-insensitively) -> used as the
    failure message."""
    check = _module_tests_check(tmp_path, monkeypatch, "2 Failed, 3 passed\n")
    assert check.status == CheckStatus.FAIL
    assert "failed" in check.message.lower()


def test_error_keyword_is_recognized(tmp_path, monkeypatch):
    """Isolates the second half of the or: 'error' present, 'failed'
    absent."""
    check = _module_tests_check(tmp_path, monkeypatch, "CollectionERROR during import\n")
    assert check.status == CheckStatus.FAIL
    assert "error" in check.message.lower()


def test_neither_keyword_falls_back_to_generic_message(tmp_path, monkeypatch):
    """Neither keyword present -> falls back to the generic "Tests
    failed" default. Paired with the tests above: only keyword presence
    differs."""
    check = _module_tests_check(tmp_path, monkeypatch, "something went sideways\n")
    assert check.status == CheckStatus.FAIL
    assert check.message == "Tests failed"
