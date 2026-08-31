"""
MC/DC coverage for milestone/system.py's MilestoneSystem.run_milestone_test
trigger-module check: a milestone can require both a set of completed
modules AND one specific "trigger" module (e.g. the module whose
capstone example actually demonstrates the milestone), checked
separately after the required-modules check passes.
"""

from platforms.cli.core.config import CLIConfig
from platforms.cli.processes.milestone.system import MilestoneSystem


def _system(tmp_path, monkeypatch, *, completed_modules: set[str]):
    system = MilestoneSystem(CLIConfig.from_project_root(tmp_path))
    system.MILESTONES = {
        "1": {
            "name": "Test Milestone",
            "required_modules": [],
            "trigger_module": "05",
        }
    }
    monkeypatch.setattr(system, "_is_module_completed", lambda mod: mod in completed_modules)
    return system


# ---------------------------------------------------------------------------
# trigger_module and not self._is_module_completed(trigger_module)
# ---------------------------------------------------------------------------


def test_trigger_module_present_and_completed_passes(tmp_path, monkeypatch):
    """Baseline: trigger_module truthy, _is_module_completed True -> "not
    completed" is False, the whole and is False -> passes this check."""
    system = _system(tmp_path, monkeypatch, completed_modules={"05"})
    result = system.run_milestone_test("1")
    assert result.get("error") != "Trigger module 05 not completed"


def test_trigger_module_present_but_not_completed_fails(tmp_path, monkeypatch):
    """trigger_module truthy, _is_module_completed False -> and is True
    -> fails with the trigger-specific error. Paired with the baseline:
    only completion differs, isolating that half of the and."""
    system = _system(tmp_path, monkeypatch, completed_modules=set())
    result = system.run_milestone_test("1")
    assert result["success"] is False
    assert "Trigger module 05 not completed" in result["error"]


def test_no_trigger_module_configured_skips_the_check_entirely(tmp_path, monkeypatch):
    """trigger_module falsy (empty string, milestone has none configured)
    -> short-circuits before ever calling _is_module_completed for a
    trigger. Paired with the baseline: only trigger_module's presence
    differs, isolating that half of the and from the completion check's
    independent effect."""
    system = _system(tmp_path, monkeypatch, completed_modules=set())
    system.MILESTONES["1"]["trigger_module"] = ""

    result = system.run_milestone_test("1")

    assert result.get("error") != "Trigger module  not completed"
    assert result["success"] is True
