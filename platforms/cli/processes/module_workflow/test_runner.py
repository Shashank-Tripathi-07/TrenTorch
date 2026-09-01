"""The module test-running component, all in one place.

Runs a module's inline tests (its data/src/*.py `if __name__ == "__main__"`
block, in-process via runpy) and its progressive integration tests
(pytest against tests/<module>/), parses both kinds of output into a
uniform pass/fail shape, and checks a student notebook for syntax
errors before export. Used by `tren module complete`'s pipeline.

Note: `tren module test` (commands/module/test.py's ModuleTestCommand)
has its own, separately-implemented three-phase test runner (inline,
pytest with the --tinytorch educational-output flag, integration) that
does not call into this file. The two exist in parallel rather than
sharing one implementation; that's a real duplication worth resolving
later, not addressed by this file's existence.
"""

import contextlib
import io
import json
import os
import runpy
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

#: Set by the maintainer curriculum-verification loop (`tren dev test
#: --inline`, via `tren/platforms/cli_platform/dev/test.py`) so that `tren module
#: complete` -- which it shells out to per module -- tests and exports
#: the known-working reference implementation instead of a student's
#: (here, nobody's) notebook. Never set for a real student run.
VERIFY_SOLUTION_ENV = "TREN_DEV_VERIFY_SOLUTION"


def _extract_notebook_source(notebook_path: Path) -> str:
    """Concatenate a notebook's code cells into one executable script.

    Drops IPython magics/shell escapes (not valid plain Python), same
    filtering as check_notebook_syntax below. Cell order is preserved,
    so a trailing `if __name__ == "__main__":` self-test cell still
    fires when the result is run with run_name="__main__".
    """
    nb = json.loads(notebook_path.read_text(encoding="utf-8"))
    blocks = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)
        code = "\n".join(ln for ln in source.splitlines() if not ln.lstrip().startswith(("%", "!")))
        if code.strip():
            blocks.append(code)
    return "\n\n".join(blocks)


def run_inline_unit_tests(config, console, module_name: str, verbose: bool) -> dict[str, int]:
    """Run inline unit tests and parse output for detailed display.

    By default (the real student flow), this runs the student's own
    notebook (data/modules/<module>/<name>.ipynb) -- their filled-in
    code is what gets tested, matching a real stub-only assignment: an
    unsolved stub fails here with a clear NotImplementedError, not a
    silent pass. When TREN_DEV_VERIFY_SOLUTION is set (the maintainer
    curriculum-verification loop, where no student notebook has been
    solved), it runs the instructor's data/src/*.py file directly instead,
    exactly as this always worked before the stub/solution split.

    Either way, the code is executed in-process via runpy (as if it
    were `python file.py`, so `if __name__ == "__main__"` test blocks
    still fire) instead of spawning a new Python interpreter subprocess
    per module. A prior version of this tried the same change and was
    reverted after Module 10 appeared to hang: it was never actually a
    hang, direct profiling showed it stuck in real, expensive BPE
    computation inside an analyze_*() demo block (not a correctness
    check) that CI now skips entirely via the CI=true guard added to
    those blocks. With that guard in place, this is safe to retry: the
    thing that made it look like a state-leak-induced hang no longer
    runs under CI at all, and the remaining correctness-check code is
    fast. Each module's globals are still isolated per run (runpy
    builds a fresh namespace per call), matching subprocess isolation
    for the common case.
    """
    project_root = Path.cwd()
    verify_solution = os.environ.get(VERIFY_SOLUTION_ENV) == "1"

    tmp_source: Path | None = None
    if verify_solution:
        run_target = project_root / "data" / "src" / module_name / f"{module_name}.py"
        if not run_target.exists():
            if verbose:
                console.print(f"   [dim yellow]No source file found: {run_target}[/dim yellow]")
            return {"passed": 0, "failed": 0, "tests": [], "returncode": 0}
    else:
        short_name = module_name.split("_", 1)[1] if "_" in module_name else module_name
        notebook_path = project_root / "data" / "modules" / module_name / f"{short_name}.ipynb"
        if not notebook_path.exists():
            if verbose:
                console.print(f"   [dim yellow]No notebook found: {notebook_path}[/dim yellow]")
            return {"passed": 0, "failed": 0, "tests": [], "returncode": 0}
        source = _extract_notebook_source(notebook_path)
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=f"_{module_name}.py", delete=False, encoding="utf-8", dir=str(project_root)
        )
        tmp.write(source)
        tmp.close()
        tmp_source = Path(tmp.name)
        run_target = tmp_source

    # Matches the old subprocess's PYTHONPATH=project_root: makes
    # `from trentorch.core.* import ...` resolve the same way.
    project_root_str = str(project_root)
    path_was_added = project_root_str not in sys.path
    if path_was_added:
        sys.path.insert(0, project_root_str)

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    returncode = 0
    try:
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            runpy.run_path(str(run_target.absolute()), run_name="__main__")
    except SystemExit as exc:
        returncode = exc.code if isinstance(exc.code, int) else (1 if exc.code else 0)
    except Exception:
        returncode = 1
        stderr_buffer.write(traceback.format_exc())
    finally:
        if path_was_added:
            try:
                sys.path.remove(project_root_str)
            except ValueError:
                pass
        if tmp_source is not None:
            try:
                tmp_source.unlink(missing_ok=True)
            except OSError:
                pass

    stdout_text = stdout_buffer.getvalue()
    stderr_text = stderr_buffer.getvalue()

    # Parse output to extract individual test results
    tests_run = _parse_test_output(stdout_text, stderr_text, returncode)

    if verbose:
        for test in tests_run:
            icon = "✅" if test["passed"] else "❌"
            color = "green" if test["passed"] else "red"
            console.print(f"   [{color}]{icon} {test['name']}[/{color}]")
            if not test["passed"] and test.get("error"):
                # Show error on next line with indentation
                error_lines = test["error"].split("\n")
                for error_line in error_lines[:3]:  # Show first 3 lines of error
                    if error_line.strip():
                        console.print(f"      [dim red]{error_line.strip()}[/dim red]")

    passed = sum(1 for t in tests_run if t["passed"])
    failed = sum(1 for t in tests_run if not t["passed"])

    return {"passed": passed, "failed": failed, "tests": tests_run, "returncode": returncode}


