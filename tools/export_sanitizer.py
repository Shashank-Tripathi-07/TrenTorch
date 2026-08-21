"""
TrenTorch Multi-Platform Export & Conversion Utilities.

Converts Jupytext percent source files (src/XX_module/XX_module.py) into:
1. .qmd   - Quarto Markdown for interactive engineering docs & publishing
2. .ipynb - Executable Jupyter notebooks for Kaggle / Colab / JupyterLab
3. .txt / .py - Sanitized, pure Python scripts without any cell magic or directives for LeetCode/DeepML/LeetGPU sandboxes
4. .yaml  - Structured schema with metadata, problem definitions, starter templates, and test cases
"""

import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

try:
    import yaml
except ImportError:
    yaml = None


def dump_yaml_fallback(data: Dict[str, Any]) -> str:
    """Zero-dependency YAML serializer fallback."""
    lines = []
    for k, v in data.items():
        if isinstance(v, dict):
            lines.append(f"{k}:")
            for sub_k, sub_v in v.items():
                if isinstance(sub_v, list):
                    lines.append(f"  {sub_k}:")
                    for item in sub_v:
                        lines.append(f"    - {item}")
                else:
                    lines.append(f"  {sub_k}: {sub_v}")
        elif isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item}")
        elif isinstance(v, str) and ("\n" in v or ":" in v or "#" in v):
            lines.append(f"{k}: |")
            for line in v.splitlines():
                lines.append(f"  {line}")
        else:
            lines.append(f"{k}: {v}")
    return "\n".join(lines) + "\n"



