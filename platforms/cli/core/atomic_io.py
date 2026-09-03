"""
Atomic JSON reads and writes for the CLI's own state files (progress.json,
milestones.json, benchmark results, ...).

Every save used to write via `open(path, "w")` followed by
`json.dump(...)`. `open(path, "w")` truncates the file to 0 bytes the
moment it's called, before a single byte of the new content is written --
so anything short of a clean process exit between that truncation and
json.dump() finishing (a crash, Ctrl+C, power loss, OOM kill) leaves a
truncated, unparseable file on disk. Every read site for these files
already wraps json.load() in a broad except that resets to an empty
default on JSONDecodeError, which means an interrupted save doesn't just
lose the write in progress -- it silently erases everything that was
already saved, with zero indication to the user.

os.replace() is atomic on both POSIX and Windows: a reader can only ever
see the old complete file or the new complete file, never a partial one.
Writing the new content to a temp file in the same directory first (same
filesystem, so the rename is guaranteed atomic rather than falling back
to a slower non-atomic copy) and only replacing the real path once that
write has fully succeeded gets the same durability every other line of
this codebase already assumes state files have.

atomic_write_json() closes the write-side half of that hazard. The other
half is the read side: even with atomic writes, a file can still end up
corrupted by something outside this CLI's control (a manual edit gone
wrong, a disk error, an old pre-atomic-write crash from before this fix
existed). Every read site used to catch that with a bare
`except (OSError, json.JSONDecodeError): pass` and silently fall back to
an empty default -- so a student whose real progress.json exists on disk
but can't be parsed just sees "0/20 modules complete" with no hint that
their actual data might still be sitting right there, unreadable. Command
output is not the place to explain that; the moment the file fails to
parse is. read_json_or_warn() prints a specific, actionable message right
then (the exact path, the exact error, and what to do about it) before
falling back to the same default the old silent code used -- the CLI
still works, but the user finds out why their progress looks wrong
instead of being left to assume it's just gone.
"""

import json
import os
import sys
import tempfile
from pathlib import Path


def atomic_write_json(path: str | Path, data: object, *, indent: int = 2) -> None:
    """Write `data` as JSON to `path`, atomically.

    On any failure (including one raised while writing), the original
    file at `path` -- if it exists -- is left untouched; the partial
    temp file is cleaned up rather than left behind.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def read_json_or_warn(
    path: str | Path,
    default: object,
    *,
    console=None,
    label: str | None = None,
) -> object:
    """Read JSON from `path`, warning the user (instead of staying silent)
    if the file exists but can't be read.

    A missing file is completely normal (first run, nothing saved yet) and
    returns `default` with no output at all. A file that exists but fails
    to parse or open is different -- that's data loss the user needs to
    know about, not a routine "nothing here yet" case -- so it prints
    exactly what happened and where, then falls back to `default` so the
    CLI keeps working.

    `console`, if given, is a rich Console the message is printed through
    (matching the command's own output styling); without one, the message
    goes to stderr via plain print() so it's never silently dropped even
    from a code path with no console handy.
    """
    path = Path(path)
    if not path.exists():
        return default

    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        name = label or path.name
        lines = [
            (f"⚠️  {name} exists but couldn't be read -- continuing as if it's empty.", "yellow"),
            (f"   File: {path}", "dim"),
            (f"   Error: {e}", "dim"),
            ("   Your data may still be in that file -- back it up before running anything", "dim"),
            ("   that writes to it, then ask a maintainer for help recovering it.", "dim"),
        ]
        if console is not None:
            # style=, not inline [tag] markup: the error text is
            # attacker/accident-controlled (arbitrary file content), and
            # wrapping it in f"[yellow]{e}[/yellow]" would let any literal
            # "[...]" inside that text be parsed as (possibly malformed)
            # Rich markup instead of shown as plain text.
            for text, style in lines:
                console.print(text, style=style)
        else:
            for text, _style in lines:
                print(text, file=sys.stderr)
        return default
