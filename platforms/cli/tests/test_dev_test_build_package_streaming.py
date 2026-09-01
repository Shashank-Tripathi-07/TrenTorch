"""
MC/DC coverage for DevTestCommand._build_package's CI-mode streaming
keyword filter:
    if any(x in line for x in ["Converting", "Exported", "✅", "❌", "Module"]):

A generator-expression any() over 5 literal keywords, each isolated
individually the way test_runtime_ci_and_interactive_detection.py isolated
_CI_ENV_VARS.
"""

import subprocess
from pathlib import Path

import pytest

from platforms.cli.cli_platform.dev.test import DevTestCommand
from platforms.cli.core.config import CLIConfig

TRENTORCH_ROOT = Path(__file__).resolve().parents[3]

_KEYWORDS = ["Converting", "Exported", "✅", "❌", "Module"]


class _FakeProcess:
    def __init__(self, lines, returncode=0):
        self.stdout = iter(lines)
        self.returncode = returncode

    def wait(self, timeout=None):
        return self.returncode


def _build(monkeypatch, capsys, lines):
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: _FakeProcess(lines))
    cmd = DevTestCommand(CLIConfig.from_project_root(TRENTORCH_ROOT))
    cmd._build_package(TRENTORCH_ROOT, verbose=False, ci_mode=True)
    return capsys.readouterr().out


def test_line_with_none_of_the_five_keywords_is_not_printed(monkeypatch, capsys):
    """Baseline: none of the 5 keywords present -> line filtered out."""
    out = _build(monkeypatch, capsys, ["some unrelated debug line"])
    assert "some unrelated debug line" not in out


@pytest.mark.parametrize("keyword", _KEYWORDS)
def test_each_keyword_alone_is_sufficient_to_print_the_line(monkeypatch, capsys, keyword):
    """Each of the five keywords, present alone in an otherwise
    unrelated line, independently makes the any() True -> line printed.
    Paired with the baseline: only this one keyword's presence differs,
    isolating it from the other four atoms in the any()."""
    line = f"prefix {keyword} suffix"
    out = _build(monkeypatch, capsys, [line])
    assert line in out
