"""
Serve command for TrenTorch CLI.
"""

import ipaddress
import webbrowser
from argparse import ArgumentParser, Namespace
from http.server import ThreadingHTTPServer

from rich.panel import Panel
from rich.text import Text

from platforms.cli.commands.base import BaseCommand
from platforms.cli.core.console import get_console

from .handler import TrenTorchRequestHandler

LOOPBACK_BINDS = {"127.0.0.1", "::1", "localhost"}


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
            help="Host interface to bind (default: 127.0.0.1). Non-loopback exposes the code-running API to your network.",
        )
        parser.add_argument(
            "--no-browser",
            action="store_true",
            help="Do not automatically open the web browser upon startup",
        )

    @staticmethod
    def _is_loopback(host: str) -> bool:
        if host in LOOPBACK_BINDS:
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    def run(self, args: Namespace) -> int:
        """Start the companion HTTP and SSE server."""
        console = self.console or get_console()
        port = args.port
        host = args.host
        is_loopback = self._is_loopback(host)

        # The browser cannot open 0.0.0.0 / ::, so point it at localhost.
        browser_host = "localhost" if host in {"0.0.0.0", "::", ""} else host
        url = f"http://{browser_host}:{port}"

        # Inject config into handler.
        TrenTorchRequestHandler.config = self.config
        # When the operator deliberately binds a non-loopback address, trust
        # that hostname for API calls too (otherwise every call is rejected).
        TrenTorchRequestHandler.allowed_hosts = set() if is_loopback else {host, browser_host}

        server_address = (host, port)
        try:
            httpd = ThreadingHTTPServer(server_address, TrenTorchRequestHandler)
        except OSError as e:
            console.print(f"[bold red]❌ Failed to bind to {host}:{port}: {e}[/bold red]")
            console.print(f"[dim]💡 Try running with a different port: tren serve --port {port + 1}[/dim]")
            return 1

        if not is_loopback:
            console.print(
                Panel(
                    "[bold yellow]⚠️  Binding to a non-loopback address.[/bold yellow]\n"
                    f"The companion API can run pytest and export code, and it is now reachable at "
                    f"[bold]{host}:{port}[/bold] from other machines on your network.\n"
                    "Only do this on a trusted network. Use the default 127.0.0.1 otherwise.",
                    title="[bold red]Security notice[/bold red]",
                    border_style="red",
                )
            )

        info_text = Text()
        info_text.append("⚡ Tren⚡️Torch Companion Server Active!\n\n", style="bold green")
        info_text.append("🌐 Visualizer URL: ", style="bold")
        info_text.append(f"{url}\n", style="bold cyan underline")
        info_text.append(
            "📊 Features: Autograd DAG, Attention & Conv2D Visualizers, Test Streaming\n", style="dim"
        )
        info_text.append("🛑 Press Ctrl+C to stop the server anytime.", style="yellow")

        console.print()
        console.print(
            Panel(info_text, title="[bold #38bdf8]Tren⚡️Torch Companion[/bold #38bdf8]", border_style="cyan")
        )
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
