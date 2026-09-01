"""
MC/DC coverage for milestone/display.py's show_info copy of the
prereqs_met all() -- the same shape already covered for show_list's copy
in test_milestone_list_run_now_text.py. Uses two required modules so
each module's completion independently matters (a single-element list
would make the all() trivially reduce to one check).
"""

import json
from io import StringIO

from rich.console import Console

import platforms.cli.processes.milestone.display as display_module
from platforms.cli.core.config import CLIConfig
from platforms.cli.processes.milestone.display import show_info


def _milestone(required_modules):
    return {
        "id": "1",
        "name": "Test",
        "emoji": "🎯",
        "title": "Test",
        "description": "Test",
        "historical_context": "None",
        "year": 1958,
        "required_modules": required_modules,
        "script": "test.py",
    }


def _show_info(tmp_path, monkeypatch, *, completed_modules, required_modules):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "user_data").mkdir(exist_ok=True)
    (tmp_path / "user_data" / "progress.json").write_text(
        json.dumps({"completed_modules": completed_modules}), encoding="utf-8"
    )
    monkeypatch.setattr(display_module, "MILESTONE_SCRIPTS", {"1": _milestone(required_modules)})

    from argparse import Namespace

    config = CLIConfig.from_project_root(tmp_path)
    buf = StringIO()
    console = Console(file=buf, width=120, no_color=True)
    show_info(config, console, Namespace(milestone_id="1"))
    return buf.getvalue()


def test_both_required_modules_completed_shows_ready_to_run(tmp_path, monkeypatch):
    """Baseline: both required modules completed -> prereqs_met True ->
    "Ready to run!" shown."""
    out = _show_info(tmp_path, monkeypatch, completed_modules=["01", "02"], required_modules=[1, 2])
    assert "Ready to run!" in out
    assert "Locked" not in out


def test_only_first_required_module_completed_shows_locked(tmp_path, monkeypatch):
    """Only module 1 of [1, 2] completed -> all() False -> "Locked"
    shown, module 2 listed as still needed. Paired with the baseline:
    only module 2's completion differs, isolating its independent
    effect on the all()."""
    out = _show_info(tmp_path, monkeypatch, completed_modules=["01"], required_modules=[1, 2])
    assert "Locked" in out
    assert "Ready to run!" not in out
    assert "Complete modules: 02" in out


def test_only_second_required_module_completed_shows_locked(tmp_path, monkeypatch):
    """Only module 2 of [1, 2] completed -> all() False -> "Locked"
    shown, module 1 listed as still needed. Paired with the baseline:
    only module 1's completion differs, isolating its independent
    effect, distinct from the previous test's isolation of module 1."""
    out = _show_info(tmp_path, monkeypatch, completed_modules=["02"], required_modules=[1, 2])
    assert "Locked" in out
    assert "Ready to run!" not in out
    assert "Complete modules: 01" in out
