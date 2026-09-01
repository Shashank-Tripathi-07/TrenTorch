"""
MC/DC coverage for MilestoneCommand._handle_run_command's part-selection,
default-part, missing-modules-part-text, and interactive-prompt decisions.
"""

import subprocess
import sys
from argparse import Namespace
from io import StringIO

from rich.console import Console

import platforms.cli.processes.milestone.command as command_module
from platforms.cli.core.config import CLIConfig
from platforms.cli.processes.milestone.command import MilestoneCommand


def _args(**overrides):
    defaults = {"milestone_id": "01", "part": None, "skip_checks": True}
    defaults.update(overrides)
    return Namespace(**defaults)


_BANNER_FIELDS = {
    "emoji": "🚀",
    "name": "Test Milestone",
    "title": "A Test Milestone",
    "historical_context": "None",
    "description": "Test",
    "year": 1958,
}


def _setup(tmp_path, monkeypatch, milestone_factory, *, run_returncode=0):
    """milestone_factory(script_a_path, script_b_path) -> milestone dict
    (banner-display fields merged in automatically)."""
    script_a = str(tmp_path / "script_a.py")
    script_b = str(tmp_path / "script_b.py")
    (tmp_path / "script_a.py").write_text("", encoding="utf-8")
    (tmp_path / "script_b.py").write_text("", encoding="utf-8")

    milestone = {**_BANNER_FIELDS, **milestone_factory(script_a, script_b)}
    monkeypatch.setattr(command_module, "MILESTONE_SCRIPTS", {"01": milestone})
    monkeypatch.setattr(command_module, "MILESTONE_ALIASES", {})

    captured = {"scripts": []}

    def fake_run(cmd, **kwargs):
        captured["scripts"].append(cmd[1])
        return subprocess.CompletedProcess(cmd, returncode=run_returncode)

    monkeypatch.setattr(subprocess, "run", fake_run)

    cmd = MilestoneCommand(CLIConfig.from_project_root(tmp_path))
    buf = StringIO()
    cmd.console = Console(file=buf, width=120, no_color=True)
    return cmd, buf, captured, script_a, script_b


# ---------------------------------------------------------------------------
# args.part < 1 or args.part > len(all_scripts)
# ---------------------------------------------------------------------------


def test_part_within_range_runs_that_script(tmp_path, monkeypatch):
    """Baseline: part >= 1 and part <= len(scripts) -> neither half of
    the or is True, valid part selected and run."""
    cmd, buf, captured, script_a, script_b = _setup(
        tmp_path,
        monkeypatch,
        lambda a, b: {"scripts": [{"name": "A", "script": a}, {"name": "B", "script": b}]},
    )

    cmd._handle_run_command(_args(part=2))

    assert captured["scripts"] == [script_b]
    assert "Invalid part number" not in buf.getvalue()


def test_part_zero_is_below_range(tmp_path, monkeypatch):
    """part < 1 True -> the or is True, invalid-part error. Paired with
    the baseline: only part's lower-bound violation differs, isolating
    that half of the or."""
    cmd, buf, captured, script_a, script_b = _setup(
        tmp_path, monkeypatch, lambda a, b: {"scripts": [{"name": "A", "script": a}]}
    )

    result = cmd._handle_run_command(_args(part=0))

    assert result == 1
    assert "Invalid part number" in buf.getvalue()
    assert captured["scripts"] == []


def test_part_beyond_range_is_above_range(tmp_path, monkeypatch):
    """part > len(scripts) True -> the or is True, invalid-part error.
    Paired with the baseline: only part's upper-bound violation differs,
    isolating that half of the or."""
    cmd, buf, captured, script_a, script_b = _setup(
        tmp_path, monkeypatch, lambda a, b: {"scripts": [{"name": "A", "script": a}]}
    )

    result = cmd._handle_run_command(_args(part=5))

    assert result == 1
    assert "Invalid part number" in buf.getvalue()
    assert captured["scripts"] == []


# ---------------------------------------------------------------------------
# default_part is not None and 1 <= default_part <= len(all_scripts)
# ---------------------------------------------------------------------------


