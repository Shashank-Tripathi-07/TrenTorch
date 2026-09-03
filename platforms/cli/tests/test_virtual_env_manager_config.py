"""
Coverage for get_venv_path()'s CONFIG_FILE (.tinyrc) branch.

Found by direct bug hunt, not a symptom report: the original code was
`json.load(open(CONFIG_FILE))` with no `with` block and no explicit
encoding. Two independent defects from that one line:

1. The file handle it opens is never closed (a ResourceWarning fires on
   every call that reads a real .tinyrc).
2. With no `encoding=` argument, Windows falls back to the process's
   locale encoding (cp1252 in a typical US/EU install), not UTF-8. A
   .tinyrc containing a byte cp1252 has no mapping for raises
   UnicodeDecodeError, which the surrounding `except Exception: pass`
   silently swallows -- the user's custom venv_path is dropped with zero
   indication anything went wrong, falling back to the default .venv.
"""

import gc
import json
import warnings

from platforms.cli.core import virtual_env_manager


def _write_config(tmp_path, monkeypatch, raw_bytes: bytes):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("VENV_PATH", raising=False)
    config_dir = tmp_path / "maintainer_use"
    config_dir.mkdir()
    (config_dir / ".tinyrc").write_bytes(raw_bytes)
    monkeypatch.setattr(virtual_env_manager, "CONFIG_FILE", "maintainer_use/.tinyrc")


def test_get_venv_path_closes_the_config_file(tmp_path, monkeypatch):
    """The .tinyrc handle must be closed, not left for the GC to clean up."""
    raw = json.dumps({"venv_path": "custom_venv"}).encode("utf-8")
    _write_config(tmp_path, monkeypatch, raw)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ResourceWarning)
        result = virtual_env_manager.get_venv_path()
        gc.collect()

    resource_warnings = [w for w in caught if issubclass(w.category, ResourceWarning)]
    assert not resource_warnings, f"leaked an open file handle: {resource_warnings}"
    assert result.name == "custom_venv"


def test_get_venv_path_reads_utf8_config_correctly(tmp_path, monkeypatch):
    """A .tinyrc with a byte outside cp1252's mapping must still be read as
    UTF-8, not silently swallowed and replaced with the default venv."""
    # 0x81 is undefined in cp1252, so reading this file without an explicit
    # encoding="utf-8" raises UnicodeDecodeError on a Windows/cp1252 default.
    raw = json.dumps({"venv_path": "custom_venv"}).encode("utf-8")
    raw = raw.replace(b"custom_venv", b"custom_venv_\xc2\x81")
    _write_config(tmp_path, monkeypatch, raw)

    result = virtual_env_manager.get_venv_path()

    assert result.name == "custom_venv_\x81", (
        f"expected the real custom venv_path from .tinyrc, got {result} "
        "-- the config read likely failed and silently fell back to the default"
    )
