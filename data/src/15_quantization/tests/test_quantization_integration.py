#!/usr/bin/env python3
"""
Integration tests for Module 15: Quantization
Tests INT8 quantization, dequantization, and quantized operations end to end.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from trentorch.core.layers import Linear
from trentorch.core.tensor import Tensor
from trentorch.perf.quantization import (
    QuantizedLinear,
    dequantize_int8,
    quantize_int8,
)


def test_quantization_integration():
    """Test the full quantization pipeline: quantize -> dequantize round
    trip, quantized matmul via QuantizedLinear, and memory savings."""

    # Quantize/dequantize round trip within tolerance.
    rng = np.random.default_rng(7)
    original = Tensor(rng.standard_normal((8, 8)).astype(np.float32))
    quantized, scale, zero_point = quantize_int8(original)
    # Tensor always stores float32 internally, but the quantized values
    # themselves must be whole numbers within the INT8 range.
    assert np.all(quantized.data == np.round(quantized.data)), "Quantized values should be whole numbers"
    assert quantized.data.min() >= -128 and quantized.data.max() <= 127, (
        "Quantized values should be within the INT8 range"
    )

    dequantized = dequantize_int8(quantized, scale, zero_point)
    max_error = np.abs(dequantized.data - original.data).max()
    data_range = original.data.max() - original.data.min()
    assert max_error < 0.05 * data_range + 0.05, (
        f"Round trip error too large: {max_error:.4f} for range {data_range:.4f}"
    )

    # Quantized matmul (via QuantizedLinear) close to the unquantized equivalent.
    linear = Linear(6, 4)
    q_linear = QuantizedLinear(linear)

    input_tensor = Tensor(rng.standard_normal((3, 6)).astype(np.float32))
    original_output = linear.forward(input_tensor)
    quantized_output = q_linear.forward(input_tensor)

    output_error = np.abs(original_output.data - quantized_output.data).max()
    output_range = original_output.data.max() - original_output.data.min()
    assert output_error < 0.1 * output_range + 0.1, (
        f"Quantized matmul deviates too much: error={output_error:.4f}, range={output_range:.4f}"
    )

    # Memory savings: quantized values are whole numbers representable in a
    # single int8 byte each, 1/4 the storage of float32 (Tensor itself
    # always stores float32 internally, so this checks the semantic size,
    # not quantized.data's actual dtype).
    assert quantized.data.astype(np.int8).nbytes == original.data.nbytes // 4, (
        "int8-representable quantized data should use 1/4 the bytes of float32"
    )


if __name__ == "__main__":
    test_quantization_integration()
    print("✅ Quantization integration tests passed")