def test_valid_default_part_is_used_when_no_part_flag_given(tmp_path, monkeypatch):
    """Baseline: default_part not None True, in-range True -> that part
    runs automatically."""
    cmd, buf, captured, script_a, script_b = _setup(
        tmp_path,
        monkeypatch,
        lambda a, b: {
            "scripts": [{"name": "A", "script": a}, {"name": "B", "script": b}],
            "default_part": 2,
        },
    )

    cmd._handle_run_command(_args(part=None))

    assert captured["scripts"] == [script_b]


def test_no_default_part_configured_runs_all_scripts(tmp_path, monkeypatch):
    """default_part is not None is False (absent) -> short-circuits,
    falls to running every script. Paired with the baseline: only the
    presence of default_part differs, isolating that half of the and."""
    cmd, buf, captured, script_a, script_b = _setup(
        tmp_path,
        monkeypatch,
        lambda a, b: {"scripts": [{"name": "A", "script": a}, {"name": "B", "script": b}]},
    )

    cmd._handle_run_command(_args(part=None))

    assert captured["scripts"] == [script_a, script_b]


def test_default_part_above_range_falls_back_to_all_scripts(tmp_path, monkeypatch):
    """default_part not None True, upper bound violated (default_part <=
    len(all_scripts) is False) -> the and is False, falls to running
    every script. Paired with the first baseline: only the upper-bound
    check differs, isolating that half of the chained comparison."""
    cmd, buf, captured, script_a, script_b = _setup(
        tmp_path,
        monkeypatch,
        lambda a, b: {
            "scripts": [{"name": "A", "script": a}, {"name": "B", "script": b}],
            "default_part": 99,
        },
    )

    cmd._handle_run_command(_args(part=None))

    assert captured["scripts"] == [script_a, script_b]


def test_default_part_below_range_falls_back_to_all_scripts(tmp_path, monkeypatch):
    """default_part not None True, lower bound violated (1 <=
    default_part is False, e.g. 0 or negative) -> the and is False,
    falls to running every script. Paired with the baseline: only the
    lower-bound check differs, isolating the other half of the chained
    comparison -- distinct from the above-range test, which only
    isolated the upper bound."""
    cmd, buf, captured, script_a, script_b = _setup(
        tmp_path,
        monkeypatch,
        lambda a, b: {
            "scripts": [{"name": "A", "script": a}, {"name": "B", "script": b}],
            "default_part": 0,
        },
    )

    cmd._handle_run_command(_args(part=None))

    assert captured["scripts"] == [script_a, script_b]


# ---------------------------------------------------------------------------
# args.part is not None (previously "and len(script_configs) == 1", a
# dead clause removed while writing this test -- see the fix's comment
# in milestone/command.py)
# ---------------------------------------------------------------------------


def test_missing_modules_with_a_specific_part_shows_part_in_error(tmp_path, monkeypatch):
    """Baseline: args.part is not None -> the error message names the
    specific part."""
    from platforms.cli.processes.module_workflow.workflow import ModuleWorkflowCommand

    monkeypatch.setattr(ModuleWorkflowCommand, "get_progress_data", lambda self: {"completed_modules": []})
    cmd, buf, captured, script_a, script_b = _setup(
        tmp_path,
        monkeypatch,
        lambda a, b: {
            "scripts": [
                {"name": "A", "script": a, "required_modules": [1]},
                {"name": "B", "script": b, "required_modules": [2]},
            ]
        },
    )

    cmd._handle_run_command(_args(part=1, skip_checks=False))

    assert "(Part 1)" in buf.getvalue()


def test_missing_modules_without_a_part_flag_omits_part_text(tmp_path, monkeypatch):
    """args.part is not None is False -> no part text shown even though
    modules are missing. Paired with the baseline: only args.part's
    presence differs, isolating this condition directly."""
    from platforms.cli.processes.module_workflow.workflow import ModuleWorkflowCommand

    monkeypatch.setattr(ModuleWorkflowCommand, "get_progress_data", lambda self: {"completed_modules": []})
    cmd, buf, captured, script_a, script_b = _setup(
        tmp_path,
        monkeypatch,
        lambda a, b: {
            "scripts": [
                {"name": "A", "script": a, "required_modules": [1]},
                {"name": "B", "script": b, "required_modules": [2]},
            ]
        },
    )

    cmd._handle_run_command(_args(part=None, skip_checks=False))

    assert "(Part" not in buf.getvalue()


