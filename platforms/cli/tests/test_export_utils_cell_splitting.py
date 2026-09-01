"""
MC/DC coverage (plus a real fix) for export_utils.py's cell-splitting
logic -- the file docs/testing-strategy.md section 1 names directly as the
cause of two real historical incidents (a dropped import, a dropped
MSEBackward class), both from tooling that reformatted data/src/<NN>/<NN>.py
without understanding its jupytext cell structure. There were zero tests
for this file's own parsing functions before this, despite section 3.2 of
that doc proposing exactly this kind of verification.

## The bug found and fixed here

make_stub_variant/make_solution_variant only ever check whether cells[i+1]
is solution-tagged to decide whether cells[i] is its stub. Neither function
checks whether cells[i] itself is already solution-tagged before falling
through to "append it as an ordinary cell" -- so a solution cell that isn't
reachable as some earlier cell's +1 partner (the very first cell in a file,
or a cell that directly follows another solution cell) falls straight
through unmodified. In make_stub_variant that means the full, unstripped
solution code gets copied into the student-facing package: worse than the
historical incidents (a drop), this is a leak.

Reproduced directly with a synthetic source (two solution cells back to
back, no stub for the second one): the stub variant included the second
solution's complete implementation verbatim. A live scan of all 20 real
data/src/<NN>/<NN>.py files found this pattern doesn't currently occur
anywhere (this suite's test_no_orphaned_solution_cells_in_live_curriculum
makes that check permanent), so this was a latent defect, not an active
leak. Fixed by making both functions raise UnpairedSolutionCellError the
moment they'd otherwise fall through on a solution cell, turning the
previously-silent failure mode loud, matching every other regression in
section 6 of that doc: catch it at the source, not downstream.
"""

from pathlib import Path

import pytest

from platforms.cli.commands.export_utils import (
    UnpairedSolutionCellError,
    _split_directives,
    discover_modules,
    make_solution_variant,
    make_stub_variant,
)

TRENTORCH_ROOT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# _split_directives: two while-loop decisions
#   (a) idx < len(lines) and lines[idx].strip() == ""   (skip blank lines)
#   (b) idx < len(lines) and lines[idx].startswith("#|") (collect directives)
# ---------------------------------------------------------------------------


def test_directives_immediately_after_header_no_blank_line():
    """(a): idx<len True, blank check False on the first line -> loop body
    never runs, directive-collection starts right at the header's next
    line. Paired with the next test: only the blank-line's presence
    differs, isolating (a)'s blank-check condition."""
    header, directives, body = _split_directives("# %% cell\n#| export\ncode_here")
    assert header == "# %% cell"
    assert directives == ["#| export"]
    assert body == "code_here"


def test_blank_lines_tolerated_between_header_and_directives():
    """(a): blank-check True for one iteration, then False -> loop runs
    once. This is the exact pattern the function's own docstring cites
    as a real bug in 05_dataloader.py that a stricter version once
    mishandled. Paired with the test above: only the blank line differs."""
    header, directives, body = _split_directives("# %% cell\n\n#| export\ncode_here")
    assert header == "# %% cell"
    assert directives == ["#| export"]
    assert body == "code_here"


def test_multiple_blank_lines_all_skipped():
    """(a): blank-check True for multiple iterations in a row -- confirms
    the loop doesn't stop after just one blank line."""
    header, directives, body = _split_directives("# %% cell\n\n\n\n#| export\ncode_here")
    assert directives == ["#| export"]
    assert body == "code_here"


def test_no_directives_at_all_falls_through_to_body():
    """(b): the first non-blank line doesn't start with '#|' -> the
    directive-collection loop's body-check is False on its first
    evaluation, zero directives collected. Paired with the header-only
    test above: only the '#|' prefix differs, isolating (b)."""
    header, directives, body = _split_directives("# %% cell\nregular code, no directive")
    assert header == "# %% cell"
    assert directives == []
    assert body == "regular code, no directive"


