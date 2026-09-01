"""
Fuzz coverage for tui/app.py, batch 4 (final batch) of the fuzz-testing
survey (issue #72).

Survey result for this batch: no new bug found. The TUI has no free-text
input widgets at all (it's purely OptionList/Button-driven -- grepped for
`Input(` and found none), so the only external string that ever reaches
it is `--module`/`-m`'s value, passed straight into
TrenTorchApp.__init__ -> normalize_module_number(), the exact function
PR #70 already fixed and fuzz-tested. Every index-based access found
(milestone_keys[index]) is already bounds-checked, and the one other
int() call site (milestone required_modules) operates on hardcoded
curriculum data in constants.py, not external input.

This file is confirmatory: it fuzzes the actual TrenTorchApp constructor
end-to-end (not just the underlying normalize_module_number function in
isolation, which is already covered by test_fuzz_number_parsing.py) to
prove the whole integration point holds, the way test_fuzz_text_parsers.py
did for export_utils.py's already-hardened cell-splitting logic.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from platforms.cli.core.config import CLIConfig

pytest.importorskip("textual")

from platforms.cli.tui.app import TrenTorchApp  # noqa: E402  (after importorskip)


@given(st.one_of(st.none(), st.text()))
@settings(max_examples=200, deadline=None)
def test_app_construction_never_raises_on_arbitrary_initial_module(initial_module):
    """No string handed to --module should be able to crash TUI startup
    before a single frame is even drawn."""
    config = CLIConfig.from_project_root()
    app = TrenTorchApp(config=config, initial_module=initial_module)
    assert app.initial_module  # always resolves to *something*, never blows up


def test_app_construction_handles_isdigit_but_unparseable_char():
    """The specific Unicode-digit character class PR #70 fixed
    (str.isdigit() True, int() raises), exercised through the real
    TUI entry point this time, not the underlying function directly."""
    config = CLIConfig.from_project_root()
    app = TrenTorchApp(config=config, initial_module="²")
    assert app.initial_module == "²"


def test_app_construction_still_resolves_a_real_module():
    config = CLIConfig.from_project_root()
    app = TrenTorchApp(config=config, initial_module="1")
    assert app.initial_module == "01"


def test_app_construction_defaults_when_no_module_given():
    config = CLIConfig.from_project_root()
    app = TrenTorchApp(config=config, initial_module=None)
    assert app.initial_module == "01"
