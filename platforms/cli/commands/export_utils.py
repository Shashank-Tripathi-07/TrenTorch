"""
Shared helpers for TrenTorch export workflows.

These utilities are used by both ExportCommand and SrcCommand to avoid
duplicate logic when converting source files to notebooks, exporting via
nbdev, and protecting generated files.
"""

import json
import re
import stat
import subprocess
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Stub / solution variant splitting
#
# data/src/<NN>/<NN>.py holds paired cells: a stub cell (raises NotImplementedError,
# no #| export) immediately followed by its solution cell (tags=["solution"],
# has #| export). Two things get generated from that single source:
#
#   - stub variant   -> data/modules/   (student-facing; the solution cell is
#                        dropped entirely, and #| export is added back onto
#                        the stub so a student's own filled-in code is what
#                        gets picked up by nbdev once they solve it)
#   - solution variant -> data/solutions/ (maintainer/CI-only reference; the
#                        stub cell is dropped, solution cell kept as-is -- this
#                        is exactly what data/src/<NN>/<NN>.py looked like before
#                        the stub/solution split)
# ---------------------------------------------------------------------------

_CELL_SPLIT = re.compile(r"(?=^# %%)", re.MULTILINE)
_EXPORT_DIRECTIVE = "#| export"


def _cell_header(cell_text: str) -> str:
    return cell_text.split("\n", 1)[0]


def _is_solution_cell(cell_text: str) -> bool:
    header = _cell_header(cell_text)
    return 'tags=["solution"]' in header or "tags=['solution']" in header


def _split_directives(cell_text: str):
    """Return (header_line, directive_lines, body) for one cell's text.

    Tolerates blank lines between the `# %%` header and the first `#|`
    directive line (a real pattern found in src/05_dataloader/05_dataloader.py
    that a stricter, no-blank-line version of this function once silently
    mishandled, leaving a stray #| export sitting unrecognized in a cell's
    body instead of its directive list -- which meant nbdev never exported
    that cell at all).
    """
    lines = cell_text.split("\n")
    header_line = lines[0]
    idx = 1
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    directive_lines = []
    while idx < len(lines) and lines[idx].startswith("#|"):
        directive_lines.append(lines[idx])
        idx += 1
    body = "\n".join(lines[idx:])
    return header_line, directive_lines, body


class UnpairedSolutionCellError(ValueError):
    """A solution-tagged cell wasn't reachable as some earlier cell's
    +1 partner (either it's the very first real cell in the file, or it
    directly follows another solution cell that already consumed the
    pairing check).

    Pairing only ever inspects cells[i+1] to decide whether cells[i] is a
    stub; nothing ever checks whether cells[i] is itself already a solution
    cell before falling through to "append it as an ordinary cell". An
    orphaned solution cell hitting that fallthrough is exactly how the
    dropped-MSEBackward and dropped-Profiler-import incidents (section 6 of
    docs/testing-strategy.md) happened, and in make_stub_variant it's worse
    than a drop: the cell's full, unmodified solution code gets copied
    straight into the student-facing package instead of being stripped.
    Raising here turns that into a loud, immediate export failure instead
    of a silent correctness or academic-integrity bug.
    """


