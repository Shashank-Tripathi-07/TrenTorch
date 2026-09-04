"""
Coverage for CLIConfig.from_project_root()'s auto-detect fallback.

`tren` is a console-script entry point (found via PATH regardless of
cwd), so a bare invocation from a directory outside any TrenTorch
checkout previously fell back to treating that unrelated directory as
the project root, silently looking for user_data/, data/src/, etc. in
the wrong place. It now falls back to modules.py's own installed
location (_find_project_root(), which walks up from that file's real
path) instead.
"""

from platforms.cli.core.config import CLIConfig


def test_project_root_resolves_from_inside_checkout(tmp_path, monkeypatch):
    """cwd inside a checkout (or a subdirectory of one) resolves to that
    checkout's own root, not the real installed package location --
    this is what lets a maintainer juggling multiple clones cd into a
    specific one and have tren operate on that one."""
    checkout = tmp_path / "some_checkout"
    (checkout / "data" / "src").mkdir(parents=True)
    (checkout / "pyproject.toml").write_text("[project]\nname = 'fake'\n")

    nested = checkout / "data" / "src"
    monkeypatch.chdir(nested)

    config = CLIConfig.from_project_root()

    assert config.project_root == checkout


def test_project_root_falls_back_to_install_location_outside_any_checkout(tmp_path, monkeypatch):
    """cwd outside any TrenTorch checkout entirely (no pyproject.toml
    anywhere up the tree) must NOT silently treat that unrelated
    directory as the project root -- it should fall back to the real
    installed checkout instead, so `tren` run from e.g. a student's home
    directory still finds the real data/src/, user_data/, etc."""
    unrelated = tmp_path / "totally" / "unrelated" / "directory"
    unrelated.mkdir(parents=True)
    monkeypatch.chdir(unrelated)

    config = CLIConfig.from_project_root()

    # Must resolve to the real TrenTorch checkout this test itself is
    # running from, never to `unrelated` or any of its parents.
    assert config.project_root != unrelated
    assert not str(config.project_root).startswith(str(tmp_path))
    assert (config.project_root / "pyproject.toml").exists()
    assert (config.project_root / "data" / "src").exists()


def test_project_root_explicit_argument_bypasses_autodetect(tmp_path):
    """Passing project_root explicitly skips auto-detection entirely,
    regardless of cwd or checkout state -- used by tests/tools that need
    to point CLIConfig at an arbitrary directory."""
    explicit = tmp_path / "wherever"
    explicit.mkdir()

    config = CLIConfig.from_project_root(project_root=explicit)

    assert config.project_root == explicit
    assert config.modules_dir == explicit / "data" / "src"
