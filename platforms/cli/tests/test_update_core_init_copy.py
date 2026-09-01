"""
MC/DC coverage for UpdateCommand._update_tinytorch_package's core/
__init__.py copy decision: src_core.exists() and dst_core.exists().
"""

from platforms.cli.cli_platform.system.update import UpdateCommand
from platforms.cli.core.config import CLIConfig


def _update_package(tmp_path, *, src_core_exists, dst_core_exists):
    src_pkg = tmp_path / "src_pkg"
    dst_pkg = tmp_path / "dst_pkg"
    src_pkg.mkdir()
    dst_pkg.mkdir()

    if src_core_exists:
        (src_pkg / "core").mkdir()
        (src_pkg / "core" / "__init__.py").write_text("# new version", encoding="utf-8")
    if dst_core_exists:
        (dst_pkg / "core").mkdir()
        (dst_pkg / "core" / "__init__.py").write_text("# old version", encoding="utf-8")

    cmd = UpdateCommand(CLIConfig.from_project_root(tmp_path))
    cmd._update_tinytorch_package(src_pkg, dst_pkg)
    dst_init = dst_pkg / "core" / "__init__.py"
    return dst_init.read_text(encoding="utf-8") if dst_init.exists() else None


def test_both_core_dirs_exist_copies_init(tmp_path):
    """Baseline: src_core.exists() True, dst_core.exists() True ->
    core/__init__.py copied over."""
    result = _update_package(tmp_path, src_core_exists=True, dst_core_exists=True)
    assert result == "# new version"


def test_missing_source_core_dir_does_not_copy(tmp_path):
    """src_core.exists() False -> the and is False, nothing copied.
    Paired with the baseline: only src_core's existence differs,
    isolating that half of the and."""
    result = _update_package(tmp_path, src_core_exists=False, dst_core_exists=True)
    assert result == "# old version"  # untouched


def test_missing_destination_core_dir_does_not_crash_or_copy(tmp_path):
    """dst_core.exists() False -> the and is False, nothing copied (and
    no attempt to write into a directory that doesn't exist). Paired
    with the baseline: only dst_core's existence differs, isolating that
    half of the and."""
    result = _update_package(tmp_path, src_core_exists=True, dst_core_exists=False)
    assert result is None
