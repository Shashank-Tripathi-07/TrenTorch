"""
MC/DC coverage for DevTestCommand.run()'s Step-1 build gate.

`tren dev test` decides whether to (re)build the package before running
anything with:

    if not args.no_build and not run_user_journey and not run_inline:

a 3-condition AND (call the conditions P = not args.no_build,
Q = not run_user_journey, R = not run_inline). This is the exact gate
docs/testing-strategy.md's pre-merge checklist item 1 depends on ("re-run
tren dev export --all... before trusting a local pytest run"): if this
condition is ever miswired, a maintainer could silently run tests against
a stale package and get a false "zero regressions" signal, which is what
actually produced two of the incidents in section 6 of that doc. It had
no dedicated test before this.

A 4-case MC/DC set for a 3-term AND: an all-true baseline, plus each
condition flipped alone.
"""

from argparse import Namespace
from unittest.mock import MagicMock

import pytest

from platforms.cli.cli_platform.dev.test import DevTestCommand, TestResult
from platforms.cli.core.config import CLIConfig

PROJECT_ROOT_MARKER = __file__


def _base_args(**overrides):
    defaults = {
        "no_build": False,
        "inline": False,
        "all": False,
        "unit": False,
        "integration": False,
        "e2e": False,
        "cli": False,
        "milestone": False,
        "module": None,
        "ci": True,
        "verbose": False,
        "parallel": False,
        "user_journey": False,
    }
    defaults.update(overrides)
    return Namespace(**defaults)


@pytest.fixture
def command(tmp_path):
    cmd = DevTestCommand(CLIConfig.from_project_root(tmp_path))
    # Force the build step to be attempted (rather than skipped via the
    # "package already built" import check) and every phase -- build
    # included -- to report failure immediately, so run() always exits
    # after the first phase it actually reaches. That isolates the Step 1
    # gate itself: whichever branch it takes, nothing past the first
    # phase call runs for real (no subprocess, no actual build/export).
    cmd._check_imports = MagicMock(return_value=False)
    failing = TestResult(name="phase", passed=False)
    cmd._build_package = MagicMock(return_value=failing)
    cmd._run_inline_tests = MagicMock(return_value=failing)
    cmd._run_unit_tests = MagicMock(return_value=failing)
    cmd._run_cli_tests = MagicMock(return_value=failing)
    cmd._run_integration_tests = MagicMock(return_value=failing)
    cmd._run_e2e_tests = MagicMock(return_value=failing)
    cmd._run_milestone_tests = MagicMock(return_value=failing)
    cmd._run_user_journey = MagicMock(return_value=failing)
    return cmd


def test_build_runs_when_all_gate_conditions_true(command):
    """P=True, Q=True, R=True -> build attempted (baseline)."""
    command.run(_base_args())
    assert command._build_package.called


def test_no_build_flag_skips_build(command):
    """P=False, Q=True, R=True -> build skipped. Paired with the baseline:
    only P differs, isolating args.no_build's effect."""
    command.run(_base_args(no_build=True))
    assert not command._build_package.called


def test_user_journey_skips_build(command):
    """P=True, Q=False, R=True -> build skipped. Paired with the baseline:
    only Q differs, isolating user_journey's effect."""
    command.run(_base_args(user_journey=True))
    assert not command._build_package.called


def test_inline_skips_build(command):
    """P=True, Q=True, R=False -> build skipped. Paired with the baseline:
    only R differs, isolating args.inline's effect."""
    command.run(_base_args(inline=True))
    assert not command._build_package.called
