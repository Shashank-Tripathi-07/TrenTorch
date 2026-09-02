"""The Jupyter component's process logic, all in one place.

Everything `tren` does with Jupyter lives here: choosing Notebook vs
Lab, finding or starting the one shared server a project uses, opening
a module's notebook in it, and scoping the `%tren` magic to the
`trentorch` kernel. This used to be split three ways (server lifecycle
in module/workflow.py, magic registration in commands/setup.py, the
magic itself in jupyter_magic.py) purely because each piece got added
at a different time; the component is one thing, so its process logic
lives in one file. tren/jupyter_magic.py stays separate on purpose:
that file has to import cleanly inside a Jupyter kernel with no `tren`
CLI context at all, which is a real constraint this module doesn't
share.
"""

import json
import os
import re
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

from rich.prompt import Prompt

from ..core.runtime import is_interactive


def resolve_jupyter_ui(notebook: bool, lab: bool) -> bool:
    """Return True for the classic Notebook UI, False for Lab.

    An explicit --notebook or --lab always wins, no prompt. With
    neither, ask when there's a real terminal to ask on (Notebook
    recommended, since that's the closer match to the single-document
    editing a module is); in CI or any other non-interactive context,
    fall back to Lab without prompting rather than hang waiting for
    an answer nobody can give.
    """
    if notebook:
        return True
    if lab:
        return False
    if not is_interactive():
        return False
    choice = Prompt.ask(
        "Open in [cyan]Notebook[/cyan] or [cyan]Lab[/cyan]? (notebook recommended)",
        choices=["notebook", "lab"],
        default="notebook",
    )
    return choice == "notebook"


