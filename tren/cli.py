"""
TrenTorch Engineering CLI (tren).

Lightweight, robust CLI orchestrator for systems engineering workflows:
- `tren convert [module] --format [qmd|ipynb|txt|yaml|all]`
- `tren test [module]`
- `tren info`
"""

import argparse
import json
import os
import sys
from pathlib import Path

from trentorch.export_sanitizer import (
    to_qmd,
    to_ipynb,
    to_sandbox_code,
    to_platform_yaml,
)


def get_project_root() -> Path:
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "pyproject.toml").exists() or (current / "src").exists():
            return current
        current = current.parent
    return Path.cwd()


def handle_convert(args):
    project_root = get_project_root()
    src_dir = project_root / "src"
    
    if args.module == "all":
        module_dirs = sorted([d for d in src_dir.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))])
    else:
        module_dirs = []
        for d in src_dir.iterdir():
            if d.is_dir() and (d.name == args.module or d.name.startswith(f"{args.module}_") or d.name.endswith(f"_{args.module}")):
                module_dirs.append(d)
                break
        if not module_dirs:
            print(f"❌ Module not found: {args.module}")
            return 1

    formats = ["qmd", "ipynb", "txt", "yaml"] if args.format == "all" else [args.format]
    print(f"⚡ TrenTorch: Converting {len(module_dirs)} module(s) to [{', '.join(formats)}]...")

    count = 0
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

            rel_path = target_file.relative_to(project_root) if target_file.is_relative_to(project_root) else target_file
            print(f"  ✓ {mod_name} → {rel_path}")
            count += 1

    print(f"\n✅ Successfully generated {count} target artifact(s) in 'build/'.")
    return 0


def handle_info(args):
    print("🔥 TrenTorch - Machine Learning Systems Engineering Framework")
    print(f"  Project Root: {get_project_root()}")
    print("  Supported Formats: .qmd, .ipynb, .yaml, .txt, .py")
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="tren",
        description="TrenTorch Engineering CLI Orchestrator"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Convert command
    convert_parser = subparsers.add_parser("convert", help="Convert modules to platform formats (.qmd, .ipynb, .yaml, .txt, .py)")
    convert_parser.add_argument("module", nargs="?", default="all", help="Module identifier (e.g. 01, 01_tensor, all)")
    convert_parser.add_argument("--format", choices=["qmd", "ipynb", "txt", "py", "yaml", "all"], default="all", help="Target format")
    convert_parser.add_argument("--out", "-o", type=str, default=None, help="Output folder")
    convert_parser.set_defaults(func=handle_convert)

    # Info command
    info_parser = subparsers.add_parser("info", help="Display TrenTorch environment info")
    info_parser.set_defaults(func=handle_info)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
