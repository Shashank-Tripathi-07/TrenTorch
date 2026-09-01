"""
MC/DC-adjacent coverage for print_ascii_logo's per-line coloring decision
(i == 0 / i >= 1 and i <= 5 / else). The 7-line ASCII logo is a fixed,
hardcoded constant inside the function rather than a parameter, so the
loop bounds can never see a genuinely different input in production --
independently varying "i >= 1" from "i <= 5" the way other decisions in
this pass do isn't meaningful here. What's real and worth locking down
instead: that the actual, fixed 7-line asset gets exactly the coloring
the code intends, checked directly against Rich's own style spans rather
than guessing from rendered ANSI text.
"""

from rich.align import Align

from platforms.cli.core.console import print_ascii_logo
from platforms.cli.core.theme import Theme


def _captured_logo_text(monkeypatch):
    captured = {}

    def fake_center(renderable, *a, **k):
        captured["text"] = renderable
        return renderable

    monkeypatch.setattr(Align, "center", staticmethod(fake_center))
    print_ascii_logo()
    return captured["text"]


def test_first_line_is_pure_flame_color(monkeypatch):
    """i == 0 -> the whole line gets FLAME_COLOR, no per-character
    splitting."""
    text = _captured_logo_text(monkeypatch)
    first_line = text.plain.split("\n")[0]
    style_at_start = next(s.style for s in text.spans if s.start == 0)
    assert style_at_start == Theme.BRAND_FLAME
    # A single span covering the whole first line confirms it wasn't
    # split character-by-character the way lines 1-5 are.
    assert any(s.start == 0 and s.end == len(first_line) for s in text.spans)


def test_middle_lines_are_split_per_character_for_tiny_letters(monkeypatch):
    """1 <= i <= 5 -> each character is styled individually (TINY_COLOR
    for T/I/N/Y, TORCH_COLOR otherwise), not one span per line."""
    text = _captured_logo_text(monkeypatch)
    lines = text.plain.split("\n")
    line_1_start = len(lines[0]) + 1  # +1 for the newline
    # A per-character split means many short spans in this region, not
    # one long one covering the whole line.
    spans_in_line_1 = [s for s in text.spans if line_1_start <= s.start < line_1_start + len(lines[1])]
    assert len(spans_in_line_1) > 1


def test_last_logo_line_is_pure_torch_color_not_split(monkeypatch):
    """i == 6 (the else branch, past the i <= 5 boundary) -> the whole
    line gets TORCH_COLOR as one span again, like line 0 but a different
    color."""
    text = _captured_logo_text(monkeypatch)
    lines = text.plain.split("\n")
    last_logo_line = lines[6]
    last_line_start = sum(len(line_text) + 1 for line_text in lines[:6])
    matching_spans = [
        s for s in text.spans if s.start == last_line_start and s.end == last_line_start + len(last_logo_line)
    ]
    assert len(matching_spans) == 1
    assert matching_spans[0].style == Theme.BRAND_PRIMARY
