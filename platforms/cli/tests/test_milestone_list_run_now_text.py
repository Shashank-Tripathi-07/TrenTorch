"""
MC/DC coverage for milestone/display.py's show_list "Run now" decision:
prereqs_met and not is_complete.
"""

import json
from io import StringIO

from rich.console import Console

import platforms.cli.processes.milestone.display as display_module
from platforms.cli.core.config import CLIConfig
from platforms.cli.processes.milestone.display import show_list


def _milestone(required_modules=None):
    return {
        "id": "1",
        "name": "Test",
        "emoji": "🎯",
        "title": "Test",
        "description": "Test",
        "historical_context": "None",
        "year": 1958,
        "required_modules": required_modules or [1],
    }


def _show_list(tmp_path, monkeypatch, *, completed_modules, completed_milestones, required_modules=None):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "user_data").mkdir(exist_ok=True)
    (tmp_path / "user_data" / "progress.json").write_text(
        json.dumps({"completed_modules": completed_modules}), encoding="utf-8"
    )
    (tmp_path / "user_data" / "milestones.json").write_text(
        json.dumps({"completed_milestones": completed_milestones}), encoding="utf-8"
    )
    monkeypatch.setattr(
        display_module, "MILESTONE_SCRIPTS", {"1": _milestone(required_modules=required_modules)}
    )

    from argparse import Namespace

    config = CLIConfig.from_project_root(tmp_path)
    buf = StringIO()
    console = Console(file=buf, width=120, no_color=True)
    show_list(config, console, Namespace(simple=False))
    return buf.getvalue()


def test_prereqs_met_and_not_complete_shows_run_now(tmp_path, monkeypatch):
    """Baseline: prereqs_met True, is_complete False -> "Run now" shown."""
    out = _show_list(tmp_path, monkeypatch, completed_modules=["01"], completed_milestones=[])
    assert "Run now" in out


def test_prereqs_met_but_already_complete_omits_run_now(tmp_path, monkeypatch):
    """prereqs_met True, is_complete True -> "not is_complete" False,
    the and is False -> no "Run now" text. Paired with the baseline:
    only is_complete differs, isolating that half of the and."""
    out = _show_list(tmp_path, monkeypatch, completed_modules=["01"], completed_milestones=["1"])
    assert "Run now" not in out


def test_prereqs_not_met_omits_run_now_and_shows_requirement(tmp_path, monkeypatch):
    """prereqs_met False -> the and is False regardless of is_complete
    (short-circuits). Paired with the baseline: only prereqs_met
    differs, isolating that half of the and. Falls to the elif branch
    instead, showing what's still required."""
    out = _show_list(tmp_path, monkeypatch, completed_modules=[], completed_milestones=[])
    assert "Run now" not in out
    assert "Required: Complete modules" in out


# ---------------------------------------------------------------------------
# prereqs_met's own all(): with a single required module (the tests above)
# this trivially reduces to one check. These use two required modules so
# each module's completion is shown to independently matter.
# ---------------------------------------------------------------------------


def test_both_required_modules_completed_is_prereqs_met(tmp_path, monkeypatch):
    """Baseline: both of two required modules completed -> prereqs_met
    True -> "Run now" shown."""
    out = _show_list(
        tmp_path,
        monkeypatch,
        completed_modules=["01", "02"],
        completed_milestones=[],
        required_modules=[1, 2],
    )
    assert "Run now" in out


def test_only_first_of_two_required_modules_completed_is_not_prereqs_met(tmp_path, monkeypatch):
    """Only module 1 of [1, 2] completed -> all() False. Paired with the
    baseline: only module 2's completion differs, isolating its
    independent effect."""
    out = _show_list(
        tmp_path, monkeypatch, completed_modules=["01"], completed_milestones=[], required_modules=[1, 2]
    )
    assert "Run now" not in out


def test_only_second_of_two_required_modules_completed_is_not_prereqs_met(tmp_path, monkeypatch):
    """Only module 2 of [1, 2] completed -> all() False. Paired with the
    baseline: only module 1's completion differs, isolating its
    independent effect, distinct from the previous test's isolation of
    module 2."""
    out = _show_list(
        tmp_path, monkeypatch, completed_modules=["02"], completed_milestones=[], required_modules=[1, 2]
    )
    assert "Run now" not in out
