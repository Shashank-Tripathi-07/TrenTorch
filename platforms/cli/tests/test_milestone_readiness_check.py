"""
MC/DC coverage for ModuleWorkflowCommand._check_milestone_readiness's
readiness decision: all_modules_done = all(m in completed_set for m in required),
tested with two required modules so each independently matters (a single-
element required list would make the all() trivially reduce to one check).
"""

from io import StringIO

import pytest
from rich.console import Console

import platforms.cli.processes.milestone as milestone_module
from platforms.cli.core.config import CLIConfig
from platforms.cli.processes.module_workflow.workflow import ModuleWorkflowCommand


@pytest.fixture
def workflow(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "user_data").mkdir(exist_ok=True)
    cmd = ModuleWorkflowCommand(CLIConfig.from_project_root(tmp_path))
    cmd.console = Console(file=StringIO(), width=200, no_color=True)
    return cmd


def _milestone():
    return {"name": "Test Milestone", "required_modules": [1, 2]}


def _readiness(workflow, monkeypatch, completed_modules):
    monkeypatch.setattr(milestone_module, "MILESTONE_SCRIPTS", {"1": _milestone()})
    return workflow._check_milestone_readiness(completed_modules)


def test_both_required_modules_completed_marks_ready(workflow, monkeypatch):
    """Baseline: both required modules (1 and 2) completed -> all() True
    -> milestone marked "ready"."""
    result = _readiness(workflow, monkeypatch, ["01", "02"])
    assert ("1", "Test Milestone", "ready") in result


def test_only_first_required_module_completed_is_not_ready(workflow, monkeypatch):
    """Only module 1 of [1, 2] completed -> all() False -> milestone not
    in the result at all (neither "ready" nor "unlocked"). Paired with
    the baseline: only module 2's completion differs, isolating its
    independent effect on the all()."""
    result = _readiness(workflow, monkeypatch, ["01"])
    assert not any(mid == "1" for mid, _, _ in result)


def test_only_second_required_module_completed_is_not_ready(workflow, monkeypatch):
    """Only module 2 of [1, 2] completed -> all() False. Paired with the
    baseline: only module 1's completion differs, isolating its
    independent effect, distinct from the previous test's isolation of
    module 1."""
    result = _readiness(workflow, monkeypatch, ["02"])
    assert not any(mid == "1" for mid, _, _ in result)


def test_neither_required_module_completed_is_not_ready(workflow, monkeypatch):
    """Neither required module completed -> all() False, same outcome as
    the single-module-missing cases but confirms the all() doesn't
    require exactly one missing item to short-circuit correctly."""
    result = _readiness(workflow, monkeypatch, [])
    assert not any(mid == "1" for mid, _, _ in result)


def test_already_completed_milestone_reports_unlocked_not_ready(workflow, monkeypatch):
    """A milestone already in completed_milestones.json is reported as
    "unlocked" regardless of all_modules_done, since that branch is
    checked first (elif all_modules_done is only reached when the
    milestone isn't already completed)."""
    milestones_file = workflow.config.project_root / "user_data" / "milestones.json"
    milestones_file.write_text('{"completed_milestones": ["1"]}', encoding="utf-8")

    result = _readiness(workflow, monkeypatch, ["01", "02"])
    assert ("1", "Test Milestone", "unlocked") in result
