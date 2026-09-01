"""
MC/DC coverage for TrenMagics.exit's kernel-vs-process shutdown decision:
self.shell is not None and hasattr(self.shell, "kernel").

Extreme care here: the False branch of this decision calls os._exit(0),
a real, immediate process termination with no exception raised and no
chance for pytest to report anything -- getting the mock wrong would
silently kill the whole test run. os._exit is mocked before anything
else in every test in this file, and every other side-effecting call
(display, network, sleep) is mocked too so this magic method can be
exercised as a pure decision instead of the real notebook-teardown
sequence it drives in production.
"""

import os
import time
import urllib.request

import platforms.cli.jupyter_magic as jupyter_magic_module
from platforms.cli.jupyter_magic import TrenMagics


class _FakeKernel:
    def __init__(self):
        self.shutdown_called = False

    def do_shutdown(self, restart):
        self.shutdown_called = True


class _ShellWithKernel:
    def __init__(self):
        self.kernel = _FakeKernel()


class _ShellWithoutKernel:
    pass


def _exit_magic(monkeypatch, shell):
    # os._exit first, before anything else can go wrong.
    exit_calls = []
    monkeypatch.setattr(os, "_exit", lambda code: exit_calls.append(code))

    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    monkeypatch.setattr(jupyter_magic_module, "display", lambda *a, **k: None)
    monkeypatch.setattr(jupyter_magic_module, "_running_server", lambda: (None, None))
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: None)

    magic = TrenMagics(shell=shell)
    magic.exit("")
    return exit_calls


def test_shell_present_with_kernel_shuts_down_the_kernel_not_the_process(monkeypatch):
    """Baseline: shell is not None True, hasattr(shell, "kernel") True
    -> do_shutdown() called, os._exit never reached."""
    shell = _ShellWithKernel()
    exit_calls = _exit_magic(monkeypatch, shell)

    assert shell.kernel.shutdown_called is True
    assert exit_calls == []


def test_shell_present_without_kernel_falls_back_to_process_exit(monkeypatch):
    """shell is not None True, hasattr(shell, "kernel") False -> the and
    is False, falls to os._exit(0). Paired with the baseline: only the
    kernel attribute's presence differs, isolating that half of the and."""
    shell = _ShellWithoutKernel()
    exit_calls = _exit_magic(monkeypatch, shell)

    assert exit_calls == [0]


def test_no_shell_at_all_falls_back_to_process_exit(monkeypatch):
    """shell is not None is False -> the and is False regardless of any
    kernel attribute, short-circuits straight to os._exit(0). Paired
    with the baseline: only whether a shell exists differs, isolating
    that half of the and from the kernel-attribute check's independent
    effect."""
    exit_calls = _exit_magic(monkeypatch, shell=None)

    assert exit_calls == [0]
