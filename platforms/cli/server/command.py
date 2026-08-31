"""
Serve command for TrenTorch CLI.
"""

import sys
import webbrowser
from argparse import ArgumentParser, Namespace
from http.server import ThreadingHTTPServer

from rich.panel import Panel
from rich.text import Text

from platforms.cli.commands.base import BaseCommand
from platforms.cli.core.console import get_console
from platforms.cli.core.theme import Theme

from .handler import TrenTorchRequestHandler


class ServeCommand(BaseCommand):
    """Launch the TrenTorch Local Companion Server & Visualizer Web UI."""

    @property
    def name(self) -> str:
        return "serve"

    @property
    def description(self) -> str:
        return "Launch the interactive TrenTorch Visualizer Companion Server"

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Add serve command arguments."""
        parser.add_argument(
            "--port",
            "-p",
            type=int,
            default=8080,
            help="Port to bind the companion server (default: 8080)",
        )
        parser.add_argument(
            "--host",
            "-H",
            type=str,
            default="127.0.0.1",
            help="Host interface to bind (default: 127.0.0.1)",
        )
        parser.add_argument(
            "--no-browser",
            action="store_true",
            help="Do not automatically open the web browser upon startup",
        )

    def run(self, args: Namespace) -> int:
        """Start the companion HTTP and SSE server."""
        console = self.console or get_console()
        port = args.port
        host = args.host
        url = f"http://{host}:{port}"

        # Inject config into handler
        TrenTorchRequestHandler.config = self.config

        server_address = (host, port)
        try:
            httpd = ThreadingHTTPServer(server_address, TrenTorchRequestHandler)
        except OSError as e:
            console.print(f"[bold red]❌ Failed to bind to {host}:{port}: {e}[/bold red]")
            console.print(f"[dim]💡 Try running with a different port: tren serve --port {port + 1}[/dim]")
            return 1

        info_text = Text()
        info_text.append("⚡ Tren⚡️Torch Companion Server Active!\n\n", style="bold green")
        info_text.append("🌐 Visualizer URL: ", style="bold")
        info_text.append(f"{url}\n", style="bold cyan underline")
        info_text.append("📊 Features: Live Autograd DAG, Attention & Conv2D Visualizers, Test Streaming\n", style="dim")
        info_text.append("🛑 Press Ctrl+C to stop the server anytime.", style="yellow")

        console.print()
        console.print(Panel(info_text, title="[bold #38bdf8]Tren⚡️Torch Companion[/bold #38bdf8]", border_style="cyan"))
        console.print()

        if not args.no_browser:
            try:
                webbrowser.open(url)
            except Exception:
                pass

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down companion server...[/yellow]")
        finally:
            httpd.server_close()
            console.print("[dim]Server stopped cleanly.[/dim]")

        return 0
