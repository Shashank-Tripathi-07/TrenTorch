"""
MC/DC coverage for the file/directory-targeting decisions in the two
reset commands -- real, destructive deletion logic, so getting these
wrong either deletes hand-written files or leaves generated ones behind.
"""

from argparse import Namespace

from platforms.cli.cli_platform.package.reset import ResetCommand
from platforms.cli.cli_platform.system.reset import SystemResetCommand
from platforms.cli.core.config import CLIConfig

# ---------------------------------------------------------------------------
# package/reset.py _reset_package:
#   str(rel_path).replace("\\", "/") not in NON_GENERATED
#   and py_file.name != "__init__.py"
# ---------------------------------------------------------------------------


def _reset_package(tmp_path, monkeypatch, files: dict[str, str]):
    monkeypatch.chdir(tmp_path)
    pkg_dir = tmp_path / "data" / "trentorch"
    for rel_path, content in files.items():
        full = pkg_dir / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")

    cmd = ResetCommand(CLIConfig.from_project_root(tmp_path))
    cmd._reset_package(Namespace(force=True))
    return {p.relative_to(pkg_dir).as_posix() for p in pkg_dir.rglob("*.py")}


def test_a_generated_file_is_removed(tmp_path, monkeypatch):
    """Baseline: not in NON_GENERATED True, not __init__.py True ->
    removed."""
    remaining = _reset_package(tmp_path, monkeypatch, {"core/tensor.py": "x"})
    assert "core/tensor.py" not in remaining


def test_a_non_generated_hand_written_file_is_preserved(tmp_path, monkeypatch):
    """not in NON_GENERATED is False -> the and is False, preserved.
    Paired with the baseline: only NON_GENERATED membership differs,
    isolating that half of the and."""
    remaining = _reset_package(tmp_path, monkeypatch, {"export_sanitizer.py": "x"})
    assert "export_sanitizer.py" in remaining


def test_any_init_file_is_preserved_regardless_of_directory(tmp_path, monkeypatch):
    """py_file.name != "__init__.py" is False -> the and is False,
    preserved, even for an __init__.py nested somewhere not literally
    matching a NON_GENERATED entry. Paired with the baseline: only
    whether the filename is __init__.py differs, isolating that half of
    the and from NON_GENERATED-membership's independent effect."""
    remaining = _reset_package(tmp_path, monkeypatch, {"core/__init__.py": "x"})
    assert "core/__init__.py" in remaining


def test_a_mix_removes_only_the_generated_file(tmp_path, monkeypatch):
    """Sanity check combining all three cases in one reset."""
    remaining = _reset_package(
        tmp_path,
        monkeypatch,
        {
            "core/tensor.py": "x",
            "export_sanitizer.py": "x",
            "core/__init__.py": "x",
        },
    )
    assert remaining == {"export_sanitizer.py", "core/__init__.py"}


# ---------------------------------------------------------------------------
# system/reset.py run(): item.is_dir() and item.name[0].isdigit()
# (module-directory clearing during `tren reset system`)
# ---------------------------------------------------------------------------


def _system_reset_modules(tmp_path, monkeypatch, entries: dict[str, str]):
    """entries: name -> "dir" or "file"."""
    modules_dir = tmp_path / "data" / "modules"
    modules_dir.mkdir(parents=True)
    for name, kind in entries.items():
        if kind == "dir":
            (modules_dir / name).mkdir()
        else:
            (modules_dir / name).write_text("", encoding="utf-8")

    cmd = SystemResetCommand(CLIConfig.from_project_root(tmp_path))
    cmd.run(Namespace(force=True, ci=True, backup=False, keep_progress=True))
    return {p.name for p in modules_dir.iterdir()}


def test_digit_prefixed_module_directory_is_cleared(tmp_path, monkeypatch):
    """Baseline: is_dir() True, name[0].isdigit() True -> removed."""
    remaining = _system_reset_modules(tmp_path, monkeypatch, {"01_tensor": "dir"})
    assert "01_tensor" not in remaining


def test_non_digit_prefixed_directory_is_preserved(tmp_path, monkeypatch):
    """is_dir() True, name[0].isdigit() False -> preserved. Paired with
    the baseline: only the name's first character differs, isolating
    that half of the and."""
    remaining = _system_reset_modules(tmp_path, monkeypatch, {"__pycache__": "dir"})
    assert "__pycache__" in remaining


def test_digit_prefixed_file_is_preserved(tmp_path, monkeypatch):
    """is_dir() False (it's a file, not a directory), even though the
    name starts with a digit -> preserved. Paired with the baseline:
    only is_dir()'s result differs, isolating that half of the and."""
    remaining = _system_reset_modules(tmp_path, monkeypatch, {"01_stray.txt": "file"})
    assert "01_stray.txt" in remaining


# ---------------------------------------------------------------------------
# system/reset.py run(): not args.force and not args.ci
# (the interactive "type 'yes' to confirm" prompt before a destructive
# system reset)
# ---------------------------------------------------------------------------


def _system_reset_prompt(tmp_path, monkeypatch, *, force, ci, response):
    modules_dir = tmp_path / "data" / "modules"
    modules_dir.mkdir(parents=True)
    (modules_dir / "01_tensor").mkdir()

    monkeypatch.setattr("builtins.input", lambda *a, **k: response)
    cmd = SystemResetCommand(CLIConfig.from_project_root(tmp_path))
    cmd.run(Namespace(force=force, ci=ci, backup=False, keep_progress=True))
    return {p.name for p in modules_dir.iterdir()}


def test_neither_force_nor_ci_asks_and_respects_a_no(tmp_path, monkeypatch):
    """Baseline: not force True, not ci True -> the and is True, prompt
    shown; a non-"yes" answer cancels, nothing is deleted."""
    remaining = _system_reset_prompt(tmp_path, monkeypatch, force=False, ci=False, response="n")
    assert "01_tensor" in remaining


def test_force_skips_the_prompt_and_proceeds(tmp_path, monkeypatch):
    """args.force True -> "not force" False, the and is False, no
    prompt -- proceeds straight to deletion regardless of what input()
    would have returned. Paired with the baseline: only force differs,
    isolating that half of the and."""
    remaining = _system_reset_prompt(tmp_path, monkeypatch, force=True, ci=False, response="n")
    assert "01_tensor" not in remaining


def test_ci_skips_the_prompt_and_proceeds(tmp_path, monkeypatch):
    """args.ci True -> "not ci" False, the and is False, no prompt.
    Paired with the baseline: only ci differs, isolating that half of
    the and from force's independent effect."""
    remaining = _system_reset_prompt(tmp_path, monkeypatch, force=False, ci=True, response="n")
    assert "01_tensor" not in remaining
