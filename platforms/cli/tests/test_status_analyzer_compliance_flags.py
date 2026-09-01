"""
MC/DC coverage for analyze_module's compliance content-sniffing: six
decisions that scan a module's source text for section markers to
compute its compliance_score. Five are 2-phrase ORs (either phrasing
counts); one (has_testing) is an AND.
"""

import subprocess

import pytest

from platforms.cli.core.status_analyzer import TinyTorchStatusAnalyzer


def _analyze_with_content(tmp_path, monkeypatch, content):
    module_dir = tmp_path / "01_tensor"
    module_dir.mkdir()
    (module_dir / "01_tensor.py").write_text(content, encoding="utf-8")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, "SUCCESS", ""))
    analyzer = TinyTorchStatusAnalyzer(repo_path=tmp_path)
    return analyzer.analyze_module(module_dir)


# ---------------------------------------------------------------------------
# Five 2-phrase ORs, each: phrase A alone / phrase B alone / neither
# ---------------------------------------------------------------------------

_OR_FLAGS = [
    ("has_introduction", "Module Introduction", "# Introduction"),
    ("has_math_background", "Mathematical Background", "Mathematical Foundation"),
    ("has_implementation", "Implementation", "Core Implementation"),
    ("has_ml_systems_questions", "ML Systems Thinking", "Systems Thinking"),
    ("has_summary", "Module Summary", "MODULE SUMMARY"),
]


@pytest.mark.parametrize("flag,phrase_a,phrase_b", _OR_FLAGS, ids=[f[0] for f in _OR_FLAGS])
def test_first_phrase_alone_sets_the_flag(tmp_path, monkeypatch, flag, phrase_a, phrase_b):
    """Baseline: phrase A present, phrase B absent -> flag True."""
    status = _analyze_with_content(tmp_path, monkeypatch, phrase_a)
    assert getattr(status, flag) is True


@pytest.mark.parametrize("flag,phrase_a,phrase_b", _OR_FLAGS, ids=[f[0] for f in _OR_FLAGS])
def test_second_phrase_alone_sets_the_flag(tmp_path, monkeypatch, flag, phrase_a, phrase_b):
    """Isolates the second disjunct: phrase B present, phrase A absent.
    Paired with the test above: only which phrase is present differs."""
    status = _analyze_with_content(tmp_path, monkeypatch, phrase_b)
    assert getattr(status, flag) is True


@pytest.mark.parametrize("flag,phrase_a,phrase_b", _OR_FLAGS, ids=[f[0] for f in _OR_FLAGS])
def test_neither_phrase_leaves_the_flag_false(tmp_path, monkeypatch, flag, phrase_a, phrase_b):
    """Neither phrase present -> flag False. Paired with both tests
    above: only phrase presence differs, isolating each disjunct."""
    status = _analyze_with_content(tmp_path, monkeypatch, "nothing relevant here")
    assert getattr(status, flag) is False


# ---------------------------------------------------------------------------
# has_testing = "Testing" in content and "test_" in content
# ---------------------------------------------------------------------------


def test_testing_word_and_test_prefix_both_present_sets_the_flag(tmp_path, monkeypatch):
    """Baseline: both substrings present -> True."""
    status = _analyze_with_content(tmp_path, monkeypatch, "## Testing\ndef test_foo(): pass")
    assert status.has_testing is True


def test_testing_word_without_test_prefix_leaves_it_false(tmp_path, monkeypatch):
    """ "Testing" present, "test_" absent -> the and is False. Paired
    with the baseline: only "test_"'s presence differs, isolating that
    half of the and."""
    status = _analyze_with_content(tmp_path, monkeypatch, "## Testing\nno prefix here")
    assert status.has_testing is False


def test_test_prefix_without_testing_word_leaves_it_false(tmp_path, monkeypatch):
    """ "test_" present, "Testing" absent -> the and is False. Paired
    with the baseline: only "Testing"'s presence differs, isolating the
    other half of the and."""
    status = _analyze_with_content(tmp_path, monkeypatch, "def test_foo(): pass")
    assert status.has_testing is False


# ---------------------------------------------------------------------------
# check_all_modules: d.is_dir() and not d.name.startswith(".")
# ---------------------------------------------------------------------------


def test_check_all_modules_includes_real_module_dirs(tmp_path, monkeypatch):
    """Baseline: is_dir() True, doesn't start with "." True -> included."""
    (tmp_path / "01_tensor").mkdir()
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, "SUCCESS", ""))
    analyzer = TinyTorchStatusAnalyzer(repo_path=tmp_path)
    analyzer.modules_path = tmp_path
    modules = analyzer.check_all_modules()
    assert "01_tensor" in modules


def test_check_all_modules_skips_dotfiles_and_dotdirs(tmp_path, monkeypatch):
    """is_dir() True, but name starts with "." -> excluded. Paired with
    the baseline: only the leading-dot check differs, isolating that
    half of the and."""
    (tmp_path / "01_tensor").mkdir()
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, "SUCCESS", ""))
    analyzer = TinyTorchStatusAnalyzer(repo_path=tmp_path)
    analyzer.modules_path = tmp_path
    modules = analyzer.check_all_modules()
    assert ".git" not in modules


def test_check_all_modules_skips_plain_files(tmp_path, monkeypatch):
    """is_dir() False (a plain file) -> excluded regardless of its name.
    Paired with the baseline: only is_dir()'s result differs, isolating
    that half of the and."""
    (tmp_path / "01_tensor").mkdir()
    (tmp_path / "README.md").write_text("", encoding="utf-8")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, "SUCCESS", ""))
    analyzer = TinyTorchStatusAnalyzer(repo_path=tmp_path)
    analyzer.modules_path = tmp_path
    modules = analyzer.check_all_modules()
    assert "README.md" not in modules
