"""
Fuzz coverage for server/handler.py's URL/header parsing -- the highest-
priority target from the fuzz-testing survey (issue #72), since the
Origin header and the raw request path are genuine network-attacker-
controlled input, not just a local CLI arg or a hand-edited progress.json.

Found via fuzzing urlparse() directly (not assumed): it raises ValueError
on a malformed IPv6-looking authority, e.g. "http://[::1" (unclosed
bracket) or a request path starting "//[::1/x". Both _request_is_local
(reads the Origin header) and do_GET/do_POST (read self.path, the raw
request target) called urlparse() with no try/except, so either one was
a real, remotely-triggerable crash of that request's handling thread.
"""

import http.client
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from platforms.cli.core.config import CLIConfig
from platforms.cli.server.handler import TrenTorchRequestHandler

# ---------------------------------------------------------------------------
# _safe_hostname: the core of the fix, tested directly (fast, no server)
# ---------------------------------------------------------------------------


@given(st.text())
@settings(max_examples=300)
def test_safe_hostname_never_raises(url):
    result = TrenTorchRequestHandler._safe_hostname(url)
    assert isinstance(result, str)


def test_safe_hostname_handles_malformed_ipv6():
    """The specific string that crashed urlparse() before the fix."""
    assert TrenTorchRequestHandler._safe_hostname("http://[::1") == ""
    assert TrenTorchRequestHandler._safe_hostname("http://[") == ""


def test_safe_hostname_still_parses_real_origins():
    assert TrenTorchRequestHandler._safe_hostname("http://localhost:8080") == "localhost"
    assert TrenTorchRequestHandler._safe_hostname("http://127.0.0.1") == "127.0.0.1"


# ---------------------------------------------------------------------------
# End-to-end: a real HTTP request with a malformed Origin header, or a
# malformed raw request path, must get a clean HTTP response -- not a
# dropped/reset connection from an unhandled exception in the handler.
# ---------------------------------------------------------------------------


@pytest.fixture
def running_server():
    config = CLIConfig.from_project_root()
    TrenTorchRequestHandler.config = config
    TrenTorchRequestHandler.allowed_hosts = set()

    server = ThreadingHTTPServer(("127.0.0.1", 0), TrenTorchRequestHandler)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "127.0.0.1", port
    finally:
        server.shutdown()
        server.server_close()


def test_malformed_origin_header_gets_clean_response_not_a_crash(running_server):
    """Before the fix: urlparse("http://[::1") inside _request_is_local
    raised, uncaught, from inside do_GET -- this request would either hang,
    reset, or 500 depending on socketserver's error handling, instead of
    the clean 403 a normal untrusted-origin request gets."""
    host, port = running_server
    req = urllib.request.Request(f"http://{host}:{port}/api/status", headers={"Origin": "http://[::1"})
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
    except urllib.error.HTTPError as e:
        status = e.code
    # Whatever the trust decision lands on, the server must respond at all
    # (not reset the connection), and it must be a real HTTP status, not a
    # 500 from an unhandled exception leaking out of the handler.
    assert status in (200, 403)


def test_malformed_request_path_gets_clean_400_not_a_dropped_connection(running_server):
    """Sends a raw request line with an absolute-form request-target (the
    form real clients use for proxied requests, e.g. "GET http://host/path
    HTTP/1.1") whose "host" is a malformed IPv6 literal. urllib.request
    itself would never construct this, so it goes through a raw socket.

    A same-shaped "//[::1/x" origin-form target doesn't reach urlparse()
    with the broken value at all: Python's own http.server collapses a
    leading "//" to a single "/" before self.path is set (an open-redirect
    hardening, unrelated to this bug) -- verified directly against this
    interpreter before relying on it, since it's what makes the absolute-
    form case the one that actually still reaches the crash."""
    host, port = running_server
    conn = http.client.HTTPConnection(host, port, timeout=5)
    try:
        conn.putrequest("GET", "http://[::1/x", skip_host=True, skip_accept_encoding=True)
        conn.putheader("Host", f"{host}:{port}")
        conn.endheaders()
        response = conn.getresponse()
        assert response.status == 400
        body = json.loads(response.read().decode("utf-8"))
        assert "error" in body
    finally:
        conn.close()


def test_leading_double_slash_path_is_collapsed_before_reaching_us(running_server):
    """Documents the http.server behavior the test above depends on: a
    "//[::1/x" origin-form target never reaches our urlparse() call with
    the un-collapsed value, so it can't reproduce the crash -- it's not
    that our fix handles it, it's that the stdlib already does, one layer
    up. If a future Python drops that hardening, this test starts failing
    loudly instead of the coverage above silently testing the wrong thing."""
    host, port = running_server
    conn = http.client.HTTPConnection(host, port, timeout=5)
    try:
        conn.putrequest("GET", "//[::1/x", skip_host=True, skip_accept_encoding=True)
        conn.putheader("Host", f"{host}:{port}")
        conn.endheaders()
        response = conn.getresponse()
        # Collapsed to "/[::1/x" by http.server itself -> falls through to
        # the static file server -> a plain 404, not our JSON 400.
        assert response.status == 404
    finally:
        conn.close()
