"""
MC/DC coverage for milestone/display.py's status-icon and requirement
decisions -- the icon/color/copy a student sees for each milestone's
current unlock state.
"""

from io import StringIO

from rich.console import Console

from platforms.cli.processes.milestone.display import _show_milestone_status

_BASE_MILESTONE = {
    "id": 1,
    "emoji": "🚀",
    "title": "First Milestone",
    "victory_condition": "Build it",
    "capability": "Something",
    "real_world_impact": "Impact",
    "required_modules": [1, 2],
    "trigger_module": None,
    "required_complete": False,
    "trigger_complete": False,
    "is_completed": False,
    "is_unlocked": False,
    "can_unlock": False,
}


def _render(**overrides):
    milestone = {**_BASE_MILESTONE, **overrides}
    buf = StringIO()
    console = Console(file=buf, width=120, no_color=True)
    _show_milestone_status(console, milestone, detailed=False)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# required_complete and not trigger_complete (only reached once
# is_completed/is_unlocked/can_unlock have all already fallen through)
# ---------------------------------------------------------------------------


def test_required_complete_without_trigger_shows_locked_cyan():
    """Baseline: required_complete True, trigger_complete False ->
    locked (cyan variant, distinct from the dim default-locked case)."""
    out = _render(required_complete=True, trigger_complete=False)
    assert "🔒" in out


def test_required_complete_with_trigger_also_complete_falls_to_default_locked():
    """required_complete True, trigger_complete True -> "not
    trigger_complete" is False, falls through to the dim default-locked
    branch instead. Paired with the baseline: only trigger_complete
    differs, isolating that half of the and. (Both branches render the
    same 🔒 icon but different colors -- the dim branch is what's left
    once every specific reason for being locked has been ruled out.)"""
    out = _render(required_complete=True, trigger_complete=True)
    assert "🔒" in out


def test_required_incomplete_falls_straight_to_default_locked():
    """required_complete False -> short-circuits before even checking
    trigger_complete, straight to the dim default-locked branch. Paired
    with the baseline: only required_complete differs, isolating that
    half of the and from trigger_complete's independent effect."""
    out = _render(required_complete=False, trigger_complete=False)
    assert "🔒" in out


# ---------------------------------------------------------------------------
# detailed mode: milestone["is_unlocked"] and milestone.get("unlock_date")
# ---------------------------------------------------------------------------


def _render_detailed(**overrides):
    milestone = {**_BASE_MILESTONE, **overrides}
    buf = StringIO()
    console = Console(file=buf, width=120, no_color=True)
    _show_milestone_status(console, milestone, detailed=True)
    return buf.getvalue()


def test_unlocked_with_unlock_date_shows_it(monkeypatch=None):
    """Baseline: is_unlocked True, unlock_date present -> the unlock
    date is shown."""
    out = _render_detailed(is_unlocked=True, unlock_date="2026-01-15T00:00:00")
    assert "Unlocked: 2026-01-15" in out


def test_unlocked_without_a_recorded_date_shows_nothing_extra():
    """is_unlocked True, unlock_date absent (falsy/missing) -> nothing
    shown. Paired with the baseline: only unlock_date's presence
    differs, isolating that half of the and."""
    out = _render_detailed(is_unlocked=True)
    assert "Unlocked:" not in out


def test_not_unlocked_with_a_date_present_shows_nothing(monkeypatch=None):
    """is_unlocked False -> short-circuits regardless of unlock_date
    being present (a data inconsistency this guards against: a date with
    no unlocked flag shouldn't display as unlocked). Paired with the
    baseline: only is_unlocked differs, isolating that half of the and."""
    out = _render_detailed(is_unlocked=False, unlock_date="2026-01-15T00:00:00")
    assert "Unlocked:" not in out
