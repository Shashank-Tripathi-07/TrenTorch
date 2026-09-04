#!/usr/bin/env python3
"""
Module Dependency Integration Testing
Tests how each module interfaces with modules that came before it
"""

import numpy as np

rng = np.random.default_rng(7)

# Module dependency graph for TrenTorch
# Current module structure:
# 01_tensor, 02_activations, 03_layers, 04_losses, 05_dataloader,
# 06_autograd, 07_optimizers, 08_training, 09_convolutions,
# 10_tokenization, 11_embeddings, 12_attention, 13_transformers,
# 14_profiling, 15_quantization, 16_compression, 17_acceleration,
# 18_memoization, 19_benchmarking, 20_capstone
MODULE_DEPENDENCIES = {
    "01_tensor": [],  # No dependencies - foundation
    "02_activations": ["01_tensor"],  # Needs Tensor
    "03_layers": ["01_tensor"],  # Needs Tensor
    "04_losses": ["01_tensor"],  # Needs Tensor
    "05_dataloader": ["01_tensor"],  # Needs Tensor
    "06_autograd": ["01_tensor"],  # Core dependency on Tensor
    "07_optimizers": ["01_tensor", "06_autograd"],  # Needs Tensor and autograd
    "08_training": ["01_tensor", "05_dataloader", "06_autograd", "07_optimizers"],  # Training loop deps
    "09_convolutions": ["01_tensor", "03_layers"],  # Needs Tensor and Layer base
    "10_tokenization": ["01_tensor"],  # Needs Tensor
    "11_embeddings": ["01_tensor"],  # Needs Tensor
    "12_attention": ["01_tensor", "03_layers"],  # Needs Tensor, Layer
    "13_transformers": ["01_tensor", "03_layers", "12_attention"],  # Full attention stack
    "14_profiling": ["01_tensor"],  # Performance analysis
    "15_quantization": ["01_tensor"],  # Optimization techniques
    "16_compression": ["01_tensor"],  # Optimization techniques
    "17_acceleration": ["01_tensor"],  # Runtime optimization (general)
    "18_memoization": ["01_tensor"],  # Runtime optimization (transformer-specific)
    "19_benchmarking": ["01_tensor"],  # Performance testing
    "20_capstone": ["01_tensor", "09_convolutions", "13_transformers"],  # Full stack
}


# Base integration tests that check module interfaces
def test_tensor_integration():
    """Test that Tensor works as expected for dependent modules."""
    import numpy as np
    from trentorch.core.tensor import Tensor

    # Test tensor creation
    t = Tensor(np.array([1, 2, 3]))
    assert t.shape == (3,), "Tensor shape should work"
    assert t.data is not None, "Tensor should have data"

    # Test tensor operations needed by other modules
    t2 = Tensor(np.array([4, 5, 6]))
    result = t.data + t2.data  # Many modules need element-wise ops
    assert result.shape == (3,), "Element-wise ops should preserve shape"


def test_layer_integration():
    """Test Layer base class interface."""
    from trentorch.core.layers import Layer

    # Test that Layer exists and has expected interface
    assert hasattr(Layer, "forward"), "Layer should have forward method"
    assert hasattr(Layer, "__call__"), "Layer should be callable"

    # Test basic layer creation
    layer = Layer()
    assert layer is not None, "Should create Layer instance"


def test_dense_integration():
    """Test Dense layer integration with Tensor."""
    from trentorch.core.layers import Linear
    from trentorch.core.tensor import Tensor

    # Test Dense with Tensor input
    layer = Linear(10, 5)
    x = Tensor(rng.standard_normal((32, 10)))
    output = layer(x)

    assert output.shape == (32, 5), "Dense should produce correct shape"
    assert isinstance(output, Tensor), "Dense should return Tensor"


