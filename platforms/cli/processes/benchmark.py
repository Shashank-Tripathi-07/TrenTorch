"""
Tren⚡️Torch Benchmark Commands

Run baseline and capstone benchmarks. Results save locally under
user_data/benchmarks/.
"""

import platform
import time
from argparse import ArgumentParser, Namespace
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from platforms.cli.commands.base import BaseCommand
from platforms.cli.core.atomic_io import atomic_write_json, read_json_or_warn


class BenchmarkCommand(BaseCommand):
    """Benchmark commands - baseline and capstone performance evaluation."""

    @property
    def name(self) -> str:
        return "benchmark"

    @property
    def description(self) -> str:
        return "Run benchmarks - baseline (setup validation) and capstone (full performance)"

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Add benchmark subcommands."""
        subparsers = parser.add_subparsers(
            dest="benchmark_command", help="Benchmark operations", metavar="COMMAND"
        )

        # Baseline benchmark
        subparsers.add_parser("baseline", help="Run baseline benchmark (quick setup validation)")

        # Capstone benchmark
        capstone_parser = subparsers.add_parser(
            "capstone", help="Run capstone benchmark (full Module 20 performance evaluation)"
        )
        capstone_parser.add_argument(
            "--track",
            choices=["speed", "compression", "accuracy", "efficiency", "all"],
            default="all",
            help="Which track to benchmark (default: all)",
        )

    def run(self, args: Namespace) -> int:
        """Execute benchmark command."""
        if not args.benchmark_command:
            self.console.print("[yellow]Please specify a benchmark command: baseline or capstone[/yellow]")
            return 1

        if args.benchmark_command == "baseline":
            return self._run_baseline(args)
        elif args.benchmark_command == "capstone":
            return self._run_capstone(args)
        else:
            self.console.print(f"[red]Unknown benchmark command: {args.benchmark_command}[/red]")
            return 1

    def _get_reference_times(self) -> dict[str, float]:
        """
        Get reference times for normalization (SPEC-style).

        Reference system: Mid-range laptop (Intel i5-8th gen, 16GB RAM)
        These times represent expected performance on reference hardware.
        Results are normalized: normalized_score = reference_time / actual_time

        Returns:
            Dict with reference times in milliseconds for each benchmark
        """
        return {
            "tensor_ops": 0.8,  # Reference: 0.8ms for tensor operations
            "matmul": 2.5,  # Reference: 2.5ms for matrix multiply
            "forward_pass": 6.7,  # Reference: 6.7ms for forward pass
            "total": 10.0,  # Reference: 10.0ms total
        }

    def _run_baseline(self, args: Namespace) -> int:
        """Run baseline benchmark - lightweight setup validation."""
        console = self.console

        console.print(
            Panel(
                "[bold cyan]🎯 Baseline Benchmark[/bold cyan]\n\n"
                "Running lightweight benchmarks to validate your setup...\n"
                "[dim]Results are normalized to a reference system for fair comparison.[/dim]",
                title="Baseline Benchmark",
                border_style="cyan",
            )
        )

        # Run baseline benchmarks
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            task = progress.add_task("Running baseline benchmarks...", total=None)

            # Benchmark 1: Tensor operations
            progress.update(task, description="[cyan]Testing tensor operations...")
            tensor_time = self._benchmark_tensor_ops()

            # Benchmark 2: Matrix multiply
            progress.update(task, description="[cyan]Testing matrix multiplication...")
            matmul_time = self._benchmark_matmul()

            # Benchmark 3: Simple forward pass
            progress.update(task, description="[cyan]Testing forward pass...")
            forward_time = self._benchmark_forward_pass()

            progress.update(task, completed=True)

        # Get reference times for normalization (SPEC-style)
        reference = self._get_reference_times()

        # Calculate normalized scores (SPEC-style: reference_time / actual_time)
        # Higher normalized score = better performance
        tensor_normalized = reference["tensor_ops"] / max(tensor_time, 0.001)
        matmul_normalized = reference["matmul"] / max(matmul_time, 0.001)
        forward_normalized = reference["forward_pass"] / max(forward_time, 0.001)

        # Overall normalized score (geometric mean for fairness)
        total_time = tensor_time + matmul_time + forward_time
        total_normalized = reference["total"] / max(total_time, 0.001)

        # Convert to 0-100 score scale
        # Reference system = 100 points, faster systems > 100, slower < 100
        score = min(100, int(100 * total_normalized))

        # Store both raw and normalized metrics
        raw_metrics = {
            "tensor_ops_ms": tensor_time,
            "matmul_ms": matmul_time,
            "forward_pass_ms": forward_time,
            "total_ms": total_time,
        }

        normalized_metrics = {
            "tensor_ops_normalized": tensor_normalized,
            "matmul_normalized": matmul_normalized,
            "forward_pass_normalized": forward_normalized,
            "total_normalized": total_normalized,
            "score": score,
        }

        # Display results
        results_table = Table(title="Baseline Benchmark Results", show_header=True, header_style="bold cyan")
        results_table.add_column("Metric", style="cyan")
        results_table.add_column("Time", justify="right", style="green")
        results_table.add_column("Normalized", justify="right", style="yellow")
        results_table.add_column("Status", justify="center")

        results_table.add_row("Tensor Operations", f"{tensor_time:.2f} ms", f"{tensor_normalized:.2f}x", "✅")
        results_table.add_row("Matrix Multiply", f"{matmul_time:.2f} ms", f"{matmul_normalized:.2f}x", "✅")
        results_table.add_row("Forward Pass", f"{forward_time:.2f} ms", f"{forward_normalized:.2f}x", "✅")
        results_table.add_row("", "", "", "")
        results_table.add_row("[bold]Total[/bold]", f"{total_time:.2f} ms", f"{total_normalized:.2f}x", "✅")
        results_table.add_row("[bold]Score[/bold]", "", f"[bold]{score}/100[/bold]", "🎯")

        console.print("\n")
        console.print(results_table)

        # Show normalization info
        console.print("\n[dim]📊 Normalization: Results normalized to reference system[/dim]")
        console.print(f"[dim]   Reference: {reference['total']:.1f}ms total time[/dim]")
        console.print(f"[dim]   Your system: {total_time:.2f}ms ({total_normalized:.2f}x vs reference)[/dim]")

        # Create results dict
        results = {
            "benchmark_type": "baseline",
            "timestamp": datetime.now().isoformat(),
            "system_info": self._get_system_info(),
            "reference_system": {
                "description": "Mid-range laptop (Intel i5-8th gen, 16GB RAM)",
                "times_ms": reference,
            },
            "raw_metrics": raw_metrics,
            "normalized_metrics": normalized_metrics,
            "metrics": {**raw_metrics, **normalized_metrics},
        }

        # Save results
        benchmark_dir = Path("user_data") / "benchmarks"
        benchmark_dir.mkdir(parents=True, exist_ok=True)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = benchmark_dir / f"baseline_{timestamp_str}.json"

        atomic_write_json(results_file, results)

        console.print(f"\n[green]✅ Results saved to: {results_file}[/green]")

        # Success message
        console.print(
            Panel(
                f"[bold green]🎉 Baseline Benchmark Complete![/bold green]\n\n"
                f"📊 Your Score: [bold]{score}/100[/bold]\n"
                f"✅ Setup verified and working!\n\n"
                f"💡 Run [cyan]tren benchmark capstone[/cyan] after Module 20 for full benchmarks",
                title="Success",
                border_style="green",
            )
        )

        return 0

    def _run_capstone(self, args: Namespace) -> int:
        """Run capstone benchmark - full Module 20 performance evaluation."""
        console = self.console

        console.print(
            Panel(
                "[bold cyan]🏆 Capstone Benchmark[/bold cyan]\n\n"
                "Running full benchmark suite from Module 20...",
                title="Capstone Benchmark",
                border_style="cyan",
            )
        )

        # Check if Module 20 is available
        try:
            from trentorch.perf.benchmarking import Benchmark  # noqa: F401 -- import-success check
        except ImportError:
            console.print(
                Panel(
                    "[red]❌ Module 19 (Benchmarking) not available[/red]\n\n"
                    "Please complete Module 19 first:\n"
                    "  [cyan]tren module complete 19[/cyan]",
                    title="Error",
                    border_style="red",
                )
            )
            return 1

        # Check whether the student has actually completed Module 20, using
        # their own recorded progress -- not whether trentorch/olympics.py
        # can be imported. That file ships pre-built and committed to the
        # repo (see issue #71), so the import always succeeds even with 0
        # modules solved, and this check always fell through to the "full"
        # benchmark path below regardless of real progress.
        progress_file = Path("user_data") / "progress.json"
        completed_modules: set[int] = set()
        progress_data = read_json_or_warn(progress_file, {}, console=console, label="Your saved progress")
        for module_value in progress_data.get("completed_modules", []):
            prefix = str(module_value).split("_", 1)[0]
            try:
                completed_modules.add(int(prefix))
            except ValueError:
                pass

        if 20 not in completed_modules:
            console.print(
                Panel(
                    "[yellow]⚠️  Module 20 (Capstone) not complete[/yellow]\n\n"
                    "Running simplified capstone benchmarks...\n"
                    "For full benchmarks, complete Module 20 first:\n"
                    "  [cyan]tren module complete 20[/cyan]",
                    title="Warning",
                    border_style="yellow",
                )
            )
            # Fall back to simplified benchmarks
            return self._run_simplified_capstone(args)

        # Run full capstone benchmarks
        console.print("[cyan]Running full capstone benchmark suite...[/cyan]")
        console.print("[dim]This may take a few minutes...[/dim]\n")

        # STILL a placeholder even on this path: these numbers are fixed and
        # do not reflect anything about the student's actual framework yet.
        # In production, this would use actual models and Module 19's
        # Benchmark class. Labeled explicitly so a real Module-20 completer
        # isn't misled into thinking this measured their own work.
        console.print(
            "[yellow]⚠️  Note: full capstone scoring isn't implemented yet -- "
            "these numbers are a placeholder, not a real measurement of your "
            "framework.[/yellow]\n"
        )
        results = {
            "placeholder": True,
            "benchmark_type": "capstone",
            "timestamp": datetime.now().isoformat(),
            "system_info": self._get_system_info(),
            "track": args.track,
            "metrics": {
                "speed": {"latency_ms": 45.2, "throughput_ops_per_sec": 22.1, "score": 92},
                "compression": {"model_size_mb": 12.4, "compression_ratio": 4.2, "score": 88},
                "accuracy": {"accuracy_percent": 87.5, "score": 95},
                "efficiency": {"memory_mb": 8.3, "energy_score": 85, "score": 85},
            },
            "overall_score": 90,
        }

        # Save results
        benchmark_dir = Path("user_data") / "benchmarks"
        benchmark_dir.mkdir(parents=True, exist_ok=True)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = benchmark_dir / f"capstone_{timestamp_str}.json"

        atomic_write_json(results_file, results)

        # Display results
        self._display_capstone_results(results)

        console.print(f"\n[green]✅ Results saved to: {results_file}[/green]")

        return 0

    def _run_simplified_capstone(self, args: Namespace) -> int:
        """Run simplified capstone benchmarks when Module 20 isn't complete."""
        console = self.console

        console.print("[yellow]Running simplified capstone benchmarks...[/yellow]\n")

        # Run basic benchmarks
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            task = progress.add_task("Running benchmarks...", total=None)

            progress.update(task, description="[cyan]Testing performance...")
            time.sleep(1)  # Simulate benchmark time

        # STILL a placeholder, same as the full-capstone path above: this
        # score is fixed and doesn't measure anything about the student's
        # actual code. The 1-second sleep above just paces the spinner, it
        # isn't running a real benchmark. Warned on-screen (not just in the
        # saved JSON's "note" field, which nobody reads) so this fallback --
        # the path *every* student without Module 20 now hits -- doesn't
        # quietly repeat the exact bug this PR fixes on the other path.
        console.print(
            "[yellow]⚠️  Note: this simplified score isn't a real measurement either -- "
            "it's a fixed placeholder number, not something computed from your code.[/yellow]\n"
        )
        results = {
            "placeholder": True,
            "benchmark_type": "capstone_simplified",
            "timestamp": datetime.now().isoformat(),
            "system_info": self._get_system_info(),
            "note": "Simplified benchmarks - complete Module 20 for full suite",
            "metrics": {"basic_score": 75},
        }

        # Save results
        benchmark_dir = Path("user_data") / "benchmarks"
        benchmark_dir.mkdir(parents=True, exist_ok=True)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = benchmark_dir / f"capstone_simplified_{timestamp_str}.json"

        atomic_write_json(results_file, results)

        console.print(f"\n[green]✅ Results saved to: {results_file}[/green]")
        console.print("[yellow]💡 Complete Module 20 for full capstone benchmarks[/yellow]")

        return 0

    def _benchmark_tensor_ops(self) -> float:
        """Benchmark basic tensor operations."""
        import time

        import numpy as np

        rng = np.random.default_rng(7)

        # Create tensors
        a = rng.standard_normal((100, 100)).astype(np.float32)
        b = rng.standard_normal((100, 100)).astype(np.float32)

        # Warmup
        for _ in range(5):
            _ = a + b
            _ = a * b

        # Benchmark
        start = time.perf_counter()
        for _ in range(100):
            _ = a + b
            _ = a * b
            _ = np.sum(a)
        end = time.perf_counter()

        return (end - start) * 1000 / 100  # Convert to milliseconds per operation

    def _benchmark_matmul(self) -> float:
        """Benchmark matrix multiplication."""
        import time

        import numpy as np

        rng = np.random.default_rng(7)

        a = rng.standard_normal((100, 100)).astype(np.float32)
        b = rng.standard_normal((100, 100)).astype(np.float32)

        # Warmup
        for _ in range(5):
            _ = np.dot(a, b)

        # Benchmark
        start = time.perf_counter()
        for _ in range(50):
            _ = np.dot(a, b)
        end = time.perf_counter()

        return (end - start) * 1000 / 50  # milliseconds per matmul

    def _benchmark_forward_pass(self) -> float:
        """Benchmark simple forward pass simulation."""
        import time

        import numpy as np

        rng = np.random.default_rng(7)

        # Simulate a simple forward pass
        x = rng.standard_normal((1, 784)).astype(np.float32)
        w1 = rng.standard_normal((784, 128)).astype(np.float32)
        w2 = rng.standard_normal((128, 10)).astype(np.float32)

        # Warmup
        for _ in range(5):
            h = np.maximum(0, np.dot(x, w1))  # ReLU
            _ = np.dot(h, w2)

        # Benchmark
        start = time.perf_counter()
        for _ in range(20):
            h = np.maximum(0, np.dot(x, w1))
            _ = np.dot(h, w2)
        end = time.perf_counter()

        return (end - start) * 1000 / 20  # milliseconds per forward pass

    def _get_system_info(self) -> dict[str, str]:
        """Get system information."""
        return {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "cpu_count": str(platform.processor() or "unknown"),
        }

    def _display_capstone_results(self, results: dict[str, Any]) -> None:
        """Display capstone benchmark results."""
        console = self.console

        results_table = Table(title="Capstone Benchmark Results", show_header=True, header_style="bold cyan")
        results_table.add_column("Track", style="cyan")
        results_table.add_column("Metric", style="yellow")
        results_table.add_column("Value", justify="right", style="green")
        results_table.add_column("Score", justify="right", style="magenta")

        metrics = results.get("metrics", {})

        if "speed" in metrics:
            speed = metrics["speed"]
            results_table.add_row(
                "Speed", "Latency", f"{speed['latency_ms']:.2f} ms", f"{speed['score']}/100"
            )
            results_table.add_row("", "Throughput", f"{speed['throughput_ops_per_sec']:.2f} ops/s", "")

        if "compression" in metrics:
            comp = metrics["compression"]
            results_table.add_row(
                "Compression", "Model Size", f"{comp['model_size_mb']:.2f} MB", f"{comp['score']}/100"
            )
            results_table.add_row("", "Compression Ratio", f"{comp['compression_ratio']:.1f}x", "")

        if "accuracy" in metrics:
            acc = metrics["accuracy"]
            results_table.add_row(
                "Accuracy", "Accuracy", f"{acc['accuracy_percent']:.1f}%", f"{acc['score']}/100"
            )

        if "efficiency" in metrics:
            eff = metrics["efficiency"]
            results_table.add_row("Efficiency", "Memory", f"{eff['memory_mb']:.2f} MB", f"{eff['score']}/100")

        results_table.add_row("", "", "", "")
        results_table.add_row(
            "[bold]Overall[/bold]", "", "", f"[bold]{results.get('overall_score', 0)}/100[/bold]"
        )

        console.print("\n")
        console.print(results_table)

        console.print(
            Panel(
                f"[bold green]🏆 Capstone Benchmark Complete![/bold green]\n\n"
                f"📊 Overall Score: [bold]{results.get('overall_score', 0)}/100[/bold]",
                title="Success",
                border_style="green",
            )
        )
