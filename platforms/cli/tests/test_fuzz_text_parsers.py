"""
Hypothesis fuzz coverage for the codebase's other pure text-parsing
functions, surveyed after test_fuzz_number_parsing.py's isdigit()/int()
findings: export_utils.py's cell-splitting functions (_cell_header,
_is_solution_cell, _split_directives, make_stub_variant,
make_solution_variant), core/modules.py's lightweight YAML parser, and
test_runner.py's subprocess-output parsers (_parse_test_output,
_parse_pytest_output, _extract_pytest_error).

These process real file/subprocess content, not just CLI args, so
malformed content is a genuine (if narrower) attack surface -- a
corrupted source file or an unexpected pytest output format shouldn't be
able to crash anything with something other than export_utils.py's own
deliberate, typed UnpairedSolutionCellError. Every function fuzzed here
came back clean (no new bug found) -- this is confirmatory coverage, not
a bug-fix commit, unlike test_fuzz_number_parsing.py.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from platforms.cli.commands.export_utils import (
    UnpairedSolutionCellError,
    _cell_header,
    _is_solution_cell,
    _split_directives,
    make_solution_variant,
    make_stub_variant,
)
from platforms.cli.core.modules import _parse_yaml_file
from platforms.cli.processes.module_workflow.test_runner import (
    _extract_pytest_error,
    _parse_pytest_output,
    _parse_test_output,
)

# ---------------------------------------------------------------------------
# Cell-level helpers: must never raise, for any text
# ---------------------------------------------------------------------------


@given(st.text())
def test_cell_header_never_raises(cell_text):
    assert isinstance(_cell_header(cell_text), str)


@given(st.text())
def test_is_solution_cell_never_raises(cell_text):
    assert isinstance(_is_solution_cell(cell_text), bool)


@given(st.text())
def test_split_directives_never_raises(cell_text):
    header_line, directive_lines, body = _split_directives(cell_text)
    assert isinstance(header_line, str)
    assert isinstance(directive_lines, list)
    assert isinstance(body, str)


# ---------------------------------------------------------------------------
# make_stub_variant / make_solution_variant: the only allowed exception is
# their own deliberate UnpairedSolutionCellError -- anything else (IndexError,
# KeyError, etc.) would be a real crash bug.
# ---------------------------------------------------------------------------


@given(st.text())
@settings(max_examples=300)
def test_make_stub_variant_never_crashes_unexpectedly(source):
    try:
        result = make_stub_variant(source)
        assert isinstance(result, str)
    except UnpairedSolutionCellError:
        pass  # deliberate, typed -- not a crash


@given(st.text())
@settings(max_examples=300)
def test_make_solution_variant_never_crashes_unexpectedly(source):
    try:
        result = make_solution_variant(source)
        assert isinstance(result, str)
    except UnpairedSolutionCellError:
        pass


# A structured strategy that actually generates realistic-ish cell soup
# (multiple "# %%" cells, some solution-tagged, some not, with directive
# lines and blank-line noise) rather than only fully random text -- random
# text alone almost never contains "# %%" or the solution tag literal, so
# it can't reach the pairing logic's real branches.
_CELL_HEADER = st.sampled_from(
    [
        "# %%",
        '# %% tags=["solution"]',
        "# %% tags=['solution']",
        '# %% tags=["solution", "hidden"]',
    ]
)
_DIRECTIVE_LINE = st.sampled_from(["#| export", "#| default_exp core.tensor", "#| hide"])
_BODY_LINE = st.text(alphabet=st.characters(blacklist_characters="\n"), max_size=20)


@st.composite
def _cell_soup(draw):
    n_cells = draw(st.integers(min_value=0, max_value=6))
    parts = []
    for _ in range(n_cells):
        header = draw(_CELL_HEADER)
        n_directives = draw(st.integers(min_value=0, max_value=2))
        directives = [draw(_DIRECTIVE_LINE) for _ in range(n_directives)]
        n_body_lines = draw(st.integers(min_value=0, max_value=3))
        body_lines = [draw(_BODY_LINE) for _ in range(n_body_lines)]
        parts.append("\n".join([header, *directives, *body_lines]))
    return "\n".join(parts)


@given(_cell_soup())
@settings(max_examples=300)
def test_make_stub_variant_handles_structured_cell_soup(source):
    try:
        make_stub_variant(source)
    except UnpairedSolutionCellError:
        pass


@given(_cell_soup())
@settings(max_examples=300)
def test_make_solution_variant_handles_structured_cell_soup(source):
    try:
        make_solution_variant(source)
    except UnpairedSolutionCellError:
        pass


# ---------------------------------------------------------------------------
# _parse_yaml_file (core/modules.py's lightweight module.yaml reader)
# ---------------------------------------------------------------------------


@given(st.text())
def test_parse_yaml_file_never_raises(content):
    result = _parse_yaml_file(content)
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# test_runner.py's subprocess-output parsers: real pytest/inline-test stdout
# and stderr, not just any string, but the format can shift (a pytest
# version bump, a truncated capture, an unrelated crash dumping a traceback
# instead of the expected markers) -- these must degrade gracefully, never
# raise, for arbitrary text standing in for "output we didn't expect."
# ---------------------------------------------------------------------------


@given(st.text(), st.text(), st.integers(min_value=-2, max_value=255))
@settings(max_examples=300)
def test_parse_test_output_never_raises(stdout, stderr, returncode):
    result = _parse_test_output(stdout, stderr, returncode)
    assert isinstance(result, list)


@given(st.text(), st.text())
@settings(max_examples=300)
def test_parse_pytest_output_never_raises(stdout, stderr):
    result = _parse_pytest_output(stdout, stderr)
    assert isinstance(result, list)


@given(st.text(), st.text(), st.text())
@settings(max_examples=300)
def test_extract_pytest_error_never_raises(stdout, stderr, test_path):
    result = _extract_pytest_error(stdout, stderr, test_path)
    assert result is None or isinstance(result, str)


# Structured strategy generating text that actually contains the markers
# these parsers look for ("::", "PASSED"/"FAILED", "✅"/"❌"), so fuzzing
# reaches the real parsing branches rather than only the early-exit path.
_PYTEST_LINE = st.sampled_from(
    [
        "tests/01_tensor/test_x.py::TestClass::test_method PASSED",
        "tests/01_tensor/test_x.py::test_bare FAILED",
        "tests/01_tensor/test_x.py FAILED",
        "::just_colons::PASSED",
        "PASSED",
        "",
    ]
)
_INLINE_LINE = st.sampled_from(
    ["✅ test_one", "❌ test_two: AssertionError boom", "❌", "✅:", "random line"]
)


@given(st.lists(_PYTEST_LINE, max_size=8).map("\n".join), st.text())
@settings(max_examples=300)
def test_parse_pytest_output_handles_marker_soup(stdout, stderr):
    result = _parse_pytest_output(stdout, stderr)
    assert isinstance(result, list)


@given(st.lists(_INLINE_LINE, max_size=8).map("\n".join), st.text(), st.integers(min_value=0, max_value=1))
@settings(max_examples=300)
def test_parse_test_output_handles_marker_soup(stdout, stderr, returncode):
    result = _parse_test_output(stdout, stderr, returncode)
    assert isinstance(result, list)
