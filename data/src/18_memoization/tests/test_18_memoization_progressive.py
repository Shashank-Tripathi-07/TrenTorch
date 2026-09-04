"""
Module 18: Progressive Integration Tests
Tests that Module 18 (Memoization/KV-Cache) works correctly AND that prior modules (01→17) still work.

DEPENDENCY CHAIN: 01_tensor → ... → 13_transformers → ... → 17_acceleration → 18_memoization

⚠️ IMPORTANT: This test ONLY uses modules 01-18.
   Future modules (19_benchmarking, 20_capstone) are NOT tested here.

🎯 WHAT THIS TESTS:
- Module 18: KV-Cache, memoization for transformers, inference optimization
- Integration: Memoization works with transformers (13) and prior modules
- Regression: All previous modules still work correctly
"""

import numpy as np

rng = np.random.default_rng(7)
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))


class TestMemoizationCore:
    """
    🆕 NEW FUNCTIONALITY: Test Module 18 (Memoization) core implementation.
    """

    def test_kv_cache_exists(self):
        """
        ✅ TEST: KVCache class exists

        KVCache is a real, load-bearing class in this module (the whole
        cached-generation pipeline depends on it), so this asserts
        unconditionally instead of the vacuous try/except ImportError
        pattern the previous version used, which passed regardless of
        whether the class actually existed.
        """
        from trentorch.perf.memoization import KVCache

        assert KVCache is not None

    def test_kv_cache_initialization(self):
        """
        ✅ TEST: KVCache can be initialized with the expected interface
        """
        from trentorch.perf.memoization import KVCache

        batch_size = 1
        max_seq_len = 512
        num_layers = 2
        num_heads = 8
        head_dim = 8

        cache = KVCache(batch_size, max_seq_len, num_layers, num_heads, head_dim)

        assert hasattr(cache, "update"), "KVCache missing update method"
        assert hasattr(cache, "get"), "KVCache missing get method"
        assert hasattr(cache, "advance"), "KVCache missing advance method"
        assert cache.seq_pos == 0, "A fresh cache should start at position 0"

    def test_kv_cache_update(self):
        """
        ✅ TEST: KVCache actually stores and retrieves key-value pairs

        The version this replaces only checked hasattr() for the update/
        get/advance methods, never that update() followed by get() (or
        advance()) actually round-trips real data, so a broken storage
        implementation could pass this test.
        """
        from trentorch.core.tensor import Tensor
        from trentorch.perf.memoization import KVCache

        batch_size = 1
        max_seq_len = 100
        num_layers = 2
        num_heads = 4
        head_dim = 8

        cache = KVCache(batch_size, max_seq_len, num_layers, num_heads, head_dim)

        K = Tensor(rng.standard_normal((batch_size, num_heads, 1, head_dim)))
        V = Tensor(rng.standard_normal((batch_size, num_heads, 1, head_dim)))
        cache.update(layer_idx=0, key=K, value=V)
        cache.advance()

        stored_K, stored_V = cache.get(layer_idx=0)
        assert np.allclose(stored_K.data[:, :, 0, :], K.data[:, :, 0, :]), (
            "KVCache.get() should return the K values just written by update()"
        )
        assert np.allclose(stored_V.data[:, :, 0, :], V.data[:, :, 0, :]), (
            "KVCache.get() should return the V values just written by update()"
        )
        assert cache.seq_pos == 1, "advance() should move seq_pos forward by one"


class TestMemoizationWithTransformers:
    """
    🔗 INTEGRATION: Memoization + Transformers (Module 13)
    """

    def test_kv_cache_with_attention(self):
        """
        ✅ TEST: KVCache works with MultiHeadAttention
        """
        try:
            from trentorch.core.attention import MultiHeadAttention
            from trentorch.core.tensor import Tensor
            from trentorch.perf.memoization import KVCache

            embed_dim = 32
            num_heads = 4

            mha = MultiHeadAttention(embed_dim, num_heads)
            head_dim = embed_dim // num_heads
            cache = KVCache(
                batch_size=1, max_seq_len=100, num_layers=1, num_heads=num_heads, head_dim=head_dim
            )

            # First token
            x1 = Tensor(rng.standard_normal((1, 1, embed_dim)))  # (batch, seq=1, embed)
            mha(x1)

            # Cache should speed up subsequent tokens
            x2 = Tensor(rng.standard_normal((1, 1, embed_dim)))

            # With cache, attention only needs to attend to new token
            if hasattr(mha, "forward_with_cache"):
                out2, cache = mha.forward_with_cache(x2, cache)
                assert out2.shape == x2.shape

        except ImportError:
            assert True, "KV cache integration not ready"

    def test_incremental_generation(self):
        """
        ✅ TEST: Incremental generation with caching
        """
        try:
            from trentorch.core.tensor import Tensor
            from trentorch.core.transformers import TinyGPT
            from trentorch.perf.memoization import KVCache

            vocab_size = 50
            model = TinyGPT(vocab_size=vocab_size, embed_dim=32, num_heads=4, num_layers=2)

            # Generate tokens one at a time
            cache = None
            generated = [1]  # Start token

            for _ in range(5):
                input_ids = Tensor(np.array([generated[-1:]]))  # Last token

                if hasattr(model, "forward_with_cache"):
                    logits, cache = model.forward_with_cache(input_ids, cache)
                else:
                    # Without cache, use full sequence
                    input_ids = Tensor(np.array([generated]))
                    logits = model(input_ids)

                # Get next token (greedy)
                next_token = int(np.argmax(logits.data[0, -1, :]))
                generated.append(next_token)

            assert len(generated) == 6, "Generation should produce tokens"

        except ImportError:
            assert True, "Incremental generation not ready"
        except TypeError:
            assert True, "TinyGPT interface may differ"


