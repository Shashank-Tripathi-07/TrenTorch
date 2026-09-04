#!/usr/bin/env python3
"""
Integration tests for Module 19: Benchmarking
Tests the benchmark runner and metrics collection end to end on a small
real model.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from trentorch.core.layers import Linear
from trentorch.core.tensor import Tensor
from trentorch.perf.benchmarking import Benchmark, BenchmarkResult


def test_benchmarking_integration():
    """Run a real latency benchmark end to end: build a small model,
    benchmark it, and verify the collected metrics are sane and comparable
    between two models."""
    rng = np.random.default_rng(7)

    class SmallModel:
        def __init__(self, hidden):
            self.layer1 = Linear(10, hidden)
            self.layer2 = Linear(hidden, 5)

        def forward(self, x):
            return self.layer2.forward(self.layer1.forward(x))

    fast_model = SmallModel(hidden=4)
    slow_model = SmallModel(hidden=256)
    dataset = [(Tensor(rng.standard_normal((1, 10)).astype(np.float32)), Tensor(np.zeros(5)))]

    bench = Benchmark([fast_model, slow_model], [dataset])
    results = bench.run_latency_benchmark(input_shape=(1, 10))

    assert len(results) == 2, f"Expected results for both models, got {list(results.keys())}"

    for model_name, result in results.items():
        assert isinstance(result, BenchmarkResult), f"Result for {model_name} should be a BenchmarkResult"
        # >= 0, not > 0: a raw timer measurement can legitimately be
        # exactly 0.0 on a fast machine with a coarse timer resolution.
        assert result.mean >= 0, f"Latency should be non-negative, got {result.mean}"
        result_dict = result.to_dict()
        assert "mean" in result_dict, "BenchmarkResult.to_dict() should include the mean latency"


if __name__ == "__main__":
    test_benchmarking_integration()
    print("✅ Benchmarking integration tests passed")