def make_stub_variant(source: str) -> str:
    """Student-facing source: solution cells dropped, stub cells gain #| export."""
    cells = _CELL_SPLIT.split(source)
    out = []
    i = 0
    while i < len(cells):
        cell = cells[i]
        # _CELL_SPLIT's lookahead matches at position 0 for any real file
        # (they always start with "# %%"), leaving an empty phantom cell at
        # index 0 that has no real header of its own. Without `cell.strip()`
        # here, that phantom would silently "absorb" a solution cell at
        # index 1 as though it were a legitimate stub pairing -- the one
        # orphan case UnpairedSolutionCellError below can't see, since the
        # phantom itself is never solution-tagged. Requiring real content
        # here excludes only that synthetic artifact; every genuine cell
        # (stub or solution) always has non-empty "# %% ..." content.
        if cell.strip() and i + 1 < len(cells) and _is_solution_cell(cells[i + 1]):
            header_line, directive_lines, body = _split_directives(cell)
            if not any(d.strip() == _EXPORT_DIRECTIVE for d in directive_lines):
                directive_lines = directive_lines + [_EXPORT_DIRECTIVE]
            new_cell = header_line + "\n"
            if directive_lines:
                new_cell += "\n".join(directive_lines) + "\n"
            new_cell += body
            out.append(new_cell)
            i += 2  # skip the paired solution cell
        else:
            if _is_solution_cell(cell):
                raise UnpairedSolutionCellError(
                    f"Cell {i} is tagged solution but isn't paired with a preceding "
                    f"stub cell (header: {_cell_header(cell)!r}). Refusing to export "
                    "it, since falling through here would copy the full solution "
                    "into the student-facing stub package unmodified."
                )
            out.append(cell)
            i += 1
    return "".join(out)


def make_solution_variant(source: str) -> str:
    """Maintainer/CI-only source: stub cells dropped, solution cells kept."""
    cells = _CELL_SPLIT.split(source)
    out = []
    i = 0
    while i < len(cells):
        cell = cells[i]
        # See the matching comment in make_stub_variant: cell.strip()
        # excludes _CELL_SPLIT's empty phantom cell at index 0 from
        # eligibility to "absorb" a solution cell at index 1.
        if cell.strip() and i + 1 < len(cells) and _is_solution_cell(cells[i + 1]):
            out.append(cells[i + 1])
            i += 2
        else:
            if _is_solution_cell(cell):
                raise UnpairedSolutionCellError(
                    f"Cell {i} is tagged solution but isn't paired with a preceding "
                    f"stub cell (header: {_cell_header(cell)!r}). This variant would "
                    "include it correctly either way, but the same malformed "
                    "structure silently leaks solution code in make_stub_variant, "
                    "so both functions fail loud together rather than one silently "
                    "succeeding while the other silently corrupts its output."
                )
            out.append(cell)
            i += 1
    return "".join(out)


# Mapping from generated package paths back to source files
# Keys are (subpackage, module) tuples matching default_exp directives
SOURCE_MAPPINGS = {
    ("core", "tensor"): "data/src/01_tensor/01_tensor.py",
    ("core", "activations"): "data/src/02_activations/02_activations.py",
    ("core", "layers"): "data/src/03_layers/03_layers.py",
    ("core", "losses"): "data/src/04_losses/04_losses.py",
    ("core", "dataloader"): "data/src/05_dataloader/05_dataloader.py",
    ("core", "autograd"): "data/src/06_autograd/06_autograd.py",
    ("core", "optimizers"): "data/src/07_optimizers/07_optimizers.py",
    ("core", "training"): "data/src/08_training/08_training.py",
    ("core", "spatial"): "data/src/09_convolutions/09_convolutions.py",
    ("core", "tokenization"): "data/src/10_tokenization/10_tokenization.py",
    ("core", "embeddings"): "data/src/11_embeddings/11_embeddings.py",
    ("core", "attention"): "data/src/12_attention/12_attention.py",
    ("core", "transformers"): "data/src/13_transformers/13_transformers.py",
    ("perf", "profiling"): "data/src/14_profiling/14_profiling.py",
    ("perf", "quantization"): "data/src/15_quantization/15_quantization.py",
    ("perf", "compression"): "data/src/16_compression/16_compression.py",
    ("perf", "acceleration"): "data/src/17_acceleration/17_acceleration.py",
    ("perf", "memoization"): "data/src/18_memoization/18_memoization.py",
    ("perf", "benchmarking"): "data/src/19_benchmarking/19_benchmarking.py",
    ("olympics",): "data/src/20_capstone/20_capstone.py",
}


