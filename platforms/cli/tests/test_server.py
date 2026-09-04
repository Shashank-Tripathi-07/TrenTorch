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


# ---------------------------------------------------------------------------
# ServeCommand unit tests (no live server needed)
# ---------------------------------------------------------------------------


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


def test_serve_command_no_browser_flag_parses():
    """--no-browser sets no_browser=True; omitting it defaults to False."""
    import argparse

    config = CLIConfig.from_project_root()
    cmd = ServeCommand(config)
    parser = argparse.ArgumentParser()
    cmd.add_arguments(parser)

    with_flag = parser.parse_args(["--no-browser"])
    assert with_flag.no_browser is True

    without_flag = parser.parse_args([])
    assert without_flag.no_browser is False


def test_serve_command_no_browser_suppresses_open(monkeypatch):
    """When --no-browser is set, webbrowser.open must never be called."""
    import webbrowser
    from argparse import Namespace
    from unittest.mock import MagicMock, patch

    opened_urls: list[str] = []
    monkeypatch.setattr(webbrowser, "open", lambda url: opened_urls.append(url))

    config = CLIConfig.from_project_root()
    cmd = ServeCommand(config)

    # Patch ThreadingHTTPServer so we don't actually bind a port.
    mock_httpd = MagicMock()
    mock_httpd.serve_forever.side_effect = KeyboardInterrupt  # exits the serve loop immediately

    with patch("platforms.cli.server.command.ThreadingHTTPServer", return_value=mock_httpd):
        args = Namespace(port=9999, host="127.0.0.1", no_browser=True)
        cmd.run(args)

    assert opened_urls == [], "webbrowser.open must not be called with --no-browser"


# ---------------------------------------------------------------------------
# Read-only REST endpoints — response shape & field completeness
# ---------------------------------------------------------------------------


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


def test_status_field_completeness(running_server):
    """Every key the Web UI depends on must be present in /api/status."""
    expected_keys = {
        "title",
        "version",
        "total_modules",
        "completed_count",
        "completed_modules",
        "started_modules",
        "completion_percentage",
        "python_version",
        "in_venv",
        "library_exported",
        "last_updated",
    }
    with urllib.request.urlopen(f"{running_server}/api/status") as resp:
        data = json.loads(resp.read().decode("utf-8"))

    assert expected_keys <= data.keys(), f"Missing keys in /api/status: {expected_keys - data.keys()}"
    # Type sanity — values must match what the front-end consumes
    assert isinstance(data["total_modules"], int)
    assert isinstance(data["completed_count"], int)
    assert isinstance(data["completed_modules"], list)
    assert isinstance(data["started_modules"], list)
    assert isinstance(data["completion_percentage"], (int, float))
    assert isinstance(data["in_venv"], bool)
    assert isinstance(data["library_exported"], bool)


def test_modules_field_completeness(running_server):
    """Each module object must carry the full set of fields the UI renders."""
    required_fields = {
        "id",
        "folder",
        "title",
        "stage",
        "description",
        "status",
        "source_path",
        "notebook_path",
    }
    valid_statuses = {"not_started", "in_progress", "completed"}

    with urllib.request.urlopen(f"{running_server}/api/modules") as resp:
        modules = json.loads(resp.read().decode("utf-8"))["modules"]

    assert len(modules) == 20
    seen_ids = set()
    for mod in modules:
        missing = required_fields - mod.keys()
        assert not missing, f"Module {mod.get('id')!r} is missing fields: {missing}"
        assert mod["id"] not in seen_ids, f"Duplicate module id: {mod['id']!r}"
        seen_ids.add(mod["id"])
        assert mod["status"] in valid_statuses, (
            f"Module {mod['id']!r} has unexpected status: {mod['status']!r}"
        )
        # Paths should be relative strings (never absolute)
        assert not mod["source_path"].startswith("/"), (
            f"source_path for {mod['id']!r} must be relative, got: {mod['source_path']!r}"
        )
        assert not mod["notebook_path"].startswith("/"), (
            f"notebook_path for {mod['id']!r} must be relative, got: {mod['notebook_path']!r}"
        )