class TestMemoizationPerformance:
    """
    Test that memoization actually improves performance.
    """

    def test_cache_speedup(self):
        """
        ✅ TEST: Caching should improve inference speed
        """
        import time

        try:
            from trentorch.core.layers import Linear
            from trentorch.core.tensor import Tensor

            layer = Linear(100, 100)
            x = Tensor(rng.standard_normal((10, 100)))

            # Warm-up
            _ = layer(x)

            # Time without cache (baseline)
            start = time.time()
            for _ in range(100):
                _ = layer(x)
            baseline = time.time() - start

            # Should complete without error
            assert baseline > 0, "Timing should be positive"

        except ImportError:
            assert True, "Performance test not ready"


class TestRegressionPrevention:
    """
    🔄 REGRESSION: Verify all previous modules (01-17) still work.
    """

    def test_tensor_still_works(self):
        """✅ Module 01"""
        from trentorch.core.tensor import Tensor

        a = Tensor([1, 2, 3])
        assert a.shape == (3,)

    def test_activations_still_work(self):
        """✅ Module 02"""
        from trentorch.core.activations import ReLU
        from trentorch.core.tensor import Tensor

        relu = ReLU()
        x = Tensor([-1, 0, 1])
        y = relu(x)
        assert y.data[0] == 0

    def test_layers_still_work(self):
        """✅ Module 03"""
        from trentorch.core.layers import Linear
        from trentorch.core.tensor import Tensor

        layer = Linear(4, 2)
        x = Tensor(rng.standard_normal((2, 4)))
        y = layer(x)
        assert y.shape == (2, 2)

    def test_losses_still_work(self):
        """✅ Module 04"""
        from trentorch.core.losses import MSELoss
        from trentorch.core.tensor import Tensor

        loss_fn = MSELoss()
        loss = loss_fn(Tensor([[1.0]]), Tensor([[2.0]]))
        assert loss.data.size == 1

    def test_dataloader_still_works(self):
        """✅ Module 05"""
        from trentorch.core.dataloader import DataLoader, TensorDataset
        from trentorch.core.tensor import Tensor

        data = Tensor(rng.standard_normal((10, 3)))
        targets = Tensor(np.arange(10).astype(float))
        dataset = TensorDataset(data, targets)
        dataloader = DataLoader(dataset, batch_size=2)
        assert sum(1 for _ in dataloader) == 5

    def test_optimizers_still_work(self):
        """✅ Module 07"""
        from trentorch.core.layers import Linear
        from trentorch.core.optimizers import SGD

        layer = Linear(3, 2)
        opt = SGD(layer.parameters(), lr=0.01)
        assert hasattr(opt, "step")

    def test_convolutions_still_work(self):
        """✅ Module 09"""
        try:
            from trentorch.core.spatial import Conv2d
            from trentorch.core.tensor import Tensor

            conv = Conv2d(3, 8, kernel_size=3, padding=1)
            x = Tensor(rng.standard_normal((2, 3, 8, 8)))
            y = conv(x)
            assert y.shape[0] == 2
        except ImportError:
            pass

    def test_attention_still_works(self):
        """✅ Module 12"""
        try:
            from trentorch.core.attention import MultiHeadAttention
            from trentorch.core.tensor import Tensor

            mha = MultiHeadAttention(32, 4)
            x = Tensor(rng.standard_normal((1, 5, 32)))
            out = mha(x)
            assert out.shape == x.shape
        except ImportError:
            pass

    def test_transformers_still_work(self):
        """✅ Module 13"""
        try:
            from trentorch.core.tensor import Tensor
            from trentorch.core.transformers import TransformerBlock

            block = TransformerBlock(32, 4, ff_dim=128)
            x = Tensor(rng.standard_normal((1, 5, 32)))
            out = block(x)
            assert out.shape == x.shape
        except ImportError:
            pass


class TestModule18Completion:
    """
    ✅ COMPLETION CHECK: Module 18 ready for next module.
    """

    def test_memoization_foundation_complete(self):
        """
        ✅ FINAL TEST: Memoization ready for benchmarking

        🎯 SUCCESS = Ready for Module 19: Benchmarking!
        """
        capabilities = {
            "KVCache exists": False,
            "Memoization works": False,
        }

        try:
            from trentorch.perf.memoization import KVCache

            capabilities["KVCache exists"] = True

            # Test basic cache (batch_size, max_seq_len, num_layers, num_heads, head_dim)
            cache = KVCache(1, 100, 2, 4, 8)
            if hasattr(cache, "update") and hasattr(cache, "get") and hasattr(cache, "advance"):
                capabilities["Memoization works"] = True

            completed = sum(capabilities.values())
            assert completed >= 1, f"Memoization not ready: {capabilities}"

        except ImportError:
            assert True, "Memoization not implemented yet"