def get_export_target(module_path: Path) -> str:
    """Read export target from #| default_exp in the source file."""
    module_name = module_path.name
    path_str = str(module_path)
    in_generated_dir = (
        "data/modules" in path_str
        or "data/solutions" in path_str
        or "data\\modules" in path_str
        or "data\\solutions" in path_str
    )
    source_path = Path("data") / "src" / module_name if in_generated_dir else module_path
    dev_file = source_path / f"{module_name}.py"
    if not dev_file.exists():
        return "unknown"

    try:
        content = dev_file.read_text(encoding="utf-8")
        match = re.search(r"#\|\s*default_exp\s+([^\n\r]+)", content)
        if match:
            return match.group(1).strip()
    except Exception:
        return "unknown"

    return "unknown"


def discover_modules(source_dir: Path = Path("data") / "src") -> list[str]:
    """List module directories under src/ excluding common non-module folders."""
    modules = []
    if source_dir.exists():
        exclude_dirs = {".quarto", "__pycache__", ".git", ".pytest_cache"}
        for module_dir in source_dir.iterdir():
            if module_dir.is_dir() and module_dir.name not in exclude_dirs:
                modules.append(module_dir.name)
    return sorted(modules)


def validate_notebook_integrity(notebook_path: Path) -> dict:
    """Basic validation for generated notebooks."""
    try:
        notebook_data = json.loads(notebook_path.read_text(encoding="utf-8"))

        issues = []
        warnings = []

        if "cells" not in notebook_data:
            issues.append("Missing 'cells' field")
        elif not isinstance(notebook_data["cells"], list):
            issues.append("'cells' field is not a list")

        if "metadata" not in notebook_data:
            warnings.append("Missing metadata field")

        if "nbformat" not in notebook_data:
            warnings.append("Missing nbformat field")

        cell_count = 0
        code_cells = 0
        markdown_cells = 0
        if "cells" in notebook_data:
            for i, cell in enumerate(notebook_data["cells"]):
                cell_count += 1
                if "cell_type" not in cell:
                    issues.append(f"Cell {i}: missing cell_type")
                    continue
                cell_type = cell["cell_type"]
                if cell_type == "code":
                    code_cells += 1
                    if "source" not in cell:
                        warnings.append(f"Code cell {i}: missing source")
                elif cell_type == "markdown":
                    markdown_cells += 1
                    if "source" not in cell:
                        warnings.append(f"Markdown cell {i}: missing source")
                else:
                    warnings.append(f"Cell {i}: unusual cell type '{cell_type}'")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "stats": {
                "total_cells": cell_count,
                "code_cells": code_cells,
                "markdown_cells": markdown_cells,
            },
        }

    except json.JSONDecodeError as e:
        return {
            "valid": False,
            "issues": [f"Invalid JSON: {str(e)}"],
            "warnings": [],
            "stats": {},
        }
    except Exception as e:
        return {
            "valid": False,
            "issues": [f"Validation error: {str(e)}"],
            "warnings": [],
            "stats": {},
        }


def check_notebook_solved(notebook_path: Path) -> tuple[bool, list[str]]:
    """Scan a student's stub notebook for code cells that still raise NotImplementedError.

    `tren module test`'s Phase 1 (data/src/<module>.py) and Phase 2 (pytest against
    the installed trentorch package) never read this notebook, so both can report
    a full pass even when every stub here is untouched. This is the check that
    actually looks at what the student wrote.
    """
    try:
        notebook_data = json.loads(notebook_path.read_text(encoding="utf-8"))
    except Exception as e:
        return False, [f"Could not read notebook: {e}"]

    unresolved = []
    for cell in notebook_data.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)

        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("raise NotImplementedError"):
                first_line = next(
                    (
                        s.strip()
                        for s in source.strip().splitlines()
                        if s.strip() and not s.strip().startswith("#|")
                    ),
                    "(empty cell)",
                )
                unresolved.append(first_line[:80])
                break

    return len(unresolved) == 0, unresolved