def test_dense_with_tensor():
    """Test that Dense properly uses Tensor for weights/bias."""
    from trentorch.core.layers import Linear
    from trentorch.core.tensor import Tensor

    layer = Linear(10, 5)

    # Check weights are Tensors
    assert isinstance(layer.weight, Tensor), "Weights should be Tensor"
    assert layer.weight.shape == (10, 5), "Weight shape should match layer dims"
    # Bias may or may not exist depending on implementation
    if hasattr(layer, "bias") and layer.bias is not None:
        assert isinstance(layer.bias, Tensor), "Bias should be Tensor"


def test_dense_with_activations():
    """Test Dense layer works with activation functions."""
    import numpy as np
    from trentorch.core.activations import ReLU, Sigmoid
    from trentorch.core.layers import Linear
    from trentorch.core.tensor import Tensor

    # Build small network: Dense -> ReLU -> Dense -> Sigmoid
    layer1 = Linear(10, 20)
    relu = ReLU()
    layer2 = Linear(20, 1)
    sigmoid = Sigmoid()

    # Forward pass
    x = Tensor(rng.standard_normal((16, 10)))
    h1 = layer1(x)
    h1_activated = relu(h1)
    output = layer2(h1_activated)
    final = sigmoid(output)

    # Check shapes preserved through network
    assert h1.shape == (16, 20), "First layer output shape"
    assert h1_activated.shape == (16, 20), "ReLU preserves shape"
    assert output.shape == (16, 1), "Second layer output shape"
    assert final.shape == (16, 1), "Sigmoid preserves shape"

    # Check sigmoid output range
    assert np.all(final.data >= 0) and np.all(final.data <= 1), "Sigmoid outputs in [0,1]"


def test_multi_layer_network():
    """Test building multi-layer networks with Dense."""
    from trentorch.core.layers import Linear
    from trentorch.core.tensor import Tensor

    # Build 3-layer network
    layers = [Linear(784, 128), Linear(128, 64), Linear(64, 10)]

    # Forward pass through all layers
    x = Tensor(rng.standard_normal((32, 784)))

    for i, layer in enumerate(layers):
        x = layer(x)
        if i == 0:
            assert x.shape == (32, 128), f"Layer {i} shape"
        elif i == 1:
            assert x.shape == (32, 64), f"Layer {i} shape"
        elif i == 2:
            assert x.shape == (32, 10), f"Layer {i} shape"

    assert x.shape == (32, 10), "Final output shape should be (32, 10)"


def test_conv2d_with_tensor():
    """Test Conv2d integration with Tensor."""
    from trentorch.core.spatial import Conv2d
    from trentorch.core.tensor import Tensor

    # Create Conv2d layer
    conv = Conv2d(in_channels=3, out_channels=16, kernel_size=3)

    # Test with image tensor (batch, channels, height, width). Only
    # batch/channel counts are asserted below, not spatial size, so this
    # uses a small stand-in for a real image -- the naive Conv2d loop
    # implementation made the original 32x32 size take ~3.5s here alone.
    x = Tensor(rng.standard_normal((8, 3, 12, 12)))
    output = conv(x)

    # Check output shape (with valid padding, output is smaller)
    assert output.shape[0] == 8, "Batch size preserved"
    assert output.shape[1] == 16, "Output channels correct"


def test_pooling_integration():
    """Test pooling layers work with Conv2d output."""
    from trentorch.core.spatial import Conv2d, MaxPool2d
    from trentorch.core.tensor import Tensor

    conv = Conv2d(3, 32, kernel_size=3, padding=1)
    pool = MaxPool2d(kernel_size=2, stride=2)

    # The size assertions below are relative (halved dimensions), not
    # absolute, so this uses a small stand-in for a real image -- the
    # naive Conv2d loop implementation made the original 28x28 size take
    # ~3.1s here alone.
    x = Tensor(rng.standard_normal((4, 3, 12, 12)))
    conv_out = conv(x)
    pool_out = pool(conv_out)

    # Pooling should reduce spatial dimensions by half
    assert pool_out.shape[2] == conv_out.shape[2] // 2
    assert pool_out.shape[3] == conv_out.shape[3] // 2


