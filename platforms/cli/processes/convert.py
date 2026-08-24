"""
Multi-Platform Conversion Command for TrenTorch CLI (tren).

Converts source modules (.py) to:
- .qmd (Quarto literate programming & engineering docs)
- .ipynb (Jupyter / Kaggle / Colab)
- .txt / .py (Sanitized scripts for LeetCode / DeepML / LeetGPU sandboxes)
- .yaml (Structured schema for autograders / judges)
"""

import json
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import List

from platforms.cli.commands.base import BaseCommand
from trentorch.export_sanitizer import (
    to_qmd,
    to_ipynb,
    to_sandbox_code,
    to_platform_yaml,
)


class ConvertCommand(BaseCommand):
    """Command to convert TrenTorch modules into various platform formats."""

    category: str = "workflow"

    @property
    def name(self) -> str:
        return "convert"

    @property
    def description(self) -> str:
        return "Convert TrenTorch modules to .qmd, .ipynb, .yaml, or sanitized .txt/.py"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "module",
            nargs="?",
            default="all",
            help="Module name or number (e.g. 01, 01_tensor, or 'all')",
        )
        parser.add_argument(
            "--format",
            choices=["qmd", "ipynb", "txt", "py", "yaml", "all"],
            default="all",
            help="Target export format (default: all)",
        )
        parser.add_argument(
            "--out",
            "-o",
            type=str,
            default=None,
            help="Output directory (default: build/<format>/)",
        )

    def run(self, args: Namespace) -> int:
        project_root = self.config.project_root
        src_dir = project_root / "data" / "src"
        console = self.console

        # Find target module directories
        if args.module == "all":
            module_dirs = sorted([d for d in src_dir.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))])
        else:
            module_dirs = []
            for d in src_dir.iterdir():
                if d.is_dir() and (d.name == args.module or d.name.startswith(f"{args.module}_") or d.name.endswith(f"_{args.module}")):
                    module_dirs.append(d)
                    break
            if not module_dirs:
                console.print(f"[red]❌ Module not found: {args.module}[/red]")
                return 1

        formats = ["qmd", "ipynb", "txt", "yaml"] if args.format == "all" else [args.format]
        console.print(f"[bold cyan]⚡ Converting {len(module_dirs)} module(s) to {', '.join(formats)}...[/bold cyan]")

        success_count = 0
        for mod_dir in module_dirs:
            src_file = mod_dir / f"{mod_dir.name}.py"
            if not src_file.exists():
                continue

            content = src_file.read_text(encoding="utf-8")
            mod_name = mod_dir.name

            for fmt in formats:
                out_dir = Path(args.out) if args.out else project_root / "build" / fmt
                out_dir.mkdir(parents=True, exist_ok=True)

                if fmt == "qmd":
                    target_file = out_dir / f"{mod_name}.qmd"
                    target_file.write_text(to_qmd(content), encoding="utf-8")
                elif fmt == "ipynb":
                    target_file = out_dir / f"{mod_name}.ipynb"
                    target_file.write_text(json.dumps(to_ipynb(content), indent=2), encoding="utf-8")
                elif fmt in {"txt", "py"}:
                    target_file = out_dir / f"{mod_name}.{fmt}"
                    target_file.write_text(to_sandbox_code(content), encoding="utf-8")
                elif fmt == "yaml":
                    target_file = out_dir / f"{mod_name}.yaml"
                    target_file.write_text(to_platform_yaml(content, module_name=mod_name), encoding="utf-8")

                console.print(f"  [green]✓[/green] {mod_name} → [dim]{target_file.relative_to(project_root)}[/dim]")
                success_count += 1

        console.print(f"\n[bold green]✅ Successfully generated {success_count} artifact(s)![/bold green]")
        return 0
