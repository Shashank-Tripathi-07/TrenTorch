"""
Tests for TrenTorch Companion Server and API Handler.
"""

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from platforms.cli.core.config import CLIConfig
from platforms.cli.server.command import ServeCommand
from platforms.cli.server.handler import TrenTorchRequestHandler


@pytest.fixture
def running_server():
    """Start the companion handler on an ephemeral loopback port."""
    config = CLIConfig.from_project_root()
    TrenTorchRequestHandler.config = config
    TrenTorchRequestHandler.allowed_hosts = set()

    server = ThreadingHTTPServer(("127.0.0.1", 0), TrenTorchRequestHandler)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()


def test_serve_command_metadata():
    """Verify ServeCommand exposes the expected CLI metadata."""
    config = CLIConfig.from_project_root()
    cmd = ServeCommand(config)
    assert cmd.name == "serve"
    assert "visualizer" in cmd.description.lower() or "companion" in cmd.description.lower()


def test_serve_command_loopback_detection():
    """Loopback addresses are recognised; public ones are not."""
    assert ServeCommand._is_loopback("127.0.0.1")
    assert ServeCommand._is_loopback("localhost")
    assert ServeCommand._is_loopback("::1")
    assert not ServeCommand._is_loopback("0.0.0.0")
    assert not ServeCommand._is_loopback("192.168.1.10")


def test_server_api_endpoints(running_server):
    """Verify all read-only REST endpoints and static files."""
    base_url = running_server

    with urllib.request.urlopen(f"{base_url}/api/status") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["total_modules"] == 20
        assert "completed_count" in data
        # Version is read from pyproject, never a hard-coded string.
        assert data["version"] and data["version"] != "0.0.0-dev"

    with urllib.request.urlopen(f"{base_url}/api/modules") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert len(data["modules"]) == 20
        assert data["modules"][0]["id"] == "01"

    with urllib.request.urlopen(f"{base_url}/api/milestones") as resp:
        assert resp.status == 200
        assert len(json.loads(resp.read().decode("utf-8"))["milestones"]) > 0

    with urllib.request.urlopen(f"{base_url}/api/autograd/demo") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "nodes" in data and "edges" in data
        assert data["illustrative"] is True

    with urllib.request.urlopen(f"{base_url}/api/benchmarks/quick") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["measured"] is True
        assert len(data["benchmarks"]) > 0
        row = data["benchmarks"][0]
        assert isinstance(row["numpy_time"], (int, float))
        # trentorch_time is a real measurement or an honest null, never a guess.
        assert row["trentorch_time"] is None or isinstance(row["trentorch_time"], (int, float))

    with urllib.request.urlopen(f"{base_url}/") as resp:
        assert resp.status == 200
        content = resp.read().decode("utf-8")
        assert "Tren⚡️Torch" in content
        assert "Autograd" in content
        # Self-contained: no external font CDN.
        assert "fonts.googleapis.com" not in content

    with urllib.request.urlopen(f"{base_url}/css/style.css") as resp:
        assert resp.status == 200
        assert "--accent-violet" in resp.read().decode("utf-8")


def test_unknown_module_is_rejected_without_spawning(running_server):
    """A bogus module id must 404 and never reach a subprocess."""
    base_url = running_server

    req = urllib.request.Request(f"{base_url}/api/modules/not-a-module/complete", method="POST")
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req)
    assert exc.value.code == 404

    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(f"{base_url}/api/modules/99/test/stream")
    assert exc.value.code == 404

    # Path-traversal-ish junk is rejected too.
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(f"{base_url}/api/modules/..%2f..%2fetc/test/stream")
    assert exc.value.code == 404


def test_cross_origin_and_foreign_host_are_blocked(running_server):
    """DNS-rebinding (Host) and cross-site (Origin) API calls get 403."""
    base_url = running_server

    foreign_host = urllib.request.Request(f"{base_url}/api/status", headers={"Host": "evil.example.com"})
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(foreign_host)
    assert exc.value.code == 403

    cross_origin = urllib.request.Request(
        f"{base_url}/api/status", headers={"Origin": "https://evil.example.com"}
    )
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(cross_origin)
    assert exc.value.code == 403

    # A loopback Origin is still fine.
    ok = urllib.request.Request(f"{base_url}/api/status", headers={"Origin": "http://localhost:9999"})
    with urllib.request.urlopen(ok) as resp:
        assert resp.status == 200


def test_no_wildcard_cors_header(running_server):
    """The old `Access-Control-Allow-Origin: *` must be gone."""
    with urllib.request.urlopen(f"{running_server}/api/status") as resp:
        assert resp.headers.get("Access-Control-Allow-Origin") != "*"