# ---------------------------------------------------------------------------
# sys.stdin.isatty() and sys.stdout.isatty() -- the "press Enter to
# begin" prompt shown once before running any script.
# ---------------------------------------------------------------------------


def test_interactive_terminal_shows_the_press_enter_prompt(tmp_path, monkeypatch):
    """Baseline: stdin.isatty() True, stdout.isatty() True -> the
    console.input() prompt is called."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    cmd, buf, captured, script_a, script_b = _setup(tmp_path, monkeypatch, lambda a, b: {"script": a})
    prompted = {}
    monkeypatch.setattr(cmd.console, "input", lambda *a, **k: prompted.setdefault("called", True) or "")

    cmd._handle_run_command(_args())

    assert prompted.get("called") is True


def test_non_interactive_stdin_skips_the_prompt(tmp_path, monkeypatch):
    """stdin.isatty() False -> short-circuits, no prompt shown
    regardless of stdout. Paired with the baseline: only stdin's tty
    status differs, isolating that half of the and."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    cmd, buf, captured, script_a, script_b = _setup(tmp_path, monkeypatch, lambda a, b: {"script": a})
    prompted = {}
    monkeypatch.setattr(cmd.console, "input", lambda *a, **k: prompted.setdefault("called", True) or "")

    cmd._handle_run_command(_args())

    assert "called" not in prompted


def test_non_interactive_stdout_skips_the_prompt(tmp_path, monkeypatch):
    """stdout.isatty() False -> also skips, even with a real stdin tty.
    Paired with the baseline: only stdout's tty status differs,
    isolating that half of the and."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    cmd, buf, captured, script_a, script_b = _setup(tmp_path, monkeypatch, lambda a, b: {"script": a})
    prompted = {}
    monkeypatch.setattr(cmd.console, "input", lambda *a, **k: prompted.setdefault("called", True) or "")

    cmd._handle_run_command(_args())

    assert "called" not in prompted


# ---------------------------------------------------------------------------
# The second isatty gate: whether to ask "Continue to next part?" after a
# part fails, only reachable with multiple parts and a non-zero exit.
# ---------------------------------------------------------------------------


def test_interactive_terminal_asks_to_continue_after_a_failed_part(tmp_path, monkeypatch):
    """Baseline: both isatty() True, a part fails, more than one part
    configured -> the "Continue to next part?" prompt fires."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    cmd, buf, captured, script_a, script_b = _setup(
        tmp_path,
        monkeypatch,
        lambda a, b: {"scripts": [{"name": "A", "script": a}, {"name": "B", "script": b}]},
        run_returncode=1,
    )
    monkeypatch.setattr(cmd.console, "input", lambda *a, **k: "")
    asked = {}
    monkeypatch.setattr("builtins.input", lambda *a, **k: asked.setdefault("called", True) or "y")

    cmd._handle_run_command(_args())

    assert asked.get("called") is True


def test_non_interactive_after_a_failed_part_does_not_ask(tmp_path, monkeypatch):
    """stdin.isatty() False -> the continue-prompt is skipped entirely;
    non-interactive mode stops on the first failure instead (per the
    code's own comment) rather than either asking or auto-continuing.
    Paired with the baseline: only stdin's tty status differs, isolating
    that half of this second and."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    cmd, buf, captured, script_a, script_b = _setup(
        tmp_path,
        monkeypatch,
        lambda a, b: {"scripts": [{"name": "A", "script": a}, {"name": "B", "script": b}]},
        run_returncode=1,
    )
    asked = {}
    monkeypatch.setattr("builtins.input", lambda *a, **k: asked.setdefault("called", True) or "y")

    cmd._handle_run_command(_args())

    assert "called" not in asked
    # Stopped after the first script's failure; the second never ran.
    assert captured["scripts"] == [script_a]
