"""
Regression test: analyze_dataloader_performance()'s shuffle_overhead
calculation must not crash on a zero-elapsed-time measurement.

Same class of bug as data/src/17_acceleration, data/src/19_benchmarking,
and data/src/20_capstone's own zero-latency regression tests: a raw
time.time() measurement can legitimately be exactly 0.0 on a fast
machine with a coarse timer resolution (~15.6ms on Windows), and
shuffle_overhead's division by time_no_shuffle had no floor.

Not currently reachable from CI (the call site at the bottom of this
module is commented out -- this is an opt-in demo function), but the
crash is real the moment anyone uncomments it and runs on a fast enough
machine, so it's fixed and covered the same as every other copy of this
bug found this session.
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).parent.parent / "05_dataloader.py"


def _load_module():
    """Import 05_dataloader.py as a module without running its
    if __name__ == "__main__" blocks (module.__name__ isn't "__main__"
    after exec_module, so those guards never fire)."""
    trentorch_root = Path(__file__).parent.parent.parent.parent.parent
    if str(trentorch_root) not in sys.path:
        sys.path.insert(0, str(trentorch_root))
    spec = importlib.util.spec_from_file_location("dataloader_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    with patch("builtins.print"):
        spec.loader.exec_module(module)
    return module


def test_analyze_dataloader_performance_survives_zero_elapsed_time():
    """Real bug reproduced then fixed: force time.time() to return the
    same value on every call (elapsed = 0.0 for both the shuffled and
    unshuffled loads) and confirm analyze_dataloader_performance()
    completes without raising -- before the fix, this raised
    ZeroDivisionError from shuffle_overhead's unguarded division by
    time_no_shuffle."""
    module = _load_module()

    with patch("time.time", return_value=1000.0), patch("builtins.print"):
        # Should not raise. A pre-fix run raises:
        #   ZeroDivisionError: float division by zero
        module.analyze_dataloader_performance()
