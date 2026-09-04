"""
Coverage for SetupCommand.add_tren_to_path's decision logic: whether to
prompt at all (no venv found / already on PATH / --skip-path), and how
it handles the user's answer or a non-interactive EOFError. The actual
PATH mutation itself is covered separately in test_path_manager.py --
this only checks that SetupCommand wires into it correctly, always via
a monkeypatched add_bin_dir_to_path so no test here ever touches the
real registry or a real rc file.
"""

from rich.console import Console

from platforms.cli.cli_platform import setup as setup_cmd_module
from platforms.cli.cli_platform.setup import SetupCommand
from platforms.cli.core.config import CLIConfig


def _make_cmd(
    tmp_path, monkeypatch, *, venv_exists, already_on_path, confirm_answer=None, add_result=(True, "ok")
):
    """Build a SetupCommand with everything about PATH state controlled
    by the caller, and self.console swapped for a headless one."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    if venv_exists:
        (project_root / ".venv").mkdir()

    cmd = SetupCommand(CLIConfig.from_project_root(project_root))
    cmd.console = Console(file=None, quiet=True)

    monkeypatch.setattr(setup_cmd_module, "is_on_path", lambda bin_dir: already_on_path)

    added_with = {}

    def fake_add(bin_dir):
        added_with["bin_dir"] = bin_dir
        return add_result

    monkeypatch.setattr(setup_cmd_module, "add_bin_dir_to_path", fake_add)

    if confirm_answer is not None:
        from rich.prompt import Confirm

        monkeypatch.setattr(Confirm, "ask", staticmethod(lambda *a, **k: confirm_answer))
    else:

        def raise_eof(*a, **k):
            raise EOFError

        from rich.prompt import Confirm

        monkeypatch.setattr(Confirm, "ask", staticmethod(raise_eof))

    return cmd, added_with


def test_no_venv_skips_without_prompting(tmp_path, monkeypatch):
    cmd, added_with = _make_cmd(tmp_path, monkeypatch, venv_exists=False, already_on_path=False)

    result = cmd.add_tren_to_path()

    assert result is True
    assert added_with == {}


def test_already_on_path_skips_without_prompting(tmp_path, monkeypatch):
    cmd, added_with = _make_cmd(tmp_path, monkeypatch, venv_exists=True, already_on_path=True)

    result = cmd.add_tren_to_path()

    assert result is True
    assert added_with == {}


def test_skip_flag_skips_without_prompting(tmp_path, monkeypatch):
    cmd, added_with = _make_cmd(tmp_path, monkeypatch, venv_exists=True, already_on_path=False)

    result = cmd.add_tren_to_path(skip=True)

    assert result is True
    assert added_with == {}


def test_user_declines_prompt_does_not_touch_path(tmp_path, monkeypatch):
    cmd, added_with = _make_cmd(
        tmp_path, monkeypatch, venv_exists=True, already_on_path=False, confirm_answer=False
    )

    result = cmd.add_tren_to_path()

    assert result is True
    assert added_with == {}


def test_user_accepts_prompt_calls_add_bin_dir_to_path(tmp_path, monkeypatch):
    cmd, added_with = _make_cmd(
        tmp_path, monkeypatch, venv_exists=True, already_on_path=False, confirm_answer=True
    )

    result = cmd.add_tren_to_path()

    assert result is True
    assert added_with["bin_dir"] is not None


def test_add_bin_dir_failure_is_reported_but_not_fatal(tmp_path, monkeypatch):
    cmd, added_with = _make_cmd(
        tmp_path,
        monkeypatch,
        venv_exists=True,
        already_on_path=False,
        confirm_answer=True,
        add_result=(False, "permission denied"),
    )

    result = cmd.add_tren_to_path()

    assert result is False
    assert added_with["bin_dir"] is not None


def test_non_interactive_eof_skips_gracefully(tmp_path, monkeypatch):
    cmd, added_with = _make_cmd(tmp_path, monkeypatch, venv_exists=True, already_on_path=False)

    result = cmd.add_tren_to_path()

    assert result is True
    assert added_with == {}
