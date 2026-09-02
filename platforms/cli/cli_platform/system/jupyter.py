"""
Jupyter command for TrenTorch CLI: starts Jupyter notebook server.
"""

import subprocess
from argparse import ArgumentParser, Namespace

from rich.panel import Panel

from platforms.cli.commands.base import BaseCommand


class JupyterCommand(BaseCommand):
    @property
    def name(self) -> str:
        return "jupyter"

    @property
    def description(self) -> str:
        return "Start Jupyter notebook server"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--notebook", action="store_true", help="Start classic notebook")
        parser.add_argument("--lab", action="store_true", help="Start JupyterLab")
        parser.add_argument("--port", type=int, default=8888, help="Port to run on (default: 8888)")

    def run(self, args: Namespace) -> int:
        console = self.console

        console.print(
            Panel("📓 Jupyter Notebook Server", title="Interactive Development", border_style="bright_green")
        )

        # Determine which Jupyter to start
        if args.lab:
            cmd = ["jupyter", "lab", "--port", str(args.port)]
            console.print(f"🚀 Starting JupyterLab on port {args.port}...")
        else:
            cmd = ["jupyter", "notebook", "--port", str(args.port)]
            console.print(f"🚀 Starting Jupyter Notebook on port {args.port}...")

        console.print("💡 Open your browser to the URL shown above")
        console.print("📁 Navigate to your module's notebook directory")
        console.print("🔄 Press Ctrl+C to stop the server")

        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            console.print("\n🛑 Jupyter server stopped")
        except FileNotFoundError:
            console.print(
                Panel(
                    "[red]❌ Jupyter not found. Install with: pip install jupyter[/red]",
                    title="Error",
                    border_style="red",
                )
            )
            return 1

        return 0