def run_integration_tests(config, console, module_name: str, verbose: bool) -> dict[str, int]:
    """Run progressive integration tests using pytest."""
    project_root = Path.cwd()

    # Most modules use test_<module>_progressive.py; a few (15/16/17/19/20)
    # use test_<topic>_core.py / test_<topic>_integration.py instead, so fall
    # back to any test_*_progressive.py, then any test_*.py in the dir.
    module_test_dir = project_root / "data" / "src" / module_name / "tests"
    integration_test_targets = []
    primary_test_file = module_test_dir / f"test_{module_name}_progressive.py"
    if primary_test_file.exists():
        integration_test_targets = [primary_test_file]
    elif module_test_dir.exists():
        matches = sorted(module_test_dir.glob("test_*_progressive.py"))
        if matches:
            integration_test_targets = matches
        else:
            integration_test_targets = sorted(module_test_dir.glob("test_*.py"))

    if not integration_test_targets:
        # No integration tests for this module yet
        if verbose:
            console.print(f"   [dim yellow]No integration tests found: {primary_test_file}[/dim yellow]")
        return {"passed": 0, "failed": 0, "tests": [], "returncode": 0}

    # Run pytest with verbose output
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *[str(f) for f in integration_test_targets],
            "-v",
            "--tb=short",
            "-o",
            "addopts=",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=project_root,
    )

    # Parse pytest output
    tests_run = _parse_pytest_output(result.stdout, result.stderr)

    if not tests_run and result.returncode != 0:
        # pytest itself errored (e.g. a collection-time import failure) rather
        # than legitimately having zero tests, except two non-failure cases:
        # exit 5 (pytest's "no tests collected") and exit 4 with the export
        # gate message (conftest.py's unconditional check trips for early
        # modules mid progressive-build, before later core files exist yet).
        error_msg = (result.stderr or result.stdout).strip()
        is_no_tests_collected = result.returncode == 5
        is_progressive_export_gate = result.returncode == 4 and "TINYTORCH PACKAGE NOT EXPORTED" in error_msg
        if not is_no_tests_collected and not is_progressive_export_gate:
            concise_error = (
                "\n".join(error_msg.split("\n")[:5]) if error_msg else "pytest exited with an error"
            )
            tests_run = [
                {
                    "name": "pytest_collection",
                    "passed": False,
                    "error": concise_error,
                }
            ]

    if verbose:
        for test in tests_run:
            icon = "✅" if test["passed"] else "❌"
            color = "green" if test["passed"] else "red"
            console.print(f"   [{color}]{icon} {test['name']}[/{color}]")
            if not test["passed"] and test.get("error"):
                # Show error on next line with indentation
                error_lines = test["error"].split("\n")
                for error_line in error_lines[:3]:  # Show first 3 lines of error
                    if error_line.strip():
                        console.print(f"      [dim red]{error_line.strip()}[/dim red]")

    passed = sum(1 for t in tests_run if t["passed"])
    failed = sum(1 for t in tests_run if not t["passed"])

    return {"passed": passed, "failed": failed, "tests": tests_run, "returncode": result.returncode}


