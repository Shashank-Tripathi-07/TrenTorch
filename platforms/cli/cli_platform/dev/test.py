"""
Unified Developer Test Command for TrenTorch.

Simple, explicit test types:
    tren dev test                 # Default: unit tests
    tren dev test --unit          # Unit tests only
    tren dev test --integration   # Integration tests
    tren dev test --e2e           # End-to-end tests
    tren dev test --all           # All test types
    tren dev test --release       # Full release validation (destructive)

Think like PyTorch: explicit, predictable, one way to do things.
"""

import json
import os
import subprocess
import sys
import time
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path

from rich.panel import Panel

from platforms.cli.commands.base import BaseCommand


@dataclass
class TestResult:
    """Result of a test phase."""

    name: str
    passed: bool
    duration: float = 0.0
    message: str = ""
    test_count: int = 0


class DevTestCommand(BaseCommand):
    """Unified developer testing command."""

    @property
    def name(self) -> str:
        return "test"

    @property
    def description(self) -> str:
        return "Run tests: --unit, --integration, --e2e, --all, --release"

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Add test command arguments."""
        # Test type flags (can combine multiple)
        parser.add_argument("--unit", "-u", action="store_true", help="Run unit tests (module-level)")
        parser.add_argument("--integration", "-i", action="store_true", help="Run integration tests")
        parser.add_argument("--e2e", "-e", action="store_true", help="Run end-to-end tests")
        parser.add_argument("--cli", action="store_true", help="Run CLI tests")
        parser.add_argument("--all", "-a", action="store_true", help="Run all test types")
        parser.add_argument(
            "--user-journey",
            action="store_true",
            dest="user_journey",
            help="Full user journey validation (runs every milestone, then verifies tren system reset)",
        )
        parser.add_argument(
            "--release",
            action="store_true",
            dest="user_journey",
            help="Alias for --user-journey; full destructive release validation",
        )
        parser.add_argument(
            "--milestone",
            action="store_true",
            help="Run milestone tests (validates milestone scripts execute)",
        )
        parser.add_argument(
            "--inline",
            action="store_true",
            help="Run inline tests from src/ (progressive: test + export each module)",
        )

        # Options
        parser.add_argument(
            "--module", "-m", type=str, metavar="N", help="Test specific module (e.g., -m 06)"
        )
        parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
        parser.add_argument("--ci", action="store_true", help="CI mode: JSON output, strict exit codes")
        parser.add_argument(
            "--no-build", action="store_true", help="Skip package build (assumes already exported)"
        )
        parser.add_argument(
            "--parallel",
            action="store_true",
            help=(
                "Run pytest with -n auto (pytest-xdist) for CLI and E2E tests. "
                "Not applied to --unit or --integration: measured neutral-to-slower "
                "for unit (many small tests, worker spawn overhead dominates) and "
                "surfaced an order-dependent failure under integration that didn't "
                "occur serially. CLI (-43%% wall time) and E2E (-29%%) measured "
                "clean with identical pass/fail results as serial."
            ),
        )

    def run(self, args: Namespace) -> int:
        """Run the test suite."""
        console = self.console
        project_root = self.config.project_root
        start_time = time.time()

        # Determine what tests to run
        run_inline = args.inline or args.all
        run_user_journey = getattr(args, "user_journey", False)
        run_unit = (
            args.unit
            or args.all
            or (
                not any(
                    [
                        args.unit,
                        args.integration,
                        args.e2e,
                        args.cli,
                        args.all,
                        run_user_journey,
                        args.milestone,
                        args.inline,
                    ]
                )
            )
        )
        run_integration = args.integration or args.all
        run_e2e = args.e2e or args.all
        run_cli = args.cli or args.all
        run_milestone = args.milestone or args.all

        # Build test type list for display
        test_types = []
        if run_inline:
            test_types.append("inline")
        if run_unit:
            test_types.append("unit")
        if run_integration:
            test_types.append("integration")
        if run_e2e:
            test_types.append("e2e")
        if run_cli:
            test_types.append("cli")
        if run_milestone:
            test_types.append("milestone")
        if run_user_journey:
            test_types.append("user-journey")

        # Header
        if not args.ci:
            console.print()
            test_desc = ", ".join(test_types) if test_types else "unit"
            module_desc = f" (module {args.module})" if args.module else ""
            console.print(
                Panel(
                    f"[bold cyan]🧪 Running: {test_desc}{module_desc}[/bold cyan]\n\n"
                    f"[bold]Test Types:[/bold]\n"
                    f"  [bold]--inline[/bold]           Inline tests from src/ (progressive)\n"
                    f"  [bold]--unit[/bold] (-u)        Pytest unit tests\n"
                    f"  [bold]--integration[/bold] (-i) Cross-module integration tests\n"
                    f"  [bold]--e2e[/bold] (-e)         End-to-end user journey tests\n"
                    f"  [bold]--cli[/bold]              CLI command tests\n"
                    f"  [bold]--milestone[/bold]        Milestone script tests\n"
                    f"  [bold]--all[/bold] (-a)         All of the above\n"
                    f"  [bold]--user-journey[/bold]     Full user journey (all milestones, then verifies reset)\n\n"
                    f"[bold]Options:[/bold]\n"
                    f"  [bold]-m N[/bold]               Test specific module\n"
                    f"  [bold]--no-build[/bold]         Skip export (assume already built)\n"
                    f"  [bold]--ci[/bold]               JSON output for automation",
                    title="🔥 TrenTorch Developer Tests",
                    border_style="cyan",
                )
            )
            console.print()

        results: list[TestResult] = []

        # Step 1: build the package, unless --no-build (explicit skip),
        # --release (resets and rebuilds each module), or --inline (tests
        # and exports each module progressively instead).
        if not args.no_build and not run_user_journey and not run_inline:
            if not args.ci:
                console.print("[bold]Step 1: Build Package[/bold]")

            # For milestone tests, we need ALL modules exported
            # For other tests, a quick import check is sufficient
            if run_milestone:
                # Milestone tests require full package - always rebuild
                if not args.ci:
                    console.print("  [dim]Milestone tests require full package export...[/dim]")
                result = self._build_package(project_root, args.verbose, args.ci)
                results.append(result)
                if not args.ci:
                    self._print_result(result)
                if not result.passed:
                    return self._finish(results, start_time, args)
            else:
                # Quick import check for other test types
                import_ok = self._check_imports(project_root)
                if import_ok:
                    if not args.ci:
                        console.print("  [green]✓[/green] Package already built")
                else:
                    result = self._build_package(project_root, args.verbose, args.ci)
                    results.append(result)
                    if not args.ci:
                        self._print_result(result)
                    if not result.passed:
                        return self._finish(results, start_time, args)

            if not args.ci:
                console.print()

        # =====================================================================
        # Step 2: Run requested test types
        # =====================================================================

        # Inline tests run first (they build the package progressively)
        if run_inline:
            if not args.ci:
                console.print("[bold]Running: Inline Tests (progressive module build)[/bold]")
            result = self._run_inline_tests(project_root, args.module, args.verbose, args.ci)
            results.append(result)
            if not args.ci:
                self._print_result(result)
                console.print()
            # If inline tests fail, stop here - package isn't fully built
            if not result.passed:
                return self._finish(results, start_time, args)

        if run_unit:
            if not args.ci:
                console.print("[bold]Running: Unit Tests[/bold]")
            result = self._run_unit_tests(project_root, args.module, args.verbose, args.ci)
            results.append(result)
            if not args.ci:
                self._print_result(result)
                console.print()

        if run_cli:
            if not args.ci:
                console.print("[bold]Running: CLI Tests[/bold]")
            result = self._run_cli_tests(project_root, args.verbose, args.ci, args.parallel)
            results.append(result)
            if not args.ci:
                self._print_result(result)
                console.print()

        if run_integration:
            if not args.ci:
                console.print("[bold]Running: Integration Tests[/bold]")
            result = self._run_integration_tests(project_root, args.verbose, args.ci)
            results.append(result)
            if not args.ci:
                self._print_result(result)
                console.print()

        if run_e2e:
            if not args.ci:
                console.print("[bold]Running: E2E Tests[/bold]")
            result = self._run_e2e_tests(project_root, args.verbose, args.ci, args.parallel)
            results.append(result)
            if not args.ci:
                self._print_result(result)
                console.print()

        if run_milestone:
            if not args.ci:
                console.print("[bold]Running: Milestone Tests[/bold]")
            result = self._run_milestone_tests(project_root, args.verbose, args.ci)
            results.append(result)
            if not args.ci:
                self._print_result(result)
                console.print()

        if run_user_journey:
            if not args.ci:
                console.print("[bold]Running: User Journey Validation[/bold]")
                console.print("[yellow]⚠️  This will reset and rebuild ALL modules![/yellow]")
            result = self._run_user_journey(project_root, args)
            results.append(result)
            if not args.ci:
                self._print_result(result)
                console.print()

        return self._finish(results, start_time, args)

    def _print_result(self, result: TestResult) -> None:
        """Print a single test result."""
        if result.passed:
            count = f" ({result.test_count} tests)" if result.test_count else ""
            self.console.print(f"  [green]✓[/green] {result.name}{count} [dim]({result.duration:.1f}s)[/dim]")
        else:
            self.console.print(f"  [red]✗[/red] {result.name} [dim]({result.duration:.1f}s)[/dim]")
            if result.message:
                self.console.print(f"    [dim red]{result.message}[/dim red]")

    def _check_imports(self, project_root: Path) -> bool:
        """Quick check if package is already built.

        trentorch/ lives at data/trentorch/, not the repo root, and CI
        never runs an editable `pip install -e .` (see bin/tren and
        conftest.py's own data/ sys.path entries for why that's normally
        not needed). A bare `-c "from trentorch import ..."` subprocess
        has no way to find it without that install, so it must add
        data/ to sys.path itself first.
        """
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import sys; sys.path.insert(0, 'data'); "
                    "from trentorch import Tensor; assert Tensor is not None",
                ],
                cwd=project_root,
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _build_package(self, project_root: Path, verbose: bool, ci_mode: bool = False) -> TestResult:
        """Build package by exporting all modules from src/.

        This runs 'tren dev export --all' which:
        1. Converts data/src/*.py → data/modules/*.ipynb (stub) + data/solutions/*.ipynb (jupytext)
        2. Runs nbdev_export from data/solutions/ to copy working code to trentorch/core/

        This ensures the full trentorch package is available for testing.
        Note: This does NOT run inline tests - use --inline for that.
        """
        start = time.time()

        if ci_mode:
            print(f"\n{'=' * 60}")
            print("  BUILD PACKAGE")
            print("  Command: tren dev export --all")
            print(f"{'=' * 60}")

        try:
            # Use 'dev export --all' to build the package from src/
            # This creates notebooks and exports to trentorch/core/
            cmd = [sys.executable, str(project_root / "bin" / "tren"), "dev", "export", "--all"]

            if ci_mode:
                # Stream output in CI mode
                process = subprocess.Popen(
                    cmd,
                    cwd=project_root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                )

                for line in process.stdout:
                    line = line.rstrip()
                    # Show key progress lines
                    if any(x in line for x in ["Converting", "Exported", "✅", "❌", "Module"]):
                        print(f"  {line}")

                process.wait(timeout=600)
                returncode = process.returncode
                stderr = ""
            else:
                result = subprocess.run(
                    cmd,
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=600,  # 10 minutes for full build
                )
                returncode = result.returncode
                stderr = result.stderr if hasattr(result, "stderr") else ""

            if ci_mode:
                print(f"{'=' * 60}")
                if returncode == 0:
                    print("  RESULT: BUILD SUCCESS")
                else:
                    print("  RESULT: BUILD FAILED")
                print(f"{'=' * 60}\n")

            if returncode == 0:
                return TestResult(name="Build package", passed=True, duration=time.time() - start)
            else:
                return TestResult(
                    name="Build package",
                    passed=False,
                    duration=time.time() - start,
                    message=stderr[:200] if stderr else "Build failed",
                )
        except subprocess.TimeoutExpired:
            return TestResult(
                name="Build package",
                passed=False,
                duration=time.time() - start,
                message="Timed out after 10 minutes",
            )
        except Exception as e:
            return TestResult(
                name="Build package", passed=False, duration=time.time() - start, message=str(e)[:100]
            )

    def _run_pytest(
        self,
        project_root: Path,
        test_path: str,
        name: str,
        verbose: bool,
        timeout: int = 300,
        extra_args: list[str] = None,
        ci_mode: bool = False,
    ) -> TestResult:
        """Run pytest on a path and return result."""
        import os
        import re

        start = time.time()
        full_path = project_root / test_path

        if not full_path.exists():
            return TestResult(name=name, passed=True, duration=0, message="No tests found")

        # Set up environment with project root in PYTHONPATH
        # This allows tests to import from trentorch.core.*
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH", "")
        if pythonpath:
            env["PYTHONPATH"] = f"{project_root}{os.pathsep}{pythonpath}"
        else:
            env["PYTHONPATH"] = str(project_root)

        try:
            # In CI mode, use verbose output for better visibility
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                str(full_path),
                "-v",  # Always verbose in CI for visibility
                "--tb=short",
                "--no-cov",
            ]
            if extra_args:
                cmd.extend(extra_args)

            if ci_mode:
                # Print header for CI visibility
                print(f"\n{'=' * 60}")
                print(f"  {name.upper()}")
                print(f"  Path: {test_path}")
                print(f"{'=' * 60}")

                # Stream output in CI mode
                process = subprocess.Popen(
                    cmd,
                    cwd=project_root,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                )

                output_lines = []
                test_count = 0
                passed_count = 0
                failed_count = 0

                error_count = 0
                for line in process.stdout:
                    line = line.rstrip()
                    output_lines.append(line)

                    # Print test results as they happen
                    if "::" in line and (
                        " PASSED" in line or " FAILED" in line or " ERROR" in line or " SKIPPED" in line
                    ):
                        # Extract test name and status
                        if " PASSED" in line:
                            passed_count += 1
                            status = "✓"
                        elif " FAILED" in line:
                            failed_count += 1
                            status = "✗"
                        elif " ERROR" in line:
                            failed_count += 1
                            status = "!"
                        else:
                            status = "-"
                        # Extract just the test name. "::" is guaranteed
                        # present here (the outer if already checked), but
                        # the part after it being nothing but whitespace
                        # (so .split() returns []) isn't -- that used to
                        # raise IndexError here, caught by this method's
                        # own outer except Exception, which silently
                        # truncated live CI test-streaming mid-run instead
                        # of just skipping this one unparseable line.
                        name_parts = line.split("::")[-1].split()
                        test_name = name_parts[0] if name_parts else line
                        print(f"  {status} {test_name}")
                        test_count += 1
                    elif line.startswith("ERROR "):
                        # Collection errors (no :: in the line)
                        error_count += 1
                        print(f"  ERROR {line[6:]}")
                    elif line.startswith("FAILED"):
                        print(f"  {line}")
                    elif "ImportError" in line or "ModuleNotFoundError" in line or "No module named" in line:
                        # Show import errors for debugging
                        print(f"  >>> {line}")
                    elif line.startswith("E ") or line.startswith("    "):
                        # Show traceback lines (E prefix or indented)
                        if (
                            "import" in line.lower()
                            or "module" in line.lower()
                            or "not found" in line.lower()
                        ):
                            print(f"  >>> {line}")

                process.wait(timeout=timeout)

                # Print summary
                print(f"{'=' * 60}")
                if process.returncode == 0:
                    print(f"  RESULT: {passed_count} tests PASSED")
                else:
                    parts = []
                    if error_count > 0:
                        parts.append(f"{error_count} errors")
                    if failed_count > 0:
                        parts.append(f"{failed_count} failed")
                    parts.append(f"{passed_count} passed")
                    print(f"  RESULT: {', '.join(parts)}")
                print(f"{'=' * 60}\n")

                if process.returncode == 0:
                    return TestResult(
                        name=name,
                        passed=True,
                        duration=time.time() - start,
                        test_count=test_count,
                        message=f"{passed_count} passed",
                    )
                else:
                    # Include errors in the failure message
                    total_failures = failed_count + error_count
                    return TestResult(
                        name=name,
                        passed=False,
                        duration=time.time() - start,
                        test_count=test_count,
                        message=f"{total_failures} failed/errors, {passed_count} passed",
                    )
            else:
                # Non-CI mode: capture output
                result = subprocess.run(
                    cmd,
                    cwd=project_root,
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=timeout,
                )

                # Count tests from output
                test_count = 0
                summary = ""
                for line in result.stdout.split("\n"):
                    if "passed" in line:
                        summary = line.strip()
                        match = re.search(r"(\d+) passed", line)
                        if match:
                            test_count = int(match.group(1))
                        break

                if result.returncode == 0:
                    return TestResult(
                        name=name,
                        passed=True,
                        duration=time.time() - start,
                        test_count=test_count,
                        message=summary,
                    )
                else:
                    # Extract failure info
                    for line in result.stdout.split("\n"):
                        if "failed" in line.lower() or "error" in line.lower():
                            summary = line.strip()[:80]
                            break
                    return TestResult(
                        name=name,
                        passed=False,
                        duration=time.time() - start,
                        message=summary or "Tests failed",
                    )
        except subprocess.TimeoutExpired:
            return TestResult(
                name=name,
                passed=False,
                duration=time.time() - start,
                message=f"Timed out after {timeout // 60} minutes",
            )
        except Exception as e:
            return TestResult(name=name, passed=False, duration=time.time() - start, message=str(e)[:100])

    def _run_inline_tests(
        self, project_root: Path, module: str | None, verbose: bool, ci_mode: bool
    ) -> TestResult:
        """Run inline tests from src/ files progressively.

        This simulates the student journey:
        1. For each module in order (01 → 20):
           a. Run inline tests from src/XX_module/XX_module.py
           b. If tests pass, export to trentorch/core/
           c. If tests fail, stop and report

        Calls dev export / module complete in-process instead of spawning
        two `sys.executable bin/tren ...` subprocesses per module (40
        fresh-interpreter-plus-CLI-import spawns for a 20-module run).
        Measured locally, same machine, same conditions: 189s -> 123s for
        5 modules (~35% faster), with identical pass/fail results
        (including module 09's naive-Conv2d path) verified before and
        after via the full local test suite.
        """
        import io

        from rich.console import Console as RichConsole

        from platforms.cli.cli_platform.dev.export import DevExportCommand
        from platforms.cli.core.modules import get_module_mapping
        from platforms.cli.processes.module_workflow import ModuleWorkflowCommand

        start = time.time()
        console = self.console
        module_mapping = get_module_mapping()

        # Determine which modules to test
        if module:
            module_num = module.zfill(2)
            if module_num not in module_mapping:
                return TestResult(
                    name=f"Inline tests (module {module_num})",
                    passed=False,
                    duration=0,
                    message=f"Module {module_num} not found",
                )
            # Test up to and including the specified module
            target_int = int(module_num)
            module_nums = [
                m for m in sorted(module_mapping.keys(), key=lambda x: int(x)) if int(m) <= target_int
            ]
        else:
            module_nums = sorted(module_mapping.keys(), key=lambda x: int(x))

        passed_modules = 0
        failed_module = None

        # Print header for CI visibility
        if ci_mode:
            print(f"\n{'=' * 60}")
            print(f"  INLINE TESTS: Testing {len(module_nums)} modules progressively")
            print(f"{'=' * 60}")

        # dev export and module complete both print verbose Rich panels
        # unconditionally. The subprocess version relied on
        # capture_output=True to silently swallow that unless a module
        # failed; matching that here means giving each command a Console
        # that writes to an in-memory buffer instead of real stdout, and
        # only dumping the buffer's tail if that module actually fails.
        quiet_buffer = io.StringIO()
        quiet_console = RichConsole(file=quiet_buffer, no_color=True, width=100)

        export_cmd = DevExportCommand(self.config)
        export_cmd.console = quiet_console
        workflow_cmd = ModuleWorkflowCommand(self.config)
        workflow_cmd.console = quiet_console

        # Matches the env var the subprocess version set per-subprocess:
        # this whole loop runs in maintainer verify-solution mode.
        prev_verify = os.environ.get("TREN_DEV_VERIFY_SOLUTION")
        os.environ["TREN_DEV_VERIFY_SOLUTION"] = "1"

        try:
            for module_num in module_nums:
                module_name = module_mapping[module_num]

                # Always show module progress (important for CI visibility)
                if ci_mode:
                    print(
                        f"  [{passed_modules + 1}/{len(module_nums)}] Module {module_num}: {module_name}...",
                        end=" ",
                        flush=True,
                    )
                else:
                    console.print(f"  [dim]Module {module_num} ({module_name})...[/dim]")

                quiet_buffer.seek(0)
                quiet_buffer.truncate(0)

                # Step 1: Export notebook from src/ to data/modules/ + data/solutions/
                _profile_export_start = time.time()
                try:
                    export_rc = export_cmd._export_specific_modules([module_name], quiet_console)
                except Exception as e:
                    failed_module = f"{module_num}:export_exception:{str(e)[:50]}"
                    if ci_mode:
                        print(f"✗ EXPORT ERROR: {str(e)[:200]}")
                    else:
                        console.print(f"  [red]✗ EXPORT ERROR: {str(e)[:200]}[/red]")
                    break
                if ci_mode and os.environ.get("TREN_PROFILE") == "1":
                    print(
                        f"\n      [TREN_PROFILE] {module_num} export in-process: {time.time() - _profile_export_start:.2f}s"
                    )
                if export_rc != 0:
                    failed_module = f"{module_num}:export"
                    # The buffered output is the only place the real reason
                    # for the failure lives (quiet_console wrote it there
                    # instead of the real console). Show it either way, not
                    # only under --ci -- a local, non-CI run that hits this
                    # used to get nothing but "Failed at NN:export" with no
                    # way to self-diagnose (issue #158).
                    buf = quiet_buffer.getvalue()
                    if ci_mode:
                        print("✗ EXPORT FAILED")
                        if buf:
                            print("      Output (last 500 chars):")
                            for line in buf[-500:].split("\n")[-10:]:
                                if line.strip():
                                    print(f"        {line}")
                    else:
                        console.print("  [red]✗ EXPORT FAILED[/red]")
                        if buf:
                            console.print("  [dim]Output (last 500 chars):[/dim]")
                            for line in buf[-500:].split("\n")[-10:]:
                                if line.strip():
                                    console.print(f"    [dim]{line}[/dim]")
                    break

                quiet_buffer.seek(0)
                quiet_buffer.truncate(0)

                # Step 2: Run module complete (tests + copy to trentorch/core/).
                # --skip-export: the export call just above already ran
                # nbdev's export to the package -- see the commit that
                # introduced --skip-export here for the full rationale.
                _profile_complete_start = time.time()
                _profile_on = os.environ.get("TREN_PROFILE") == "1"
                try:
                    rc = workflow_cmd.complete_module(module_num, skip_tests=False, skip_export=True)
                except Exception as e:
                    failed_module = f"{module_num}:{str(e)[:30]}"
                    if ci_mode:
                        print(f"✗ ERROR: {str(e)[:50]}")
                    break

                if ci_mode and _profile_on:
                    print(
                        f"      [TREN_PROFILE] {module_num} complete in-process: {time.time() - _profile_complete_start:.2f}s"
                    )

                if rc == 0:
                    passed_modules += 1
                    if ci_mode:
                        print("✓ PASSED")
                    else:
                        console.print("    [green]✓[/green] Passed")
                else:
                    failed_module = f"{module_num}:{module_name}"
                    # Same gap as the export-failure branch above: the
                    # buffered output is the only place the real test
                    # failure lives (quiet_console wrote it there instead
                    # of the real console). Show it either way, not only
                    # under --ci -- a local, non-CI run used to get nothing
                    # but "Failed" with no way to self-diagnose.
                    buf = quiet_buffer.getvalue()
                    if ci_mode:
                        print("✗ FAILED")
                        if buf:
                            print("      Error output:")
                            for line in buf.split("\n")[-15:]:
                                if line.strip():
                                    print(f"        {line}")
                    else:
                        console.print("    [red]✗[/red] Failed")
                        if buf:
                            console.print("  [dim]Error output:[/dim]")
                            for line in buf.split("\n")[-15:]:
                                if line.strip():
                                    console.print(f"    [dim]{line}[/dim]")
                    break
        finally:
            if prev_verify is None:
                os.environ.pop("TREN_DEV_VERIFY_SOLUTION", None)
            else:
                os.environ["TREN_DEV_VERIFY_SOLUTION"] = prev_verify

        # Print summary for CI
        if ci_mode:
            print(f"{'=' * 60}")
            if failed_module:
                print(f"  RESULT: FAILED at {failed_module}")
            else:
                print(f"  RESULT: ALL {passed_modules} MODULES PASSED")
            print(f"{'=' * 60}\n")

        duration = time.time() - start

        if failed_module:
            return TestResult(
                name="Inline tests",
                passed=False,
                duration=duration,
                test_count=passed_modules,
                message=f"Failed at {failed_module}",
            )
        else:
            return TestResult(
                name="Inline tests",
                passed=True,
                duration=duration,
                test_count=passed_modules,
                message=f"{passed_modules}/{len(module_nums)} modules passed",
            )

    def _run_unit_tests(
        self, project_root: Path, module: str | None, verbose: bool, ci_mode: bool = False
    ) -> TestResult:
        """Run unit tests.

        Per-module unit tests live at data/src/<NN_name>/tests/, moved
        there from tests/<NN_name>/ in the vertical-slice restructuring
        so one module's code and its tests sit together. This used to
        target the old tests/ location, which silently collected zero
        module unit tests after that move (pytest doesn't error on an
        empty match under a valid parent directory, it just reports
        nothing to run) -- CI's "Unit Tests" stage kept passing while
        actually running only the handful of tests still loose at the
        tests/ root, not the ~570 real per-module tests.
        """
        if module:
            module_num = module.zfill(2)
            test_dirs = list((project_root / "data" / "src").glob(f"{module_num}_*"))
            if not test_dirs:
                return TestResult(
                    name=f"Unit tests (module {module_num})",
                    passed=True,
                    duration=0,
                    message="No tests found for this module",
                )
            test_path = str(test_dirs[0].relative_to(project_root))
            name = f"Unit tests (module {module_num})"
        else:
            test_path = "data/src"
            name = "Unit tests"

        return self._run_pytest(
            project_root, test_path, name, verbose, extra_args=["-m", "not slow"], ci_mode=ci_mode
        )

    def _run_cli_tests(
        self, project_root: Path, verbose: bool, ci_mode: bool = False, parallel: bool = False
    ) -> TestResult:
        """Run CLI tests.

        Moved to platforms/cli/tests/ in the vertical-slice restructuring
        (from tests/cli/). Same silent-empty-collection gap as
        _run_unit_tests above: this reported "0 tests, passed" instead of
        actually running the CLI suite until fixed.
        """
        extra_args = ["-n", "auto"] if parallel else None
        return self._run_pytest(
            project_root,
            "platforms/cli/tests",
            "CLI tests",
            verbose,
            timeout=120,
            extra_args=extra_args,
            ci_mode=ci_mode,
        )

    def _run_integration_tests(self, project_root: Path, verbose: bool, ci_mode: bool = False) -> TestResult:
        """Run integration tests.

        Not parallelized: a local -n auto run surfaced an order-dependent
        failure (test_deep_network_gradient_chain) that didn't occur
        serially, while unrelated re-runs of the same file also showed
        pre-existing seed-sensitive flakiness independent of parallelism.
        Needs the flaky tests fixed and reproducibility confirmed before
        this is safe to parallelize.
        """
        return self._run_pytest(
            project_root, "tests/integration", "Integration tests", verbose, ci_mode=ci_mode
        )

    def _run_e2e_tests(
        self, project_root: Path, verbose: bool, ci_mode: bool = False, parallel: bool = False
    ) -> TestResult:
        """Run E2E tests."""
        extra_args = ["-m", "quick"]
        if parallel:
            extra_args += ["-n", "auto"]
        return self._run_pytest(
            project_root,
            "tests/e2e",
            "E2E tests",
            verbose,
            timeout=600,
            extra_args=extra_args,
            ci_mode=ci_mode,
        )

    def _run_milestone_tests(self, project_root: Path, verbose: bool, ci_mode: bool = False) -> TestResult:
        """Run milestone tests from data/milestones/tests/.

        These are pytest-based tests that verify milestone scripts execute correctly.
        Requires the package to be fully exported with all modules completed.

        Moved to data/milestones/tests/ in the vertical-slice restructuring
        (from tests/milestones/).
        """
        return self._run_pytest(
            project_root,
            "data/milestones/tests",
            "Milestone tests",
            verbose,
            timeout=900,
            extra_args=["-m", "slow or not slow"],
            ci_mode=ci_mode,  # 15 min, run all including slow tests
        )

    def _run_user_journey(self, project_root: Path, args: Namespace) -> TestResult:
        """Verify every milestone runs correctly, then verify reset actually works.

        Previously: destructively reset, then rebuilt all 20 modules from
        scratch via `module start`/`module complete`, identical work to
        what Stage 1 already verifies minutes earlier in the same pipeline
        run, running milestones interleaved at their unlock checkpoints.

        Restructured: milestones now run first, against the already-built
        package (the same artifact Stages 2-5 already reuse from Stage 1,
        instead of a second full rebuild). Reset is verified separately and
        cheaply afterward, by actually calling `tren system reset --force
        --ci` (the real command a user would run, previously this function
        just hand-rolled the same file-clearing logic inline without
        touching the real command at all) and checking it actually cleared
        the right state, instead of a rebuild-and-reverify.

        This drops the milestone-unlock-checkpoint interleaving (each
        milestone previously only ran against its minimum required
        modules). Checkpoints span modules 03-19, nearly the entire
        progressive build, so that interleaving was never actually saving
        rebuild work, it was only buying a narrower guarantee (a milestone
        doesn't accidentally depend on a not-yet-unlocked module) that's a
        much rarer regression class than "does a milestone work at all",
        which is what actually matters and is still fully covered here.
        """
        from platforms.cli.processes.milestone import MILESTONE_SCRIPTS

        start = time.time()
        console = self.console
        ci_mode = args.ci

        failed_milestones = []
        passed_milestones = 0

        # =====================================================================
        # Step 1: Run every milestone against the already-built package
        # =====================================================================
        if ci_mode:
            print(f"\n{'=' * 60}")
            print(f"  USER JOURNEY: {len(MILESTONE_SCRIPTS)} milestones against the built package")
            print(f"{'=' * 60}")
        else:
            console.print("  [dim]Running all milestones against the built package...[/dim]")

        for milestone_id in sorted(MILESTONE_SCRIPTS.keys()):
            milestone_name = MILESTONE_SCRIPTS[milestone_id].get("name", milestone_id)
            milestone_start = time.time()
            if ci_mode:
                print(f"  → tren milestone run {milestone_id} ({milestone_name})", end=" ", flush=True)

            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        str(project_root / "bin" / "tren"),
                        "milestone",
                        "run",
                        milestone_id,
                        "--skip-checks",
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=project_root,
                    # 15 min: milestone 04 alone takes ~7.5 min on a typical CI
                    # runner (real training, not a hang) -- 300s failed every run.
                    timeout=900,
                )
                milestone_duration = time.time() - milestone_start
                if result.returncode == 0:
                    passed_milestones += 1
                    if ci_mode:
                        print(f"✓ ({milestone_duration:.1f}s)")
                else:
                    failed_milestones.append(milestone_id)
                    if ci_mode:
                        print(f"✗ FAILED ({milestone_duration:.1f}s)")
                        for line in result.stdout.split("\n")[-8:]:
                            if line.strip():
                                print(f"      {line}")
            except subprocess.TimeoutExpired:
                failed_milestones.append(milestone_id)
                if ci_mode:
                    print("✗ TIMEOUT (>900s)")
            except Exception as e:
                failed_milestones.append(milestone_id)
                if ci_mode:
                    print(f"✗ ERROR: {str(e)[:30]}")

        # =====================================================================
        # Step 2: Verify the real reset command actually works
        # =====================================================================
        if ci_mode:
            print(f"\n{'=' * 60}")
            print("  USER JOURNEY: Verify tren system reset")
            print(f"{'=' * 60}")
        else:
            console.print("  [dim]Verifying tren system reset...[/dim]")

        reset_ok = False
        reset_detail = ""
        try:
            reset_result = subprocess.run(
                [sys.executable, str(project_root / "bin" / "tren"), "system", "reset", "--force", "--ci"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=project_root,
                timeout=120,
            )

            modules_dir = project_root / "data" / "modules"
            core_dir = project_root / "data" / "trentorch" / "core"
            progress_file = project_root / "user_data" / "progress.json"

            modules_cleared = True
            if modules_dir.exists():
                modules_cleared = not any(
                    item.is_dir() and item.name[:1].isdigit() for item in modules_dir.iterdir()
                )

            core_cleared = True
            if core_dir.exists():
                core_cleared = not any(
                    f.name not in ("__init__.py", "platform.py") for f in core_dir.glob("*.py")
                )

            progress_cleared = not progress_file.exists()

            reset_ok = reset_result.returncode == 0 and modules_cleared and core_cleared and progress_cleared
            if ci_mode:
                if reset_ok:
                    print("  ✓ Reset verified: data/modules/, data/trentorch/core/, and progress all cleared")
                else:
                    print("  ✗ Reset verification FAILED")
                    print(f"      exit code: {reset_result.returncode}")
                    print(
                        f"      modules cleared: {modules_cleared}, core cleared: {core_cleared}, progress cleared: {progress_cleared}"
                    )
                    reset_detail = (
                        f"exit={reset_result.returncode} modules={modules_cleared} "
                        f"core={core_cleared} progress={progress_cleared}"
                    )
        except subprocess.TimeoutExpired:
            if ci_mode:
                print("  ✗ Reset TIMEOUT (>120s)")
            reset_detail = "timeout"
        except Exception as e:
            if ci_mode:
                print(f"  ✗ Reset ERROR: {str(e)[:50]}")
            reset_detail = str(e)[:50]

        # =====================================================================
        # Summary
        # =====================================================================
        total_time = time.time() - start
        all_passed = len(failed_milestones) == 0 and reset_ok

        if ci_mode:
            print(f"\n{'=' * 60}")
            if all_passed:
                print(f"  RESULT: ALL PASSED ({passed_milestones} milestones, reset verified)")
            else:
                print("  RESULT: FAILED")
                if failed_milestones:
                    print(f"    Failed milestones: {', '.join(failed_milestones)}")
                if not reset_ok:
                    print(f"    Reset verification failed: {reset_detail}")
            print(f"{'=' * 60}\n")

        if all_passed:
            return TestResult(
                name="User journey",
                passed=True,
                duration=total_time,
                test_count=passed_milestones,
                message=f"{passed_milestones} milestones, reset verified",
            )
        else:
            failures = []
            if failed_milestones:
                failures.append(f"milestones: {', '.join(failed_milestones)}")
            if not reset_ok:
                failures.append(f"reset verification failed: {reset_detail}")
            return TestResult(
                name="User journey", passed=False, duration=total_time, message="; ".join(failures)[:100]
            )

    def _finish(self, results: list[TestResult], start_time: float, args: Namespace) -> int:
        """Show final summary and return exit code."""
        console = self.console
        total_time = time.time() - start_time

        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)
        total_tests = sum(r.test_count for r in results)
        all_passed = failed == 0

        if args.ci:
            # JSON output for CI
            output = {
                "success": all_passed,
                "duration_seconds": round(total_time, 2),
                "passed": passed,
                "failed": failed,
                "total_tests": total_tests,
                "results": [
                    {
                        "name": r.name,
                        "passed": r.passed,
                        "duration": round(r.duration, 2),
                        "test_count": r.test_count,
                        "message": r.message,
                    }
                    for r in results
                ],
            }
            print(json.dumps(output, indent=2))
        else:
            # Rich summary
            if all_passed:
                test_info = f"{total_tests} tests" if total_tests else f"{passed} phases"
                console.print(
                    Panel(
                        f"[bold green]✅ ALL TESTS PASSED[/bold green]\n\n"
                        f"[green]{test_info}[/green] completed in [dim]{total_time:.1f}s[/dim]",
                        title="🎉 Success",
                        border_style="green",
                    )
                )
            else:
                failed_names = [r.name for r in results if not r.passed]
                console.print(
                    Panel(
                        f"[bold red]❌ TESTS FAILED[/bold red]\n\n"
                        f"[green]{passed}[/green] passed  [red]{failed}[/red] failed  [dim]{total_time:.1f}s[/dim]\n\n"
                        f"Failed: {', '.join(failed_names)}",
                        title="⚠️ Test Failures",
                        border_style="red",
                    )
                )

        return 0 if all_passed else 1
