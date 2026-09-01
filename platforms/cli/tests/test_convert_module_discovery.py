"""
MC/DC coverage for ConvertCommand.run's two module-discovery decisions:
the "all" filter (d.is_dir() and not d.name.startswith((".", "_"))) and
the specific-module 4-atom OR
(d.is_dir() and (d.name == args.module or d.name.startswith(f"{args.module}_")
 or d.name.endswith(f"_{args.module}"))).

The real conversion functions (to_qmd/to_ipynb/to_sandbox_code/to_platform_yaml)
are mocked out -- this file only exercises which module directories get
selected, not the conversion logic itself.
"""

from argparse import Namespace
from io import StringIO

from rich.console import Console

from platforms.cli.core.config import CLIConfig
from platforms.cli.processes.convert import ConvertCommand


def _run_convert(tmp_path, monkeypatch, entries: dict, *, module="all", fmt="qmd"):
    """entries: name -> "dir_with_src" | "dir_no_src" | "file"."""
    src_dir = tmp_path / "data" / "src"
    src_dir.mkdir(parents=True)
    for name, kind in entries.items():
        if kind == "dir_with_src":
            (src_dir / name).mkdir()
            (src_dir / name / f"{name}.py").write_text("x = 1\n", encoding="utf-8")
        elif kind == "dir_no_src":
            (src_dir / name).mkdir()
        else:
            (src_dir / name).write_text("", encoding="utf-8")

    import trentorch.export_sanitizer as sanitizer_module

    monkeypatch.setattr(sanitizer_module, "to_qmd", lambda content: "qmd")
    monkeypatch.setattr(sanitizer_module, "to_ipynb", lambda content: {"cells": []})
    monkeypatch.setattr(sanitizer_module, "to_sandbox_code", lambda content: "code")
    monkeypatch.setattr(sanitizer_module, "to_platform_yaml", lambda content, module_name=None: "yaml: true")

    cmd = ConvertCommand(CLIConfig.from_project_root(tmp_path))
    buf = StringIO()
    cmd.console = Console(file=buf, width=200, no_color=True)
    result = cmd.run(Namespace(module=module, format=fmt, out=str(tmp_path / "build")))
    return result, buf.getvalue()


# ---------------------------------------------------------------------------
# "all" filter: d.is_dir() and not d.name.startswith((".", "_"))
# ---------------------------------------------------------------------------


def test_regular_module_directory_is_converted(tmp_path, monkeypatch):
    """Baseline: is_dir() True, name doesn't start with "." or "_" ->
    included."""
    _, out = _run_convert(tmp_path, monkeypatch, {"01_tensor": "dir_with_src"})
    assert "01_tensor" in out
    assert "Converting 1 module" in out


def test_dotfile_directory_is_excluded_from_all(tmp_path, monkeypatch):
    """is_dir() True, name starts with "." -> excluded. Paired with the
    baseline: only the leading-dot name differs, isolating that half of
    the and."""
    _, out = _run_convert(
        tmp_path,
        monkeypatch,
        {"01_tensor": "dir_with_src", ".hidden": "dir_with_src"},
    )
    assert "Converting 1 module" in out


def test_underscore_prefixed_directory_is_excluded_from_all(tmp_path, monkeypatch):
    """is_dir() True, name starts with "_" -> excluded. Paired with the
    baseline: only the leading-underscore name differs, isolating that
    half of the and (distinct atom from the dot-prefix test, since
    startswith((".", "_")) is itself a 2-way check inside the not)."""
    _, out = _run_convert(
        tmp_path,
        monkeypatch,
        {"01_tensor": "dir_with_src", "__pycache__": "dir_with_src"},
    )
    assert "Converting 1 module" in out


def test_plain_file_is_excluded_from_all(tmp_path, monkeypatch):
    """is_dir() False (a regular file) -> excluded regardless of name.
    Paired with the baseline: only is_dir()'s result differs, isolating
    that half of the and."""
    _, out = _run_convert(
        tmp_path,
        monkeypatch,
        {"01_tensor": "dir_with_src", "readme.txt": "file"},
    )
    assert "Converting 1 module" in out


# ---------------------------------------------------------------------------
# specific-module OR: d.is_dir() and (name == module or
#                                      name.startswith(f"{module}_") or
#                                      name.endswith(f"_{module}"))
# ---------------------------------------------------------------------------


def test_exact_name_match_is_found(tmp_path, monkeypatch):
    """Baseline: is_dir() True, name == args.module -> found."""
    result, out = _run_convert(tmp_path, monkeypatch, {"tensor": "dir_with_src"}, module="tensor")
    assert result == 0
    assert "Module not found" not in out


def test_prefix_match_is_found(tmp_path, monkeypatch):
    """name == module False, name.startswith(f"{module}_") True ->
    found. Paired with the baseline: only which disjunct matches
    differs, isolating this atom."""
    result, out = _run_convert(tmp_path, monkeypatch, {"01_tensor": "dir_with_src"}, module="01")
    assert result == 0
    assert "Module not found" not in out


def test_suffix_match_is_found(tmp_path, monkeypatch):
    """Neither exact nor prefix match, name.endswith(f"_{module}") True
    -> found. Isolates the third disjunct."""
    result, out = _run_convert(tmp_path, monkeypatch, {"foo_tensor": "dir_with_src"}, module="tensor")
    assert result == 0
    assert "Module not found" not in out


def test_no_match_reports_module_not_found(tmp_path, monkeypatch):
    """All three disjuncts False -> not found, run() returns 1. Paired
    with the exact-match baseline: only the module name's relation to
    the directory name differs."""
    result, out = _run_convert(tmp_path, monkeypatch, {"01_tensor": "dir_with_src"}, module="unrelated")
    assert result == 1
    assert "Module not found: unrelated" in out


def test_file_named_exactly_like_module_is_not_found(tmp_path, monkeypatch):
    """is_dir() False, even with an exact name match -> not found.
    Paired with the exact-match baseline: only is_dir()'s result
    differs, isolating that half of the outer and."""
    result, out = _run_convert(tmp_path, monkeypatch, {"tensor": "file"}, module="tensor")
    assert result == 1
    assert "Module not found: tensor" in out


def test_first_match_wins_and_stops_searching(tmp_path, monkeypatch):
    """The specific-module loop breaks on the first match; a module
    lacking a source file simply produces zero converted artifacts
    rather than falling through to a later, unrelated matching dir."""
    result, out = _run_convert(tmp_path, monkeypatch, {"01_tensor": "dir_no_src"}, module="01")
    assert result == 0
    assert "Converting 1 module" in out
    assert "Successfully generated 0 artifact" in out
