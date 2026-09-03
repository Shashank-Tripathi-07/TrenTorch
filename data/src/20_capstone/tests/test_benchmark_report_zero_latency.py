"""
Regression test: test_unit_benchmark_report() must accept a zero-latency
measurement, not assert it's impossible.

Real bug, caught by CI (Stage 1, windows-2022) the same way Module 17's
ZeroDivisionError was: once _parse_test_output's own silent-failure-
swallowing bug was fixed, a crash that used to be invisible (it happened
after other markers had already printed as passing) started actually
failing the build, the way it always should have.

`BenchmarkReport.benchmark_model`'s own metrics dict already documents
that a raw time.time() measurement can legitimately be exactly 0.0ms on
a fast machine with a coarse timer (~15.6ms resolution on Windows) --
that's the exact reasoning `throughput_samples_per_sec` is floored for
in that same function. `latency_ms_mean` itself was never floored (it's
meant to be the real, raw measurement), so `assert
metrics['latency_ms_mean'] > 0` was simply asserting something that was
never actually guaranteed, unlike `latency_ms_std >= 0` right next to it.
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).parent.parent / "20_capstone.py"


def _load_module():
    """Import 20_capstone.py as a module without running its
    if __name__ == "__main__" block (module.__name__ isn't "__main__"
    after exec_module, so that guard never fires)."""
    trentorch_root = Path(__file__).parent.parent.parent.parent.parent
    if str(trentorch_root) not in sys.path:
        sys.path.insert(0, str(trentorch_root))
    spec = importlib.util.spec_from_file_location("capstone_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    with patch("builtins.print"):
        spec.loader.exec_module(module)
    return module


def test_benchmark_report_survives_zero_elapsed_time():
    """Real bug reproduced then fixed: force time.time() to return the
    same value on every call (elapsed = 0.0 for every timed forward
    pass) and confirm test_unit_benchmark_report() completes without
    raising -- before the fix, this raised
    AssertionError: Latency should be positive."""
    module = _load_module()

    with patch("time.time", return_value=1000.0), patch("builtins.print"):
        # Should not raise. A pre-fix run raises:
        #   AssertionError: Latency should be positive
        module.test_unit_benchmark_report()
