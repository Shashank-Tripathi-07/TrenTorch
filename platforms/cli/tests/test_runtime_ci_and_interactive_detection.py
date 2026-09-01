"""
MC/DC coverage for core/runtime.py's is_ci() and is_interactive() -- the
module's own docstring documents a real historical bug this split fixed
(sys.stdin.isatty() alone silently broke progress sync for real students
on Windows Git Bash/MinTTY). is_ci()'s any() is a generator expression
over os.environ.get(var), a shape neither AST scan in this pass's earlier
sweeps would have matched (they only matched any()/all() over a literal
list/tuple), found by hand while looking at this file specifically.
"""

import sys

import pytest

from platforms.cli.core.runtime import _CI_ENV_VARS, is_ci, is_interactive

# ---------------------------------------------------------------------------
# is_ci(): any(os.environ.get(var) for var in _CI_ENV_VARS), 7 atoms
# ---------------------------------------------------------------------------


def _clear_all_ci_vars(monkeypatch):
    for var in _CI_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_none_of_the_seven_ci_vars_set_is_not_ci(monkeypatch):
    """Baseline: every CI env var unset -> is_ci() False."""
    _clear_all_ci_vars(monkeypatch)
    assert is_ci() is False


@pytest.mark.parametrize("var", _CI_ENV_VARS)
def test_each_ci_var_alone_is_sufficient(monkeypatch, var):
    """Each of the seven env vars, set alone with the other six unset,
    independently makes is_ci() True. Paired with the baseline: only
    this one var's presence differs each time, isolating it from the
    other six atoms in the any()."""
    _clear_all_ci_vars(monkeypatch)
    monkeypatch.setenv(var, "1")
    assert is_ci() is True


# ---------------------------------------------------------------------------
# is_interactive(): not is_ci() and stdin.isatty() and stdout.isatty()
# ---------------------------------------------------------------------------


def test_interactive_terminal_outside_ci_is_interactive(monkeypatch):
    """Baseline: not is_ci() True, both isatty() True -> interactive."""
    _clear_all_ci_vars(monkeypatch)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    assert is_interactive() is True


def test_ci_environment_is_never_interactive_even_with_real_ttys(monkeypatch):
    """is_ci() True -> "not is_ci()" False, short-circuits to non-
    interactive regardless of real ttys (the exact conflation the
    module's docstring warns against, tested the other direction: CI
    must win over a genuinely interactive-looking terminal). Paired with
    the baseline: only is_ci()'s value differs, isolating that half."""
    monkeypatch.setenv("CI", "true")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    assert is_interactive() is False


def test_non_tty_stdin_outside_ci_is_not_interactive(monkeypatch):
    """not is_ci() True, stdin.isatty() False -> not interactive
    (the Windows Git Bash / MinTTY case the module docstring exists to
    describe). Paired with the baseline: only stdin's tty status
    differs, isolating that condition from is_ci()'s independent
    effect."""
    _clear_all_ci_vars(monkeypatch)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    assert is_interactive() is False


def test_non_tty_stdout_outside_ci_is_not_interactive(monkeypatch):
    """not is_ci() True, stdin.isatty() True, stdout.isatty() False ->
    not interactive. Paired with the baseline: only stdout's tty status
    differs, isolating that condition."""
    _clear_all_ci_vars(monkeypatch)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    assert is_interactive() is False


def test_closed_stream_is_treated_as_not_interactive(monkeypatch):
    """A stream whose isatty() raises (closed/replaced, e.g. by a test
    harness) is caught and treated as non-interactive rather than
    propagating -- the deliberately conservative fallback the
    docstring names explicitly."""
    _clear_all_ci_vars(monkeypatch)

    def raising_isatty():
        raise ValueError("I/O operation on closed file")

    monkeypatch.setattr(sys.stdin, "isatty", raising_isatty)
    assert is_interactive() is False
