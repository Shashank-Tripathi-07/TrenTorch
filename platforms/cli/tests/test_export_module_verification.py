"""
MC/DC coverage for ModuleWorkflowCommand.export_module's export-verification
code-line filter:
    code_lines = [line for line in content.split("\n")
                  if line.strip() and not line.strip().startswith("#")]

Two atoms per line: "line.strip()" (non-blank) and
"not line.strip().startswith('#')" (not a comment).
"""

from io import StringIO

from rich.console import Console

from platforms.cli.core.config import CLIConfig
from platforms.cli.processes.module_workflow.workflow import ModuleWorkflowCommand


def _export(tmp_path, monkeypatch, *, exported_content: str):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TREN_DEV_VERIFY_SOLUTION", raising=False)

    module_dir = tmp_path / "data" / "modules" / "01_tensor"
    module_dir.mkdir(parents=True)
    (module_dir / "tensor.ipynb").write_text("{}", encoding="utf-8")

    import platforms.cli.commands.export_utils as export_utils_module

    monkeypatch.setattr(export_utils_module, "get_export_target", lambda path: "core.tensor")
    monkeypatch.setattr(export_utils_module, "ensure_writable_target", lambda target: None)

    lib_dir = tmp_path / "data" / "trentorch" / "core"
    lib_dir.mkdir(parents=True)
    target_file = lib_dir / "tensor.py"

    import nbdev.export as nbdev_export_module

    def fake_nb_export(notebook_path, lib_path):
        target_file.write_text(exported_content, encoding="utf-8")

    monkeypatch.setattr(nbdev_export_module, "nb_export", fake_nb_export)

    cmd = ModuleWorkflowCommand(CLIConfig.from_project_root(tmp_path))
    buf = StringIO()
    cmd.console = Console(file=buf, width=200, no_color=True)
    result = cmd.export_module("01_tensor")
    return result, buf.getvalue()


def test_exported_file_with_real_code_lines_passes_verification(tmp_path, monkeypatch):
    """Baseline: multiple non-blank, non-comment lines -> passes (>= 2
    code_lines required)."""
    result, out = _export(tmp_path, monkeypatch, exported_content="x = 1\ny = 2\n")
    assert result == 0
    assert "verification failed" not in out


def test_blank_lines_are_not_counted_as_code(tmp_path, monkeypatch):
    """line.strip() False (blank line) -> excluded even though it's not
    a comment. Paired with the baseline: an exported file made entirely
    of blank lines has zero code_lines, isolating the blank-line half of
    the and."""
    result, out = _export(tmp_path, monkeypatch, exported_content="\n\n\n")
    assert result == 1
    assert "verification failed" in out


def test_comment_only_lines_are_not_counted_as_code(tmp_path, monkeypatch):
    """line.strip() True, "not line.strip().startswith('#')" False (a
    comment) -> excluded. Paired with the baseline: an exported file
    made entirely of non-blank comment lines has zero code_lines,
    isolating the comment half of the and."""
    result, out = _export(tmp_path, monkeypatch, exported_content="# comment one\n# comment two\n")
    assert result == 1
    assert "verification failed" in out


def test_mix_of_one_real_line_and_comments_falls_short_of_threshold(tmp_path, monkeypatch):
    """Exactly one real code line (plus comments/blanks, all filtered
    out) -> code_lines has length 1, below the "< 2" threshold ->
    still fails. Confirms comment and blank lines are excluded
    independently, not just when one of them is the only content."""
    result, out = _export(tmp_path, monkeypatch, exported_content="# header\n\nx = 1\n")
    assert result == 1
    assert "verification failed" in out