def test_multiple_directives_collected_until_non_directive_line():
    """(b): blank-check True across several iterations then False --
    confirms multiple #| lines are all collected, not just the first."""
    header, directives, body = _split_directives("# %% cell\n#| export\n#| default_exp foo\ncode")
    assert directives == ["#| export", "#| default_exp foo"]
    assert body == "code"


def test_header_only_cell_exhausts_idx_before_either_loop_runs():
    """(a) and (b): idx==len(lines) from the very first check in both
    loops (a single-line cell, no body at all) -- isolates the
    idx<len(lines) half of both decisions rather than the content check."""
    header, directives, body = _split_directives("# %% cell")
    assert header == "# %% cell"
    assert directives == []
    assert body == ""


def test_directives_with_nothing_after_them_also_exhausts_idx():
    """(b): idx reaches len(lines) exactly while still inside the
    directive-collection loop (no body follows the last directive)."""
    header, directives, body = _split_directives("# %% cell\n#| export")
    assert directives == ["#| export"]
    assert body == ""


# ---------------------------------------------------------------------------
# make_stub_variant / make_solution_variant: the pairing decision
#   i + 1 < len(cells) and _is_solution_cell(cells[i + 1])
# ---------------------------------------------------------------------------


def _cell(header_extra: str, body: str) -> str:
    return f"# %% {header_extra}\n{body}\n\n"


def test_normal_stub_solution_pair_is_recognized():
    """Baseline: i+1<len True, cells[i+1] is solution True -> paired.
    The stub cell gains #| export, the solution cell is dropped from the
    stub variant and kept (alone) in the solution variant."""
    source = _cell("stub-a", "raise NotImplementedError") + _cell('tags=["solution"]', "return 42")

    stub = make_stub_variant(source)
    solution = make_solution_variant(source)

    assert "#| export" in stub
    assert "raise NotImplementedError" in stub
    assert "return 42" not in stub
    assert "return 42" in solution


# ---------------------------------------------------------------------------
# not any(d.strip() == _EXPORT_DIRECTIVE for d in directive_lines)
# (avoids duplicating #| export onto a stub cell that already has it)
# ---------------------------------------------------------------------------


def test_stub_without_export_directive_gets_it_added():
    """Baseline: no directive_lines equal "#| export" -> the not any()
    is True, so it gets appended."""
    source = "# %% stub-a\n#| default_exp core.tensor\nraise NotImplementedError\n\n" + _cell(
        'tags=["solution"]', "return 42"
    )

    stub = make_stub_variant(source)

    assert stub.count("#| export") == 1
    assert "#| default_exp core.tensor" in stub


def test_stub_already_containing_export_directive_is_not_duplicated():
    """Any directive line already equals "#| export" -> not any() is
    False, nothing appended. Paired with the baseline: only the existing
    directive's presence differs, isolating this condition -- without
    it, a stub cell that's already correctly tagged would end up with
    "#| export" twice."""
    source = "# %% stub-a\n#| export\nraise NotImplementedError\n\n" + _cell('tags=["solution"]', "return 42")

    stub = make_stub_variant(source)

    assert stub.count("#| export") == 1


def test_last_cell_has_no_next_cell_to_pair_with():
    """i+1<len is False (this is the last cell) -> not paired, appended
    as-is regardless of whether it's a solution cell. Paired with the
    baseline: only "is there a next cell" differs, isolating i+1<len(cells)."""
    source = _cell("stub-a", "raise NotImplementedError") + _cell("plain-b", "just_code()")

    stub = make_stub_variant(source)

    assert "just_code()" in stub
    assert "#| export" not in stub  # the pairing branch never fired


def test_next_cell_not_solution_tagged_is_not_paired():
    """i+1<len True, but cells[i+1] is NOT solution -> not paired. Paired
    with the baseline: only the next cell's solution tag differs,
    isolating _is_solution_cell(cells[i+1])."""
    source = _cell("cell-a", "x = 1") + _cell("cell-b", "y = 2")

    stub = make_stub_variant(source)

    assert "x = 1" in stub
    assert "y = 2" in stub
    assert "#| export" not in stub