def find_running_jupyter_server(project_root: Path):
    """Return (base_url, token) for a Jupyter server already rooted at
    the project root, or (None, None) if none is running there.

    Reads live state from `jupyter server list` rather than tracking a
    PID ourselves, so it self-heals if the server was closed outside
    tren's control.
    """
    try:
        result = subprocess.run(
            ["jupyter", "server", "list"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
    except FileNotFoundError:
        return None, None
    if result.returncode != 0:
        return None, None

    project_root_str = str(project_root.resolve())
    for line in result.stdout.splitlines():
        match = re.match(r"^(https?://\S+?/)(?:\?token=(\S+))?\s*::\s*(.+)$", line.strip())
        if not match:
            continue
        url, token, root_dir = match.groups()
        if os.path.normcase(os.path.normpath(root_dir.strip())) == os.path.normcase(
            os.path.normpath(project_root_str)
        ):
            return url, token
    return None, None


def start_jupyter_server(project_root: Path) -> bool:
    """Spawn one Jupyter Lab server rooted at the project root.

    Detached so it outlives this `tren` process; every subsequent
    `tren module start/view/resume` finds and reuses it via
    `find_running_jupyter_server` instead of starting another.

    Its own stdout/stderr go to user_data/jupyter.log rather than
    DEVNULL: if find_running_jupyter_server later fails to detect it
    (slow machine, timing), that log is real, checkable output --
    unlike DEVNULL, which left an earlier error message pointing at
    "the terminal output above" that was never actually printed
    anywhere (issue #139).

    Uses `sys.executable -m jupyterlab`, not a bare "jupyter lab"
    command: the latter depends on subcommand discovery finding a
    `jupyter-lab` entry point on PATH, and if some other Python
    installation's `jupyter` happens to resolve first on PATH (a real,
    reproduced case, not hypothetical), that other installation's own
    subcommand discovery runs instead -- silently failing to launch
    anything at all rather than using this venv's own jupyterlab,
    which was confirmed installed and working via `python -m
    jupyterlab` in the same environment where bare `jupyter lab`
    printed nothing but its own top-level help. `-m` sidesteps PATH
    resolution entirely: it's tied to the exact interpreter running
    `tren` itself.
    """
    try:
        cmd = [sys.executable, "-m", "jupyterlab", "--no-browser", f"--notebook-dir={project_root}"]
        detach_kwargs = (
            {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS}
            if sys.platform == "win32"
            else {"start_new_session": True}
        )
        log_dir = project_root / "user_data"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = open(log_dir / "jupyter.log", "w", encoding="utf-8")
        subprocess.Popen(
            cmd,
            cwd=str(project_root),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            **detach_kwargs,
        )
    except FileNotFoundError:
        return False

    # 40 tries at 0.5s = 20s, up from 10s: a slow or memory-constrained
    # machine can genuinely take longer than 10s for Jupyter to finish
    # starting and register with `jupyter server list`.
    for _ in range(40):
        time.sleep(0.5)
        base_url, _ = find_running_jupyter_server(project_root)
        if base_url is not None:
            return True
    return True


def open_jupyter(config, console, module_name: str, notebook: bool = False, lab: bool = False) -> int:
    """Open a module's notebook in Jupyter, reusing one shared server.

    Every module used to spawn its own `jupyter lab` process rooted in
    that module's own directory, an untracked process per `tren module
    start` that left the CLI with no idea what was still running (see
    deep-dive.md). One server rooted at the project root, reused across
    every module and every `%tren` call inside it, replaces that: the
    terminal is only needed once, to bring the server up.
    """
    try:
        classic_notebook = resolve_jupyter_ui(notebook, lab)
        module_dir = config.project_root / "data" / "modules" / module_name
        if not module_dir.exists():
            console.print(f"[yellow]⚠️  Module directory not found: {module_name}[/yellow]")
            return 1

        short_name = module_name.split("_", 1)[1] if "_" in module_name else module_name
        notebook_path = module_dir / f"{short_name}.ipynb"
        if not notebook_path.exists():
            notebooks = list(module_dir.glob("*.ipynb"))
            notebook_path = notebooks[0] if notebooks else None

        base_url, token = find_running_jupyter_server(config.project_root)
        if base_url is None:
            console.print("[cyan]🚀 Starting a shared Jupyter Lab server...[/cyan]")
            if not start_jupyter_server(config.project_root):
                console.print("[yellow]⚠️  Jupyter Lab not found. Install with:[/yellow]")
                console.print("[dim]pip install jupyterlab[/dim]")
                return 1
            base_url, token = find_running_jupyter_server(config.project_root)
        else:
            console.print("[cyan]🔗 Reusing the already-running Jupyter Lab server...[/cyan]")

        if base_url is None:
            log_path = config.project_root / "user_data" / "jupyter.log"
            console.print("[yellow]⚠️  Jupyter Lab started but its URL couldn't be detected.[/yellow]")
            console.print(f"[dim]Check {log_path} for the URL and token.[/dim]")
            return 1

        # One jupyter_server backend serves both UIs; /tree is the classic
        # Notebook interface (Notebook 7, requires the `notebook` package
        # alongside jupyterlab), /lab/tree is Jupyter Lab. Same running
        # server either way, just a different frontend path.
        ui_path = "tree" if classic_notebook else "lab/tree"
        if notebook_path and notebook_path.exists():
            relative = notebook_path.relative_to(config.project_root)
            url = f"{base_url}{ui_path}/{relative.as_posix()}"
        else:
            url = f"{base_url}{'tree' if classic_notebook else 'lab'}"
        if token:
            url += f"?token={token}"

        webbrowser.open(url)

        ui_name = "Jupyter Notebook" if classic_notebook else "Jupyter Lab"
        console.print(f"[green]✅ Opened in {ui_name}[/green]")
        console.print(f"[dim]If it didn't open automatically: {url}[/dim]")
        console.print()
        module_number = module_name.split("_", 1)[0]
        console.print("[bold]From inside a notebook cell, no need to come back here:[/bold]")
        console.print(f"  [cyan]%tren module complete {module_number}[/cyan]")
        return 0

    except FileNotFoundError:
        console.print("[yellow]⚠️  Jupyter Lab not found. Install with:[/yellow]")
        console.print("[dim]pip install jupyterlab[/dim]")
        return 1


def register_jupyter_magic(config, console) -> None:
    """Scope-load the %tren magic for the 'trentorch' kernel only.

    Points that kernel's IPYTHONDIR at a project-local directory
    (instead of the user's global ~/.ipython) and drops a startup
    script there that registers TrenMagics. Other kernels and other
    IPython sessions on the machine are untouched.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "jupyter", "--data-dir"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        if result.returncode != 0:
            return
        kernel_json_path = Path(result.stdout.strip()) / "kernels" / "trentorch" / "kernel.json"
        if not kernel_json_path.exists():
            return

        ipython_dir = config.project_root / "user_data" / "ipython"
        startup_dir = ipython_dir / "profile_default" / "startup"
        startup_dir.mkdir(parents=True, exist_ok=True)
        (startup_dir / "00-tren-magic.py").write_text(
            "try:\n"
            "    from platforms.cli.jupyter_magic import load_ipython_extension\n"
            "    load_ipython_extension(get_ipython())\n"
            "except Exception:\n"
            "    pass\n",
            encoding="utf-8",
        )

        spec = json.loads(kernel_json_path.read_text(encoding="utf-8"))
        spec.setdefault("env", {})["IPYTHONDIR"] = str(ipython_dir)
        kernel_json_path.write_text(json.dumps(spec, indent=1), encoding="utf-8")

        console.print("[green]✅ %tren magic registered for the 'trentorch' kernel[/green]")
        console.print("[dim]   Run tren commands from inside Jupyter: %tren module complete 01[/dim]")
    except Exception as e:
        console.print(f"[yellow]⚠️  Could not register %tren magic: {e}[/yellow]")
        console.print("[dim]   tren commands still work from the terminal as usual[/dim]")
