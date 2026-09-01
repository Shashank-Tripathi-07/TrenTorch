"""
MC/DC coverage for PreflightCommand._check_structure's directory-existence
decision (path.exists() and path.is_dir()), which appears twice
(required and optional directories).
"""

from platforms.cli.cli_platform.dev.preflight import CheckStatus, PreflightCommand
from platforms.cli.core.config import CLIConfig


def _structure_check(tmp_path, *, data_modules_kind, trentorch_kind):
    """kind: "dir", "file", or None (doesn't exist)."""
    (tmp_path / "data" / "src").mkdir(parents=True)
    (tmp_path / "data" / "milestones").mkdir(parents=True)
    (tmp_path / "tests").mkdir(parents=True)
    (tmp_path / "platforms" / "cli").mkdir(parents=True)

    if data_modules_kind == "dir":
        (tmp_path / "data" / "modules").mkdir(parents=True)
    elif data_modules_kind == "file":
        (tmp_path / "data").mkdir(parents=True, exist_ok=True)
        (tmp_path / "data" / "modules").write_text("", encoding="utf-8")

    if trentorch_kind == "dir":
        (tmp_path / "data" / "trentorch").mkdir(parents=True, exist_ok=True)
    elif trentorch_kind == "file":
        (tmp_path / "data").mkdir(parents=True, exist_ok=True)
        (tmp_path / "data" / "trentorch").write_text("", encoding="utf-8")

    cmd = PreflightCommand(CLIConfig.from_project_root(tmp_path))
    category = cmd._check_structure(tmp_path, verbose=False)
    checks_by_name = {c.name: c for c in category.checks}
    return checks_by_name


# ---------------------------------------------------------------------------
# Required dir loop: path.exists() and path.is_dir()
# ---------------------------------------------------------------------------


def test_existing_directory_passes(tmp_path):
    """Baseline: exists() True, is_dir() True -> PASS."""
    checks = _structure_check(tmp_path, data_modules_kind="dir", trentorch_kind=None)
    assert checks["data/modules/ exists"].status == CheckStatus.PASS


def test_missing_directory_fails(tmp_path):
    """exists() False -> FAIL, is_dir() never matters. Paired with the
    baseline: only existence differs, isolating that half of the and."""
    checks = _structure_check(tmp_path, data_modules_kind=None, trentorch_kind=None)
    assert checks["data/modules/ exists"].status == CheckStatus.FAIL


def test_path_exists_as_a_file_not_a_directory_fails(tmp_path):
    """exists() True, is_dir() False (it's a regular file at that path)
    -> FAIL. Paired with the baseline: only is_dir()'s result differs,
    isolating that half of the and."""
    checks = _structure_check(tmp_path, data_modules_kind="file", trentorch_kind=None)
    assert checks["data/modules/ exists"].status == CheckStatus.FAIL


# ---------------------------------------------------------------------------
# Optional dir loop: same decision, separate loop (data/trentorch/)
# ---------------------------------------------------------------------------


def test_optional_directory_present_passes(tmp_path):
    """Same decision, the optional-directories loop: exists() True,
    is_dir() True -> PASS."""
    checks = _structure_check(tmp_path, data_modules_kind="dir", trentorch_kind="dir")
    assert checks["data/trentorch/ exists"].status == CheckStatus.PASS


def test_optional_directory_as_a_file_warns_not_fails(tmp_path):
    """Same decision in the optional loop: exists() True, is_dir() False
    -> WARN (not FAIL -- optional dirs use WARN on either "missing" or
    "not a directory", the required-dirs loop's own separate FAIL
    branch is a distinct copy of the same is_dir() decision, not this
    one)."""
    checks = _structure_check(tmp_path, data_modules_kind="dir", trentorch_kind="file")
    assert checks["data/trentorch/ exists"].status == CheckStatus.WARN


# ---------------------------------------------------------------------------
# Regression: modules_dir.is_dir() before the module-count iterdir() call.
# Used to be modules_dir.exists(), which raised NotADirectoryError and
# crashed the whole preflight run if data/modules existed as a plain file.
# ---------------------------------------------------------------------------


def test_data_modules_as_a_file_does_not_crash_the_module_count_check(tmp_path):
    """A state the required-dirs loop already flags as FAIL (data/modules
    exists but isn't a directory) used to crash _check_structure entirely
    a few lines later, instead of just skipping the module-count check
    it can't meaningfully run in that state."""
    checks = _structure_check(tmp_path, data_modules_kind="file", trentorch_kind=None)
    assert checks["data/modules/ exists"].status == CheckStatus.FAIL
    assert not any(name.startswith("Module count") for name in checks)
