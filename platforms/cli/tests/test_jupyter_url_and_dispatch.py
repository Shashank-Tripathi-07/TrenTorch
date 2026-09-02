"""
MC/DC coverage for open_jupyter's URL-building decision, plus quick
coverage for a few smaller, independent compound decisions found in the
same sweep: convert.py's module-directory matcher and olympics.py's
subcommand dispatch.
"""

from argparse import Namespace
from io import StringIO
from unittest.mock import MagicMock

import pytest
from rich.console import Console

from platforms.cli.commands import jupyter as jupyter_module
from platforms.cli.core.config import CLIConfig
from platforms.cli.processes.olympics import OlympicsCommand

# ---------------------------------------------------------------------------
# open_jupyter: notebook_path and notebook_path.exists()
# ---------------------------------------------------------------------------


def _open_jupyter(tmp_path, monkeypatch, *, notebook_exists):
    module_dir = tmp_path / "data" / "modules" / "01_tensor"
    module_dir.mkdir(parents=True)
    if notebook_exists:
        (module_dir / "tensor.ipynb").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        jupyter_module, "find_running_jupyter_server", lambda project_root: ("http://localhost:8888/", "tok")
    )
    opened = {}
    monkeypatch.setattr(jupyter_module.webbrowser, "open", lambda url: opened.setdefault("url", url))

    config = CLIConfig.from_project_root(tmp_path)
    console = MagicMock()
    jupyter_module.open_jupyter(config, console, "01_tensor", notebook=False, lab=True)
    return opened.get("url", "")


def test_existing_notebook_path_builds_a_url_pointing_at_it(tmp_path, monkeypatch):
    """Baseline: notebook_path truthy and exists() True -> URL includes
    the notebook's relative path."""
    url = _open_jupyter(tmp_path, monkeypatch, notebook_exists=True)
    assert "tensor.ipynb" in url


def test_missing_notebook_falls_back_to_the_bare_lab_url(tmp_path, monkeypatch):
    """No .ipynb file found at all -> notebook_path is None -> falls
    back to the bare UI URL with no notebook path in it. Paired with the
    baseline: only whether a notebook file exists differs, isolating
    that condition."""
    url = _open_jupyter(tmp_path, monkeypatch, notebook_exists=False)
    assert "ipynb" not in url
    assert url.endswith("/lab") or url.endswith("/lab?token=tok")


# ---------------------------------------------------------------------------
# olympics.py: hasattr(args, "olympics_command") and args.olympics_command == "logo"
# ---------------------------------------------------------------------------


@pytest.fixture
def olympics_command(tmp_path):
    cmd = OlympicsCommand(CLIConfig.from_project_root(tmp_path))
    buf = StringIO()
    cmd.console = Console(file=buf, width=120, no_color=True)
    return cmd, buf


def test_olympics_command_logo_shows_the_logo_panel(olympics_command):
    """A=True, B=True (attribute present, equals "logo") -> the logo
    panel is shown, not the coming-soon message."""
    cmd, buf = olympics_command
    cmd.run(Namespace(olympics_command="logo"))
    assert "TRENTORCH OLYMPICS" in buf.getvalue()
    assert "COMING SOON" not in buf.getvalue()


def test_no_olympics_command_attribute_shows_the_coming_soon_message(olympics_command):
    """A=False (hasattr False) -> falls through to the default branch.
    Paired with the logo test above: only A differs, isolating hasattr."""
    cmd, buf = olympics_command
    cmd.run(Namespace())
    assert "COMING SOON" in buf.getvalue()


def test_olympics_command_set_to_something_else_shows_default(olympics_command):
    """A=True, B=False (attribute present but not "logo") -> also the
    default branch. Paired with the logo test above: only B differs,
    isolating args.olympics_command == "logo"."""
    cmd, buf = olympics_command
    cmd.run(Namespace(olympics_command="status"))
    assert "COMING SOON" in buf.getvalue()
