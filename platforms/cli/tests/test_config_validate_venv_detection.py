"""
MC/DC coverage for CLIConfig.validate()'s in_venv decision -- the copy
that actually gatekeeps `tren`'s own startup validation (main.py's
validate_environment() call), not just a status display like the other
copies of this same shape in status_analyzer.py/health.py/info.py.
4 atoms: VIRTUAL_ENV env var, sys.prefix != sys.base_prefix,
sys.real_prefix, and (venv_path.exists() and packages importable).
"""

import sys

from platforms.cli.core.config import CLIConfig

_VENV_ISSUE_SUBSTRING = "Virtual environment not activated"


def _validate(tmp_path, monkeypatch, *, venv_var, differing_prefix, real_prefix, venv_dir_exists):
    (tmp_path / "data" / "src").mkdir(parents=True)

    if venv_var:
        monkeypatch.setenv("VIRTUAL_ENV", str(tmp_path))
    else:
        monkeypatch.delenv("VIRTUAL_ENV", raising=False)

    if differing_prefix:
        monkeypatch.setattr(sys, "prefix", "/fake/venv")
        monkeypatch.setattr(sys, "base_prefix", "/fake/system")
    else:
        monkeypatch.setattr(sys, "prefix", "/fake/same")
        monkeypatch.setattr(sys, "base_prefix", "/fake/same")

    if real_prefix:
        monkeypatch.setattr(sys, "real_prefix", "/fake/old-venv", raising=False)
    else:
        monkeypatch.delattr(sys, "real_prefix", raising=False)

    venv_path = tmp_path / ".venv"
    if venv_dir_exists:
        venv_path.mkdir()

    config = CLIConfig.from_project_root(tmp_path)
    config.required_packages = []  # isolate from real dependency availability
    if venv_dir_exists:
        config._packages_available = lambda: True
    issues = config.validate(venv_path=venv_path)
    return issues


def test_virtual_env_var_alone_satisfies_the_check(tmp_path, monkeypatch):
    """Baseline: VIRTUAL_ENV set True, everything else False -> no venv
    issue reported."""
    issues = _validate(
        tmp_path, monkeypatch, venv_var=True, differing_prefix=False, real_prefix=False, venv_dir_exists=False
    )
    assert not any(_VENV_ISSUE_SUBSTRING in i for i in issues)


def test_differing_prefixes_alone_satisfies_the_check(tmp_path, monkeypatch):
    """Method 2 alone True -> no issue. Paired with the baseline: only
    which method fires differs, isolating this condition."""
    issues = _validate(
        tmp_path, monkeypatch, venv_var=False, differing_prefix=True, real_prefix=False, venv_dir_exists=False
    )
    assert not any(_VENV_ISSUE_SUBSTRING in i for i in issues)


def test_real_prefix_alone_satisfies_the_check(tmp_path, monkeypatch):
    """Method 3 alone True -> no issue. This is the one atom none of the
    other in-repo copies of this same 4-condition shape had isolated on
    its own yet."""
    issues = _validate(
        tmp_path, monkeypatch, venv_var=False, differing_prefix=False, real_prefix=True, venv_dir_exists=False
    )
    assert not any(_VENV_ISSUE_SUBSTRING in i for i in issues)


def test_venv_dir_with_available_packages_alone_satisfies_the_check(tmp_path, monkeypatch):
    """Method 4 alone True (venv_path.exists() and packages importable)
    -> no issue. Isolates the fourth disjunct, itself a nested and."""
    issues = _validate(
        tmp_path, monkeypatch, venv_var=False, differing_prefix=False, real_prefix=False, venv_dir_exists=True
    )
    assert not any(_VENV_ISSUE_SUBSTRING in i for i in issues)


def test_none_of_the_four_signals_reports_the_issue(tmp_path, monkeypatch):
    """All four False -> the venv issue is reported. Paired with all
    four tests above: only one condition flips at a time from this
    baseline, isolating each independently."""
    issues = _validate(
        tmp_path,
        monkeypatch,
        venv_var=False,
        differing_prefix=False,
        real_prefix=False,
        venv_dir_exists=False,
    )
    assert any(_VENV_ISSUE_SUBSTRING in i for i in issues)


def test_venv_dir_exists_but_packages_unavailable_still_reports_the_issue(tmp_path, monkeypatch):
    """Method 4's nested and: venv_path.exists() True but packages
    importable False -> method 4 itself is False, isolating that half of
    the nested and within the fourth disjunct."""
    tmp_path_venv = tmp_path / ".venv"
    tmp_path_venv.mkdir()
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.setattr(sys, "prefix", "/fake/same")
    monkeypatch.setattr(sys, "base_prefix", "/fake/same")
    monkeypatch.delattr(sys, "real_prefix", raising=False)
    (tmp_path / "data" / "src").mkdir(parents=True)

    config = CLIConfig.from_project_root(tmp_path)
    config.required_packages = []
    config._packages_available = lambda: False
    issues = config.validate(venv_path=tmp_path_venv)

    assert any(_VENV_ISSUE_SUBSTRING in i for i in issues)
