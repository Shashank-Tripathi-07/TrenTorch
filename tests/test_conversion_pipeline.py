"""
Tests for TrenTorch Multi-Platform Conversion Pipeline & Platform Adapters.
"""

import ast
import json
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

from trentorch.core.platform import PlatformDetector
from trentorch.export_sanitizer import (
    extract_frontmatter_and_cells,
    to_ipynb,
    to_platform_yaml,
    to_qmd,
    to_sandbox_code,
)

SAMPLE_JUPYTEXT_SOURCE = '''# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
# ---

# %% [markdown]
"""
# Module 01: Tensor Operations
Welcome to Tensor foundations!
"""

# %% nbgrader={"grade": false, "grade_id": "imports", "solution": true}
#| default_exp core.tensor
#| export
import numpy as np

class Tensor:
    """A foundational Tensor wrapper."""
    def __init__(self, data, requires_grad=False):
        self.data = np.array(data)
        self.requires_grad = requires_grad

    def shape(self):
        return self.data.shape

# %% [markdown]
"""
## Tests and Assertions
"""

# %%
def test_tensor():
    t = Tensor([1, 2, 3])
    assert t.shape() == (3,)
'''


def test_extract_cells():
    header, cells = extract_frontmatter_and_cells(SAMPLE_JUPYTEXT_SOURCE)
    assert len(cells) >= 3
    assert any(c["type"] == "markdown" for c in cells)
    assert any(c["type"] == "code" for c in cells)


def test_to_qmd():
    qmd = to_qmd(SAMPLE_JUPYTEXT_SOURCE, title="Tensor Operations")
    assert 'title: "Tensor Operations"' in qmd
    assert "```{python}" in qmd
    assert "class Tensor:" in qmd
    assert "#| default_exp" not in qmd  # stripped nbdev directives


def test_to_ipynb():
    nb = to_ipynb(SAMPLE_JUPYTEXT_SOURCE)
    assert "cells" in nb
    assert nb["nbformat"] == 4
    assert len(nb["cells"]) >= 3
    # Check JSON serializable
    dumped = json.dumps(nb)
    assert len(dumped) > 0


def test_to_sandbox_code():
    code = to_sandbox_code(SAMPLE_JUPYTEXT_SOURCE)
    # Check valid Python syntax via AST
    parsed = ast.parse(code)
    assert parsed is not None
    assert "class Tensor:" in code
    assert "# %%" not in code
    assert "#| export" not in code


def test_to_platform_yaml():
    yaml_str = to_platform_yaml(SAMPLE_JUPYTEXT_SOURCE, module_name="01_tensor")
    assert "id: 01_tensor" in yaml_str or 'id: "01_tensor"' in yaml_str
    assert "starter_code:" in yaml_str
    assert "class Tensor:" in yaml_str
    if yaml is not None:
        data = yaml.safe_load(yaml_str)
        assert data["id"] == "01_tensor"
        assert "starter_code" in data
        assert "class Tensor:" in data["starter_code"]


def test_platform_detector():
    platform = PlatformDetector.get_platform()
    assert platform in {"jupyter", "standard"}
    assert isinstance(PlatformDetector.is_interactive(), bool)


def test_real_module_conversion():
    source_file = Path("data/src/01_tensor/01_tensor.py")
    if source_file.exists():
        raw_code = source_file.read_text(encoding="utf-8")
        sandbox_code = to_sandbox_code(raw_code)
        assert len(sandbox_code) > 100
        assert "class Tensor" in sandbox_code

        qmd_code = to_qmd(raw_code)
        assert "```{python}" in qmd_code

        yaml_code = to_platform_yaml(raw_code, module_name="01_tensor")
        assert "starter_code:" in yaml_code
        if yaml is not None:
            parsed_yaml = yaml.safe_load(yaml_code)
            assert parsed_yaml["id"] == "01_tensor"
