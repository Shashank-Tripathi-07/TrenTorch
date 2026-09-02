"""
Regression test: test_unit_fusion_speedup() must not crash when the
unfused timing loop measures as exactly 0.0 seconds.

Real bug, caught by CI (Stage 1, windows-2022) once
_parse_test_output's own silent-failure-swallowing bug (see
test_test_runner_result_reporting.py) was fixed and stopped hiding it:
`unfused_time = time.time() - start` can legitimately come back as
0.0 on a fast machine/small size if the whole timed loop completes
within time.time()'s wall-clock resolution. `speedup` already guarded
against the equivalent case for `fused_time` (`if fused_time > 0 else
1.0`), but `unfused_per_elem`/`unfused_bandwidth` divided by the
unguarded `unfused_time` directly, raising ZeroDivisionError.
"""

import importlib.util
import sys
import time
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).parent.parent / "17_acceleration.py"


def _load_module():
    """Import 17_acceleration.py as a module without running its
    if __name__ == "__main__" block (module.__name__ isn't "__main__"
    after exec_module, so that guard never fires)."""
    trentorch_root = Path(__file__).parent.parent.parent.parent.parent
    if str(trentorch_root) not in sys.path:
        sys.path.insert(0, str(trentorch_root))
    spec = importlib.util.spec_from_file_location("acceleration_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    with patch("builtins.print"):
        spec.loader.exec_module(module)
    return module


def test_fusion_speedup_survives_zero_elapsed_time():
    """Real bug reproduced then fixed: force time.time() to return the
    same value on every call (elapsed = 0.0 for both timed loops) and
    confirm test_unit_fusion_speedup() completes without raising --
    before the fix, this raised ZeroDivisionError from the unguarded
    unfused_bandwidth calculation."""
    module = _load_module()

    with patch("time.time", return_value=1000.0), patch("builtins.print"):
        # Should not raise. A pre-fix run raises:
        #   ZeroDivisionError: float division by zero
        # from unfused_bandwidth's division by unfused_time.
        module.test_unit_fusion_speedup()
