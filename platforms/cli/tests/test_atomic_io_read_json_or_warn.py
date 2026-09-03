"""
Coverage for atomic_io.read_json_or_warn -- the read-side companion to
atomic_write_json.

Found by direct audit ("errors should never go silent"): every progress.json
/ milestones.json read site in the CLI caught a corrupted or unreadable
file with a bare `except (OSError, json.JSONDecodeError): pass` and
silently fell back to an empty default. A student whose real progress.json
exists on disk but fails to parse (a manual edit gone wrong, a disk error,
an old pre-atomic-write crash) just sees "0/20 modules complete" with zero
indication their actual data might still be sitting right there,
unreadable -- indistinguishable from genuinely having no progress.

read_json_or_warn() keeps the same "don't crash the CLI" behavior (still
returns the default) but prints exactly what happened and where, so the
user finds out why their progress looks wrong instead of assuming it's
gone.
"""

import json
from io import StringIO

from rich.console import Console

from platforms.cli.core.atomic_io import read_json_or_warn


def test_missing_file_returns_default_silently(tmp_path):
    """A file that was never created (first run, nothing saved yet) is a
    completely normal case -- no warning, just the default."""
    target = tmp_path / "progress.json"
    buf = StringIO()
    console = Console(file=buf, width=120, no_color=True)

    result = read_json_or_warn(target, {"completed_modules": []}, console=console)

    assert result == {"completed_modules": []}
    assert buf.getvalue() == ""


def test_valid_file_returns_its_real_content(tmp_path):
    target = tmp_path / "progress.json"
    target.write_text(json.dumps({"completed_modules": ["01", "02", "03"]}), encoding="utf-8")
    buf = StringIO()
    console = Console(file=buf, width=120, no_color=True)

    result = read_json_or_warn(target, {}, console=console)

    assert result == {"completed_modules": ["01", "02", "03"]}
    assert buf.getvalue() == ""


def test_corrupted_file_warns_and_returns_default(tmp_path):
    """The actual regression: a file that exists but fails to parse must
    warn, not silently pretend it was never there."""
    target = tmp_path / "progress.json"
    target.write_text('{"completed_modules": ["01", "02"', encoding="utf-8")  # truncated JSON
    buf = StringIO()
    console = Console(file=buf, width=120, no_color=True)

    result = read_json_or_warn(
        target, {"completed_modules": []}, console=console, label="Your saved progress"
    )
    out = buf.getvalue()

    assert result == {"completed_modules": []}
    assert "Your saved progress" in out
    assert "couldn't be read" in out
    assert str(target) in out


def test_corrupted_file_path_is_not_word_wrapped(tmp_path):
    """A long enough path must not get reflowed mid-word to fit the
    console's width. Found live in CI: a Windows runner's deeply nested
    temp directory pushed 'File: <path>' past a default-width console,
    and Rich wrapped it right through the middle of the filename --
    corrupting the one piece of information (where's the broken file?)
    this whole warning exists to hand the user. Forcing a narrow console
    width here reproduces that deterministically, independent of however
    long any given OS's actual temp path happens to be."""
    nested = tmp_path / "a_deeply" / "nested" / "temp" / "directory" / "structure" / "like_ci_uses"
    nested.mkdir(parents=True)
    target = nested / "progress.json"
    target.write_text('{"a": 1', encoding="utf-8")  # truncated JSON

    buf = StringIO()
    console = Console(file=buf, width=40, no_color=True)  # narrow enough to force a wrap

    read_json_or_warn(target, {}, console=console, label="Your saved progress")
    out = buf.getvalue()

    assert str(target) in out, f"path got wrapped/split across lines:\n{out}"
    # The user needs to know what to actually do, not just that
    # something went wrong.
    assert "back it up" in out.lower()


def test_corrupted_file_without_console_warns_to_stderr(tmp_path, capsys):
    """Read sites with no Rich console handy (e.g. an HTTP request
    handler) must still surface the warning somewhere, not swallow it."""
    target = tmp_path / "progress.json"
    target.write_text("not json at all", encoding="utf-8")

    result = read_json_or_warn(target, {}, label="Your saved progress")
    captured = capsys.readouterr()

    assert result == {}
    assert "Your saved progress" in captured.err
    assert "couldn't be read" in captured.err
