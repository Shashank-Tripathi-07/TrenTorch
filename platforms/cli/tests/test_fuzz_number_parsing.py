"""
Hypothesis-based fuzz coverage for the codebase's number-parsing entry
points -- functions that take a raw string (a CLI arg, or content read back
from progress.json) and try to turn it into an int.

Found via survey: `str.isdigit()` returns True for 128 distinct Unicode
code points (superscripts like "²", Devanagari/Tamil/etc. numerals,
circled digits, ...) that `int()` then rejects with ValueError -- so the
common `if s.isdigit(): int(s)` pattern is not actually safe against
arbitrary text, only against ASCII digits. Both bugs here were found by
this fuzz pass, not assumed in advance.
"""

from hypothesis import example, given
from hypothesis import strategies as st

from platforms.cli.core.modules import normalize_module_number
from platforms.cli.processes.milestone import _module_progress_to_int

# A curated sample of the 128 "isdigit() True, int() raises" code points
# (superscript/subscript digits and Ethiopic digits, verified individually
# against int() -- not every isdigit()-True character behaves this way;
# e.g. Tibetan digit one (U+0F21) is a real decimal digit int() accepts
# fine, so it's deliberately not in this list), used as concrete
# regression examples alongside the broader random-text fuzzing below.
ISDIGIT_BUT_NOT_INT_PARSEABLE = ["²", "³", "⁹", "₀", "፩", "፰"]


# ---------------------------------------------------------------------------
# normalize_module_number: must never raise, for any string input
# ---------------------------------------------------------------------------


@given(st.text())
@example("²")  # superscript two -- the original crash this fixes
@example("²_module")
def test_normalize_module_number_never_raises(module_input):
    """No string input should crash this -- worst case, an unrecognized
    input is returned unchanged (the function's own documented fallback
    for non-numeric input), never an uncaught exception."""
    result = normalize_module_number(module_input)
    assert isinstance(result, str)


def test_normalize_module_number_handles_isdigit_but_unparseable_chars():
    """Concrete regression check for the specific bug class: each of
    these isdigit()s True but int() rejects. Before the fix, this raised
    ValueError instead of falling back to the unrecognized-input path."""
    for char in ISDIGIT_BUT_NOT_INT_PARSEABLE:
        assert normalize_module_number(char) == char
        assert normalize_module_number(f"{char}_tensor") == f"{char}_tensor"


def test_normalize_module_number_still_normalizes_real_ascii_digits():
    """The fix doesn't regress the actual documented behavior."""
    assert normalize_module_number("1") == "01"
    assert normalize_module_number("15") == "15"
    assert normalize_module_number("15_quantization") == "15"


# ---------------------------------------------------------------------------
# _module_progress_to_int: must never raise, for any input shape
# ---------------------------------------------------------------------------


@given(st.one_of(st.text(), st.integers(), st.none(), st.floats(), st.booleans()))
@example("²_tensor")
def test_module_progress_to_int_never_raises(value):
    """progress.json's completed_modules list isn't schema-validated, so
    this needs to tolerate arbitrary JSON-decodable values, not just the
    well-formed "01_tensor" strings it normally sees."""
    result = _module_progress_to_int(value)
    assert result is None or isinstance(result, int)


def test_module_progress_to_int_handles_isdigit_but_unparseable_prefix():
    """Same bug class as normalize_module_number, different function:
    a module entry whose numeric-looking prefix isn't int()-parseable
    should resolve to None (unrecognized), not raise."""
    for char in ISDIGIT_BUT_NOT_INT_PARSEABLE:
        assert _module_progress_to_int(f"{char}_tensor") is None


def test_module_progress_to_int_still_parses_real_entries():
    assert _module_progress_to_int("01_tensor") == 1
    assert _module_progress_to_int("01") == 1
    assert _module_progress_to_int(1) == 1
    assert _module_progress_to_int("not_a_number") is None
