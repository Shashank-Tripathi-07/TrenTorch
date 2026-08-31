"""
MC/DC coverage for TinyTorchStatusAnalyzer.check_environment()'s venv-detection
decision.

The decision is `hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix")
and sys.base_prefix != sys.prefix)`, three independent conditions (call them
A, B, C). It has no dedicated unit test today: the only thing that touches
it is tests/environment/test_setup_validation.py, which re-derives the same
boolean expression against the *real* running interpreter rather than
exercising the analyzer's own code with each condition varied, so it can't
catch a typo like `and` swapped for `or`, or `!=` swapped for `==`, in this
function.

This gets real MC/DC coverage: four cases, each fully pinning A, B, and C
via monkeypatch (never relying on whatever venv state pytest happens to be
running under), chosen so each condition's independent effect on the
decision outcome is demonstrated by a pair of cases that differ only in
that one condition, with the others held fixed at values that don't mask
it.
"""

import sys

from platforms.cli.core.status_analyzer import TinyTorchStatusAnalyzer


def _virtual_env_active(monkeypatch, tmp_path, *, real_prefix, base_prefix, prefix):
    if real_prefix is None:
        monkeypatch.delattr(sys, "real_prefix", raising=False)
    else:
        monkeypatch.setattr(sys, "real_prefix", real_prefix, raising=False)

    if base_prefix is None:
        monkeypatch.delattr(sys, "base_prefix", raising=False)
    else:
        monkeypatch.setattr(sys, "base_prefix", base_prefix, raising=False)

    monkeypatch.setattr(sys, "prefix", prefix)

    return TinyTorchStatusAnalyzer(repo_path=tmp_path).check_environment()["virtual_env_active"]


def test_real_prefix_alone_drives_true(monkeypatch, tmp_path):
    """A=True, B=False (C short-circuited) -> True."""
    result = _virtual_env_active(
        monkeypatch, tmp_path, real_prefix="/fake/system-python", base_prefix=None, prefix="/fake/venv"
    )
    assert result is True


def test_no_real_prefix_no_base_prefix_is_false(monkeypatch, tmp_path):
    """A=False, B=False -> False. Paired with the test above: only A
    differs (True -> False), isolating A's effect."""
    result = _virtual_env_active(
        monkeypatch, tmp_path, real_prefix=None, base_prefix=None, prefix="/fake/venv"
    )
    assert result is False


def test_base_prefix_true_with_differing_paths_is_true(monkeypatch, tmp_path):
    """A=False, B=True, C=True -> True. Paired with the next test: only B
    differs (True vs False below), C held at True (paths differ)."""
    result = _virtual_env_active(
        monkeypatch, tmp_path, real_prefix=None, base_prefix="/fake/base", prefix="/fake/venv"
    )
    assert result is True


def test_no_base_prefix_attr_is_false(monkeypatch, tmp_path):
    """A=False, B=False -> False. Paired with the previous test: only B
    differs (True -> False), isolating B's effect."""
    result = _virtual_env_active(
        monkeypatch, tmp_path, real_prefix=None, base_prefix=None, prefix="/fake/venv"
    )
    assert result is False


def test_base_prefix_equal_to_prefix_is_false(monkeypatch, tmp_path):
    """A=False, B=True, C=False -> False. Paired with
    test_base_prefix_true_with_differing_paths_is_true: only C differs
    (True -> False), isolating C's effect."""
    result = _virtual_env_active(
        monkeypatch, tmp_path, real_prefix=None, base_prefix="/fake/same-path", prefix="/fake/same-path"
    )
    assert result is False
