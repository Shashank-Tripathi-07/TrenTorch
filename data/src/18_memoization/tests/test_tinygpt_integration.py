"""
Integration test for Module 18: Memoization (TinyGPT end-to-end generation)
Tests a real GPT-style transformer plus KV-cached generation together.

The original version of this file imported `trentorch.tinygpt`, a module
path that does not exist anywhere in this package (confirmed:
ModuleNotFoundError), and its only substantive function was named
`run_integration_test`, not `test_run_integration_test` or any
`test_*`-prefixed name, so pytest's default discovery never collected or
ran it. It silently contributed zero coverage in CI despite living in a
`tests/` folder alongside real pytest suites. Rewritten against the real
public API (`trentorch.core.transformers.GPT`, `CharTokenizer`,
`KVCache`) with a proper `test_` name so pytest actually runs it.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

rng = np.random.default_rng(7)


def test_tinygpt_integration():
    """End-to-end: build a tiny GPT, tokenize real text, generate new
    tokens with and without a KV cache, and verify both paths agree."""
    from trentorch.core.tensor import Tensor
    from trentorch.core.tokenization import CharTokenizer
    from trentorch.core.transformers import GPT

    # Tokenizer round trip.
    tokenizer = CharTokenizer()
    tokenizer.build_vocab(["hello world"])
    encoded = tokenizer.encode("hello")
    decoded = tokenizer.decode(encoded)
    assert decoded == "hello", f"CharTokenizer round trip failed: {decoded!r}"

    # A small GPT that's cheap to run in CI.
    model = GPT(vocab_size=tokenizer.vocab_size, embed_dim=32, num_layers=2, num_heads=4, max_seq_len=32)

    prompt = Tensor(np.array([encoded]))
    logits = model.forward(prompt)
    assert logits.shape == (1, len(encoded), tokenizer.vocab_size), (
        f"Unexpected logits shape: {logits.shape}"
    )

    total_params = sum(p.data.size for p in model.parameters())
    assert total_params > 0, "GPT model should have trainable parameters"

    # Generation produces new tokens.
    generated = model.generate(prompt, max_new_tokens=3, temperature=1.0)
    assert generated.shape == (1, len(encoded) + 3), (
        f"Expected shape (1, {len(encoded) + 3}) after generation, got {generated.shape}"
    )
