"""
Regression coverage for PR #161 / issue #158: DevTestCommand._run_inline_tests
hides the real failure reason unless --ci is passed.

Both the export step (Step 1) and the module-complete step (Step 2) buffer
their real output into a quiet console instead of writing it to the real
one, then only dumped that buffer inside `if ci_mode:`. A local, non-CI run
that hit either failure got a bare "FAILED" line with nothing to
self-diagnose from.

PR #161 fixed Step 1's branch. Step 2's branch, five lines below it in the
same function, had the identical gap and was left unfixed -- caught in
review, fixed here alongside a regression test for both, asserting on the
actual printed console output (not an internal return value), since that's
exactly the kind of check that would have caught the Step 2 sibling
automatically instead of relying on someone noticing on review.
"""

from io import StringIO
from unittest.mock import patch

from rich.console import Console

from platforms.cli.cli_platform.dev.test import DevTestCommand
from platforms.cli.core.config import CLIConfig


def _run_inline_single_module(tmp_path, monkeypatch, *, export_ok, complete_ok, complete_output):
    """Drive DevTestCommand._run_inline_tests() for a single module, with
    the export and module-complete steps faked out so the test controls
    exactly which step fails and what it wrote to its own quiet console
    before failing."""
    monkeypatch.setattr(
        "platforms.cli.core.modules.get_module_mapping",
        lambda: {"01": "01_tensor"},
    )

    def fake_export(self, module_names, console):
        return 0 if export_ok else 1

    def fake_complete(self, module_num, skip_tests, skip_export):
        # Simulate the real behavior: complete_module prints its failure
        # detail to its own (quiet) console before returning a non-zero rc.
        if complete_output:
            self.console.print(complete_output)
        return 0 if complete_ok else 1

    monkeypatch.setattr(
        "platforms.cli.cli_platform.dev.export.DevExportCommand._export_specific_modules",
        fake_export,
    )
    monkeypatch.setattr(
        "platforms.cli.processes.module_workflow.ModuleWorkflowCommand.complete_module",
        fake_complete,
    )

    cmd = DevTestCommand(CLIConfig.from_project_root(tmp_path))
    buf = StringIO()
    cmd.console = Console(file=buf, width=120, no_color=True)

    with patch("builtins.print"):
        cmd._run_inline_tests(tmp_path, module="01", verbose=False, ci_mode=False)

    return buf.getvalue()


def test_export_failure_shows_buffered_output_without_ci(tmp_path, monkeypatch):
    """Step 1 (export): the fix PR #161 actually made."""
    out = _run_inline_single_module(
        tmp_path, monkeypatch, export_ok=False, complete_ok=True, complete_output=None
    )
    assert "EXPORT FAILED" in out


def test_module_complete_failure_shows_buffered_output_without_ci(tmp_path, monkeypatch):
    """Step 2 (module complete): the sibling bug caught in review, fixed
    alongside this test. Before the fix, a non-CI run reaching this branch
    printed only 'Failed' with none of complete_module's own diagnostic
    output, identical to the pre-PR-161 export-failure symptom."""
    out = _run_inline_single_module(
        tmp_path,
        monkeypatch,
        export_ok=True,
        complete_ok=False,
        complete_output="NotImplementedError: TODO: implement Tensor.__init__",
    )
    assert "Failed" in out
    assert "NotImplementedError: TODO: implement Tensor.__init__" in out
