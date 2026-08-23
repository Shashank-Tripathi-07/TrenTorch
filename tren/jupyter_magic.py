"""IPython magic so `tren` commands run inside a Jupyter cell, in-process.

Registered automatically for the "tinytorch" kernel (see
tren/commands/setup.py's kernel registration and the startup script it
writes under .tren/ipython/). Usage in a notebook cell:

    %tren module complete 01
    %tren module test 01
    %tren milestone run 01

Each call goes straight through TrenTorchCLI.run(), the exact same
dispatch path `tren <command>` uses on the command line, no subprocess,
so there is no second CLI process and no context switch back to a
terminal. A small pass/fail badge renders under the cell afterward.
"""

import html
import shlex
import time

from IPython.core.magic import Magics, line_magic, magics_class
from IPython.display import HTML, display


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


@magics_class
class TrenMagics(Magics):
    """Registers the %tren line magic."""

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


def load_ipython_extension(ipython) -> None:
    ipython.register_magics(TrenMagics)
