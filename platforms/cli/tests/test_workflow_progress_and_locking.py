"""
MC/DC coverage for module_workflow/workflow.py's progress-tracking and
module-locking decisions -- real state that determines what a student is
told they've completed and which modules are unlocked.
"""

from argparse import Namespace

import pytest

import platforms.cli.processes.module_workflow.workflow as workflow_module
from platforms.cli.core.config import CLIConfig
from platforms.cli.processes.module_workflow.workflow import ModuleWorkflowCommand

# ---------------------------------------------------------------------------
# update_progress: "started_modules" in progress and
#                  module_number in progress["started_modules"]
# ---------------------------------------------------------------------------


@pytest.fixture
def workflow(tmp_path):
    return ModuleWorkflowCommand(CLIConfig.from_project_root(tmp_path))


def test_completing_a_started_module_removes_it_from_started(workflow):
    """Baseline: "started_modules" key present, module_number present in
    it -> removed from started_modules on completion (prevents
    double-tracking, per the code's own comment)."""
    workflow.save_progress_data({"started_modules": ["01_tensor"], "completed_modules": []})

    workflow.update_progress("01_tensor", "01_tensor")

    progress = workflow.get_progress_data()
    assert "01_tensor" not in progress["started_modules"]
    assert "01_tensor" in progress["completed_modules"]


def test_completing_a_module_not_in_started_modules_does_not_crash(workflow):
    """ "started_modules" key present, but this module_number isn't in it
    -> the removal branch doesn't fire (no .remove() on a missing item,
    which would raise). Paired with the baseline: only whether this
    module is in the list differs, isolating that half of the and."""
    workflow.save_progress_data({"started_modules": ["02_activations"], "completed_modules": []})

    workflow.update_progress("01_tensor", "01_tensor")  # should not raise

    progress = workflow.get_progress_data()
    assert "02_activations" in progress["started_modules"]
    assert "01_tensor" in progress["completed_modules"]


def test_completing_a_module_with_no_started_modules_key_does_not_crash(workflow):
    """ "started_modules" key absent entirely -> short-circuits before
    even checking membership (avoiding a KeyError). Paired with the
    baseline: only the key's presence differs, isolating that half."""
    workflow.save_progress_data({"completed_modules": []})

    workflow.update_progress("01_tensor", "01_tensor")  # should not raise

    progress = workflow.get_progress_data()
    assert "01_tensor" in progress["completed_modules"]


# ---------------------------------------------------------------------------
# show_status's readiness check: prev_num in completed or int(num) == 1
# ---------------------------------------------------------------------------


def _readiness(num: str, completed: set) -> str:
    """Mirrors the exact branch this decision drives (not started, not
    complete -> Ready vs Locked), to isolate it from show_status's much
    larger table-rendering method."""
    prev_num = f"{int(num) - 1:02d}"
    if prev_num in completed or int(num) == 1:
        return "ready"
    return "locked"


def test_module_01_is_always_ready_regardless_of_any_prior_completion():
    """Baseline: int(num) == 1 True -> ready, regardless of the first
    condition (there is no module 00 to have completed)."""
    assert _readiness("01", completed=set()) == "ready"


def test_later_module_is_ready_when_the_previous_one_is_completed():
    """int(num) == 1 False, prev_num in completed True -> ready. Paired
    with the baseline: only which condition is True differs, isolating
    "prev_num in completed"."""
    assert _readiness("03", completed={"02"}) == "ready"


def test_later_module_is_locked_when_the_previous_one_is_not_completed():
    """Both False -> locked. Paired with the test above: only whether
    the previous module is completed differs, isolating that condition
    from int(num) == 1's independent effect."""
    assert _readiness("03", completed={"01"}) == "locked"


# ---------------------------------------------------------------------------
# run(): hasattr(args, "module_command") and args.module_command
# (the same dispatcher pattern as the 5 classes in
# test_dispatcher_no_subcommand_gate.py -- falls through to a help panel
# rather than dispatching a subcommand.)
# ---------------------------------------------------------------------------


def _capture_help_panel(workflow, args):
    from io import StringIO

    from rich.console import Console

    buf = StringIO()
    workflow.console = Console(file=buf, width=120, no_color=True)
    result = workflow.run(args)
    return result, buf.getvalue()


def test_missing_module_command_attribute_shows_the_help_panel(workflow):
    """A=False -> run() doesn't try to dispatch a subcommand at all,
    falling through to the help panel (return 0)."""
    result, out = _capture_help_panel(workflow, Namespace())
    assert result == 0
    assert "Module Lifecycle Commands" in out


