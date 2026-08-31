"""
MC/DC coverage for dev/export.py's wrong-directory guard and its
modules/--all dispatch, plus _export_all_modules's stub/solution
conversion-failure gate.
"""

from argparse import Namespace
from unittest.mock import MagicMock

from platforms.cli.cli_platform.dev.export import DevExportCommand
from platforms.cli.core.config import CLIConfig

# ---------------------------------------------------------------------------
# is_tinytorch_root = (data/trentorch/__init__.py exists) or
#                      (data/src exists and pyproject.toml exists)
# ---------------------------------------------------------------------------


def _run_export(tmp_path, monkeypatch, *, has_package_init, has_src, has_pyproject, args):
    if has_package_init:
        pkg_dir = tmp_path / "data" / "trentorch"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    if has_src:
        (tmp_path / "data" / "src").mkdir(parents=True, exist_ok=True)
    if has_pyproject:
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    cmd = DevExportCommand(CLIConfig.from_project_root(tmp_path))
    cmd._export_specific_modules = MagicMock(return_value=0)
    cmd._export_all_modules = MagicMock(return_value=0)
    result = cmd.run(args)
    return result, cmd


def test_package_init_alone_passes_the_guard(tmp_path, monkeypatch):
    """A=True (data/trentorch/__init__.py exists), B/C irrelevant (short
    -circuits) -> guard passes, dispatch proceeds."""
    result, cmd = _run_export(
        tmp_path,
        monkeypatch,
        has_package_init=True,
        has_src=False,
        has_pyproject=False,
        args=Namespace(all=True),
    )
    assert cmd._export_all_modules.called


def test_neither_signal_fails_the_guard(tmp_path, monkeypatch):
    """A=False, B=False, C=False -> guard fails, dispatch never reached.
    Paired with the test above: only A differs, isolating it."""
    result, cmd = _run_export(
        tmp_path,
        monkeypatch,
        has_package_init=False,
        has_src=False,
        has_pyproject=False,
        args=Namespace(all=True),
    )
    assert result == 1
    assert not cmd._export_all_modules.called


def test_src_and_pyproject_together_pass_the_guard(tmp_path, monkeypatch):
    """A=False, B=True, C=True -> (B and C) makes the or True -> guard
    passes. Paired with the "neither" test: both B and C flip together
    here, isolating their combined effect from A's independent effect."""
    result, cmd = _run_export(
        tmp_path,
        monkeypatch,
        has_package_init=False,
        has_src=True,
        has_pyproject=True,
        args=Namespace(all=True),
    )
    assert cmd._export_all_modules.called


def test_src_without_pyproject_fails_the_guard(tmp_path, monkeypatch):
    """A=False, B=True, C=False -> (B and C) is False -> guard fails.
    Paired with the B-and-C-together test: only C differs, isolating C's
    independent effect within the and."""
    result, cmd = _run_export(
        tmp_path,
        monkeypatch,
        has_package_init=False,
        has_src=True,
        has_pyproject=False,
        args=Namespace(all=True),
    )
    assert result == 1
    assert not cmd._export_all_modules.called


def test_pyproject_without_src_fails_the_guard(tmp_path, monkeypatch):
    """A=False, B=False, C=True -> (B and C) is False -> guard fails.
    Paired with the B-and-C-together test: only B differs, isolating B's
    independent effect within the and."""
    result, cmd = _run_export(
        tmp_path,
        monkeypatch,
        has_package_init=False,
        has_src=False,
        has_pyproject=True,
        args=Namespace(all=True),
    )
    assert result == 1
    assert not cmd._export_all_modules.called


# ---------------------------------------------------------------------------
# hasattr(args, "modules") and args.modules
# hasattr(args, "all") and args.all
# ---------------------------------------------------------------------------


def test_modules_list_dispatches_to_specific_export(tmp_path, monkeypatch):
    """First gate: hasattr True, args.modules truthy -> specific-modules
    export runs, --all's export never even checked."""
    result, cmd = _run_export(
        tmp_path,
        monkeypatch,
        has_package_init=True,
        has_src=False,
        has_pyproject=False,
        args=Namespace(modules=["01_tensor"], all=False),
    )
    assert cmd._export_specific_modules.called
    assert not cmd._export_all_modules.called


def test_all_flag_dispatches_to_export_all(tmp_path, monkeypatch):
    """First gate falls through (no modules), second gate: hasattr True,
    args.all truthy -> export-all runs."""
    result, cmd = _run_export(
        tmp_path,
        monkeypatch,
        has_package_init=True,
        has_src=False,
        has_pyproject=False,
        args=Namespace(modules=[], all=True),
    )
    assert not cmd._export_specific_modules.called
    assert cmd._export_all_modules.called


def test_neither_modules_nor_all_shows_usage_error(tmp_path, monkeypatch):
    """Both gates false -> neither export path runs, falls to the usage
    error panel."""
    result, cmd = _run_export(
        tmp_path,
        monkeypatch,
        has_package_init=True,
        has_src=False,
        has_pyproject=False,
        args=Namespace(modules=[], all=False),
    )
    assert not cmd._export_specific_modules.called
    assert not cmd._export_all_modules.called
    assert result == 1


# ---------------------------------------------------------------------------
# _export_all_modules: not converted_stub or not converted_solution
# ---------------------------------------------------------------------------


def _export_all_with_conversions(tmp_path, monkeypatch, *, stub_result, solution_result):
    from io import StringIO

    from rich.console import Console

    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "solutions").mkdir(
        parents=True
    )  # empty: rglob("*.ipynb") finds nothing, no real I/O
    cmd = DevExportCommand(CLIConfig.from_project_root(tmp_path))

    def fake_convert(variant, target_root):
        return stub_result if variant == "stub" else solution_result

    monkeypatch.setattr(cmd, "_convert_all_modules", fake_convert)
    buf = StringIO()
    console = Console(file=buf, width=120, no_color=True)
    result = cmd._export_all_modules(console)
    return result, buf.getvalue()


def test_both_variants_convert_something_skips_the_conversion_error(tmp_path, monkeypatch):
    """Baseline: converted_stub truthy, converted_solution truthy -> "not
    X or not Y" is False, the "No modules converted" failure panel is
    never shown (nothing left in data/solutions/ for the later nbdev
    step, but that's not this decision's concern)."""
    result, out = _export_all_with_conversions(
        tmp_path, monkeypatch, stub_result=["01_tensor"], solution_result=["01_tensor"]
    )
    assert "No modules converted" not in out


def test_empty_stub_conversion_fails_here(tmp_path, monkeypatch):
    """converted_stub falsy (empty list) -> "not converted_stub" True ->
    the or is True -> fails immediately with "No modules converted".
    Paired with the baseline: only converted_stub's emptiness differs,
    isolating that half of the or."""
    result, out = _export_all_with_conversions(
        tmp_path, monkeypatch, stub_result=[], solution_result=["01_tensor"]
    )
    assert result == 1


def test_empty_solution_conversion_fails_here(tmp_path, monkeypatch):
    """converted_solution falsy -> also fails. Paired with the baseline:
    only converted_solution's emptiness differs, isolating that half."""
    result, out = _export_all_with_conversions(
        tmp_path, monkeypatch, stub_result=["01_tensor"], solution_result=[]
    )
    assert result == 1
