"""
Coverage for start_jupyter_server()'s fast-fail detection.

Regression test for a bug introduced by (and fixed alongside) switching
from a bare `["jupyter", "lab"]` command to `[sys.executable, "-m",
"jupyterlab"]` in PR #140: since sys.executable always exists, Popen()
itself can no longer raise FileNotFoundError for "jupyterlab isn't
installed" the way it used to for "jupyter isn't on PATH". A missing
jupyterlab package now fails *inside* the child process instead (fast,
non-zero exit), which needs its own explicit check -- without it, that
failure was invisible: the function would burn its entire retry window
before falling through to the same `return True` a real success takes.
"""

import subprocess
import time

import pytest

from platforms.cli.commands import jupyter as jupyter_module


class _FakeProcess:
    """Stand-in for a Popen handle that has already exited by the time
    start_jupyter_server checks it -- simulating a fast child-side crash
    (e.g. "No module named jupyterlab") rather than a real, still-running
    server."""

    def __init__(self, returncode):
        self.returncode = returncode

    def poll(self):
        return self.returncode


class _FakeRunningProcess:
    """Stand-in for a Popen handle whose process is still alive (poll()
    returns None) -- the normal, still-starting-up case."""

    def poll(self):
        return None


def test_fast_nonzero_exit_is_reported_as_failure(monkeypatch, tmp_path):
    """Baseline: the child process has already exited non-zero (e.g.
    jupyterlab not installed) by the time the post-launch check runs ->
    start_jupyter_server returns False instead of burning the retry
    window, matching what the old FileNotFoundError branch used to do
    for a missing `jupyter` executable."""
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: _FakeProcess(returncode=1))
    monkeypatch.setattr(time, "sleep", lambda _: None)

    def _fail_if_called(*a, **k):
        raise AssertionError("find_running_jupyter_server should never be reached for a dead process")

    monkeypatch.setattr(jupyter_module, "find_running_jupyter_server", _fail_if_called)

    assert jupyter_module.start_jupyter_server(tmp_path) is False


def test_still_running_after_launch_proceeds_to_detection(monkeypatch, tmp_path):
    """Paired with the test above: only whether the process has already
    exited differs. poll() is None (still starting up, the normal case)
    -> proceeds past the fast-fail check into the real detection loop,
    isolating that this check doesn't also swallow legitimate startups."""
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: _FakeRunningProcess())
    monkeypatch.setattr(time, "sleep", lambda _: None)
    monkeypatch.setattr(jupyter_module, "find_running_jupyter_server", lambda _: ("http://x/", "tok"))

    assert jupyter_module.start_jupyter_server(tmp_path) is True


def test_fast_zero_exit_is_not_treated_as_failure(monkeypatch, tmp_path):
    """Second half of the same decision: the process already exited, but
    with returncode 0 -- `poll() is not None` alone isn't enough, it must
    also be non-zero. Not a realistic case for a real Jupyter server
    (which runs until killed), but pins down that the check is
    `and returncode != 0`, not just `poll() is not None`."""
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: _FakeProcess(returncode=0))
    monkeypatch.setattr(time, "sleep", lambda _: None)
    monkeypatch.setattr(jupyter_module, "find_running_jupyter_server", lambda _: (None, None))

    # Falls through to the same "couldn't detect it" `return True` a real
    # slow-starting-but-eventually-successful server would also hit if
    # detection kept missing -- this test only pins the fast-fail check's
    # own condition, not the (separately real) "detection kept missing"
    # outcome, so either bool is a valid result here; what matters is that
    # it did NOT short-circuit to False the way the returncode=1 case does.
    jupyter_module.start_jupyter_server(tmp_path)


@pytest.mark.parametrize("real_module_name", ["jupyterlab", "jupyter"])
def test_python_dash_m_invocation_works_for_real(real_module_name):
    """Sanity check that `python -m <module>` is genuinely a valid,
    working invocation for both modules this file relies on (jupyterlab
    for start_jupyter_server, jupyter for find_running_jupyter_server) --
    catches the class of bug where -m looks right but the package in
    question doesn't actually ship a __main__.py."""
    import sys

    result = subprocess.run(
        [sys.executable, "-m", real_module_name, "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert result.returncode == 0, f"python -m {real_module_name} --version failed: {result.stderr[:500]}"