def test_module_command_present_but_falsy_shows_the_help_panel(workflow):
    """A=True (hasattr), B=False (falsy value, e.g. None) -> still falls
    through to the help panel. Paired with the test above: only which
    half of "hasattr and truthy" fails differs."""
    result, out = _capture_help_panel(workflow, Namespace(module_command=None))
    assert result == 0
    assert "Module Lifecycle Commands" in out


def test_module_command_present_and_truthy_dispatches_instead(workflow, monkeypatch):
    """A=True, B=True -> dispatches to the named subcommand's own branch
    instead of falling through to the default show_status() call. Uses
    "list" (not "status", which coincidentally also calls show_status
    via its own elif branch and wouldn't distinguish "dispatched" from
    "fell through") so the mock cleanly proves which path fired. Paired
    with both tests above: only the attribute's truthiness differs,
    isolating that half of the and."""
    called = {}
    monkeypatch.setattr(workflow, "show_status", lambda: called.setdefault("show_status", True) or 0)
    monkeypatch.setattr(
        workflow, "list_modules", lambda json_mode=False: called.setdefault("list_modules", True) or 0
    )

    workflow.run(Namespace(module_command="list"))

    assert called.get("list_modules") is True
    assert "show_status" not in called


# ---------------------------------------------------------------------------
# complete_module: regression coverage for a real dead-code fix.
#
# `success = True` was set once at the top of complete_module and never
# reassigned anywhere in the function -- every failure path already
# returns 1 directly instead. That made three separate `if success:`-style
# checks (gating the Step 3 integration-test run, the celebration panel,
# and the milestone-unlock check) permanently true, and the function's
# own `return 0 if success else 1` permanently return 0. Removed the dead
# variable; these tests confirm the simplification didn't change
# observable behavior on the one path that actually runs (success),
# which is all that path could ever have been.
# ---------------------------------------------------------------------------


def _mock_complete_module_dependencies(monkeypatch, *, integration_result=None, milestone_unlocks_called):
    monkeypatch.setattr(
        workflow_module,
        "run_inline_unit_tests",
        lambda config, console, module_name, verbose: {"passed": 1, "failed": 0},
    )
    monkeypatch.setattr(workflow_module, "check_notebook_syntax", lambda config, module_name: {"ok": True})
    monkeypatch.setattr(
        workflow_module,
        "run_integration_tests",
        lambda config, console, module_name, verbose: integration_result or {"passed": 0, "failed": 0},
    )
    monkeypatch.setattr(
        workflow_module,
        "check_and_run_milestone_unlocks",
        lambda config, console: milestone_unlocks_called.setdefault("called", True),
    )


def test_complete_module_full_success_path_returns_0_and_celebrates(workflow, monkeypatch):
    """Every step succeeds -> reaches the end unconditionally (nothing
    left to gate it on), shows the celebration panel, checks for
    milestone unlocks, and returns 0."""
    from io import StringIO

    from rich.console import Console

    workflow.save_progress_data({"completed_modules": []})
    monkeypatch.setattr(workflow, "export_module", lambda module_name: 0)
    milestone_calls = {}
    _mock_complete_module_dependencies(monkeypatch, milestone_unlocks_called=milestone_calls)
    buf = StringIO()
    workflow.console = Console(file=buf, width=120, no_color=True)

    result = workflow.run(
        Namespace(module_command="complete", module_number="01", skip_tests=False, skip_export=False)
    )

    assert result == 0
    assert "Module Complete!" in buf.getvalue()
    assert milestone_calls.get("called") is True


def test_complete_module_skip_tests_still_completes_and_celebrates(workflow, monkeypatch):
    """skip_tests=True skips Steps 1 and 3 entirely, but still reaches
    the celebration panel and returns 0 -- confirming the panel and
    return value were never actually contingent on the tests having run
    successfully in the first place (the dead `success` flag they used
    to be gated on couldn't have been False here either)."""
    from io import StringIO

    from rich.console import Console

    workflow.save_progress_data({"completed_modules": []})
    monkeypatch.setattr(workflow, "export_module", lambda module_name: 0)
    milestone_calls = {}
    _mock_complete_module_dependencies(monkeypatch, milestone_unlocks_called=milestone_calls)
    buf = StringIO()
    workflow.console = Console(file=buf, width=120, no_color=True)

    result = workflow.run(
        Namespace(module_command="complete", module_number="01", skip_tests=True, skip_export=False)
    )

    assert result == 0
    assert "Module Complete!" in buf.getvalue()


