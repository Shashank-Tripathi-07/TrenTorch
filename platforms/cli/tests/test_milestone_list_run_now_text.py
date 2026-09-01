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


def _milestone():
    return {
        "id": "1",
        "name": "Test",
        "emoji": "🎯",
        "title": "Test",
        "description": "Test",
        "historical_context": "None",
        "year": 1958,
        "required_modules": [1],
    }


def _show_list(tmp_path, monkeypatch, *, completed_modules, completed_milestones):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "user_data").mkdir(exist_ok=True)
    (tmp_path / "user_data" / "progress.json").write_text(
        json.dumps({"completed_modules": completed_modules}), encoding="utf-8"
    )
    (tmp_path / "user_data" / "milestones.json").write_text(
        json.dumps({"completed_milestones": completed_milestones}), encoding="utf-8"
    )
    monkeypatch.setattr(display_module, "MILESTONE_SCRIPTS", {"1": _milestone()})

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
