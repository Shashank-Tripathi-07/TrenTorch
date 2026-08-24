# TrenTorch: How It Actually Works, From First Principles

*Every claim in this document is sourced from reading the actual code: `bin/tren`, `platforms/cli/main.py`, `platforms/cli/core/*.py`, `platforms/cli/**/*.py`, `pyproject.toml`, `requirements.txt`, and `trentorch/__init__.py`, cross-checked against a real TrenTorch environment on disk (measured directory sizes, not estimates). Where the code has an if/else branch, both branches are described. Where a described feature exists only in an open, unmerged pull request rather than on `dev`, that is stated explicitly, not silently assumed. Written for the upstream `harvard-edge/cs249r_book` repository; TrenTorch inherited the same `tren` source verbatim, so the mechanics below are still accurate to this fork's code. This fork also inherited upstream's `install.sh` (a one-line-curl installer hardcoded to upstream's own hosted URL and repo) and the optional community backend it could talk to; both have since been removed rather than kept pointing at someone else's infrastructure (see [`design.md`](design.md#community-dashboard-and-progress-sync-removed)).*

---

## Part 1: Two Ways To Invoke `tren`

Upstream's one-line-curl installer (`quarto/install.sh`) has been removed from this fork along with the rest of the Quarto-hosted content; it was hardcoded to upstream's own URL and repository and never usable as an install path for TrenTorch itself. Setup here goes through `pip install -r requirements.txt && pip install -e .` (see [`implementation.md`](implementation.md#prerequisites)) instead.

There are two entry points into the resulting code, and they resolve `sys.path` differently:

```text
Path A: the installed console script (created by `pip install -e .`)
────────────────────────────────────────────────────────────────────
  .venv/Scripts/tren.exe   (Windows)   or   .venv/bin/tren   (Unix)
        │
        │  This is a tiny compiled/generated launcher that pip creates
        │  from the `[project.scripts] tren = "platforms.cli.main:main"` entry in
        │  pyproject.toml. It only exists once `pip install -e .` has run,
        │  and only works once the venv is activated (or its Scripts/bin
        │  directory is on PATH).
        ▼
  platforms.cli.main:main()

Path B: bin/tren (a plain Python script, no pip install required)
────────────────────────────────────────────────────────────────────
  python bin/tren <command>
        │
        │  Explicitly computes trentorch_root from its own file location
        │  (two directories up from bin/tren), inserts it at the FRONT
        │  of sys.path, and os.chdir()'s into it before importing
        │  anything, so `Path.cwd()`-based logic throughout the CLI
        │  behaves correctly regardless of where the script was invoked
        │  from. This exists for CI and for anyone who doesn't want an
        │  editable pip install at all.
        ▼
  platforms.cli.main:main()      (same function, same code, either way)
```

Both paths converge on the exact same `main()`, the difference is only in how `sys.path` and the working directory get set up before that function runs.

---

## Part 2: What Happens Every Single Time You Type `tren ...`

Before any subcommand's own logic runs, `platforms/cli/main.py`'s `TrenTorchCLI` does the same fixed sequence, every time, regardless of which command was typed.

```text
                          $ tren module start 01
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│ 1. Windows encoding fix (module import time, before anything else)     │
│    if sys.platform == "win32": reconfigure stdout/stderr to UTF-8.     │
│    Without this, the emoji this CLI prints everywhere (✅❌🔥) raises   │
│    an unhandled UnicodeEncodeError and crashes with a raw traceback    │
│    on most Windows terminals, since the interpreter's default stream   │
│    encoding there is a legacy codepage (e.g. cp1252), not UTF-8.       │
└───────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│ 2. TrenTorchCLI() constructed                                          │
│    - CLIConfig.from_project_root(): walks UP from cwd looking for a    │
│      pyproject.toml to decide where "the project" is. If none is       │
│      found anywhere up the tree, falls back to plain cwd.              │
│    - Registers 9 command classes into one dict (main.py's own          │
│      comment calls this the "SINGLE SOURCE OF TRUTH"): setup, system,  │
│      module, dev, package, milestone, benchmark, olympics, convert.    │
└───────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│ 3. create_parser(), and this is a detail worth knowing:                │
│    argparse subparsers are built for ALL TEN command groups on EVERY   │
│    invocation, not just the one you're running. Every group's own      │
│    add_arguments() executes regardless of which subcommand you typed.  │
│    (Practical consequence: if one command group's argument-parsing     │
│    code were ever slow or broken, it would affect every tren command,  │
│    not just its own.)                                                  │
└───────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│ 4. Virtual-environment guard                                            │
│                                                                          │
│    if command not in ['setup', None]:                                  │
│        in_venv = (sys.prefix != sys.base_prefix)                       │
│                    OR  os.environ.get("VIRTUAL_ENV") is not None       │
│        if not in_venv and TITO_ALLOW_SYSTEM != "1":                    │
│            print_error(...); return 1                                  │
│                                                                          │
│    Every command except `setup` (and no command at all) REFUSES to run │
│    outside an activated venv. This is deliberate: it's the thing that  │
│    stops a student from accidentally running against their system      │
│    Python and getting confusing version-mismatch errors. The escape    │
│    hatch is TITO_ALLOW_SYSTEM=1, meant for CI containers that already  │
│    manage their own isolation.                                         │
└───────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│ 5. Banner + first-run welcome                                           │
│    print_banner() unless --no-color or the command is JSON-output-     │
│    only (--json, or `module path`). First run ever (detected by        │
│    user_data/ not existing yet) also shows a one-time "each notebook is    │
│    stub-only, no solutions included" welcome panel, then creates       │
│    .tren/ just to mark that the welcome was shown, so it never shows   │
│    again.                                                              │
└───────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│ 6. Environment validation (skipped for `system health`, which exists    │
│    specifically to diagnose a broken environment: it can't refuse to  │
│    run just because the environment looks broken)                      │
│    Checks: Python version, venv-active-ness (again, more thoroughly),  │
│    src/ directory exists, and that numpy/rich/yaml/pytest/jupytext all  │
│    import successfully. Currently NON-FATAL: issues are printed, but   │
│    the command proceeds anyway (there's a comment in the code marking  │
│    this permissive behavior as temporary/for development).             │
└───────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│ 7. Dispatch to the actual command class's execute(parsed_args). This    │
│    is where `module start 01`'s own logic finally begins (Part 3).     │
└───────────────────────────────────────────────────────────────────────┘
```

None of steps 1–6 touch the network or spawn a subprocess. They're all local: reading env vars, walking the filesystem for `pyproject.toml`, importing already-installed packages. The first point at which *anything* leaves the machine or spawns a new OS process depends entirely on which subcommand you ran.

---

## Part 3: The Core Student Loop, `start` → edit → `complete`

This is the loop a student repeats 20 times (once per module). Each module is independent curriculum content (a tensor library, then activations, then layers...), but the *mechanics* of starting and completing one are identical every time.

### 3.1 Module identity: there is no hardcoded module list

`platforms/cli/core/modules.py`'s `_discover_modules()` scans `src/` at runtime for directories matching the regex `^(\d{2})_(\w+)$` and builds the number→folder mapping from whatever it finds, cached with `@lru_cache`. **Nothing enumerates "there are 20 modules" as a constant anywhere in this discovery path.** If a 21st `src/21_whatever/` directory existed, it would simply appear. (Other parts of the codebase, like the milestone system's `PRIMARY_EXPORT_LABELS` dict, do hardcode 01-20 as display labels; that's a separate, static lookup table, not the module registry itself.)

### 3.2 `tren module start 01`, full decision tree

```text
                    tren module start 01
                            │
                            ▼
              normalize "01" -> "01"  (already 2-digit)
                            │
                            ▼
              "01" in module_mapping (from src/ discovery)?
                    │                           │
                   NO                          YES
                    │                           │
          ❌ "Module 01 not found"              ▼
          + list available range      is_module_started("01")?
                                        (checks .tren/progress.json's
                                         started_modules list, a JSON
                                         file, NOT a filesystem check,
                                         and this matters: see below)
                                          │                    │
                                         YES                   NO
                                          │                    │
                              ⚠️ "already started"      (fresh module,
                              -> suggests `resume`       falls through to
                              -> return 1, STOP HERE.    the prerequisite
                              This fires regardless of   check below)
                              whether data/modules/01_tensor/
                              actually still exists on
                              disk or not (see below).

              Prerequisite check (module_num > 1 only):
              for every i in 1..module_num-1:
                  is f"{i:02d}" in completed_modules?
                            │                    │
                        ALL YES               ANY NO
                            │                    │
                    (continue)          🔒 "Module N is locked"
                                         + table of missing
                                           prerequisites
                                         + "Complete modules in
                                           order", return 1
                            │
                            ▼
              data/modules/01_tensor/ exists on disk?
                    │                        │
                   YES                      NO
                    │                        │
              (skip creation,      src/01_tensor/ exists?
               go straight to            │           │
               success panel)          YES          NO
                                          │            │
                              _create_module_from_src()  ❌ "Source not
                              -> convert_py_to_notebook()   found", return 1
                              -> spawns a REAL SUBPROCESS:
                                 jupytext --to ipynb
                                   src/01_tensor/01_tensor.py
                                   --output data/modules/01_tensor/tensor.ipynb
                              (this is CPU + disk work: jupytext parses
                               the percent-format .py file and writes a
                               real .ipynb JSON file, typically well
                               under a second for a single module)
                                          │
                                          ▼
                            validate_notebook_integrity() on the
                            result, checks "cells" key exists and
                            is a list, counts code vs markdown cells
                                          │
                                          ▼
                            mark_module_started("01")
                            -> writes .tren/progress.json
                            (disk write, a few hundred bytes)
                                          │
                                          ▼
                            Success panel + milestone-proximity hint
                            ("0 modules until unlock" if relevant)
                                          │
                            ┌─────────────┴─────────────┐
                            │                            │
                     --no-jupyter flag?              (no flag)
                            │                            │
                     print "ready (notebook       open_jupyter():
                     created)" and STOP HERE.      finds the one shared
                     Nothing further runs.          server via `jupyter
                     (This is what CI/testing       server list` (jupyter
                     uses; the flag exists          commands/jupyter.py),
                     specifically so automation     reuses it if already
                     never launches a real          running, otherwise
                     Jupyter server.)                spawns exactly one,
                                                     detached, rooted at
                                                     the project root, then
                                                     opens this module's
                                                     notebook in it.
```

**A currently-real dead end worth naming precisely.** `started_modules` in `.tren/progress.json` and the actual notebook on disk under `data/modules/` are two independently-maintained facts, and nothing keeps them in sync. `tren system reset --keep-progress` is a documented command that deliberately clears `data/modules/` while intentionally leaving `started_modules` untouched. Hit that combination (or lose `data/modules/` some other way, e.g. a partial restore from backup) and `tren module start N` will refuse forever with "already started," pointing at `tren module resume N`. Resume, in turn, accepts (tracking says started) and only discovers the notebook is missing deep inside `open_jupyter` (`tren/commands/jupyter.py`), failing with "Module directory not found" and no further guidance. Neither command's own error message mentions the actual fix, `tren module reset N --force`, which does work. A pull request fixing exactly this (both commands checking whether the notebook genuinely exists before trusting the tracking flag, and recreating it from `src/` when it doesn't) is open at the time of writing (harvard-edge/cs249r_book#2026), not yet merged.

### 3.3 Jupyter server lifecycle: one shared server, not one per launch

This used to be a real gap: every `tren module start/resume/view` call spawned a brand-new `jupyter lab` subprocess with no tracking, so five calls in one session meant five separate servers, none of which `tren` would ever stop. Fixed 2026-08-23: `tren/commands/jupyter.py`'s `find_running_jupyter_server()` reads live state from `jupyter server list` (not a PID `tren` tracks itself, so it self-heals if the server was closed outside `tren`'s control) and `open_jupyter()` reuses that server if one is already rooted at the project root, only calling `start_jupyter_server()` to spawn one when none exists. The same file also owns `resolve_jupyter_ui()` (the Notebook-or-Lab prompt) and `register_jupyter_magic()` (scoping the `%tren` magic to the `tinytorch` kernel, called from `tren setup`) — the whole Jupyter component's process logic lives in this one file rather than being split across `module/workflow.py`, `commands/setup.py`, and `jupyter_magic.py` the way it originally grew.

### 3.4 What Jupyter Lab actually costs, once it's running

Once `jupyter lab` is up, it's a real local web server: it binds a TCP port (8888 by default, and every additional untracked instance from 3.3 binds the next free one), runs a Python kernel process per open notebook (a second Python process, separate from the `tren` process that launched it), and serves a JavaScript frontend over HTTP to whatever browser tab it opens. This is the only point in the entire student workflow where a long-lived network listener exists on the machine, every other `tren` command starts, does its work, and exits.

---

## Part 4: `tren module complete`, The Four-Step Pipeline

This is the command that actually turns a student's edited notebook into working, importable code. It is the single most consequential command in the whole system, and it is **not** the same thing as `tren module test` (that only runs Step 1 and never touches the package).

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Pre-check: sequential completion                                       │
│                                                                          │
│   if module_num > 1 and f"{module_num-1:02d}" not in completed_modules: │
│       ❌ "You must complete module {prev} first", return 1            │
│                                                                          │
│   This is a SEPARATE, STRICTER gate than `module start`'s prerequisite  │
│   check. `start` only requires prior modules be complete to START a    │
│   later one; `complete` re-checks the immediately-preceding module      │
│   specifically, every single time, even if you already passed the      │
│   gate once when you started this module.                              │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ STEP 1/4: Unit Tests            [subprocess, CPU-bound]                 │
│                                                                          │
│   subprocess.run([sys.executable, "src/01_tensor/01_tensor.py"])       │
│                                                                          │
│   This runs the INSTRUCTOR's src/ file directly as a script, not the   │
│   student's notebook. The src/ file has an `if __name__ == "__main__"` │
│   block containing the same tests a student's implementation must      │
│   pass; running the plain .py file means this step needs no jupytext   │
│   conversion and no exported package, it's the fastest possible      │
│   feedback loop. PYTHONPATH is set to include project_root so the      │
│   script can import trentorch.core.* (from anything ALREADY exported   │
│   by earlier modules). If this step fails: STOP. Nothing past this     │
│   point runs.                                                          │
└────────────────────────────────────────────────────────────────────────┘
                                    │ (only if not --skip-tests)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ STEP 1.5: Notebook syntax check   [pure Python, in-process, no subprocess]│
│                                                                          │
│   Reads data/modules/01_tensor/tensor.ipynb as JSON, and for every code      │
│   cell, strips IPython magics (%...) and shell escapes (!...), then     │
│   compile(code, ..., "exec"), WITHOUT executing it, just compiling.  │
│                                                                          │
│   Why this exists as a separate step from Step 1: Step 1 tests the     │
│   INSTRUCTOR's src/ file. This step is the first and only point that   │
│   actually looks at the STUDENT'S notebook before export. Without it,  │
│   a syntax error the student introduced in their notebook (but not in  │
│   src/, since they're different files) would slip straight through to  │
│   a broken export with no clear error message pointing at the cause.   │
└────────────────────────────────────────────────────────────────────────┘
                                    │ (only if not --skip-export)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ STEP 2/4: Export to package     [in-process function call, disk I/O,   │
│                                   real code generation]                 │
│                                                                          │
│   from nbdev.export import nb_export                                    │
│   nb_export(data/modules/01_tensor/tensor.ipynb, lib_path=trentorch/)        │
│                                                                          │
│   nbdev reads the notebook's cells looking for `#| export` markers      │
│   (present in every code cell the student is meant to keep) and the    │
│   `#| default_exp core.tensor` directive at the top of the source, and  │
│   writes trentorch/core/tensor.py, REAL PYTHON SOURCE, generated      │
│   fresh from the notebook's cell contents, not a copy of anything.      │
│                                                                          │
│   Verification (not part of nbdev itself, added on top): confirms the  │
│   target file now exists, and that it has more than one non-comment,   │
│   non-blank line, catching the case where a notebook technically has │
│   #| export cells, but they're empty or all-comments, which would      │
│   otherwise produce a "successful" export of nothing.                  │
└────────────────────────────────────────────────────────────────────────┘
                                    │ (only if not --skip-tests, and Step 2 succeeded)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ STEP 3/4: Integration Tests     [subprocess: pytest]                    │
│                                                                          │
│   subprocess.run([sys.executable, "-m", "pytest",                       │
│                    "tests/01_tensor/test_01_tensor_progressive.py",     │
│                    "-v", "--tb=short"])                                 │
│                                                                          │
│   This is the FIRST point in the whole pipeline that imports FROM       │
│   THE REAL, JUST-EXPORTED trentorch.core.tensor, Steps 1 and 1.5      │
│   never touch the package at all. Deliberately ordered AFTER export     │
│   (comment in the code is explicit about this): these tests exist to   │
│   prove the exported package actually works, not just that the         │
│   instructor's reference script does.                                  │
│                                                                          │
│   pytest itself triggers conftest.py's pytest_configure hook FIRST      │
│   (Part 7), which can independently abort the whole test session      │
│   before a single test runs, if the package export state looks broken. │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ STEP 4/4: Progress tracking      [disk write, JSON]                     │
│                                                                          │
│   update_progress("01", "01_tensor") -> .tren/progress.json gains       │
│   "01" in completed_modules, plus a completion timestamp.               │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Milestone unlock check           [disk read + write, no subprocess]     │
│                                                                          │
│   For every milestone not already unlocked/completed, checks whether   │
│   its full set of required module numbers is now a subset of           │
│   completed_modules. If a NEW milestone becomes runnable as a direct    │
│   result of THIS module completing, prints a distinct panel: "Milestone│
│   ready to run" with the exact `tren milestone run NN` command.         │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Progress sync offer              [conditional network call, see Part 6] │
│                                                                          │
│   auto_sync_after_completion(), the single shared decision point for  │
│   whether an HTTP request leaves the machine right now.                 │
└────────────────────────────────────────────────────────────────────────┘
```

If *any* of Steps 1, 1.5, 2, or 3 fails, `complete_module` returns immediately with exit code 1. Step 4 (and everything after it) never runs on a failed module, `completed_modules` in the tracking file only ever gains an entry after all four steps genuinely pass.

---

## Part 5: The Two Conversions Students Confuse (and Why They're Different Tools)

There are exactly two file-format conversions in this whole system, and they run at different times, use different libraries, and go in different directions:

```text
┌──────────────────────────────────────────────────────────────────┐
│  CONVERSION A: jupytext (src/*.py  ->  data/modules/*.ipynb)            │
│  ─────────────────────────────────────────────────────────────    │
│  WHEN:    tren module start N   (only if the notebook doesn't      │
│           already exist)                                           │
│  RUNS AS: an external subprocess (jupytext --to ipynb ...)         │
│  READS:   the INSTRUCTOR's src/NN_name/NN_name.py                  │
│  WRITES:  data/modules/NN_name/name.ipynb , the file the student      │
│           actually opens and edits in Jupyter                       │
│  PURPOSE: turn plain "percent-format" Python (# %% cell markers)   │
│           into a real, openable .ipynb notebook, ONCE, so the      │
│           student has something to work in.                        │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  CONVERSION B: nbdev (data/modules/*.ipynb  ->  trentorch/**/*.py)       │
│  ─────────────────────────────────────────────────────────────    │
│  WHEN:    tren module complete N   (every single time, not just    │
│           once)                                                     │
│  RUNS AS: an in-process Python function call (nb_export)           │
│  READS:   the STUDENT's edited data/modules/NN_name/name.ipynb          │
│  WRITES:  trentorch/core/name.py (or perf/, or olympics/),  the  │
│           real Python package a student can `import trentorch`     │
│  PURPOSE: turn the student's notebook cells marked `#| export`     │
│           into a real, importable module, EVERY time they complete │
│           the module (so re-running `complete` after a fix         │
│           legitimately re-generates the package file).             │
└──────────────────────────────────────────────────────────────────┘
```

Confusing these two is exactly the mistake the docs call out explicitly: `tren module test N` alone never runs Conversion B, only `tren module complete N` does. A student who tests repeatedly but never runs `complete` never actually gets their work into `trentorch/`.

There is a **third**, separate export path, `tren dev export`, that a developer/maintainer uses to rebuild the *entire curriculum* by running Conversion A for every module (overwriting student notebooks, which `module start`'s version deliberately never does) and then Conversion B for every module. This is explicitly a maintainer tool, not part of the student loop.

---

## Part 6: The Only Network Calls in the Whole System

Every place in the codebase that makes an outbound network request, and exactly what triggers it:

```text
┌────────────────────┬──────────────────────────────┬───────────────────────────────┐
│ Trigger             │ What it calls                │ What happens if it fails       │
├────────────────────┼──────────────────────────────┼───────────────────────────────┤
│ install.sh startup  │ GitHub tags API (version)    │ Falls back to fetching         │
│                      │                               │ pyproject.toml raw, then to    │
│                      │                               │ "latest" as a plain string,  │
│                      │                               │ install still proceeds.        │
├────────────────────┼──────────────────────────────┼───────────────────────────────┤
│ install.sh do_install│ git clone (the actual        │ HARD FAILURE. Install cannot   │
│                      │ download)                    │ proceed without this.          │
├────────────────────┼──────────────────────────────┼───────────────────────────────┤
│ tren system update   │ GitHub tags API + a second    │ Clear "could not check         │
│ --check / update     │ sparse git clone (same         │ updates" message; nothing on   │
│                      │ mechanism as install.sh)       │ disk changes.                  │
└────────────────────┴──────────────────────────────┴───────────────────────────────┘
```

**Every module in the normal 20-module student loop is 100% offline.** This fork previously had an optional `tren community login` / progress-sync path (a browser-based login plus a POST to a hosted backend after completing a module or milestone); it talked to the original TrenTorch project's own infrastructure, was never usable from this fork, and has since been removed along with the rest of the community/docs-site code (see [`design.md`](design.md#community-dashboard-and-progress-sync-removed)). The table above no longer includes it.

---

## Part 7: The Test Gatekeeper, Why `conftest.py` Exists At All

This is the single most important defensive mechanism in the whole codebase, and it exists because of a specific, structural danger in how `trentorch/__init__.py` is written:

```python
try:
    from .core.tensor import Tensor
except ImportError:
    Tensor = None
```text

Every one of the 20 module imports in `trentorch/__init__.py` follows this exact pattern. It has to: a student who has only completed 3 of 20 modules needs `import trentorch` to work at all, not crash because module 15 doesn't exist yet. But the cost of that design is real: **if a module's export is broken or missing, `Tensor` silently becomes `None` instead of raising an error.** A test that does `assert Tensor is not None` correctly catches this, but a test that does something like `x = Tensor([1,2,3])` when `Tensor` is `None` raises a plain `TypeError: 'NoneType' object is not callable`, which is a confusing failure that doesn't point at the real cause. Worse, a badly-written test that doesn't actually exercise the imported symbol can pass vacuously while testing nothing.

`tests/conftest.py`'s `pytest_configure` hook runs **before any test in the whole suite**. As of the current `dev` branch, here is exactly what it checks, no more and no less:

```
┌─────────────────────────────────────────────────────────────────┐
│ Check 1: do these four specific files exist?                      │
│   trentorch/core/tensor.py                                        │
│   trentorch/core/activations.py                                   │
│   trentorch/core/layers.py                                        │
│   trentorch/core/losses.py                                        │
│                                                                     │
│ Check 2: `from trentorch import Tensor`, is Tensor None?            │
│                                                                     │
│ Check 3: is Tensor actually instantiable, not just importable?     │
│   t = Tensor([1, 2, 3])                                            │
│   does it have a .data attribute? a .shape attribute?              │
│                                                                     │
│ Any single failure across all three checks -> pytest.UsageError,   │
│ which aborts the ENTIRE pytest session immediately, before a       │
│ single test runs, printing the exact `tren dev export --all` fix. │
└─────────────────────────────────────────────────────────────────┘
```text

**This only ever checks modules 01-04.** Modules 05 through 20 are not examined by this gate at all right now, hard or soft. A broken or missing export in, say, module 12 (Attention) is invisible to this specific check; whatever silent-`None` failure it's meant to guard against for module 12 would have to be caught by that module's own tests, if they happen to exercise the right symbol directly.

An open, unmerged pull request (harvard-edge/cs249r_book#2023) proposes replacing this with a full 20-module registry and a two-tier hard/soft strategy (foundational modules 01-04 still hard-fail; modules 05-20 would get a non-blocking stderr warning instead of no check at all). That is a real, reviewed, but not-yet-merged change, described here so it isn't confused with what's actually running today.

This can be bypassed entirely with `TRENTORCH_SKIP_EXPORT_CHECK=1`, used by the codebase's own test suite so that testing other things doesn't trigger this gate recursively.

---

## Part 8: Hardware and Resource Usage, Command by Command

A direct answer to "what actually uses CPU/memory/disk/network," per command family:

```
┌────────────────────────┬──────┬────────┬─────────┬──────────────────────────┐
│ Command                │ CPU  │ Disk   │ Network │ Notes                     │
├────────────────────────┼──────┼────────┼─────────┼──────────────────────────┤
│ tren system info/health│ low  │ read   │ none    │ pure introspection        │
│ tren module status/list│ low  │ read   │ none    │ reads .tren/progress.json │
│ tren module start N    │ low- │ write  │ none    │ jupytext subprocess only  │
│                         │ med  │ (few   │         │ if notebook doesn't exist │
│                         │      │ KB-MB) │         │ yet; typically <1s        │
│ tren module start      │ low  │ +port  │ none    │ spawns a real, LONG-LIVED │
│  (without --no-jupyter)│      │ bind   │         │ jupyter lab subprocess +  │
│                         │      │        │         │ a browser tab; keeps      │
│                         │      │        │         │ running after tren exits  │
│ tren module test N     │ low- │ read   │ none    │ 2 subprocesses (python    │
│                         │ med  │        │         │ script, then pytest)      │
│ tren module complete N │ med  │ read + │ 0 or 1  │ up to 3 subprocesses      │
│                         │      │ write  │ HTTP    │ (unit test script,        │
│                         │      │ (new   │ POST    │ pytest) + 1 in-process    │
│                         │      │ .py    │         │ nbdev export + an         │
│                         │      │ file)  │         │ OPTIONAL sync POST        │
│                         │      │        │         │ (only if logged in)       │
│ tren dev test --all     │ high │ read + │ none    │ exports + tests EVERY     │
│                         │      │ write  │         │ module in sequence;       │
│                         │      │ (all   │         │ genuinely the heaviest    │
│                         │      │ 20)    │         │ single local operation    │
│ tren package nbdev      │ high │ read + │ none    │ re-EXECUTES every         │
│  --test                 │      │ write  │         │ notebook's cells as real  │
│                         │      │        │         │ Jupyter kernels, the    │
│                         │      │        │         │ most CPU-intensive        │
│                         │      │        │         │ single command in the     │
│                         │      │        │         │ system                    │
│ tren benchmark baseline │ med  │ write  │ none    │ real numpy tensor ops,    │
│                         │      │ (JSON  │         │ timed on the actual CPU,  │
│                         │      │ result)│         │ not simulated             │
└────────────────────────┴──────┴────────┴─────────┴──────────────────────────┘
```text

Nothing in this system uses a GPU. `numpy` is the only numerical dependency (`requirements.txt`), and every tensor operation a student implements runs on the CPU via NumPy's own (typically multi-threaded, BLAS-backed) array operations, the CPU cost scales with whatever NumPy operations a student's own code calls, not anything TrenTorch adds on top.

---

## Part 9: Full If/Else Catalog, Every Environmental Branch That Changes Behavior

Consolidating every conditional branch surfaced across Parts 1–8 that depends on the *environment* rather than user choice:

```
┌───────────────────────────────┬───────────────────────────────────────────┐
│ Condition                     │ What changes                                │
├───────────────────────────────┼───────────────────────────────────────────┤
│ Windows vs. Unix (sys.platform)│ - stdout/stderr forced to UTF-8 on Windows │
│                                │ - venv bin dir: Scripts/ vs bin/           │
│                                │ - `make` is often absent on Windows        │
│                                │   (dev build/dev clean fail with a clear   │
│                                │   "install make" message rather than a     │
│                                │   raw FileNotFoundError)                   │
├───────────────────────────────┼───────────────────────────────────────────┤
│ Inside a venv vs. not          │ Every command except `setup` refuses to    │
│                                │ run at all (Part 2, step 4), unless        │
│                                │ TITO_ALLOW_SYSTEM=1                        │
├───────────────────────────────┼───────────────────────────────────────────┤
│ CI vs. interactive vs. neither │ Three-way, not two-way (Part 6.1): CI      │
│ (is_ci() / is_interactive())   │ never syncs; interactive asks first;       │
│                                │ logged-in-but-non-TTY syncs WITHOUT asking │
├───────────────────────────────┼───────────────────────────────────────────┤
│ jupyter/jupyterlab installed?  │ `tren system jupyter` and `open_jupyter`   │
│                                │ fail cleanly with an install hint if the   │
│                                │ `jupyter` binary isn't resolvable on PATH  │
│                                │ (this can happen even when the Python      │
│                                │ PACKAGES are installed, if the venv's      │
│                                │ Scripts/bin directory isn't on PATH for    │
│                                │ whatever process is invoking tren)         │
├───────────────────────────────┼───────────────────────────────────────────┤
│ Module tracking vs. disk       │ started_modules/completed_modules in       │
│ desync                         │ .tren/progress.json can go out of sync     │
│                                │ with data/modules/ on disk (e.g. `tren system   │
│                                │ reset --keep-progress` intentionally       │
│                                │ clears one but not the other). On `dev`    │
│                                │ right now, `start` and `resume` both       │
│                                │ dead-end on "already started" / "directory │
│                                │ not found" with no escape (Part 3.3); a    │
│                                │ fix is open, unmerged (PR #2026).          │
├───────────────────────────────┼───────────────────────────────────────────┤
│ Module export missing/broken   │ conftest.py (Part 7) hard-fails the whole  │
│                                │ test session, but only checks modules      │
│                                │ 01-04 right now; 05-20 aren't covered      │
│                                │ (unmerged PR extends this to all 20)       │
├───────────────────────────────┼───────────────────────────────────────────┤
│ Sequential completion gate     │ `module start` only checks prerequisites   │
│                                │ once, when starting; `module complete`     │
│                                │ RE-CHECKS the immediately-prior module     │
│                                │ every time, independently                  │
├───────────────────────────────┼───────────────────────────────────────────┤
│ WSL vs. native                 │ auth.py's local callback server detects    │
│                                │ WSL via /proc/version and swaps in the     │
│                                │ actual WSL IP (via `hostname -I`) for the  │
│                                │ OAuth redirect URL, since Windows' browser │
│                                │ can't reach WSL's normal 127.0.0.1         │
└───────────────────────────────┴───────────────────────────────────────────┘
```text

---

## Part 10: Full End-to-End Sequence, Start to Finish

Tying every part above into one linear trace, from a user's very first keystroke to a completed course:

```
 USER                          MACHINE                          NETWORK
  │                               │                                 │
  │ git clone && cd trentorch     │                                 │
  │ python -m venv .venv          │                                 │
  │ pip install -r requirements.txt │                               │
  │ pip install -e .              │                                 │
  ├──────────────────────────────>│  [~300 MB now on disk]          │
  │                               │                                 │
  │ activate .venv                │                                 │
  │ tren setup                    │                                 │
  ├──────────────────────────────>│  venv guard PASSES (activated)  │
  │                               │  create profile, verify env      │
  │                               │                                 │
  │ tren module start 01          │                                 │
  ├──────────────────────────────>│  01 not started, no prereqs      │
  │                               │  needed (module 1)               │
  │                               │  notebook doesn't exist →         │
  │                               │  jupytext subprocess writes       │
  │                               │  data/modules/01_tensor/tensor.ipynb  │
  │                               │  mark_module_started("01")       │
  │                               │  spawn jupyter lab (untracked,   │
  │                               │  Part 3.3) ──────────────────────│  binds :8888,
  │                               │                                 │  opens browser
  │ [edits notebook in browser]   │                                 │
  │                               │                                 │
  │ tren module complete 01       │                                 │
  ├──────────────────────────────>│  Step 1: run src/01_tensor.py    │
  │                               │  as subprocess (tests instructor │
  │                               │  reference, not student code)    │
  │                               │  Step 1.5: compile() every code  │
  │                               │  cell in the STUDENT's notebook  │
  │                               │  Step 2: nb_export(), writes   │
  │                               │  REAL trentorch/core/tensor.py   │
  │                               │  from the student's cells        │
  │                               │  Step 3: pytest against the      │
  │                               │  JUST-EXPORTED package           │
  │                               │  (conftest.py's gatekeeper runs  │
  │                               │  first, Part 7)                  │
  │                               │  Step 4: completed_modules       │
  │                               │  gains "01"                      │
  │                               │  milestone-unlock check           │
  │                               │                                 │
  │  [... repeat for modules      │                                 │
  │      02 through 20 ...]       │                                 │
  │                               │                                 │
  │ tren milestone run 01         │                                 │
  ├──────────────────────────────>│  prereqs met (from completed set)│
  │                               │  subprocess.run() the actual      │
  │                               │  milestone Python script,         │
  │                               │  importing student's REAL, now-  │
  │                               │  exported trentorch package       │
  │                               │  update .tren/milestones.json    │
  │                               │                                 │
  │ [after module 20 completes]   │                                 │
  │                               │  20/20 completed, all 6           │
  │                               │  milestones unlockable            │
  │                               │  student now has a real,          │
  │                               │  importable `trentorch` package,  │
  │                               │  built entirely from their own    │
  │                               │  code, entirely on their own      │
  │                               │  CPU, with zero network calls     │
  │                               │  required at any point            │
```text

---

## Summary: The One-Sentence Version of Every Part

1. **Install**: a single Bash script does a sparse, blob-filtered, shallow git clone of one subdirectory of a monorepo, then builds a venv and pip-installs into it, nothing else is downloaded, and every network/subprocess step has an explicit timeout after a real prior bug where one didn't.
2. **Every `tren` invocation**: fixes Windows encoding, resolves the project root by walking up for `pyproject.toml`, builds argument parsers for all 10 command groups regardless of which one you're using, refuses to run outside a venv (except `setup`), then dispatches.
3. **`module start`**: checks tracking state, self-heals if that state has desynced from the actual files on disk, checks prerequisites, converts `src/*.py` to a notebook via a real `jupytext` subprocess if one doesn't exist, and optionally spawns a real, currently-untracked, long-lived `jupyter lab` server.
4. **`module complete`**: a strict four-step pipeline (instructor-reference unit tests, notebook syntax check, real `nbdev` export of the student's own cells into a real Python file, then pytest against that just-exported package) where any failure stops everything before progress is ever recorded.
5. **Two separate conversions** exist and are easy to confuse: `jupytext` runs once, source→notebook, at `start` time; `nbdev` runs every time, notebook→package, at `complete` time.
6. **Network calls are rare and optional**: an optional update check is the only one left, the entire 20-module curriculum works completely offline.
7. **The test gatekeeper exists because of a specific danger**: `trentorch/__init__.py`'s `try/except ImportError: X = None` pattern means a broken export can silently become `None` instead of an error, so `conftest.py` hard-fails the whole test session if the four foundational modules aren't properly exported before any test runs; modules 05-20 aren't covered by this check yet (a fix that would extend it to all 20 is open, unmerged).
8. **No GPU is used anywhere**; every operation is either pure Python/JSON bookkeeping, a subprocess (`jupytext`, `pytest`, a plain `python` script, `jupyter lab`), or NumPy math on the CPU.
