"""
MC/DC coverage for MilestoneSystem.get_milestone_status's can_unlock
computation (a 3-atom and) and the "first eligible milestone becomes
next_milestone" selection built on top of it.
"""

import json

from platforms.cli.core.config import CLIConfig
from platforms.cli.processes.milestone.system import MilestoneSystem


def _system(tmp_path, monkeypatch, milestones, *, completed_modules=None, unlocked=None):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "user_data").mkdir(exist_ok=True)
    (tmp_path / "user_data" / "progress.json").write_text(
        json.dumps({"completed_modules": completed_modules or []}), encoding="utf-8"
    )
    if unlocked:
        (tmp_path / "user_data" / "milestones.json").write_text(
            json.dumps({"unlocked_milestones": unlocked, "completed_milestones": []}), encoding="utf-8"
        )

    system = MilestoneSystem(CLIConfig.from_project_root(tmp_path))
    system.MILESTONES = milestones
    return system


def _milestone(required_modules=None, trigger_module=""):
    return {
        "name": "Test",
        "title": "Test",
        "required_modules": required_modules or [],
        "trigger_module": trigger_module,
    }


# ---------------------------------------------------------------------------
# can_unlock = required_complete and trigger_complete and not is_unlocked
# ---------------------------------------------------------------------------


def test_all_three_conditions_true_can_unlock(tmp_path, monkeypatch):
    """Baseline: required_complete True, trigger_complete True,
    is_unlocked False -> can_unlock True."""
    system = _system(
        tmp_path,
        monkeypatch,
        {"1": _milestone(required_modules=[1], trigger_module="02")},
        completed_modules=["01", "02"],
    )
    status = system.get_milestone_status()
    assert status["milestones"]["1"]["can_unlock"] is True


def test_required_incomplete_blocks_unlock(tmp_path, monkeypatch):
    """required_complete False -> can_unlock False. Paired with the
    baseline: only required-module completion differs, isolating that
    condition."""
    system = _system(
        tmp_path,
        monkeypatch,
        {"1": _milestone(required_modules=[1], trigger_module="02")},
        completed_modules=["02"],  # module 01 (required) not completed
    )
    status = system.get_milestone_status()
    assert status["milestones"]["1"]["can_unlock"] is False


def test_trigger_incomplete_blocks_unlock(tmp_path, monkeypatch):
    """trigger_complete False -> can_unlock False. Paired with the
    baseline: only the trigger module's completion differs, isolating
    that condition."""
    system = _system(
        tmp_path,
        monkeypatch,
        {"1": _milestone(required_modules=[1], trigger_module="02")},
        completed_modules=["01"],  # trigger module 02 not completed
    )
    status = system.get_milestone_status()
    assert status["milestones"]["1"]["can_unlock"] is False


def test_already_unlocked_blocks_can_unlock(tmp_path, monkeypatch):
    """is_unlocked True -> "not is_unlocked" False -> can_unlock False,
    even though both other conditions are satisfied. Paired with the
    baseline: only is_unlocked differs, isolating that condition."""
    system = _system(
        tmp_path,
        monkeypatch,
        {"1": _milestone(required_modules=[1], trigger_module="02")},
        completed_modules=["01", "02"],
        unlocked=["1"],
    )
    status = system.get_milestone_status()
    assert status["milestones"]["1"]["can_unlock"] is False


# ---------------------------------------------------------------------------
# elif milestone_status["can_unlock"] and not status["next_milestone"]
# ---------------------------------------------------------------------------


def test_first_eligible_milestone_becomes_next(tmp_path, monkeypatch):
    """Two milestones both eligible to unlock -> only the first one
    encountered (dict iteration order) becomes next_milestone; the
    second's can_unlock True doesn't overwrite it, because
    next_milestone is already set by then."""
    system = _system(
        tmp_path,
        monkeypatch,
        {
            "1": _milestone(required_modules=[1]),
            "2": _milestone(required_modules=[1]),
        },
        completed_modules=["01"],
    )
    status = system.get_milestone_status()
    assert status["milestones"]["1"]["can_unlock"] is True
    assert status["milestones"]["2"]["can_unlock"] is True
    assert status["next_milestone"] == "1"


def test_no_eligible_milestone_leaves_next_milestone_none(tmp_path, monkeypatch):
    """can_unlock False for every milestone -> next_milestone stays
    None. Paired with the test above: only whether any milestone is
    eligible differs, isolating can_unlock's effect on this selection."""
    system = _system(
        tmp_path,
        monkeypatch,
        {"1": _milestone(required_modules=[1])},
        completed_modules=[],
    )
    status = system.get_milestone_status()
    assert status["milestones"]["1"]["can_unlock"] is False
    assert status["next_milestone"] is None
