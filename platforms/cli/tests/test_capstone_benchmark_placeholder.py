"""
Regression coverage for issue #93 / PR #95: `tren benchmark capstone`
showed a confident "Complete! 90/100" result -- saved as a real file and
offered for public submission -- even with 0 modules completed.

Root cause: the "is Module 20 done" check tested whether
`trentorch.olympics` could be imported. That module ships pre-built and
committed to the repo (the same root cause as issue #71), so the import
always succeeded regardless of the student's real progress, and the code
always fell through to the "full" capstone path -- which was itself still
an unfinished, hardcoded placeholder.

The fix checks the student's own `user_data/progress.json` instead, and
both the "full" and "simplified" fallback paths now mark their saved
results `"placeholder": True` and print an on-screen warning, since the
simplified fallback (what every under-Module-20 student now hits) had
the exact same silent-fake-score problem the "full" path did.
"""

import json
from argparse import Namespace
from io import StringIO

from rich.console import Console

from platforms.cli.core.config import CLIConfig
from platforms.cli.processes.benchmark import BenchmarkCommand


def _run_capstone(tmp_path, monkeypatch, completed_modules):
    monkeypatch.chdir(tmp_path)
    user_data = tmp_path / "user_data"
    user_data.mkdir()
    (user_data / "progress.json").write_text(
        json.dumps({"completed_modules": completed_modules}), encoding="utf-8"
    )

    config = CLIConfig.from_project_root(tmp_path)
    cmd = BenchmarkCommand(config)
    cmd.console = Console(file=StringIO(), width=120, no_color=True)

    args = Namespace(track="all")
    cmd._run_capstone(args)
    return cmd.console.file.getvalue(), user_data / "benchmarks"


def test_zero_modules_falls_back_to_simplified_not_a_fake_full_score(tmp_path, monkeypatch):
    """The concrete regression case for issue #93: 0 completed modules must
    never produce the old "Complete! 90/100" full-capstone result."""
    output, benchmark_dir = _run_capstone(tmp_path, monkeypatch, completed_modules=[])

    assert "Module 20 (Capstone) not complete" in output
    assert "90/100" not in output
    assert "Running full capstone benchmark suite" not in output

    simplified_files = list(benchmark_dir.glob("capstone_simplified_*.json"))
    assert len(simplified_files) == 1
    saved = json.loads(simplified_files[0].read_text(encoding="utf-8"))
    assert saved["placeholder"] is True


def test_simplified_fallback_warns_on_screen_not_just_in_the_saved_json(tmp_path, monkeypatch):
    """The gap found reviewing PR #95: the simplified fallback -- what every
    under-Module-20 student hits post-fix -- must warn on-screen that its
    score is a fixed placeholder, not bury that only in the saved file's
    "note" field where nobody reads it."""
    output, _ = _run_capstone(tmp_path, monkeypatch, completed_modules=[])

    assert "placeholder" in output.lower()


def test_module_20_complete_still_flags_the_full_result_as_placeholder(tmp_path, monkeypatch):
    """Even once a student genuinely completes Module 20, the "full"
    capstone path is still an unfinished placeholder (hardcoded numbers) --
    it must say so on-screen and in the saved file, not present fixed
    numbers as if they were computed from the student's own code."""
    output, benchmark_dir = _run_capstone(tmp_path, monkeypatch, completed_modules=["20"])

    assert "placeholder" in output.lower()

    full_files = list(benchmark_dir.glob("capstone_2*.json"))
    full_files = [f for f in full_files if "simplified" not in f.name]
    assert len(full_files) == 1
    saved = json.loads(full_files[0].read_text(encoding="utf-8"))
    assert saved["placeholder"] is True
