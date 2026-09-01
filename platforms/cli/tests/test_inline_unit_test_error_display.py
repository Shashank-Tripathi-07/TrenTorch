"""
Regression coverage for issue #76 / PR #77: `tren module complete` showing
a truncated traceback with no actual error message on a failed unit test.

PR #77 fixed `_parse_test_output`'s `concise_error` to keep the *last* 5
lines of a traceback instead of the first 5 (a traceback's exception
type/message is always its last line). That fix was real and necessary,
but on its own it didn't actually resolve the reported symptom: the
verbose console-print loop in `run_inline_unit_tests` (the code path
`tren module complete` actually runs through) re-slices the already-
fixed error string with the identical bug -- `error_lines[:3]` instead
of `error_lines[-3:]` -- so the message got truncated a second time,
downstream of the first fix. Confirmed live before the second fix: an
unsolved-module repro through the real console-print path still showed
zero lines of the actual exception, only call-stack frames, with only
the `_parse_test_output` half of the fix applied.

This test exercises the real, full path (a genuinely unsolved notebook,
executed through runpy exactly as a student's `tren module complete`
would) and asserts on the actual printed console output, not just the
internal data structure -- the existing test_test_runner_result_reporting.py
and test_fuzz_text_parsers.py coverage only checked _parse_test_output's
return value, which is exactly why this bug survived a first fix attempt.
"""

import json
from io import StringIO

from rich.console import Console

from platforms.cli.core.config import CLIConfig
from platforms.cli.processes.module_workflow.test_runner import run_inline_unit_tests

_UNSOLVED_NOTEBOOK = {
    "cells": [
        {
            "cell_type": "code",
            "source": [
                "class Tensor:\n",
                "    def __init__(self, data):\n",
                '        raise NotImplementedError("TODO: implement Tensor.__init__")\n',
                "\n",
                "def test_creation():\n",
                "    t = Tensor(5.0)\n",
                "    assert t is not None\n",
                "\n",
                "test_creation()\n",
            ],
            "metadata": {},
            "outputs": [],
            "execution_count": None,
        }
    ],
    "metadata": {},
    "nbformat": 4,
    "nbformat_minor": 5,
}


def test_unsolved_module_shows_the_actual_exception_message(tmp_path, monkeypatch):
    """The concrete regression case for issue #76: a student's unsolved
    stub must surface its real NotImplementedError message on the
    console, not just the call-stack frames leading up to it."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TREN_DEV_VERIFY_SOLUTION", raising=False)

    module_dir = tmp_path / "data" / "modules" / "01_tensor"
    module_dir.mkdir(parents=True)
    (module_dir / "tensor.ipynb").write_text(json.dumps(_UNSOLVED_NOTEBOOK), encoding="utf-8")

    buf = StringIO()
    console = Console(file=buf, width=120, no_color=True)
    config = CLIConfig.from_project_root(tmp_path)

    result = run_inline_unit_tests(config, console, "01_tensor", verbose=True)
    out = buf.getvalue()

    assert result["failed"] == 1
    assert "NotImplementedError: TODO: implement Tensor.__init__" in out
