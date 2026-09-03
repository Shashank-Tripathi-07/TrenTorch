"""
Coverage for atomic_io.atomic_write_json -- the shared helper introduced
to replace every `open(path, "w")` + `json.dump(...)` state-file save in
the CLI (progress.json, milestones.json, benchmark results, profile.json,
submission/config files).

Found by direct bug hunt: `open(path, "w")` truncates the file to 0 bytes
the instant it's called, before a single byte of the new content exists.
Any interruption between that truncation and json.dump() finishing --
crash, Ctrl+C, power loss, OOM kill -- leaves a truncated, unparseable
file on disk. Every read site for these files wraps json.load() in a
broad except that resets to an empty default on JSONDecodeError, so an
interrupted save doesn't just lose the write in progress, it silently
erases everything that was already saved. Reproduced standalone before
this fix: simulated a truncated progress.json, confirmed json.load()
raised JSONDecodeError, confirmed the read path silently discarded 5
previously-completed modules.

atomic_write_json fixes this by writing to a temp file in the same
directory and only replacing the real path with os.replace() -- atomic
on both POSIX and Windows -- once the write has fully succeeded.
"""

import json
from unittest.mock import patch

import pytest

from platforms.cli.core.atomic_io import atomic_write_json


def test_atomic_write_json_round_trips(tmp_path):
    target = tmp_path / "state.json"
    data = {"completed_modules": ["01", "02", "03"], "streak_days": 12}

    atomic_write_json(target, data)

    assert json.loads(target.read_text(encoding="utf-8")) == data


def test_atomic_write_json_creates_parent_directories(tmp_path):
    target = tmp_path / "nested" / "user_data" / "progress.json"

    atomic_write_json(target, {"a": 1})

    assert target.exists()
    assert json.loads(target.read_text(encoding="utf-8")) == {"a": 1}


def test_atomic_write_json_leaves_the_original_file_untouched_on_failure(tmp_path):
    """The regression this whole fix exists for: if the write is
    interrupted (here, simulated by making os.replace raise, standing in
    for a crash/Ctrl+C/power loss between the temp file finishing and the
    atomic rename), the real file at `path` must be exactly what it was
    before -- never truncated, never partial."""
    target = tmp_path / "progress.json"
    original = {"completed_modules": ["01", "02", "03", "04", "05"], "streak_days": 12}
    target.write_text(json.dumps(original), encoding="utf-8")

    with patch("os.replace", side_effect=OSError("simulated crash before rename")):
        with pytest.raises(OSError):
            atomic_write_json(target, {"completed_modules": ["01", "02"]})

    # Before the fix (a plain open(path, "w")), this exact interruption
    # point would have already truncated the file to 0 bytes. With the
    # temp-file-then-rename approach, the original content must survive
    # completely intact.
    assert json.loads(target.read_text(encoding="utf-8")) == original


def test_atomic_write_json_cleans_up_its_temp_file_on_failure(tmp_path):
    target = tmp_path / "progress.json"

    with patch("os.replace", side_effect=OSError("simulated failure")):
        with pytest.raises(OSError):
            atomic_write_json(target, {"a": 1})

    leftover_temp_files = [p for p in tmp_path.iterdir() if p.name != "progress.json"]
    assert leftover_temp_files == [], f"left a temp file behind: {leftover_temp_files}"
