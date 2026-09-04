#!/usr/bin/env python3
"""
Integration tests for Module 16: Compression
Tests pruning and model size reduction end to end.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from trentorch.core.layers import Linear, Sequential
from trentorch.perf.compression import magnitude_prune, measure_sparsity


def test_compression_integration():
    """Test the pruning pipeline end to end: build a model, prune it to a
    target sparsity, and verify both the measured sparsity and the actual
    zero count in the underlying weight data agree with the target."""
    model = Sequential(Linear(64, 32), Linear(32, 16))

    # measure_sparsity returns a percentage (0-100), not a fraction.
    sparsity_before = measure_sparsity(model)
    assert sparsity_before < 5.0, (
        f"Freshly initialized model should start near-dense, got {sparsity_before:.1f}% sparsity"
    )

    target_sparsity_pct = 70.0
    magnitude_prune(model, sparsity=target_sparsity_pct / 100.0)

    sparsity_after = measure_sparsity(model)
    assert abs(sparsity_after - target_sparsity_pct) < 5.0, (
        f"Expected ~{target_sparsity_pct:.0f}% sparsity after pruning, got {sparsity_after:.1f}%"
    )

    # Verify real zeros exist in the actual weight arrays, not just in the
    # reported statistic.
    total_zeros = 0
    total_weight_elements = 0
    for param in model.parameters():
        if len(param.shape) > 1:  # weights, not biases
            total_zeros += np.count_nonzero(param.data == 0)
            total_weight_elements += param.data.size

    actual_sparsity_pct = 100.0 * total_zeros / total_weight_elements
    assert abs(actual_sparsity_pct - target_sparsity_pct) < 5.0, (
        f"Weight data itself should show ~{target_sparsity_pct:.0f}% zeros, got {actual_sparsity_pct:.1f}%"
    )


if __name__ == "__main__":
    test_compression_integration()
    print("✅ Compression integration tests passed")