def test_milestones_field_completeness(running_server):
    """Each milestone object must carry the full set of fields the UI renders."""
    required_fields = {
        "id",
        "name",
        "year",
        "title",
        "emoji",
        "description",
        "required_modules",
        "is_unlocked",
    }
    with urllib.request.urlopen(f"{running_server}/api/milestones") as resp:
        milestones = json.loads(resp.read().decode("utf-8"))["milestones"]

    assert len(milestones) > 0
    for ms in milestones:
        missing = required_fields - ms.keys()
        assert not missing, f"Milestone {ms.get('id')!r} is missing fields: {missing}"
        assert isinstance(ms["year"], int), (
            f"Milestone {ms['id']!r}: year must be int, got {type(ms['year'])}"
        )
        assert isinstance(ms["required_modules"], list), (
            f"Milestone {ms['id']!r}: required_modules must be a list"
        )
        assert isinstance(ms["is_unlocked"], bool), f"Milestone {ms['id']!r}: is_unlocked must be bool"


def test_autograd_demo_node_and_edge_shapes(running_server):
    """Every node and edge in the autograd DAG must have the required fields."""
    node_required = {"id", "label", "type", "shape"}
    edge_required = {"source", "target", "label"}
    valid_node_types = {"input", "param", "op", "loss"}

    with urllib.request.urlopen(f"{running_server}/api/autograd/demo") as resp:
        data = json.loads(resp.read().decode("utf-8"))

    assert data["illustrative"] is True
    assert "note" in data, "/api/autograd/demo must include a 'note' field"

    for node in data["nodes"]:
        missing = node_required - node.keys()
        assert not missing, f"Node {node.get('id')!r} missing fields: {missing}"
        assert node["type"] in valid_node_types, f"Node {node['id']!r} has unknown type: {node['type']!r}"
        assert isinstance(node["shape"], list), f"Node {node['id']!r}: shape must be a list"

    node_ids = {n["id"] for n in data["nodes"]}
    for edge in data["edges"]:
        missing = edge_required - edge.keys()
        assert not missing, f"Edge missing fields: {missing}"
        assert edge["source"] in node_ids, f"Edge source {edge['source']!r} references a non-existent node"
        assert edge["target"] in node_ids, f"Edge target {edge['target']!r} references a non-existent node"


def test_benchmarks_all_three_rows(running_server):
    """All three benchmark rows (matmul, softmax, conv2d) must be present and well-typed."""
    with urllib.request.urlopen(f"{running_server}/api/benchmarks/quick") as resp:
        data = json.loads(resp.read().decode("utf-8"))

    rows = data["benchmarks"]
    assert len(rows) == 3, f"Expected 3 benchmark rows, got {len(rows)}"

    for row in rows:
        assert "op" in row and isinstance(row["op"], str)
        assert "unit" in row and isinstance(row["unit"], str)
        assert "numpy_time" in row and isinstance(row["numpy_time"], (int, float))
        assert row["numpy_time"] > 0, f"numpy_time must be positive: {row['numpy_time']}"
        assert "throughput_gflops" in row and isinstance(row["throughput_gflops"], (int, float))
        # trentorch_time must be an honest measurement or an honest null — never negative
        tt = row.get("trentorch_time")
        assert tt is None or isinstance(tt, (int, float)), (
            f"trentorch_time must be float or null, got {type(tt)}"
        )
        if tt is not None:
            assert tt > 0, f"trentorch_time must be positive when present: {tt}"

    # Rows must appear in a stable, predictable order (matmul, softmax, conv2d)
    assert "Mult" in rows[0]["op"] or "Matrix" in rows[0]["op"] or "matmul" in rows[0]["op"].lower()
    assert "softmax" in rows[1]["op"].lower() or "attention" in rows[1]["op"].lower()
    assert "conv" in rows[2]["op"].lower() or "2d" in rows[2]["op"].lower()


# ---------------------------------------------------------------------------
# Unknown-endpoint 404 handling
# ---------------------------------------------------------------------------


def test_unknown_api_get_path_returns_404(running_server):
    """An unrecognised /api/ GET path must return 404 JSON, not a 500 or file."""
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(f"{running_server}/api/does-not-exist")
    assert exc.value.code == 404
    body = json.loads(exc.value.read().decode("utf-8"))
    assert "error" in body


def test_unknown_api_post_path_returns_404(running_server):
    """An unrecognised POST path must return 404 JSON."""
    req = urllib.request.Request(
        f"{running_server}/api/modules/01/no-such-action",
        method="POST",
        data=b"",
    )
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req)
    assert exc.value.code == 404
    body = json.loads(exc.value.read().decode("utf-8"))
    assert "error" in body


# ---------------------------------------------------------------------------
# Module-ID validation / injection guards
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Security: origin / host checks
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# OPTIONS pre-flight
# ---------------------------------------------------------------------------


