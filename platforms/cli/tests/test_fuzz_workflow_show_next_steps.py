"""
Fuzz coverage for module_workflow/workflow.py's show_next_steps, batch 3
of the fuzz-testing survey (issue #72).

show_next_steps(completed_module: str) called int(completed_module) with
no guard. It isn't reachable from any real CLI code path today (every
caller of the complete workflow already validates the module number via
module_mapping before a point that would lead here -- confirmed by
grepping the codebase for callers: the only one is this file's own test),
but nothing at the function's own boundary enforces that, so a future
caller (or a refactor that removes the upstream guard) could hand it
unvalidated input and crash. Fixed defensively since the cost was two
lines and the alternative is a landmine with no test coverage of its own
input validation.
"""

from io import StringIO
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from rich.console import Console

from platforms.cli.core.config import CLIConfig
from platforms.cli.processes.module_workflow.workflow import ModuleWorkflowCommand

TRENTORCH_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def command():
    cmd = ModuleWorkflowCommand(CLIConfig.from_project_root(TRENTORCH_ROOT))
    cmd.console = Console(file=StringIO(), width=120, no_color=True)
    return cmd


@given(st.text())
@settings(max_examples=200)
def test_show_next_steps_never_raises(text):
    """Broad fuzz: no string handed to this should be able to crash it."""
    cmd = ModuleWorkflowCommand(CLIConfig.from_project_root(TRENTORCH_ROOT))
    cmd.console = Console(file=StringIO(), width=120, no_color=True)
    cmd.show_next_steps(text)  # must not raise


def test_show_next_steps_handles_non_numeric_module_id(command):
    """The concrete regression case: int() on a non-numeric string used
    to raise ValueError, uncaught, straight out of this function."""
    command.show_next_steps("not-a-number")  # must not raise


def test_show_next_steps_still_works_for_a_real_module(command):
    command.show_next_steps("01")
    out = command.console.file.getvalue()
    assert "Module 01" in out