def _parse_test_output(stdout: str, stderr: str, returncode: int) -> list:
    """
    Parse inline test output to extract individual test results.
    Looks for patterns like:
    - ✅ test_function_name
    - ❌ test_function_name: AssertionError
    """
    tests = []
    lines = stdout.split("\n")

    for line in lines:
        line_stripped = line.strip()
        # Look for test result markers
        if line_stripped.startswith("✅") or line_stripped.startswith("❌"):
            passed = line_stripped.startswith("✅")
            # Extract test name and error
            if ":" in line_stripped:
                parts = line_stripped.split(":", 1)
                name = parts[0][2:].strip()  # Remove emoji
                error = parts[1].strip() if len(parts) > 1 else None
            else:
                name = line_stripped[2:].strip()  # Remove emoji
                error = None

            tests.append({"name": name, "passed": passed, "error": error})

    # If no explicit test markers found, infer from return code
    if not tests:
        if returncode == 0:
            # Tests passed (or no tests)
            if stdout.strip() or stderr.strip():
                tests.append({"name": "module_execution", "passed": True, "error": None})
        else:
            # Tests failed
            # Try to extract error from stderr or stdout
            error_msg = stderr.strip() if stderr.strip() else stdout.strip()
            # A traceback's actual exception type/message is always the last
            # line, not the first -- the lines before it are just call-stack
            # frames. Keep the last few lines, not the first few, so the
            # message survives the truncation.
            error_lines = error_msg.split("\n")
            concise_error = "\n".join(error_lines[-5:]) if error_lines else "Test execution failed"

            tests.append({"name": "module_execution", "passed": False, "error": concise_error})

    return tests


def _parse_pytest_output(stdout: str, stderr: str) -> list:
    """
    Parse pytest verbose output to extract individual test results.
    Looks for patterns like:
    - tests/02_activations/test_progressive_integration.py::TestClass::test_method PASSED
    """
    tests = []
    lines = stdout.split("\n")
    seen_tests = set()  # Avoid duplicates

    for line in lines:
        if "::" in line and ("PASSED" in line or "FAILED" in line):
            passed = "PASSED" in line

            # Extract test path and status
            parts = line.split()
            if len(parts) >= 2:
                test_path = parts[0]

                # Skip if already seen
                if test_path in seen_tests:
                    continue
                seen_tests.add(test_path)

                # Format: file.py::Class::method -> "Class: method"
                path_parts = test_path.split("::")
                if len(path_parts) >= 3:
                    class_name = path_parts[1].replace("Test", "").replace("Module", "Module ")
                    method_name = path_parts[2].replace("test_", "").replace("_", " ").title()
                    display_name = f"{class_name}: {method_name}"
                elif len(path_parts) >= 2:
                    method_name = path_parts[1].replace("test_", "").replace("_", " ").title()
                    display_name = method_name
                else:
                    display_name = test_path

                tests.append(
                    {
                        "name": display_name,
                        "passed": passed,
                        "error": None if passed else _extract_pytest_error(stdout, stderr, test_path),
                    }
                )

    return tests


def _extract_pytest_error(stdout: str, stderr: str, test_path: str) -> str | None:
    """Extract error message for a specific failed test from pytest output."""
    lines = stdout.split("\n")
    for i, line in enumerate(lines):
        if test_path in line and "FAILED" in line:
            # Look ahead for error details (typically in next 5-10 lines)
            for j in range(i + 1, min(i + 15, len(lines))):
                error_line = lines[j].strip()
                if "AssertionError" in error_line or "Error:" in error_line or "assert" in error_line:
                    return error_line

    # Fallback: check stderr
    if stderr:
        stderr_lines = stderr.split("\n")
        for line in stderr_lines:
            if "Error" in line or "assert" in line:
                return line.strip()

    return "Test failed (see output for details)"


def check_notebook_syntax(config, module_name: str) -> dict:
    """Compile each code cell of the student notebook to catch syntax errors
    before export, with a precise cell/line number -- a faster, clearer
    signal than the one runpy would eventually raise while actually running
    the notebook in run_inline_unit_tests.

    Returns ``{'ok': bool, 'error': Optional[str]}``. A missing notebook is
    not an error; some flows have nothing to check yet.
    """
    import json

    short_name = module_name.split("_", 1)[1] if "_" in module_name else module_name
    target_root = "solutions" if os.environ.get(VERIFY_SOLUTION_ENV) == "1" else "modules"
    notebook_path = config.project_root / "data" / target_root / module_name / f"{short_name}.ipynb"
    if not notebook_path.exists():
        return {"ok": True, "error": None}
    try:
        nb = json.loads(notebook_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return {"ok": False, "error": f"Could not read {notebook_path.name}: {e}"}

    for idx, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)
        # Drop IPython magics and shell escapes, which are not valid Python
        # and would otherwise raise a spurious SyntaxError.
        code = "\n".join(ln for ln in source.splitlines() if not ln.lstrip().startswith(("%", "!")))
        if not code.strip():
            continue
        try:
            compile(code, f"{notebook_path.name}[cell {idx}]", "exec")
        except SyntaxError as e:
            return {
                "ok": False,
                "error": (f"SyntaxError in {notebook_path.name} cell {idx} (line {e.lineno}): {e.msg}"),
            }
    return {"ok": True, "error": None}
