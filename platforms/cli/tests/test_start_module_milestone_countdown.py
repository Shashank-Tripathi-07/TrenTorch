"""
MC/DC coverage for ModuleWorkflowCommand.start_module's "modules until
unlock" computation:
    modules_left = len([r for r in required if r not in completed_nums])

This started as a 2-atom "r not in completed_nums and r >= module_num".
Writing the independent-isolation test for "r >= module_num" showed it's
dead: the prerequisite check a few lines above already returns 1 if any
module before module_num is incomplete, so any required r < module_num is
guaranteed already in completed_nums by the time this line runs. Fixed by
dropping the redundant half rather than testing an unreachable branch.
"""

from io import StringIO

import pytest
from rich.console import Console

import platforms.cli.processes.module_workflow.workflow as workflow_module
from platforms.cli.core.config import CLIConfig
from platforms.cli.processes.module_workflow.workflow import ModuleWorkflowCommand


@pytest.fixture
def workflow(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cmd = ModuleWorkflowCommand(CLIConfig.from_project_root(tmp_path))
    cmd.console = Console(file=StringIO(), width=200, no_color=True)
    return cmd


def _start(workflow, monkeypatch, *, module_mapping, completed, required, module_num):
    monkeypatch.setattr(workflow_module, "get_module_mapping", lambda: module_mapping)
    monkeypatch.setattr(
        workflow_module.ModuleWorkflowCommand,
        "_get_milestone_for_module",
        lambda self, num: ("1", "Test Milestone", required),
    )
    workflow.save_progress_data({"completed_modules": completed, "started_modules": []})

    normalized = f"{module_num:02d}"
    module_name = module_mapping[normalized]
    module_dir = workflow.config.project_root / "data" / "modules" / module_name
    module_dir.mkdir(parents=True)
    short_name = module_name.split("_", 1)[1]
    (module_dir / f"{short_name}.ipynb").write_text("{}", encoding="utf-8")

    buf = StringIO()
    workflow.console = Console(file=buf, width=200, no_color=True)
    workflow.start_module(normalized, no_jupyter=True)
    return buf.getvalue()


def _mapping(up_to: int) -> dict:
    return {f"{i:02d}": f"{i:02d}_module{i}" for i in range(1, up_to + 1)}


def test_uncompleted_required_module_counts_toward_countdown(workflow, monkeypatch):
    """Baseline: for required module r, r not in completed_nums True ->
    counted, shown since modules_left <= 3. (required must include
    module_num itself: the milestone row only prints when
    "module_num in required" is True.)"""
    out = _start(workflow, monkeypatch, module_mapping=_mapping(3), completed=[], required=[1], module_num=1)
    assert "1 modules until unlock" in out


def test_completed_required_module_does_not_count(workflow, monkeypatch):
    """r not in completed_nums False (it's already completed) -> not
    counted. Paired with the baseline: only whether r is in
    completed_nums differs, isolating that half of the and."""
    out = _start(
        workflow, monkeypatch, module_mapping=_mapping(3), completed=["01"], required=[1], module_num=1
    )
    assert "0 modules until unlock" in out


def test_multiple_uncompleted_required_modules_all_count(workflow, monkeypatch):
    """Two required modules, neither completed -> both counted
    independently (confirms the filter isn't just checking "any", it
    genuinely counts each element)."""
    out = _start(
        workflow, monkeypatch, module_mapping=_mapping(3), completed=[], required=[1, 2], module_num=1
    )
    assert "2 modules until unlock" in out
