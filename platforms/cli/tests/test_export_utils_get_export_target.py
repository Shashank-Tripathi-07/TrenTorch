"""
MC/DC coverage for export_utils.get_export_target's in_generated_dir
decision (a 4-way or covering both path-separator styles for
data/modules/ and data/solutions/).
"""

from pathlib import Path, PurePosixPath, PureWindowsPath

from platforms.cli.commands.export_utils import get_export_target


def _with_marker_source(tmp_path, monkeypatch, module_name="01_tensor"):
    monkeypatch.chdir(tmp_path)
    src_dir = tmp_path / "data" / "src" / module_name
    src_dir.mkdir(parents=True)
    (src_dir / f"{module_name}.py").write_text("#| default_exp core.tensor\n", encoding="utf-8")


def test_forward_slash_data_modules_redirects_to_source(tmp_path, monkeypatch):
    """Baseline: "data/modules" in path_str True -> redirected to
    data/src/<module>/, finds the real source file."""
    _with_marker_source(tmp_path, monkeypatch)
    result = get_export_target(PurePosixPath("data/modules/01_tensor"))
    assert result == "core.tensor"


def test_forward_slash_data_solutions_redirects_to_source(tmp_path, monkeypatch):
    """Isolates the second disjunct: "data/solutions" present, the other
    three substrings absent."""
    _with_marker_source(tmp_path, monkeypatch)
    result = get_export_target(PurePosixPath("data/solutions/01_tensor"))
    assert result == "core.tensor"


def test_backslash_data_modules_redirects_to_source(tmp_path, monkeypatch):
    """Isolates the third disjunct: "data\\modules" present (Windows-
    style separator), the other three substrings absent."""
    _with_marker_source(tmp_path, monkeypatch)
    result = get_export_target(PureWindowsPath("data\\modules\\01_tensor"))
    assert result == "core.tensor"


def test_backslash_data_solutions_redirects_to_source(tmp_path, monkeypatch):
    """Isolates the fourth disjunct: "data\\solutions" present, the
    other three substrings absent."""
    _with_marker_source(tmp_path, monkeypatch)
    result = get_export_target(PureWindowsPath("data\\solutions\\01_tensor"))
    assert result == "core.tensor"


def test_path_matching_none_of_the_four_substrings_is_used_as_is(tmp_path, monkeypatch):
    """None of the four disjuncts True -> in_generated_dir False,
    module_path used directly instead of redirecting to data/src/. A
    path with no generated-dir markers and no real source file at that
    exact location returns "unknown" -- proving the redirect didn't
    fire. Paired with the four tests above: only the substring's
    presence differs each time, isolating each disjunct in turn."""
    monkeypatch.chdir(tmp_path)
    # A source file *does* exist at data/src/01_tensor/, but since none
    # of the four substrings match, get_export_target must not find it.
    _with_marker_source(tmp_path, monkeypatch)
    result = get_export_target(Path("somewhere/else/01_tensor"))
    assert result == "unknown"
