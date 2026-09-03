"""
Atomic JSON writes for the CLI's own state files (progress.json,
milestones.json, benchmark results, ...).

Every one of these used to write via `open(path, "w")` followed by
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
"""

import json
import os
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
