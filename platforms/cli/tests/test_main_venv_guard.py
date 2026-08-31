"""
MC/DC coverage for TrenTorchCLI.run()'s virtual-environment guard.

Every `tren` command other than `setup` (and no-command) is gated by:

    in_venv = sys.prefix != sys.base_prefix or os.environ.get("VIRTUAL_ENV") is not None
    allow_system = os.environ.get("TITO_ALLOW_SYSTEM") == "1"
    if not in_venv and not allow_system:
        ... return 1

three independent atomic conditions (call them A, B, C). This is the single
highest-traffic decision in the whole CLI -- it runs on every invocation of
every command -- and had no dedicated test before this.

While writing this, found a real (if currently harmless) instance of the
project's own documented rename-migration bug pattern (section 6 of
docs/testing-strategy.md, the `tito` -> `trentorch` renames): three test
files (platforms/cli/tests/test_release_regressions.py,
tests/e2e/test_user_journey.py, data/milestones/tests/test_milestones_run.py)
set `TREN_ALLOW_SYSTEM=1` in the subprocess env expecting it to be this
escape hatch, but this code (and every doc describing it, and both CI
workflow files) has only ever read `TITO_ALLOW_SYSTEM`. It doesn't fail any
test today only because those subprocess calls already run with
sys.executable pointing at an activated venv, so A is independently True
and C's value never gets exercised. Fixed those three call sites to set the
name this guard actually reads.

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

    if allow_system_set:
        monkeypatch.setenv("TITO_ALLOW_SYSTEM", "1")
    else:
        monkeypatch.delenv("TITO_ALLOW_SYSTEM", raising=False)


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
    C differs, isolating TITO_ALLOW_SYSTEM's effect."""
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
    monkeypatch.delenv("TITO_ALLOW_SYSTEM", raising=False)

    assert app.run(["setup"]) == 0
    assert ran.get("called") is True


def test_os_environ_get_matches_the_name_used_everywhere_else():
    """Documents the migration-name gap directly: os.environ has no
    built-in tie to what a test file happens to set, so this pins the
    literal env var name main.py reads, the same way section 6 of
    docs/testing-strategy.md pins check_tinytorch_package()'s `import
    tito` regression -- a future rename of this variable should have to
    touch this assertion on purpose."""
    import inspect

    from platforms.cli import main as main_module

    source = inspect.getsource(main_module.TrenTorchCLI.run)
    assert 'os.environ.get("TITO_ALLOW_SYSTEM")' in source
    assert "TREN_ALLOW_SYSTEM" not in source
