"""
MC/DC coverage for core/modules.py's compound decisions: project-root
discovery, display-name derivation, and the tiny hand-rolled YAML-ish
parser for module.yaml.
"""

from platforms.cli.core.modules import (
    _find_project_root,
    _parse_yaml_file,
    get_module_display_name,
)

# ---------------------------------------------------------------------------
# _find_project_root: (current / "pyproject.toml").exists() and
#                      (current / "data" / "src").exists()
#
# The search starts from Path(__file__).resolve().parent -- this module's
# own location -- so isolating each half means monkeypatching that
# module-level __file__ to point into a constructed tmp_path tree instead
# of the real repo, rather than passing a directory in as an argument.
# ---------------------------------------------------------------------------


def _find_root_from(tmp_path, monkeypatch, start_subdir):
    fake_file = tmp_path / start_subdir / "modules.py"
    fake_file.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("platforms.cli.core.modules.__file__", str(fake_file))
    return _find_project_root()


def test_root_found_when_both_markers_present(tmp_path, monkeypatch):
    """Baseline: both markers present at some ancestor -> that directory
    is returned."""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "data" / "src").mkdir(parents=True)

    result = _find_root_from(tmp_path, monkeypatch, "platforms/cli/core")

    assert result == tmp_path


def test_root_falls_back_to_cwd_when_only_pyproject_present(tmp_path, monkeypatch):
    """pyproject.toml exists, data/src doesn't -> that ancestor is
    rejected, search continues up to the filesystem root and falls back
    to cwd. Paired with the baseline: only data/src's presence differs,
    isolating that half of the and."""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")

    result = _find_root_from(tmp_path, monkeypatch, "platforms/cli/core")

    assert result != tmp_path


def test_root_falls_back_to_cwd_when_only_data_src_present(tmp_path, monkeypatch):
    """data/src exists, pyproject.toml doesn't -> also rejected. Paired
    with the baseline: only pyproject.toml's presence differs, isolating
    the other half of the and."""
    (tmp_path / "data" / "src").mkdir(parents=True)

    result = _find_root_from(tmp_path, monkeypatch, "platforms/cli/core")

    assert result != tmp_path


def test_yaml_parser_skips_blank_lines_and_comments():
    """Two independent skip conditions in one loop: `not line` (blank)
    and `line.startswith("#")` (comment) -- both must be individually
    demonstrated to have no effect on real key: value lines around them."""
    content = "\n# a comment\ntitle: Tensors\n\n# another comment\nsubtitle: Foundations\n"
    result = _parse_yaml_file(content)
    assert result == {"title": "Tensors", "subtitle": "Foundations"}


def test_yaml_parser_line_with_no_colon_is_silently_skipped():
    """A non-blank, non-comment line with no ':' -> "if ':' in line" is
    False, contributes nothing. Isolates that check from the blank/comment
    skips above (this line is neither blank nor a comment)."""
    result = _parse_yaml_file("not a key value pair\ntitle: Tensors\n")
    assert result == {"title": "Tensors"}


def test_yaml_parser_value_containing_a_colon_only_splits_on_the_first():
    """split(":", 1) -- confirms a value that itself contains ':' (e.g. a
    URL or a time) isn't truncated."""
    result = _parse_yaml_file("description: See https://example.com:8080/docs\n")
    assert result == {"description": "See https://example.com:8080/docs"}


# ---------------------------------------------------------------------------
# get_module_display_name: folder and "_" in folder
# ---------------------------------------------------------------------------


def test_display_name_splits_on_underscore_and_title_cases(monkeypatch):
    """Baseline: folder truthy, "_" present -> the part after the first
    underscore, title-cased."""
    monkeypatch.setattr("platforms.cli.core.modules.get_module_name", lambda module_input: "15_quantization")
    assert get_module_display_name("15") == "Quantization"


def test_display_name_folder_without_underscore_is_unknown(monkeypatch):
    """folder truthy, but no "_" present -> falls through to "Unknown".
    Paired with the baseline: only the underscore's presence differs."""
    monkeypatch.setattr("platforms.cli.core.modules.get_module_name", lambda module_input: "orphanfolder")
    assert get_module_display_name("99") == "Unknown"


def test_display_name_no_folder_at_all_is_unknown(monkeypatch):
    """folder itself is falsy (module not found) -> "Unknown" without
    ever checking for an underscore. Paired with the baseline: only
    folder's truthiness differs, isolating that half of the and."""
    monkeypatch.setattr("platforms.cli.core.modules.get_module_name", lambda module_input: None)
    assert get_module_display_name("nonexistent") == "Unknown"