def test_attention_with_dense():
    """Test attention mechanism uses Dense layers."""
    from trentorch.core.attention import MultiHeadAttention
    from trentorch.core.tensor import Tensor

    attention = MultiHeadAttention(embed_dim=64, num_heads=4)
    x = Tensor(rng.standard_normal((2, 10, 64)))  # (batch, seq_len, embed_dim)

    output = attention(x)
    assert output.shape == x.shape, "Attention preserves shape"


def test_multihead_integration():
    """Test multi-head attention integration."""
    from trentorch.core.attention import MultiHeadAttention
    from trentorch.core.tensor import Tensor

    mha = MultiHeadAttention(embed_dim=64, num_heads=8)
    x = Tensor(rng.standard_normal((2, 10, 64)))

    output = mha(x)
    assert output.shape == x.shape, "MHA preserves input shape"


def test_autograd_integration():
    """Test autograd system with Tensor.

    NOTE: This test requires autograd to be enabled (Module 06+).
    It will skip if requires_grad is not available.
    """
    import numpy as np
    from trentorch.core.tensor import Tensor

    # Check if autograd is enabled (requires_grad parameter available)
    try:
        x = Tensor(np.array([[1, 2], [3, 4]]), requires_grad=True)
    except TypeError:
        # requires_grad not available - autograd not enabled yet
        return  # Skip test

    assert hasattr(x, "grad"), "Tensor should have grad attribute"
    assert x.requires_grad, "Should track gradients"


def test_optimizer_integration():
    """Test optimizers work with layers."""
    from trentorch.core.layers import Linear
    from trentorch.core.optimizers import SGD

    layer = Linear(10, 5)
    params = layer.parameters()
    SGD(params, lr=0.01)

    # Test optimizer has params
    assert len(params) > 0, "Layer should have parameters"


def test_training_loop_integration():
    """Test training loop integrates optimizer and autograd.

    Previously only asserted `loss is not None`, without ever calling
    backward() or step(), so a completely broken backward pass or
    optimizer could not be caught here despite the docstring's claim.
    Now exercises the real integration: backward() populates gradients,
    and step() actually changes the model's weights.
    """
    from trentorch.core.layers import Linear
    from trentorch.core.losses import MSELoss
    from trentorch.core.optimizers import SGD
    from trentorch.core.tensor import Tensor

    # Simple model
    model = Linear(10, 1)
    params = model.parameters()
    optimizer = SGD(params, lr=0.01)
    loss_fn = MSELoss()

    # Dummy data
    X = Tensor(rng.standard_normal((32, 10)))
    y = Tensor(rng.standard_normal((32, 1)))

    weight_before = model.weight.data.copy()

    # One full training step
    optimizer.zero_grad()
    predictions = model(X)
    loss = loss_fn(predictions, y)
    assert loss is not None, "Loss should be computed"

    loss.backward()
    assert model.weight.grad is not None, "backward() should populate gradients"

    optimizer.step()
    assert not np.allclose(model.weight.data, weight_before), (
        "optimizer.step() should change model weights after a real gradient update"
    )


def test_loss_backward_integration():
    """Test loss functions integrate with autograd.

    Previously only called backward() conditionally and asserted
    nothing about the result afterward, so it could only fail via an
    uncaught exception, never actually verifying gradients were
    populated. Module 06+ (autograd) is a hard dependency of this repo's
    test suite by this point, so the requires_grad TypeError skip and
    hasattr(loss, "backward") guard are dead code paths that would only
    ever mask a real regression; asserts unconditionally instead.
    """
    from trentorch.core.losses import MSELoss
    from trentorch.core.tensor import Tensor

    loss_fn = MSELoss()

    predictions = Tensor(np.array([1.0, 2.0, 3.0]), requires_grad=True)
    targets = Tensor(np.array([1.5, 2.5, 3.5]))

    loss = loss_fn(predictions, targets)
    loss.backward()

    assert predictions.grad is not None, "backward() should populate gradients on predictions"
    assert not np.allclose(predictions.grad.data, 0), "MSELoss gradient should be non-zero for a real error"