def _resolve_jupytext_path(venv_path: Path, console) -> str:
    from ..core.virtual_env_manager import get_venv_bin_dir

    jupytext_path = "jupytext"
    venv_jupytext = get_venv_bin_dir(venv_path) / "jupytext"

    if venv_jupytext.exists():
        test_result = subprocess.run(
            [str(venv_jupytext), "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if test_result.returncode == 0:
            console.print(f"[dim]🔧 Using venv jupytext: {venv_jupytext}[/dim]")
            return str(venv_jupytext)
        console.print("[dim]⚠️  Venv jupytext has issues, falling back to system[/dim]")
    console.print(f"[dim]🔧 Using system jupytext: {jupytext_path}[/dim]")
    return jupytext_path


def convert_py_to_notebook(
    module_path: Path, venv_path: Path, console, variant: str = "stub", target_root: str = "data/modules"
) -> bool:
    """Convert src/<module>.py to <target_root>/<module>.ipynb using jupytext.

    variant selects which cell content the notebook gets:
      - "stub": solution cells dropped, stub cells gain #| export (data/modules/)
      - "solution": stub cells dropped, solution cells kept (data/solutions/)
      - "full": no filtering, exactly what src/<module>.py contains
    """
    project_root = Path(__file__).resolve().parents[3]  # trentorch project root
    module_path = module_path if module_path.is_absolute() else project_root / module_path
    module_name = module_path.name
    dev_file = module_path / f"{module_name}.py"
    if not dev_file.exists():
        console.print(f"[red]❌ Python file not found: {dev_file}[/red]")
        return False

    short_name = module_name.split("_", 1)[1] if "_" in module_name else module_name
    target_dir = project_root / target_root / module_name
    target_dir.mkdir(parents=True, exist_ok=True)
    notebook_file = target_dir / f"{short_name}.ipynb"

    source = dev_file.read_text(encoding="utf-8")
    if variant == "stub":
        transformed = make_stub_variant(source)
    elif variant == "solution":
        transformed = make_solution_variant(source)
    else:
        transformed = source

    rel_notebook = notebook_file.relative_to(project_root)
    console.print(f"[dim]📄 Source: {dev_file.name} → Target: {rel_notebook}[/dim]")
    console.print(
        "[dim]🔄 Overwriting existing notebook (Python file is source of truth)[/dim]"
        if notebook_file.exists()
        else "[dim]✨ Creating new notebook from Python file[/dim]"
    )

    tmp_source = None
    try:
        jupytext_path = _resolve_jupytext_path(venv_path, console)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=f"_{module_name}.py", delete=False, encoding="utf-8", dir=str(project_root)
        ) as tmp:
            tmp.write(transformed)
            tmp_source = Path(tmp.name)

        console.print(
            f"[dim]⚙️  Running: {jupytext_path} --to ipynb ({variant} variant) --output {notebook_file}[/dim]"
        )
        result = subprocess.run(
            [jupytext_path, "--to", "ipynb", str(tmp_source), "--output", str(notebook_file)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=project_root,
        )

        if result.returncode != 0:
            console.print(f"[red]❌ Jupytext failed with return code {result.returncode}[/red]")
            if result.stderr:
                console.print(f"[red]Error: {result.stderr.strip()}[/red]")
            return False

        validation = validate_notebook_integrity(notebook_file)
        if not validation["valid"]:
            console.print("[red]❌ Generated notebook has integrity issues:[/red]")
            for issue in validation["issues"]:
                console.print(f"[red]  • {issue}[/red]")
            return False

        if validation["warnings"]:
            console.print("[yellow]⚠️  Notebook warnings:[/yellow]")
            for warning in validation["warnings"]:
                console.print(f"[yellow]  • {warning}[/yellow]")

        stats = validation["stats"]
        console.print(
            f"[dim]📊 Generated notebook: {stats.get('total_cells', 0)} cells "
            f"({stats.get('code_cells', 0)} code, {stats.get('markdown_cells', 0)} markdown)[/dim]"
        )
        return True

    except FileNotFoundError:
        console.print("[red]❌ Jupytext not found. Install with: pip install jupytext[/red]")
        return False
    except Exception as e:
        console.print(f"[red]❌ Conversion error: {e}[/red]")
        return False
    finally:
        if tmp_source is not None:
            try:
                tmp_source.unlink(missing_ok=True)
            except OSError:
                pass


def convert_all_modules(
    venv_path: Path, console, variant: str = "stub", target_root: str = "data/modules"
) -> list[str]:
    """Convert all src modules to notebooks of the given variant."""
    converted = []
    for module_name in discover_modules():
        module_path = Path("data") / "src" / module_name
        if convert_py_to_notebook(module_path, venv_path, console, variant=variant, target_root=target_root):
            converted.append(module_name)
    return converted


def find_source_file_for_export(exported_file: Path) -> str:
    """Map an exported package file back to its source file."""
    rel_path = exported_file.relative_to(Path("data") / "trentorch")
    module_parts = rel_path.with_suffix("").parts
    if module_parts in SOURCE_MAPPINGS:
        return SOURCE_MAPPINGS[module_parts]
    if len(module_parts) >= 2:
        module_name = module_parts[-1]
        return f"data/src/XX_{module_name}/XX_{module_name}.py"
    return "data/src/[unknown]/[unknown].py"


def add_autogenerated_warnings(console) -> None:
    """Inject DO NOT EDIT headers into generated package files."""
    console.print("[yellow]🔧 Adding DO NOT EDIT warnings to all exported files...[/yellow]")
    trentorch_path = Path("data") / "trentorch"
    if not trentorch_path.exists():
        return

    files_updated = 0
    for py_file in trentorch_path.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
            if "╔═══════════════════════════════════════════════════════════════════════════════╗" in content:
                continue
            if "AUTOGENERATED! DO NOT EDIT! File to edit:" in content:
                lines = content.split("\n")
                if lines and "AUTOGENERATED! DO NOT EDIT! File to edit:" in lines[0]:
                    lines = lines[1:]
                    if lines and lines[0].strip() == "":
                        lines = lines[1:]
                    content = "\n".join(lines)

            source_file = find_source_file_for_export(py_file)
            warning_header = f"""# ╔═══════════════════════════════════════════════════════════════════════════════╗
# ║                        🚨 CRITICAL WARNING 🚨                                ║
# ║                     AUTOGENERATED! DO NOT EDIT!                              ║
# ║                                                                               ║
# ║  This file is AUTOMATICALLY GENERATED from source modules.                   ║
# ║  ANY CHANGES MADE HERE WILL BE LOST when modules are re-exported!            ║
# ║                                                                               ║
# ║  ✅ TO EDIT: {source_file:<54} ║
# ║  ✅ TO EXPORT: Run 'tren module complete XX'                                 ║
# ║                                                                               ║
# ║  🛡️ STUDENT PROTECTION: This file contains optimized implementations.        ║
# ║     Editing it directly may break module functionality and training.         ║
# ║                                                                               ║
# ║  🎓 LEARNING TIP: Work in src/ (developers) or data/modules/ (learners)      ║
# ║     The trentorch/ directory is generated code - edit source files instead!  ║
# ╚═══════════════════════════════════════════════════════════════════════════════╝
"""
            lines = content.split("\n")
            insert_index = 0
            if lines and lines[0].startswith("#!"):
                insert_index = 1
            lines.insert(insert_index, warning_header.rstrip())
            py_file.write_text("\n".join(lines), encoding="utf-8")
            files_updated += 1
        except Exception as e:
            console.print(f"[yellow]⚠️  Could not add warning to {py_file}: {e}[/yellow]")

    if files_updated > 0:
        console.print(f"[green]✅ Added auto-generated warnings to {files_updated} files[/green]")


def ensure_writable_target(export_target: str) -> None:
    """Ensure target file is writable before export."""
    if export_target == "unknown":
        return
    target_file = Path("data") / "trentorch" / (export_target.replace(".", "/") + ".py")
    if target_file.exists():
        try:
            target_file.chmod(target_file.stat().st_mode | stat.S_IWUSR)
        except Exception:
            # Best effort; ignore permission errors
            pass
