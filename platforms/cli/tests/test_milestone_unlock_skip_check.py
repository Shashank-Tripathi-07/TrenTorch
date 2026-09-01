"""
MC/DC coverage for check_and_run_milestone_unlocks's "already handled"
skip check: milestone_id in unlocked or milestone_id in completed_milestones.
"""

import json
from io import StringIO

from rich.console import Console

import platforms.cli.processes.milestone.system as system_module
from platforms.cli.core.config import CLIConfig
from platforms.cli.processes.milestone.command import MilestoneCommand
from platforms.cli.processes.milestone.system import check_and_run_milestone_unlocks


def _run(tmp_path, monkeypatch, *, unlocked, completed_milestones, module_completed):
    (tmp_path / "user_data").mkdir(exist_ok=True)
    (tmp_path / "user_data" / "progress.json").write_text(
        json.dumps({"completed_modules": module_completed}), encoding="utf-8"
    )
    (tmp_path / "user_data" / "milestones.json").write_text(
        json.dumps({"unlocked_milestones": unlocked, "completed_milestones": completed_milestones}),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        system_module,
        "MILESTONE_SCRIPTS",
        {"1": {"name": "Test", "description": "Test", "required_modules": [1]}},
    )
    monkeypatch.setattr(MilestoneCommand, "_handle_run_command", lambda self, args: 0)

    config = CLIConfig.from_project_root(tmp_path)
    console = Console(file=StringIO(), width=120, no_color=True)
    check_and_run_milestone_unlocks(config, console)

    return json.loads((tmp_path / "user_data" / "milestones.json").read_text(encoding="utf-8"))


def test_not_yet_unlocked_or_completed_and_requirements_met_gets_unlocked(tmp_path, monkeypatch):
    """Baseline: neither half of the or is True -> the skip is not hit,
    requirements are checked, and (met here) the milestone is newly
    unlocked."""
    result = _run(tmp_path, monkeypatch, unlocked=[], completed_milestones=[], module_completed=["01"])
    assert "1" in result["unlocked_milestones"]


def test_already_unlocked_is_skipped_without_reunlocking(tmp_path, monkeypatch):
    """milestone_id in unlocked True -> skipped via continue, before
    even checking requirements. Paired with the baseline: only whether
    it's already unlocked differs, isolating that half of the or.
    (unlock_dates should stay untouched -- nothing "newly" happened.)"""
    result = _run(tmp_path, monkeypatch, unlocked=["1"], completed_milestones=[], module_completed=["01"])
    assert result["unlocked_milestones"] == ["1"]
    assert "unlock_dates" not in result or "1" not in result.get("unlock_dates", {})


def test_already_completed_is_skipped_without_rerunning(tmp_path, monkeypatch):
    """milestone_id in completed_milestones True -> also skipped.
    Paired with the baseline: only whether it's already completed
    differs, isolating that half of the or from "already unlocked"'s
    independent effect."""
    result = _run(tmp_path, monkeypatch, unlocked=[], completed_milestones=["1"], module_completed=["01"])
    assert "1" not in result.get("unlocked_milestones", [])
