"""
Tests for TrenTorch Companion Server and API Handler.
"""

import json
import threading
from http.server import ThreadingHTTPServer
import urllib.request
import urllib.error

from platforms.cli.core.config import CLIConfig
from platforms.cli.server.command import ServeCommand
from platforms.cli.server.handler import TrenTorchRequestHandler


def test_serve_command_metadata():
    """Verify ServeCommand exposes the expected CLI metadata."""
    config = CLIConfig.from_project_root()
    cmd = ServeCommand(config)
    assert cmd.name == "serve"
    assert "visualizer" in cmd.description.lower() or "companion" in cmd.description.lower()


def test_server_api_endpoints():
    """Start server on a test port and verify all REST endpoints and static files."""
    config = CLIConfig.from_project_root()
    TrenTorchRequestHandler.config = config

    # Bind to ephemeral port
    server = ThreadingHTTPServer(("127.0.0.1", 0), TrenTorchRequestHandler)
    port = server.server_port
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    base_url = f"http://127.0.0.1:{port}"

    try:
        # 1. Test GET /api/status
        with urllib.request.urlopen(f"{base_url}/api/status") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "total_modules" in data
            assert data["total_modules"] == 20
            assert "completed_count" in data

        # 2. Test GET /api/modules
        with urllib.request.urlopen(f"{base_url}/api/modules") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "modules" in data
            assert len(data["modules"]) == 20
            assert data["modules"][0]["id"] == "01"

        # 3. Test GET /api/milestones
        with urllib.request.urlopen(f"{base_url}/api/milestones") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "milestones" in data
            assert len(data["milestones"]) > 0

        # 4. Test GET /api/autograd/demo
        with urllib.request.urlopen(f"{base_url}/api/autograd/demo") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "nodes" in data
            assert "edges" in data

        # 5. Test GET /api/benchmarks/quick
        with urllib.request.urlopen(f"{base_url}/api/benchmarks/quick") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "benchmarks" in data
            assert len(data["benchmarks"]) > 0

        # 6. Test Static file serving: GET / (index.html)
        with urllib.request.urlopen(f"{base_url}/") as resp:
            assert resp.status == 200
            content = resp.read().decode("utf-8")
            assert "Tren⚡️Torch" in content
            assert "Autograd" in content

        # 7. Test Static CSS: GET /css/style.css
        with urllib.request.urlopen(f"{base_url}/css/style.css") as resp:
            assert resp.status == 200
            css = resp.read().decode("utf-8")
            assert "--accent-violet" in css

    finally:
        server.shutdown()
        server.server_close()
