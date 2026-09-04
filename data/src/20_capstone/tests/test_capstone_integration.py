#!/usr/bin/env python3
"""
Integration tests for Module 20: Capstone
Tests the end-to-end submission pipeline: benchmark a real model, then
generate and validate a full submission from the resulting reports.
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from trentorch.core.tensor import Tensor

# Module 20 (capstone) is the final project module and is not exported into
# the trentorch package (confirmed: no trentorch/perf/capstone.py exists),
# unlike every earlier numbered module. Load its solution content directly
# from the source file, the same way this module's own test_module()
# harness does.
_spec = importlib.util.spec_from_file_location("capstone_20", Path(__file__).parent.parent / "20_capstone.py")
_capstone = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_capstone)
BenchmarkReport = _capstone.BenchmarkReport
SimpleMLP = _capstone.SimpleMLP
generate_submission = _capstone.generate_submission


def test_capstone_integration():
    """Benchmark a baseline and an "optimized" (smaller) model end to end,
    then generate a submission from the two reports and verify its
    structure and contents are valid."""
    rng = np.random.default_rng(7)
    X_test = Tensor(rng.standard_normal((16, 10)).astype(np.float32))
    y_test = rng.integers(0, 3, size=16)

    baseline_model = SimpleMLP(input_size=10, hidden_size=20, output_size=3)
    optimized_model = SimpleMLP(input_size=10, hidden_size=8, output_size=3)

    baseline_report = BenchmarkReport(model_name="baseline")
    baseline_report.benchmark_model(baseline_model, X_test, y_test, num_runs=5)

    optimized_report = BenchmarkReport(model_name="optimized")
    optimized_report.benchmark_model(optimized_model, X_test, y_test, num_runs=5)

    assert baseline_report.metrics["parameter_count"] > optimized_report.metrics["parameter_count"], (
        "The smaller-hidden-size model should have fewer parameters"
    )

    submission = generate_submission(baseline_report, optimized_report, student_name="Integration Test")

    assert submission["student_name"] == "Integration Test"
    assert submission["baseline"]["model_name"] == "baseline"
    assert submission["optimized"]["model_name"] == "optimized"

    improvements = submission["improvements"]
    assert improvements["compression_ratio"] > 1.0, (
        "A model with fewer parameters should report compression_ratio > 1"
    )
    assert improvements["speedup"] > 0, "Speedup should be a positive number"
    assert isinstance(improvements["accuracy_delta"], float)


if __name__ == "__main__":
    test_capstone_integration()
    print("✅ Capstone integration tests passed")