def test_options_preflight_loopback_origin_gets_cors_headers(running_server):
    """OPTIONS from a loopback Origin must return the three CORS allow-headers."""
    req = urllib.request.Request(
        f"{running_server}/api/status",
        method="OPTIONS",
        headers={"Origin": "http://localhost:8080"},
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        assert "GET" in (resp.headers.get("Access-Control-Allow-Methods") or "")
        assert "POST" in (resp.headers.get("Access-Control-Allow-Methods") or "")
        assert resp.headers.get("Access-Control-Allow-Headers") is not None


def test_options_preflight_foreign_origin_gets_no_cors_headers(running_server):
    """OPTIONS from a non-loopback Origin must not echo back any ACAO header."""
    req = urllib.request.Request(
        f"{running_server}/api/status",
        method="OPTIONS",
        headers={"Origin": "https://attacker.example.com"},
    )
    with urllib.request.urlopen(req) as resp:
        # Server returns 200 for OPTIONS but must not grant CORS to foreign origins
        assert resp.headers.get("Access-Control-Allow-Origin") != "https://attacker.example.com"


# ---------------------------------------------------------------------------
# POST /api/modules/{id}/complete — response shape
# ---------------------------------------------------------------------------


def test_post_module_complete_response_shape(running_server):
    """POST /api/modules/{id}/complete always returns the 4-key JSON shape.

    The underlying subprocess may succeed or fail depending on whether the
    student's module is implemented; we only assert the wire shape, not the
    outcome.
    """
    req = urllib.request.Request(f"{running_server}/api/modules/01/complete", method="POST", data=b"")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        ct = resp.headers.get("Content-Type", "")
        assert "application/json" in ct
        data = json.loads(resp.read().decode("utf-8"))

    assert data["module"] == "01", "Response must echo back the canonical module id"
    assert isinstance(data["success"], bool), "'success' must be a bool"
    assert isinstance(data["stdout"], str), "'stdout' must be a string"
    assert isinstance(data["stderr"], str), "'stderr' must be a string"


# ---------------------------------------------------------------------------
# GET /api/modules/{id}/test/stream — SSE wire format
# ---------------------------------------------------------------------------


def test_sse_module_test_stream_wire_format(running_server):
    """The SSE stream must emit well-formed events: start → [output*] → end.

    We run module 01 and consume the full stream. The exit code is whatever
    the student's implementation produces; we only verify the SSE protocol
    and the shape of the JSON payloads — nothing is fabricated.
    """
    url = f"{running_server}/api/modules/01/test/stream"
    req = urllib.request.Request(url)

    events: list[dict] = []
    current: dict = {}

    with urllib.request.urlopen(req, timeout=30) as resp:
        # 1. Content-Type must be SSE
        ct = resp.headers.get("Content-Type", "")
        assert "text/event-stream" in ct, f"Expected text/event-stream, got: {ct!r}"
        assert resp.headers.get("Cache-Control") == "no-cache"

        while True:
            raw_line = resp.readline()
            if not raw_line:
                break
            line = raw_line.decode("utf-8").rstrip("\r\n")

            if line.startswith("event:"):
                current["event"] = line[len("event:") :].strip()
            elif line.startswith("data:"):
                current["data"] = json.loads(line[len("data:") :].strip())
            elif line == "" and current:
                events.append(current)
                is_end = current.get("event") == "end"
                current = {}
                if is_end:
                    break
        if current:
            events.append(current)

    assert len(events) >= 2, "Stream must emit at least a 'start' and an 'end' event"

    # 3. First event must be 'start' with module id
    first = events[0]
    assert first.get("event") == "start", f"First event must be 'start', got: {first.get('event')!r}"
    start_data = first["data"]
    assert start_data.get("module") == "01"
    assert "folder" in start_data
    assert "message" in start_data

    # 4. All intermediate events (if any) must be 'output' with a 'line' key
    for ev in events[1:-1]:
        assert ev.get("event") in ("output", "error"), (
            f"Intermediate event must be 'output' or 'error', got: {ev.get('event')!r}"
        )
        if ev["event"] == "output":
            assert isinstance(ev["data"].get("line"), str)

    # 5. Last event must be 'end' with exit_code and passed
    last = events[-1]
    assert last.get("event") == "end", f"Last event must be 'end', got: {last.get('event')!r}"
    end_data = last["data"]
    assert "exit_code" in end_data, "'end' event must include exit_code"
    assert "passed" in end_data, "'end' event must include passed"
    assert isinstance(end_data["exit_code"], int)
    assert isinstance(end_data["passed"], bool)
    assert "message" in end_data, "'end' event must include a human-readable message"
