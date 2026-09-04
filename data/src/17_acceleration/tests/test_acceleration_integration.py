#!/usr/bin/env python3
"""
Integration tests for Module 17: Acceleration
Tests operator fusion and tiled computation for correctness against their
unoptimized equivalents.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from trentorch.core.tensor import Tensor


def test_acceleration_integration():
    """Test that acceleration techniques (fusion, tiling) produce results
    matching their unoptimized equivalents, not just that they run."""
    from trentorch.perf.acceleration import fused_gelu, tiled_matmul, vectorized_matmul

    rng = np.random.default_rng(7)

    # Operator fusion correctness: the fused kernel must match the
    # mathematical GELU definition it's an optimized version of.
    # unfused_gelu isn't part of the package's public API, so compare
    # directly against the reference tanh-approximation formula.
    x = Tensor(rng.standard_normal((16, 32)).astype(np.float32))
    fused_result = fused_gelu(x)
    reference = 0.5 * x.data * (1 + np.tanh(np.sqrt(2 / np.pi) * (x.data + 0.044715 * x.data**3)))
    assert np.allclose(fused_result.data, reference, atol=1e-5), (
        "fused_gelu should match the reference tanh-approximation GELU formula"
    )

    # Tiled matmul correctness against the plain vectorized matmul.
    a = Tensor(rng.standard_normal((37, 53)).astype(np.float32))
    b = Tensor(rng.standard_normal((53, 29)).astype(np.float32))
    tiled_result = tiled_matmul(a, b, tile_size=16)
    plain_result = vectorized_matmul(a, b)
    assert np.allclose(tiled_result.data, plain_result.data, atol=1e-3), (
        "tiled_matmul should match vectorized_matmul regardless of tile size"
    )
    assert tiled_result.shape == (37, 29), f"Unexpected tiled_matmul shape: {tiled_result.shape}"


if __name__ == "__main__":
    test_acceleration_integration()
    print("✅ Acceleration integration tests passed")
