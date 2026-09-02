"""
Regression test: MLPerf.run_standard_benchmark's throughput_fps must not
crash on a zero-elapsed-time measurement, and the mean_latency_ms >= 0
assertions in test_unit_mlperf_run/test_unit_mlperf must accept it.

Same class of bug as data/src/17_acceleration and data/src/20_capstone's
own zero-latency regression tests, but a different root cause: this
path times each run through precise_timer(), which correctly uses
time.perf_counter() (high-resolution, meant exactly for this) rather
than the coarse time.time() the other two modules use -- so forcing
time.time() to a constant, as tried first, never actually reproduced
the bug here; perf_counter() itself has to be mocked. Even
perf_counter() can theoretically read back 0.0 elapsed for a fast
enough operation, and `throughput_fps: float(1000 / mean_latency)`
divided by that raw value with no floor -- unlike every other
throughput/bandwidth calculation elsewhere in this curriculum, which
already floors its own timing denominator with the same reasoning.
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).parent.parent / "19_benchmarking.py"


def _load_module():
    """Import 19_benchmarking.py as a module without running its
    if __name__ == "__main__" block (module.__name__ isn't "__main__"
    after exec_module, so that guard never fires)."""
    trentorch_root = Path(__file__).parent.parent.parent.parent.parent
    if str(trentorch_root) not in sys.path:
        sys.path.insert(0, str(trentorch_root))
    spec = importlib.util.spec_from_file_location("benchmarking_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    with patch("builtins.print"):
        spec.loader.exec_module(module)
    return module


def test_mlperf_run_survives_zero_elapsed_time():
    """Real bug reproduced then fixed: force time.perf_counter() to
    return the same value on every call (elapsed = 0.0 for every timed
    forward pass) and confirm test_unit_mlperf_run() completes without
    raising -- before the fix, this raised ZeroDivisionError from
    throughput_fps's unguarded division by mean_latency."""
    module = _load_module()

    with patch("time.perf_counter", return_value=1000.0), patch("builtins.print"):
        # Should not raise. A pre-fix run raises:
        #   ZeroDivisionError: division by zero
        module.test_unit_mlperf_run()


def test_mlperf_survives_zero_elapsed_time():
    """Same scenario, the second copy of the same check
    (test_unit_mlperf)."""
    module = _load_module()

    with patch("time.perf_counter", return_value=1000.0), patch("builtins.print"):
        module.test_unit_mlperf()
