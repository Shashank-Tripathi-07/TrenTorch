"""
MC/DC coverage for TrenTorchCLI.run()'s virtual-environment guard.

Every `tren` command other than `setup` (and no-command) is gated by:

    in_venv = sys.prefix != sys.base_prefix or os.environ.get("VIRTUAL_ENV") is not None
    allow_system = os.environ.get("TREN_ALLOW_SYSTEM") == "1"
    if not in_venv and not allow_system:
        ... return 1

three independent atomic conditions (call them A, B, C). This is the single
highest-traffic decision in the whole CLI -- it runs on every invocation of
every command.

Four cases give real MC/DC: a "blocked" baseline (A=F, B=F, C=F) plus each
condition flipped alone (each flip alone must move the outcome to
"allowed").
"""

import sys

import pytest

from platforms.cli.cli_platform.setup import SetupCommand
from platforms.cli.main import TrenTorchCLI
from platforms.cli.processes.module_workflow.workflow import ModuleWorkflowCommand


class _SpyModuleCommand(ModuleWorkflowCommand):
    """create_parser() instantiates every registered command class up
    front to read its .description and call .add_arguments() while
    building the full argparse parser, for every command, not just the
    one being invoked -- so a bare stand-in without that real interface
    breaks parser construction entirely. Subclassing the real command and
    overriding only run() keeps that interface while still avoiding any
    real dispatch side effect once the guard lets execution through."""

    def run(self, parsed_args):
        return 0


@pytest.fixture
def cli(monkeypatch):
    app = TrenTorchCLI()
    monkeypatch.setitem(app.commands, "module", _SpyModuleCommand)
    return app


def _set_conditions(monkeypatch, *, differing_prefix, virtual_env_set, allow_system_set):
    if differing_prefix:
        monkeypatch.setattr(sys, "prefix", "/fake/venv")
        monkeypatch.setattr(sys, "base_prefix", "/fake/system")
    else:
        monkeypatch.setattr(sys, "prefix", "/fake/same")
        monkeypatch.setattr(sys, "base_prefix", "/fake/same")

    if virtual_env_set:
        monkeypatch.setenv("VIRTUAL_ENV", "/fake/venv")
    else:
        monkeypatch.delenv("VIRTUAL_ENV", raising=False)

    monkeypatch.delenv("TREN_ALLOW_SYSTEM", raising=False)
    if allow_system_set:
        monkeypatch.setenv("TREN_ALLOW_SYSTEM", "1")


def test_no_venv_signal_and_no_override_is_blocked(cli, monkeypatch, capsys):
    """A=False, B=False, C=False -> blocked (the baseline every flip below
    is paired against)."""
    _set_conditions(monkeypatch, differing_prefix=False, virtual_env_set=False, allow_system_set=False)

    result = cli.run(["module"])

    assert result == 1
    assert "Virtual Environment Required" in capsys.readouterr().out


def test_differing_prefix_alone_is_allowed(cli, monkeypatch):
    """A=True, B=False, C=False -> allowed. Paired with the baseline: only
    A differs, isolating sys.prefix != sys.base_prefix's effect."""
    _set_conditions(monkeypatch, differing_prefix=True, virtual_env_set=False, allow_system_set=False)

    assert cli.run(["module"]) == 0


def test_virtual_env_var_alone_is_allowed(cli, monkeypatch):
    """A=False, B=True, C=False -> allowed. Paired with the baseline: only
    B differs, isolating the VIRTUAL_ENV env var's effect."""
    _set_conditions(monkeypatch, differing_prefix=False, virtual_env_set=True, allow_system_set=False)

    assert cli.run(["module"]) == 0


def test_allow_system_alone_is_allowed(cli, monkeypatch):
    """A=False, B=False, C=True -> allowed. Paired with the baseline: only
    C differs, isolating TREN_ALLOW_SYSTEM's effect."""
    _set_conditions(monkeypatch, differing_prefix=False, virtual_env_set=False, allow_system_set=True)

    assert cli.run(["module"]) == 0


def test_setup_command_bypasses_the_guard_entirely(monkeypatch):
    """The guard only applies to `parsed_args.command not in ["setup",
    None]` -- confirms `tren setup` itself is exempt regardless of venv
    state, since it's the command that's supposed to create the venv."""
    app = TrenTorchCLI()
    ran = {}

    class _RecordingSetup(SetupCommand):
        def run(self, parsed_args):
            ran["called"] = True
            return 0

    monkeypatch.setitem(app.commands, "setup", _RecordingSetup)
    monkeypatch.setattr(sys, "prefix", "/fake/same")
    monkeypatch.setattr(sys, "base_prefix", "/fake/same")
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.delenv("TREN_ALLOW_SYSTEM", raising=False)

    assert app.run(["setup"]) == 0
    assert ran.get("called") is True


def test_os_environ_get_matches_the_name_used_everywhere_else():
    """Pins the literal env var name main.py reads, so a future rename
    has to touch this assertion on purpose."""
    import inspect

    from platforms.cli import main as main_module

    source = inspect.getsource(main_module.TrenTorchCLI.run)
    assert 'os.environ.get("TREN_ALLOW_SYSTEM")' in source
