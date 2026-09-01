"""
HTTP and Server-Sent Events (SSE) request handler for TrenTorch Companion.

Security model
--------------
The companion server can start local subprocesses (pytest runs, module
exports), so it is deliberately restrictive:

* It only answers API calls whose ``Host`` header is a loopback name and
  whose ``Origin`` (when present) is a loopback origin. This blocks
  DNS-rebinding and cross-site (CSRF) calls from any page the user happens
  to have open while ``tren serve`` is running.
* Module identifiers taken from the URL are resolved against the real set
  of discovered modules before anything is executed. Unknown ids get a
  404 and never reach a subprocess.
* No wildcard CORS. The web UI is served from the same origin, so it does
  not need CORS at all; cross-origin reads stay blocked.
"""

import json
import os
import subprocess
import sys
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from platforms.cli import __version__
from platforms.cli.core.config import CLIConfig
from platforms.cli.core.modules import (
    get_all_module_metadata,
    get_module_mapping,
    get_module_name,
    normalize_module_number,
)
from platforms.cli.processes.milestone.constants import MILESTONE_SCRIPTS

MODULE_STAGES = {
    "Part 1: Foundations": ["01", "02", "03", "04", "05"],
    "Part 2: Deep Learning Core": ["06", "07", "08", "09"],
    "Part 3: Architecture & Scale": ["10", "11", "12", "13"],
    "Part 4: Systems Engineering": ["14", "15", "16", "17", "18", "19", "20"],
}

# The complete, closed set of module ids the companion will ever run a
# command for. Subprocess calls use an element of this literal tuple, never
# a value derived from the request, so a URL can only ever select one of
# these fixed strings.
VALID_MODULE_IDS = tuple(num for nums in MODULE_STAGES.values() for num in nums)

# Hostnames that are always considered safe for the local companion.
LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]"}


class TrenTorchRequestHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler for TrenTorch Companion API & Static Assets."""

    config: CLIConfig = None  # Injected by server
    # Extra hostnames the operator explicitly bound to (see ServeCommand).
    allowed_hosts: set[str] = set()

    def __init__(self, *args, **kwargs):
        self.web_root = Path(__file__).resolve().parent.parent.parent / "web"
        super().__init__(*args, directory=str(self.web_root), **kwargs)

    # ---------------- REQUEST TRUST / ORIGIN CHECKS ----------------

    def _trusted_hostnames(self) -> set[str]:
        return LOOPBACK_HOSTS | {h.lower() for h in self.allowed_hosts}

    def _request_is_local(self) -> bool:
        """True only for same-machine requests that no remote page can forge.

        Guards against DNS-rebinding (Host header) and cross-site fetches
        (Origin header). Static assets do not call this; only the API does.
        """
        trusted = self._trusted_hostnames()

        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip().lower()
        if host and host not in trusted:
            return False

        origin = self.headers.get("Origin")
        if origin:
            origin_host = urlparse(origin).hostname or ""
            if origin_host.lower() not in trusted:
                return False

        return True

    def _reject_untrusted(self) -> None:
        self._send_json(
            {"error": "Forbidden: companion API is restricted to local requests."},
            status=HTTPStatus.FORBIDDEN,
        )

    def do_OPTIONS(self):
        """Handle CORS pre-flight requests (loopback origins only)."""
        origin = self.headers.get("Origin", "")
        origin_host = (urlparse(origin).hostname or "").lower()
        self.send_response(HTTPStatus.OK)
        if origin and origin_host in self._trusted_hostnames():
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        """Handle GET requests for API endpoints and static assets."""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/status":
            self._guarded(self._handle_get_status)
        elif path == "/api/modules":
            self._guarded(self._handle_get_modules)
        elif path == "/api/milestones":
            self._guarded(self._handle_get_milestones)
        elif path == "/api/autograd/demo":
            self._guarded(self._handle_get_autograd_demo)
        elif path.startswith("/api/modules/") and path.endswith("/test/stream"):
            # e.g. /api/modules/01/test/stream
            parts = path.split("/")
            mod_id = parts[3] if len(parts) > 3 else ""
            self._guarded(lambda: self._handle_sse_module_test(mod_id))
        elif path == "/api/benchmarks/quick":
            self._guarded(self._handle_get_quick_benchmarks)
        elif path.startswith("/api/"):
            self._send_json({"error": "Endpoint not found"}, status=HTTPStatus.NOT_FOUND)
        else:
            # Fallback to static file server (same-origin assets, safe to serve)
            super().do_GET()

    def do_POST(self):
        """Handle POST requests for actions."""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path.startswith("/api/modules/") and path.endswith("/complete"):
            parts = path.split("/")
            mod_id = parts[3] if len(parts) > 3 else ""
            self._guarded(lambda: self._handle_post_module_complete(mod_id))
        else:
            self._send_json({"error": "Endpoint not found"}, status=HTTPStatus.NOT_FOUND)

    def _guarded(self, handler) -> None:
        """Run an API handler only for trusted local requests."""
        if not self._request_is_local():
            self._reject_untrusted()
            return
        handler()

    # ---------------- API ENDPOINT HANDLERS ----------------

    @staticmethod
    def _resolve_module(module_input: str) -> str | None:
        """Map a request-supplied module reference to a fixed, known id.

        Returns an element of ``VALID_MODULE_IDS`` (a module-level literal),
        never a string derived from the request. Anything that does not
        match a real, discovered module is rejected before any command runs.
        """
        if not module_input or not module_input.isascii() or len(module_input) > 40:
            return None
        normalized = normalize_module_number(module_input)
        for valid in VALID_MODULE_IDS:
            if valid == normalized and get_module_name(valid) is not None:
                return valid
        return None

    def _all_module_numbers(self) -> tuple[str, ...]:
        return VALID_MODULE_IDS

    def _load_progress(self) -> dict[str, Any]:
        """Load user progress from progress.json."""
        p_file = self.config.project_root / "user_data" / "progress.json"
        if p_file.exists():
            try:
                with open(p_file) as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "started_modules": [],
            "completed_modules": [],
            "last_worked": None,
            "last_completed": None,
            "last_updated": None,
        }

    def _send_json(self, data: Any, status: HTTPStatus = HTTPStatus.OK):
        """Helper to send JSON response."""
        payload = json.dumps(data).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _handle_get_status(self):
        """Return system status and curriculum progress metrics."""
        progress = self._load_progress()
        completed = progress.get("completed_modules", [])
        started = progress.get("started_modules", [])
        total_modules = len(self._all_module_numbers())

        in_venv = sys.prefix != sys.base_prefix or os.environ.get("VIRTUAL_ENV") is not None
        tp_path = self.config.project_root / "data" / "trentorch"

        data = {
            "title": "Tren⚡️Torch Companion",
            "version": __version__,
            "total_modules": total_modules,
            "completed_count": len(completed),
            "completed_modules": completed,
            "started_modules": started,
            "completion_percentage": (
                round((len(completed) / total_modules) * 100, 1) if total_modules else 0.0
            ),
            "python_version": sys.version.split()[0],
            "in_venv": in_venv,
            "library_exported": tp_path.exists(),
            "last_updated": progress.get("last_updated"),
        }
        self._send_json(data)

    def _handle_get_modules(self):
        """Return list of all curriculum modules with rich metadata."""
        progress = self._load_progress()
        completed = set(progress.get("completed_modules", []))
        started = set(progress.get("started_modules", []))

        mapping = get_module_mapping()
        metadata_dict = get_all_module_metadata()

        modules_list = []
        for stage_name, nums in MODULE_STAGES.items():
            for num in nums:
                folder_name = mapping.get(num, f"{num}_module")
                meta = metadata_dict.get(folder_name)

                title = meta.title if meta else folder_name.replace("_", " ").title()
                desc = (
                    meta.description if meta else "Build and test this machine learning module from scratch."
                )

                if num in completed:
                    status = "completed"
                elif num in started:
                    status = "in_progress"
                else:
                    status = "not_started"

                modules_list.append(
                    {
                        "id": num,
                        "folder": folder_name,
                        "title": title,
                        "stage": stage_name,
                        "description": desc,
                        "status": status,
                        "source_path": f"data/src/{folder_name}/{folder_name}.py",
                        "notebook_path": f"data/modules/{folder_name}/{folder_name}.ipynb",
                    }
                )

        self._send_json({"modules": modules_list})

    def _handle_get_milestones(self):
        """Return list of historical milestones."""
        progress = self._load_progress()
        completed = set(progress.get("completed_modules", []))

        milestones_list = []
        for m_id, m_data in sorted(MILESTONE_SCRIPTS.items()):
            req_mods = m_data.get("required_modules", [])
            is_unlocked = all(f"{int(m):02d}" in completed for m in req_mods)

            milestones_list.append(
                {
                    "id": m_id,
                    "name": m_data.get("name"),
                    "year": m_data.get("year"),
                    "title": m_data.get("title"),
                    "emoji": m_data.get("emoji", "🏆"),
                    "description": m_data.get("description"),
                    "historical_context": m_data.get("historical_context"),
                    "required_modules": req_mods,
                    "is_unlocked": is_unlocked,
                }
            )

        self._send_json({"milestones": milestones_list})

    def _handle_get_autograd_demo(self):
        """Return a representative computational DAG for the visualizer.

        These values are an illustrative reference graph, not a live trace
        of an executed model. The UI labels it as such.
        """
        graph = {
            "illustrative": True,
            "note": "Representative MLP graph with reference values, not a live autograd trace.",
            "nodes": [
                {
                    "id": "x",
                    "label": "x (Input)",
                    "type": "input",
                    "shape": [4, 8],
                    "grad": None,
                    "val_preview": "[[0.21, -0.45, ...]]",
                },
                {
                    "id": "w1",
                    "label": "W₁ (Linear)",
                    "type": "param",
                    "shape": [8, 16],
                    "grad": "[[-0.04, 0.12, ...]]",
                    "val_preview": "[[0.52, -0.11, ...]]",
                },
                {
                    "id": "b1",
                    "label": "b₁ (Bias)",
                    "type": "param",
                    "shape": [16],
                    "grad": "[0.01, -0.05, ...]",
                    "val_preview": "[0.00, 0.00, ...]",
                },
                {
                    "id": "z1",
                    "label": "MatMul + Add",
                    "type": "op",
                    "shape": [4, 16],
                    "grad": "[[-0.12, 0.08, ...]]",
                    "op": "LinearForward",
                },
                {
                    "id": "a1",
                    "label": "ReLU",
                    "type": "op",
                    "shape": [4, 16],
                    "grad": "[[0.00, 0.08, ...]]",
                    "op": "ReLU",
                },
                {
                    "id": "w2",
                    "label": "W₂ (Head)",
                    "type": "param",
                    "shape": [16, 2],
                    "grad": "[[0.32, -0.19, ...]]",
                    "val_preview": "[[0.14, 0.88, ...]]",
                },
                {
                    "id": "b2",
                    "label": "b₂ (Bias)",
                    "type": "param",
                    "shape": [2],
                    "grad": "[0.44, -0.44]",
                    "val_preview": "[0.00, 0.00]",
                },
                {
                    "id": "logits",
                    "label": "Logits",
                    "type": "op",
                    "shape": [4, 2],
                    "grad": "[[0.22, -0.22, ...]]",
                    "op": "LinearForward",
                },
                {
                    "id": "targets",
                    "label": "y (Target)",
                    "type": "input",
                    "shape": [4, 2],
                    "grad": None,
                    "val_preview": "[[1.0, 0.0], ...]",
                },
                {
                    "id": "loss",
                    "label": "MSE Loss",
                    "type": "loss",
                    "shape": [],
                    "val_preview": "0.1428",
                    "grad": "1.0000",
                    "op": "MeanSquaredError",
                },
            ],
            "edges": [
                {"source": "x", "target": "z1", "label": "forward"},
                {"source": "w1", "target": "z1", "label": "forward"},
                {"source": "b1", "target": "z1", "label": "forward"},
                {"source": "z1", "target": "a1", "label": "activation"},
                {"source": "a1", "target": "logits", "label": "forward"},
                {"source": "w2", "target": "logits", "label": "forward"},
                {"source": "b2", "target": "logits", "label": "forward"},
                {"source": "logits", "target": "loss", "label": "prediction"},
                {"source": "targets", "target": "loss", "label": "ground_truth"},
            ],
        }
        self._send_json(graph)

    # ---------------- BENCHMARKS (measured, not fabricated) ----------------

    @staticmethod
    def _time_ms(fn, iters: int) -> float:
        # One warm-up call to avoid counting first-call allocation/JIT costs.
        fn()
        t0 = time.perf_counter()
        for _ in range(iters):
            fn()
        return ((time.perf_counter() - t0) / iters) * 1000

    def _handle_get_quick_benchmarks(self):
        """Measure real operator latency for NumPy and, when the student's
        library is exported, for TrenTorch too. Nothing here is synthesised:
        a missing TrenTorch implementation reports ``null``, not a guess.
        """
        import numpy as np

        try:
            import trentorch as tt
        except Exception:
            tt = None

        benchmarks = []

        # 1. Matrix multiplication -------------------------------------------------
        a = np.random.randn(512, 512).astype(np.float32)
        b = np.random.randn(512, 512).astype(np.float32)
        np_ms = self._time_ms(lambda: np.dot(a, b), iters=10)

        tt_ms = None
        if tt is not None and getattr(tt, "Tensor", None) is not None:
            try:
                ta, tb = tt.Tensor(a), tt.Tensor(b)
                tt_ms = round(self._time_ms(lambda: ta.matmul(tb), iters=10), 3)
            except Exception:
                tt_ms = None

        benchmarks.append(
            {
                "op": "Matrix Multiplication (512x512 FP32)",
                "unit": "ms/op",
                "numpy_time": round(np_ms, 3),
                "trentorch_time": tt_ms,
                "throughput_gflops": round((2 * 512**3) / (np_ms / 1000) / 1e9, 2),
            }
        )

        # 2. Softmax over attention rows ----------------------------------------------
        x = np.random.randn(128, 512).astype(np.float32)

        def np_softmax():
            e = np.exp(x - np.max(x, axis=-1, keepdims=True))
            return e / np.sum(e, axis=-1, keepdims=True)

        sm_ms = self._time_ms(np_softmax, iters=20)

        tt_sm = None
        if tt is not None and getattr(tt, "Softmax", None) is not None:
            try:
                layer = tt.Softmax()
                tx = tt.Tensor(x)
                tt_sm = round(self._time_ms(lambda: layer(tx), iters=20), 3)
            except Exception:
                tt_sm = None

        benchmarks.append(
            {
                "op": "Softmax Attention Row (128x512)",
                "unit": "ms/op",
                "numpy_time": round(sm_ms, 3),
                "trentorch_time": tt_sm,
                "throughput_gflops": round((5 * 128 * 512) / (sm_ms / 1000) / 1e9, 2),
            }
        )

        # 3. 2D convolution forward -------------------------------------------------
        img = np.random.randn(1, 16, 32, 32).astype(np.float32)
        ker = np.random.randn(16, 16, 3, 3).astype(np.float32)

        def np_conv2d():
            windows = np.lib.stride_tricks.sliding_window_view(img, (3, 3), axis=(2, 3))
            # windows: (1, 16, 30, 30, 3, 3) -> contract in-channels + kernel
            return np.einsum("nihwkl,oikl->nohw", windows, ker)

        conv_ms = self._time_ms(np_conv2d, iters=5)

        tt_conv = None
        if tt is not None and getattr(tt, "Conv2d", None) is not None:
            try:
                conv = tt.Conv2d(16, 16, 3)
                timg = tt.Tensor(img)
                tt_conv = round(self._time_ms(lambda: conv(timg), iters=5), 3)
            except Exception:
                tt_conv = None

        # 2*Cout*Cin*K*K*Hout*Wout FLOPs
        conv_flops = 2 * 16 * 16 * 3 * 3 * 30 * 30
        benchmarks.append(
            {
                "op": "2D Convolution Forward (3x3 Kernel, 16ch)",
                "unit": "ms/op",
                "numpy_time": round(conv_ms, 3),
                "trentorch_time": tt_conv,
                "throughput_gflops": round(conv_flops / (conv_ms / 1000) / 1e9, 2),
            }
        )

        self._send_json(
            {
                "measured": True,
                "trentorch_available": tt is not None,
                "note": (
                    "NumPy figures are measured on this machine. TrenTorch figures "
                    "appear once the matching module is exported to data/trentorch."
                ),
                "benchmarks": benchmarks,
            }
        )

    # ---------------- SUBPROCESS-BACKED ENDPOINTS ----------------

    def _subprocess_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["TREN_ALLOW_SYSTEM"] = "1"
        env["TITO_ALLOW_SYSTEM"] = "1"
        return env

    def _handle_sse_module_test(self, module_input: str):
        """Run pytest for a known module and stream output over SSE."""
        num = self._resolve_module(module_input)
        if num is None:
            self._send_json(
                {"error": f"Unknown module: {module_input!r}"},
                status=HTTPStatus.NOT_FOUND,
            )
            return

        folder = get_module_mapping().get(num, f"{num}_module")

        try:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
        except (BrokenPipeError, ConnectionResetError):
            return

        def _send_event(event_type: str, data: Any) -> bool:
            payload = f"event: {event_type}\ndata: {json.dumps(data)}\n\n".encode()
            try:
                self.wfile.write(payload)
                self.wfile.flush()
                return True
            except (BrokenPipeError, ConnectionResetError):
                return False

        # module test only accepts the canonical 2-digit id resolved above.
        cmd = [sys.executable, "-m", "platforms.cli.main", "module", "test", num, "--verbose"]

        if not _send_event(
            "start", {"module": num, "folder": folder, "message": f"Starting test run for Module {num}..."}
        ):
            return

        proc = None
        try:
            # argv is a fixed literal list; `num` is the canonical id from
            # the module allow-list, so nothing here is shell-interpreted or
            # attacker-controlled.
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(self.config.project_root),
                env=self._subprocess_env(),
            )

            if proc.stdout:
                for line in proc.stdout:
                    if not _send_event("output", {"line": line.rstrip()}):
                        proc.kill()
                        return

            proc.wait()
            rc = proc.returncode
            _send_event(
                "end",
                {
                    "exit_code": rc,
                    "passed": rc == 0,
                    "message": "Tests Passed!" if rc == 0 else "Tests Failed.",
                },
            )
        except (BrokenPipeError, ConnectionResetError):
            if proc:
                proc.kill()
        except Exception as e:  # surface any failure to the client
            _send_event("error", {"error": str(e)})

    def _handle_post_module_complete(self, module_input: str):
        """Trigger module complete / export for a known module."""
        num = self._resolve_module(module_input)
        if num is None:
            self._send_json(
                {"error": f"Unknown module: {module_input!r}"},
                status=HTTPStatus.NOT_FOUND,
            )
            return

        # argv is a fixed literal list; `num` is the canonical id from the
        # module allow-list, so nothing here is shell-interpreted or
        # attacker-controlled.
        cmd = [sys.executable, "-m", "platforms.cli.main", "module", "complete", num]

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.config.project_root),
                env=self._subprocess_env(),
            )
            success = res.returncode == 0
            self._send_json(
                {
                    "module": num,
                    "success": success,
                    "stdout": res.stdout,
                    "stderr": res.stderr,
                }
            )
        except Exception as e:
            self._send_json({"error": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
