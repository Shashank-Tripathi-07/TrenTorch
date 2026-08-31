"""
MC/DC coverage for a pattern repeated identically across 5 command
dispatcher classes: `if not hasattr(args, "X_command") or not
args.X_command:` shows a help panel (return 0) instead of dispatching to
a subcommand. Two atoms: A = not hasattr(...), B = not args.X_command
(only evaluated if the attribute exists).

Tested via Namespace objects that vary which case applies, using an
unrecognized subcommand name to reach the (return 1) "unknown subcommand"
branch when the attribute is truthy -- proves the gate didn't fire
without needing to invoke any real, heavier subcommand class.
"""

from argparse import Namespace

import pytest

from platforms.cli.cli_platform.dev.dev import DevCommand
from platforms.cli.cli_platform.package.package import PackageCommand
from platforms.cli.cli_platform.package.reset import ResetCommand
from platforms.cli.cli_platform.system.system import SystemCommand
from platforms.cli.core.config import CLIConfig
from platforms.cli.processes.milestone.command import MilestoneCommand

CASES = [
    (DevCommand, "dev_command"),
    (PackageCommand, "package_command"),
    (ResetCommand, "reset_command"),
    (SystemCommand, "system_command"),
    (MilestoneCommand, "milestone_command"),
]


@pytest.mark.parametrize("command_class,attr_name", CASES, ids=[c.__name__ for c, _ in CASES])
def test_missing_attribute_entirely_shows_help(command_class, attr_name, tmp_path):
    """A=True (hasattr False) -> help shown, return 0. This is the
    baseline every other case here is paired against."""
    cmd = command_class(CLIConfig.from_project_root(tmp_path))
    assert cmd.run(Namespace()) == 0


@pytest.mark.parametrize("command_class,attr_name", CASES, ids=[c.__name__ for c, _ in CASES])
def test_attribute_present_but_none_shows_help(command_class, attr_name, tmp_path):
    """A=False (hasattr True), B=True (falsy value) -> help shown,
    return 0. Paired with the attribute-truthy test below: only B
    differs, isolating "not args.X_command"."""
    cmd = command_class(CLIConfig.from_project_root(tmp_path))
    assert cmd.run(Namespace(**{attr_name: None})) == 0


@pytest.mark.parametrize("command_class,attr_name", CASES, ids=[c.__name__ for c, _ in CASES])
def test_attribute_present_and_truthy_skips_the_help_gate(command_class, attr_name, tmp_path):
    """A=False, B=False (a real, if unrecognized, value) -> the gate
    doesn't fire at all; falls through to subcommand dispatch, which
    reports "unknown subcommand" (return 1) rather than the help panel's
    0. Paired with both tests above: only the attribute's truthiness
    differs, isolating each half of the decision in turn."""
    cmd = command_class(CLIConfig.from_project_root(tmp_path))
    result = cmd.run(Namespace(**{attr_name: "not-a-real-subcommand"}))
    assert result != 0