def test_complete_module_verify_solution_env_skips_milestone_check(workflow, monkeypatch):
    """The one real (non-dead) half of the old `success and
    os.environ.get(...) != "1"` decision: VERIFY_SOLUTION_ENV=1 skips
    the milestone-unlock check, by design (see the code's own comment)."""
    from io import StringIO

    from rich.console import Console

    workflow.save_progress_data({"completed_modules": []})
    monkeypatch.setattr(workflow, "export_module", lambda module_name: 0)
    monkeypatch.setenv("TREN_DEV_VERIFY_SOLUTION", "1")
    milestone_calls = {}
    _mock_complete_module_dependencies(monkeypatch, milestone_unlocks_called=milestone_calls)
    buf = StringIO()
    workflow.console = Console(file=buf, width=120, no_color=True)

    result = workflow.run(
        Namespace(module_command="complete", module_number="01", skip_tests=True, skip_export=False)
    )

    assert result == 0
    assert "called" not in milestone_calls


# ---------------------------------------------------------------------------
# Regression coverage for PR #169 / issue #168: `tren dev test --inline`
# (TREN_DEV_VERIFY_SOLUTION=1) was silently marking real student progress
# complete, because update_progress() ran unconditionally on that path.
# Any student could run the maintainer-only verification command
# themselves and instantly unlock the whole course with zero code written.
# The fix gated update_progress() on the same env var, and a same-PR
# follow-up then had to skip complete_module()'s sequential-completion
# gate in that mode too, since that gate reads completed_modules from the
# exact file update_progress() had just stopped writing to. Without the
# skip, module 02 immediately failed with "you must complete module 01
# first" even right after module 01 itself verified clean (caught live by
# CI's own Stage 1 build). Both PR #169 commits were verified only by a
# manual before/after run described in their commit messages; these tests
# are the automated coverage neither commit had, so a future change to
# either update_progress() or the sequential gate can't silently reopen
# the loophole or reintroduce the regression without a test failing first.
# ---------------------------------------------------------------------------


def test_complete_module_verify_solution_mode_does_not_write_progress(workflow, monkeypatch):
    """The actual loophole: TREN_DEV_VERIFY_SOLUTION=1 must leave
    progress.json completely untouched, not just "01" missing from it.
    Seeding it with unrelated existing progress and asserting the whole
    file is byte-for-byte unchanged proves update_progress() never wrote
    at all, rather than merely writing something that happens not to
    include "01"."""
    from io import StringIO

    from rich.console import Console

    seed = {"completed_modules": ["05"], "started_modules": ["06"]}
    workflow.save_progress_data(seed)
    before = workflow.get_progress_data()

    monkeypatch.setenv("TREN_DEV_VERIFY_SOLUTION", "1")
    monkeypatch.setattr(workflow, "export_module", lambda module_name: 0)
    _mock_complete_module_dependencies(monkeypatch, milestone_unlocks_called={})
    workflow.console = Console(file=StringIO(), width=120, no_color=True)

    result = workflow.run(
        Namespace(module_command="complete", module_number="01", skip_tests=True, skip_export=False)
    )

    assert result == 0
    after = workflow.get_progress_data()
    assert after == before, f"progress.json changed in verify-solution mode: {before} -> {after}"


def test_complete_module_verify_solution_mode_does_not_block_on_sequential_gate(workflow, monkeypatch):
    """The follow-up fix's regression: since update_progress() now
    correctly no-ops in verify-solution mode, completed_modules never
    gains "01", so completing module "02" right after must not hit the
    sequential-completion gate ("you must complete module 01 first"),
    which reads from that same never-updated file. Runs 01 then 02 in the
    same sequence CI's own Stage 1 build hit this in."""
    from io import StringIO

    from rich.console import Console

    monkeypatch.setenv("TREN_DEV_VERIFY_SOLUTION", "1")
    monkeypatch.setattr(workflow, "export_module", lambda module_name: 0)
    _mock_complete_module_dependencies(monkeypatch, milestone_unlocks_called={})
    workflow.console = Console(file=StringIO(), width=120, no_color=True)

    result_01 = workflow.run(
        Namespace(module_command="complete", module_number="01", skip_tests=True, skip_export=False)
    )
    result_02 = workflow.run(
        Namespace(module_command="complete", module_number="02", skip_tests=True, skip_export=False)
    )

    assert result_01 == 0
    assert result_02 == 0, "module 02 was blocked by the sequential gate in verify-solution mode"
    # And the loophole fix still holds across both calls.
    assert workflow.get_progress_data() == {
        "started_modules": [],
        "completed_modules": [],
        "last_worked": None,
        "last_completed": None,
        "last_updated": None,
    }