def test_orphaned_solution_cell_raises_instead_of_leaking(monkeypatch=None):
    """Regression for the bug this file fixes: a solution cell that
    directly follows another solution cell (so it's never any cell's
    +1 partner) used to fall through silently. Now it's a loud,
    immediate failure in both variants instead of a leak or a drop."""
    source = (
        _cell("cell-a", "x = 1")
        + _cell('tags=["solution"]', "class First:\n    pass")
        + _cell('tags=["solution"]', "class Second:\n    pass")
    )

    with pytest.raises(Exception) as exc_info:
        make_stub_variant(source)
    assert "Second" not in str(exc_info.value)  # message names the header/index, not full body

    with pytest.raises(Exception):
        make_solution_variant(source)


def test_orphaned_solution_cell_error_type():
    """Same as above, pinned to the specific exception type so a future
    refactor can't accidentally weaken this to a warning or a silent
    default without a test failing."""
    source = _cell('tags=["solution"]', "class Orphan:\n    pass") + _cell("cell-b", "x = 1")

    with pytest.raises(UnpairedSolutionCellError):
        make_stub_variant(source)


def test_orphaned_first_real_cell_also_raises():
    """A second gap found while fixing the first: _CELL_SPLIT's lookahead
    always produces an empty phantom cell at index 0 for any real file
    (they all start with "# %%"). The initial fix's own else-branch check
    missed this: the phantom, never itself solution-tagged, would happily
    "pair" with a solution cell at index 1 and silently absorb it (as a
    drop, not a leak, since _split_directives("") produces nothing).
    Requiring the current cell to have real content before it's eligible
    to pair closes that too -- this is the case
    test_no_orphaned_solution_cells_in_live_curriculum's live scan
    specifically had to check for index 1, not index 0, to catch."""
    source = _cell('tags=["solution"]', "class Orphan:\n    pass")

    with pytest.raises(UnpairedSolutionCellError):
        make_stub_variant(source)
    with pytest.raises(UnpairedSolutionCellError):
        make_solution_variant(source)


def test_no_orphaned_solution_cells_in_live_curriculum():
    """Makes the live scan performed while investigating this bug
    permanent: no data/src/<NN>/<NN>.py file currently has a solution
    cell that isn't reachable as some preceding cell's +1 partner. This
    is exactly the invariant docs/testing-strategy.md section 3.2
    proposes a dedicated verification script for; asserting it here
    means a future edit that reintroduces the pattern fails export
    (via UnpairedSolutionCellError) AND fails this fast, no-build,
    no-export check in the same pytest run other unit tests use."""
    src_dir = TRENTORCH_ROOT / "data" / "src"
    checked = 0
    for module_file in sorted(src_dir.glob("*/*.py")):
        checked += 1
        source = module_file.read_text(encoding="utf-8")
        # Either variant raises identically on an orphan; solution is the
        # cheaper one to fully materialize since it does no directive work.
        make_solution_variant(source)
    assert checked == 20, f"expected 20 curriculum modules, found {checked}"


# ---------------------------------------------------------------------------
# discover_modules: module_dir.is_dir() and module_dir.name not in exclude_dirs
# ---------------------------------------------------------------------------


def test_discover_modules_includes_real_module_dirs(tmp_path):
    """Baseline: is_dir True, name not excluded True -> included."""
    (tmp_path / "01_tensor").mkdir()
    (tmp_path / "02_activations").mkdir()

    assert discover_modules(tmp_path) == ["01_tensor", "02_activations"]


def test_discover_modules_skips_files(tmp_path):
    """is_dir False -> excluded regardless of name. Paired with the
    baseline: only is_dir() differs, isolating that condition."""
    (tmp_path / "01_tensor").mkdir()
    (tmp_path / "not_a_module.py").write_text("x = 1", encoding="utf-8")

    assert discover_modules(tmp_path) == ["01_tensor"]


def test_discover_modules_skips_known_non_module_dirs(tmp_path):
    """is_dir True, but name IS in exclude_dirs -> excluded. Paired with
    the baseline: only exclude-list membership differs, isolating that
    condition."""
    (tmp_path / "01_tensor").mkdir()
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / ".git").mkdir()

    assert discover_modules(tmp_path) == ["01_tensor"]
