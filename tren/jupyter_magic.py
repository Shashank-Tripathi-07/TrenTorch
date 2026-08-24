"""IPython magic so `tren` commands run inside a Jupyter cell, in-process.

Registered automatically for the "tinytorch" kernel (see
tren/platforms/cli_platform/setup.py's kernel registration and the startup script it
writes under user_data/ipython/). Usage in a notebook cell:

    %tren module complete 01
    %tren module test 01
    %tren milestone run 01
    %exit

Each %tren call goes straight through TrenTorchCLI.run(), the exact
same dispatch path `tren <command>` uses on the command line, no
subprocess, so there is no second CLI process and no context switch
back to a terminal. A small pass/fail badge renders under the cell
afterward. %exit is the matching bookend: it saves the notebook, shuts
down the one shared Jupyter server, and exits the kernel, all from
inside the browser, no need to switch to a terminal to tear anything
down either.
"""

import html
import shlex
import time
import urllib.request

from IPython.core.magic import Magics, line_magic, magics_class
from IPython.display import HTML, Javascript, display


def _badge(command: str, ok: bool, detail: str) -> str:
    color = "#188038" if ok else "#c5221f"
    bg = "#e6f4ea" if ok else "#fce8e6"
    icon = "✓" if ok else "✗"
    safe_command = html.escape(command)
    safe_detail = html.escape(detail)
    return (
        '<div style="display:inline-block;margin-top:4px;padding:4px 10px;'
        f'border-radius:6px;background:{bg};color:{color};'
        'font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;">'
        f'{icon} tren {safe_command} &mdash; {safe_detail}</div>'
    )


def _running_server():
    """(url, token) of the shared Jupyter server this kernel belongs to.

    Reads jupyter_server's own in-process registry, the same data
    `jupyter server list` prints, rather than assuming a fixed
    localhost:8888. If more than one server happens to be running this
    takes the first; `tren module start` only ever starts one per
    project, so in the normal case there is exactly one to find.
    """
    try:
        from jupyter_server.serverapp import list_running_servers
    except ImportError:
        return None, None
    servers = list(list_running_servers())
    if not servers:
        return None, None
    server = servers[0]
    return server.get("url"), server.get("token")


@magics_class
class TrenMagics(Magics):
    """Registers the %tren and %exit line magics."""

    @line_magic
    def tren(self, line: str) -> None:
        """Run a tren CLI command without leaving the notebook.

        Example: %tren module complete 01
        """
        from tren.main import TrenTorchCLI

        argv = shlex.split(line)
        if not argv:
            display(HTML(_badge("", False, "usage: %tren <command> [args...]")))
            return

        start = time.time()
        try:
            exit_code = TrenTorchCLI().run(argv)
        except SystemExit as exc:
            exit_code = exc.code if isinstance(exc.code, int) else 1
        duration = time.time() - start
        display(HTML(_badge(line, exit_code == 0, f"{duration:.1f}s")))

    @line_magic
    def exit(self, line: str = "") -> None:
        """Save this notebook, shut down the shared Jupyter server, and exit.

        Usage: %exit

        There is no kernel-side API that reliably saves a notebook's
        live, possibly-unsaved browser state in both Jupyter Lab and
        Notebook 7 (they don't share the classic `Jupyter.notebook`
        JS object Notebook 6 exposed), so this dispatches the same
        Ctrl+S keystroke a person would press, which both UIs bind to
        "save" natively, then gives the browser a moment to actually
        write it before shutting anything down.
        """
        display(Javascript(
            "document.dispatchEvent(new KeyboardEvent('keydown', "
            "{key: 's', code: 'KeyS', ctrlKey: true, bubbles: true}));"
        ))
        time.sleep(1.5)

        base_url, token = _running_server()
        if base_url:
            shutdown_url = f"{base_url}api/shutdown"
            if token:
                shutdown_url += f"?token={token}"
            try:
                urllib.request.urlopen(
                    urllib.request.Request(shutdown_url, method="POST"), timeout=5
                )
            except Exception:
                pass  # the server tearing itself down mid-response is expected

        display(HTML(_badge("exit", True, "saved · server shutting down · goodbye")))
        time.sleep(0.5)

        if self.shell is not None and hasattr(self.shell, "kernel"):
            self.shell.kernel.do_shutdown(False)
        else:
            import os
            os._exit(0)


def load_ipython_extension(ipython) -> None:
    ipython.register_magics(TrenMagics)