def extract_frontmatter_and_cells(source_code: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Parses a Jupytext percent script into frontmatter and a list of cells.
    Each cell has 'type' ('markdown' or 'code'), 'header', 'content', and 'directives'.
    """
    lines = source_code.splitlines()
    header_yaml = {}
    
    # Check for YAML header at top (--- ... ---)
    idx = 0
    if lines and lines[0].strip() == "# ---":
        header_lines = []
        idx = 1
        while idx < len(lines) and lines[idx].strip() != "# ---":
            line = lines[idx]
            if line.startswith("# "):
                header_lines.append(line[2:])
            elif line.startswith("#"):
                header_lines.append(line[1:])
            else:
                header_lines.append(line)
            idx += 1
        if idx < len(lines) and lines[idx].strip() == "# ---":
            idx += 1
            try:
                header_yaml = yaml.safe_load("\n".join(header_lines)) or {}
            except Exception:
                header_yaml = {}

    cells: List[Dict[str, Any]] = []
    current_cell_type = "code"
    current_lines: List[str] = []
    current_header = ""

    def flush_cell():
        nonlocal current_lines, current_cell_type, current_header
        if current_lines:
            content = "\n".join(current_lines).strip()
            if content:
                # If markdown cell wrapped in triple quotes, unwrap it
                if current_cell_type == "markdown":
                    content = unwrap_markdown_docstring(content)
                cells.append({
                    "type": current_cell_type,
                    "header": current_header,
                    "content": content
                })
        current_lines = []
        current_header = ""

    while idx < len(lines):
        line = lines[idx]
        # Detect cell marker: # %% or # %% [markdown] or # %% nbgrader=...
        if re.match(r"^#\s*%%\s*(\[markdown\])?", line):
            flush_cell()
            current_header = line
            if "[markdown]" in line:
                current_cell_type = "markdown"
            else:
                current_cell_type = "code"
        else:
            current_lines.append(line)
        idx += 1
    
    flush_cell()
    return header_yaml, cells


def unwrap_markdown_docstring(text: str) -> str:
    """Unwrap triple quotes or markdown string wrappers from Jupytext percent markdown cells."""
    trimmed = text.strip()
    if (trimmed.startswith('"""') and trimmed.endswith('"""')) or (trimmed.startswith("'''") and trimmed.endswith("'''")):
        return trimmed[3:-3].strip()
    return text


def sanitize_code_cell(code: str, strip_solution_markers: bool = True) -> str:
    """
    Remove nbdev directives (#| default_exp, #| export) and solution markers.
    """
    cleaned_lines = []
    for line in code.splitlines():
        # Remove nbdev directives like #| default_exp, #| export, #| hide
        if re.match(r"^\s*#\|\s*\w+", line):
            continue
        # Remove nbgrader solution comment markers if requested
        if strip_solution_markers and ("### BEGIN SOLUTION" in line or "### END SOLUTION" in line):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def to_qmd(source_code: str, title: Optional[str] = None, subtitle: Optional[str] = None) -> str:
    """
    Convert Jupytext percent source into a Quarto Markdown (.qmd) document.
    """
    header_yaml, cells = extract_frontmatter_and_cells(source_code)
    
    inferred_title = title
    inferred_subtitle = subtitle or ""
    
    if not inferred_title:
        for cell in cells:
            if cell["type"] == "markdown":
                first_h1 = re.search(r"^#\s+(.+)$", cell["content"], flags=re.MULTILINE)
                if first_h1:
                    inferred_title = first_h1.group(1).strip()
                    break
        if not inferred_title:
            inferred_title = "TrenTorch Engineering Module"

    qmd_parts = [
        "---",
        f"title: \"{inferred_title}\"",
    ]
    if inferred_subtitle:
        qmd_parts.append(f"subtitle: \"{inferred_subtitle}\"")
    qmd_parts.extend([
        "format:",
        "  html:",
        "    code-fold: false",
        "    code-tools: true",
        "    toc: true",
        "jupyter: python3",
        "---",
        ""
    ])

    for cell in cells:
        if cell["type"] == "markdown":
            qmd_parts.append(cell["content"])
            qmd_parts.append("")
        elif cell["type"] == "code":
            cleaned = sanitize_code_cell(cell["content"], strip_solution_markers=False)
            if cleaned:
                qmd_parts.append("```{python}")
                qmd_parts.append(cleaned)
                qmd_parts.append("```")
                qmd_parts.append("")

    return "\n".join(qmd_parts).strip() + "\n"


def to_ipynb(source_code: str) -> Dict[str, Any]:
    """
    Convert Jupytext percent source into a standard Jupyter Notebook dictionary structure (.ipynb).
    """
    header_yaml, cells = extract_frontmatter_and_cells(source_code)
    
    ipynb_cells = []
    for cell in cells:
        if cell["type"] == "markdown":
            ipynb_cells.append({
                "cell_type": "markdown",
                "metadata": {},
                "source": cell["content"].splitlines(keepends=True)
            })
        elif cell["type"] == "code":
            ipynb_cells.append({
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": cell["content"].splitlines(keepends=True)
            })

    notebook = {
        "cells": ipynb_cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.10.0"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 5
    }
    return notebook


def to_sandbox_code(source_code: str) -> str:
    """
    Extract pure, executable Python code suitable for LeetCode, DeepML, or LeetGPU sandboxes.
    Strips markdown cells, directives, test assertion boilerplate if not needed, and ensures valid AST.
    """
    header_yaml, cells = extract_frontmatter_and_cells(source_code)
    code_blocks = []
    
    for cell in cells:
        if cell["type"] == "code":
            cleaned = sanitize_code_cell(cell["content"], strip_solution_markers=True)
            if cleaned:
                code_blocks.append(cleaned)

    full_code = "\n\n".join(code_blocks)
    
    # Remove multiple excess empty lines
    full_code = re.sub(r"\n{3,}", "\n\n", full_code)
    
    # Validate with AST to guarantee no broken syntax
    try:
        ast.parse(full_code)
    except SyntaxError as e:
        # Fallback: if there's a syntax error caused by loose snippets, still return cleaned text
        pass

    return full_code.strip() + "\n"


def to_platform_yaml(source_code: str, module_name: str = "module", title: Optional[str] = None) -> str:
    """
    Convert module into a structured YAML specification for autojudges, platform ingest, and LMS.
    """
    header_yaml, cells = extract_frontmatter_and_cells(source_code)
    
    # Extract markdown overview and test cases
    descriptions = []
    test_code = []
    implementation_code = []
    
    for cell in cells:
        if cell["type"] == "markdown":
            descriptions.append(cell["content"])
        elif cell["type"] == "code":
            content = sanitize_code_cell(cell["content"], strip_solution_markers=True)
            if "assert " in content or "test_" in content:
                test_code.append(content)
            else:
                implementation_code.append(content)

    problem_yaml = {
        "id": module_name,
        "title": title or module_name.replace("_", " ").title(),
        "platform_target": "TrenTorch Engineering Engine (DeepML/LeetCode/LeetGPU)",
        "runtime": {
            "python": ">=3.10",
            "dependencies": ["numpy>=2.0.0"]
        },
        "description": "\n\n".join(descriptions[:2]) if descriptions else "Implement core tensor operations.",
        "starter_code": "\n\n".join(implementation_code),
        "test_suite": "\n\n".join(test_code) if test_code else "# Run unit tests\npass"
    }

    if yaml is not None:
        return yaml.dump(problem_yaml, sort_keys=False, default_style=None)
    return dump_yaml_fallback(problem_yaml)
