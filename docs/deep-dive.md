# TinyTorch: How It Actually Works, From First Principles

*Every claim in this document is sourced from reading the actual code: `quarto/install.sh`, `bin/tren`, `tren/main.py`, `tren/core/*.py`, `tren/commands/**/*.py`, `pyproject.toml`, `requirements.txt`, and `tinytorch/__init__.py`, cross-checked against a real, install.sh-created TinyTorch environment on disk (measured directory sizes, not estimates). Where the code has an if/else branch, both branches are described. Where a described feature exists only in an open, unmerged pull request rather than on `dev`, that is stated explicitly, not silently assumed. Written for the upstream `harvard-edge/cs249r_book` repository; TrenTorch inherited the same `install.sh` and `tren` source verbatim, so the mechanics below are still accurate to this fork's code, except that the install URL, the repo it clones, and the community backend it can optionally talk to (Part 6) are still hardcoded to upstream's own infrastructure, not this fork's.*

---

## Part 1: Before Anything Runs, The Install

Nothing about TinyTorch exists on a user's machine until they run one command:

```text
curl -sSL mlsysbook.ai/tinytorch/install.sh | bash
```

This pipes a single Bash script (`quarto/install.sh`, 874 lines) into a shell. Nothing else is downloaded first. The script itself is small (tens of KB); everything else it does is described below, step by step, matching `main()` at the bottom of the file. **This URL is upstream's**; this fork's copy of the script still points at the upstream repository until it's repointed at TrenTorch's own.

### 1.1 Pre-flight checks (before touching the disk)

```text
┌─────────────────────────────────────────────────────────────────┐
│  main()                                                          │
│                                                                   │
│  1. fetch_latest_version()   ── network call to GitHub tags API  │
│  2. print_banner()                                                │
│  3. check_write_permission() ── touch a test file, then delete it│
│  4. check_not_in_venv()      ── warn only, does not block         │
│  5. check_prerequisites()    ── git, Python 3.10+, venv module    │
│  6. check_internet()         ── git ls-remote against the real repo│
│  7. prompt_install_directory()                                    │
│  8. check_existing_directory()                                    │
│  9. show_plan_and_confirm()                                       │
│ 10. do_install()              ── the actual work (Part 1.2)       │
│ 11. print_success_message()                                       │
└─────────────────────────────────────────────────────────────────┘
```

Every one of these steps that touches the network or an external process is wrapped in `run_with_timeout()` (a wrapper around `timeout`/`gtimeout`, or a raw call if neither exists). This exists because of a real, filed bug, [issue #1960](https://github.com/harvard-edge/cs249r_book/issues/1960), where the installer would print `Git OK` and then hang forever with zero output, because a step had no timeout and something in the user's environment blocked silently. Every external call in the script now has an explicit ceiling:

| Step | Timeout | Why this exact bound |
|---|---|---|
| Detecting/validating a Python command | 5s | Windows can silently redirect `python` to a Microsoft Store placeholder that tries to open the Store and never returns |
| Checking GitHub is reachable | 15s | A firewall/VPN that drops packets instead of rejecting them can hang a plain `git ls-remote` indefinitely |
| Cloning the repo | 120s | A shallow, sparse clone of one small folder should take seconds; anything past two minutes means the network is actually broken |
| Creating the venv | 60s | Guards against a corrupted Python's internal `ensurepip` bootstrap hanging |
| Installing pip packages | 600s (10 min) | Generous on purpose: a slow-but-working install should be allowed to finish. What this actually catches is a pip config silently pointing at a private index that waits for credentials nobody can type into a piped `curl \| bash` session |
| Waiting on an interactive prompt | 30s | A `/dev/tty` that exists as a path but never delivers input (some IDE terminals, containers) must not hang forever |

If a step never finishes and hits its ceiling, the script prints a specific, diagnosed error (not a generic timeout message) and exits. It names the *likely cause* (VPN, private pip index, Store alias) rather than just "timed out."

### 1.2 The actual download and setup (`do_install`)

```text
[1/4] Downloading from GitHub...
      │
      │  git clone --depth 1 --filter=blob:none --sparse --branch main \
      │      https://github.com/harvard-edge/cs249r_book.git <tmp>/repo
      │
      │  This is a SPARSE, SHALLOW, BLOB-FILTERED clone: depth 1 means no
      │  git history, --filter=blob:none defers downloading file contents
      │  until sparse-checkout narrows the tree, and --sparse means only
      │  the tinytorch/ subdirectory of the whole monorepo actually lands
      │  on disk. The user never downloads the textbook, the hardware kit
      │  recipes, the labs, or any other sibling project in this repo.
      │
      ▼
      git sparse-checkout set tinytorch
      mv <tmp>/repo/tinytorch  ./tinytorch      (or the user's chosen name)
      rm -rf <tmp>
      │
      │  Then a cleanup pass removes ~20 developer-only paths that a
      │  learner doesn't need: paper/, instructor/, site/, scripts/,
      │  tools/, binder/, .claude/, .cursor/, .vscode/, CONTRIBUTING.md,
      │  INSTRUCTOR.md, .pre-commit-config.yaml, and more (see the
      │  REMOVE list in install.sh, lines 664-693).
      │
      │  modules/ is emptied (populated later by tren, not shipped
      │  pre-built). progress.json and .tren/ are deleted (a student
      │  starts with zero progress, even if the branch being cloned
      │  happens to have stale tracking files in it). tinytorch/core/*.py
      │  is deleted except __init__.py. This is the critical one: the
      │  package a student receives has NO implementations in it yet.
      │  Every core/*.py file the package needs is something the student
      │  will write themselves and export via tren.
      ▼
[2/4] Creating Python environment...
      │
      │  <detected-python> -m venv .venv
      │  source .venv/bin/activate   (or .venv/Scripts/activate on Windows)
      │
      ▼
[3/4] Installing dependencies...
      │
      │  pip install --upgrade pip
      │  pip install -r requirements.txt      (all packages below)
      │  pip install -e .                      (tren itself, editable)
      │
      ▼
[4/4] Verifying installation...
      │
      │  command -v tren   (confirms the entry point resolved on PATH)
      ▼
   done.
```

### 1.3 What's actually on disk afterward, and how big it is

Measured directly on a real installed environment (not estimated):

```text
tinytorch/                                          ~339 MB total (after all
├── .venv/                              ~296 MB     20 modules are built,
│   └── Lib/site-packages/                          a fresh install before
│       ├── debugpy/          31.2 MB                any module work is
│       ├── babel/            30.0 MB                closer to ~300 MB,
│       ├── jupyterlab/       23.5 MB                since .venv dominates)
│       ├── numpy/            22.0 MB
│       ├── numpy.libs/       20.1 MB   <- compiled BLAS/LAPACK, not Python
│       ├── notebook/         15.9 MB
│       ├── jedi/             14.3 MB   <- Jupyter's autocomplete engine
│       ├── pip/               10.8 MB
│       └── ...30+ more packages
├── src/                                 1.6 MB     20 module source files
│   ├── 01_tensor/01_tensor.py                       (the actual curriculum
│   ├── 02_activations/...                            content, this is what
│   └── ... 20_capstone/                              gets sparse-cloned)
├── modules/                             ~0 MB       EMPTY at install time.
│                                                     Populated one directory
│                                                     per module, only when
│                                                     `tren module start N`
│                                                     runs (Part 3).
├── tinytorch/                           ~1 MB       the actual Python
│   ├── core/                                        PACKAGE. At install
│   │   └── __init__.py   (only this file)           time, core/ has nothing
│   └── __init__.py                                  but __init__.py files,
│                                                     no Tensor, no Linear,
│                                                     nothing. Every real
│                                                     class here is written
│                                                     by the student later.
├── tren/                                1.2 MB      the CLI's own source
├── tests/                               3.5 MB       test suites (20 module
│                                                       dirs + shared conftest)
├── datasets/                            0.4 MB      tinydigits, tinytalks
├── milestones/                          0.6 MB      6 historical ML scripts
├── bin/tren                                         a standalone entry
│                                                      point (works without
│                                                      `pip install -e .`,
│                                                      see 1.4)
├── requirements.txt, pyproject.toml, settings.ini
└── README.md, LICENSE
```

The `.venv/` directory alone is roughly **87% of the total install size**. The actual curriculum content a student edits (`src/`) is under 2 MB. This is worth internalizing: almost the entire disk footprint is dependency packages (numpy's compiled math libraries, JupyterLab's web frontend, a debugger), not TinyTorch's own code.

### 1.4 Two ways to invoke `tren` (this matters for understanding "how it runs")

There are two entry points into the exact same code, and they resolve `sys.path` differently:

```text
Path A: the installed console script (created by `pip install -e .`)
────────────────────────────────────────────────────────────────────
  .venv/Scripts/tren.exe   (Windows)   or   .venv/bin/tren   (Unix)
        │
        │  This is a tiny compiled/generated launcher that pip creates
        │  from the `[project.scripts] tren = "tren.main:main"` entry in
        │  pyproject.toml. It only exists once `pip install -e .` has run,
        │  and only works once the venv is activated (or its Scripts/bin
        │  directory is on PATH).
        ▼
  tren.main:main()

Path B: bin/tren (a plain Python script, no pip install required)
────────────────────────────────────────────────────────────────────
  python bin/tren <command>
        │
        │  Explicitly computes tinytorch_root from its own file location
        │  (two directories up from bin/tren), inserts it at the FRONT
        │  of sys.path, and os.chdir()'s into it before importing
        │  anything, so `Path.cwd()`-based logic throughout the CLI
        │  behaves correctly regardless of where the script was invoked
        │  from. This exists for CI and for anyone who doesn't want an
        │  editable pip install at all.
        ▼
  tren.main:main()      (same function, same code, either way)
```

Both paths converge on the exact same `main()`, the difference is only in how `sys.path` and the working directory get set up before that function runs.

---

## Part 2: What Happens Every Single Time You Type `tren ...`

Before any subcommand's own logic runs, `tren/main.py`'s `TinyTorchCLI` does the same fixed sequence, every time, regardless of which command was typed.

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
│ 2. TinyTorchCLI() constructed                                          │
│    - CLIConfig.from_project_root(): walks UP from cwd looking for a    │
│      pyproject.toml to decide where "the project" is. If none is       │
│      found anywhere up the tree, falls back to plain cwd.              │
│    - Registers 10 command classes into one dict (main.py's own         │
│      comment calls this the "SINGLE SOURCE OF TRUTH"): setup, system,  │
│      module, dev, package, nbgrader, milestone, community, benchmark,  │
│      olympics.                                                         │
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
│    .tren/ not existing yet) also shows a one-time "Solutions are        │
│    included, this is intentional" welcome panel, then creates .tren/   │
│    just to mark that the welcome was shown, so it never shows again.  │
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

`tren/core/modules.py`'s `_discover_modules()` scans `src/` at runtime for directories matching the regex `^(\d{2})_(\w+)$` and builds the number→folder mapping from whatever it finds, cached with `@lru_cache`. **Nothing enumerates "there are 20 modules" as a constant anywhere in this discovery path.** If a 21st `src/21_whatever/` directory existed, it would simply appear. (Other parts of the codebase, like the milestone system's `PRIMARY_EXPORT_LABELS` dict, do hardcode 01-20 as display labels; that's a separate, static lookup table, not the module registry itself.)

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
                              whether modules/01_tensor/
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
              modules/01_tensor/ exists on disk?
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
                                   --output modules/01_tensor/tensor.ipynb
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
                     print "ready (notebook       _open_jupyter():
                     created)" and STOP HERE.      subprocess.Popen(
                     Nothing further runs.           ["jupyter", "lab",
                     (This is what CI/testing         "<notebook path>"])
                     uses; the flag exists            a REAL, DETACHED,
                     specifically so automation        LONG-RUNNING PROCESS
                     never launches a real             gets spawned here,
                     Jupyter server.)                  not awaited.
                                                       time.sleep(2) to let
                                                       it bind its port,
                                                       then prints instructions
                                                       and returns 0 whether
                                                       or not the server
                                                       actually came up
                                                       cleanly.
```

**A currently-real dead end worth naming precisely.** `started_modules` in `.tren/progress.json` and the actual notebook on disk under `modules/` are two independently-maintained facts, and nothing keeps them in sync. `tren system reset --keep-progress` is a documented command that deliberately clears `modules/` while intentionally leaving `started_modules` untouched. Hit that combination (or lose `modules/` some other way, e.g. a partial restore from backup) and `tren module start N` will refuse forever with "already started," pointing at `tren module resume N`. Resume, in turn, accepts (tracking says started) and only discovers the notebook is missing deep inside `_open_jupyter`, failing with "Module directory not found" and no further guidance. Neither command's own error message mentions the actual fix, `tren module reset N --force`, which does work. A pull request fixing exactly this (both commands checking whether the notebook genuinely exists before trusting the tracking flag, and recreating it from `src/` when it doesn't) is open at the time of writing (harvard-edge/cs249r_book#2026), not yet merged.

### 3.3 A currently-real gap worth naming precisely: untracked Jupyter processes

As of the current `dev` branch, **`_open_jupyter()` does not track or reuse Jupyter Lab servers it launches.** Every `tren module start`, `tren module resume`, and `tren module view` call that reaches this code path spawns a brand-new `jupyter lab` subprocess via `subprocess.Popen`, with no PID file, no "is one already running" check, and no cleanup. Run `start`/`resume`/`view` five times in one working session and you get five separate Jupyter Lab servers, each holding its own port and consuming its own memory, none of which `tren` will ever stop for you. A fix for exactly this (`_jupyter_pid_file`, `_running_jupyter_pid`, reusing an existing server instead of spawning a new one) exists as an **open, unmerged pull request** (harvard-edge/cs249r_book#2011) at the time of writing. It is not yet part of the behavior described everywhere else in this document, which reflects what's actually on `dev` right now.

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
│   script can import tinytorch.core.* (from anything ALREADY exported   │
│   by earlier modules). If this step fails: STOP. Nothing past this     │
│   point runs.                                                          │
└────────────────────────────────────────────────────────────────────────┘
                                    │ (only if not --skip-tests)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ STEP 1.5: Notebook syntax check   [pure Python, in-process, no subprocess]│
│                                                                          │
│   Reads modules/01_tensor/tensor.ipynb as JSON, and for every code      │
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
│   nb_export(modules/01_tensor/tensor.ipynb, lib_path=tinytorch/)        │
│                                                                          │
│   nbdev reads the notebook's cells looking for `#| export` markers      │
│   (present in every code cell the student is meant to keep) and the    │
│   `#| default_exp core.tensor` directive at the top of the source, and  │
│   writes tinytorch/core/tensor.py, REAL PYTHON SOURCE, generated      │
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
│   THE REAL, JUST-EXPORTED tinytorch.core.tensor, Steps 1 and 1.5      │
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
│  CONVERSION A: jupytext (src/*.py  ->  modules/*.ipynb)            │
│  ─────────────────────────────────────────────────────────────    │
│  WHEN:    tren module start N   (only if the notebook doesn't      │
│           already exist)                                           │
│  RUNS AS: an external subprocess (jupytext --to ipynb ...)         │
│  READS:   the INSTRUCTOR's src/NN_name/NN_name.py                  │
│  WRITES:  modules/NN_name/name.ipynb , the file the student      │
│           actually opens and edits in Jupyter                       │
│  PURPOSE: turn plain "percent-format" Python (# %% cell markers)   │
│           into a real, openable .ipynb notebook, ONCE, so the      │
│           student has something to work in.                        │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  CONVERSION B: nbdev (modules/*.ipynb  ->  tinytorch/**/*.py)       │
│  ─────────────────────────────────────────────────────────────    │
│  WHEN:    tren module complete N   (every single time, not just    │
│           once)                                                     │
│  RUNS AS: an in-process Python function call (nb_export)           │
│  READS:   the STUDENT's edited modules/NN_name/name.ipynb          │
│  WRITES:  tinytorch/core/name.py (or perf/, or olympics/),  the  │
│           real Python package a student can `import tinytorch`     │
│  PURPOSE: turn the student's notebook cells marked `#| export`     │
│           into a real, importable module, EVERY time they complete │
│           the module (so re-running `complete` after a fix         │
│           legitimately re-generates the package file).             │
└──────────────────────────────────────────────────────────────────┘
```

Confusing these two is exactly the mistake the docs call out explicitly: `tren module test N` alone never runs Conversion B, only `tren module complete N` does. A student who tests repeatedly but never runs `complete` never actually gets their work into `tinytorch/`.

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
│ tren community login│ Opens a browser to a hosted   │ A local HTTP server            │
│                      │ login page, waits (up to      │ (AuthReceiver) listens on      │
│                      │ 300s) for a redirect back     │ 0.0.0.0, port 54321+ (hunts up │
│                      │ carrying access/refresh       │ to +100 if taken), for a       │
│                      │ tokens                        │ callback carrying the tokens.  │
│                      │                                │ Times out silently after 5min. │
├────────────────────┼──────────────────────────────┼───────────────────────────────┤
│ tren system update   │ GitHub tags API + a second    │ Clear "could not check         │
│ --check / update     │ sparse git clone (same         │ updates" message; nothing on   │
│                      │ mechanism as install.sh)       │ disk changes.                  │
├────────────────────┼──────────────────────────────┼───────────────────────────────┤
│ Progress sync        │ POST to a Supabase Edge        │ See below: this is the ONLY  │
│ (module/milestone     │ Function                       │ network call in the normal     │
│ complete, or          │                                 │ per-module loop, and it is     │
│ `community sync`)     │                                 │ entirely optional.             │
└────────────────────┴──────────────────────────────┴───────────────────────────────┘
```

**A student who never runs `tren community login` never makes a single network request during normal module work.** Everything in Parts 3-5 (starting, editing, testing, exporting, completing 20 modules) is 100% offline. The only thing that ever calls out is the progress-sync prompt, and that prompt only appears at all if `auth.is_logged_in()` is true (i.e. credentials already exist on disk).

### 6.1 The sync decision tree (`auto_sync_after_completion`)

```text
              is_ci()?  (checks CI, GITHUB_ACTIONS, GITLAB_CI, etc. env vars)
                    │
              ┌─────┴─────┐
             YES           NO
              │             │
        do nothing.    is_logged_in()?  (credentials.json exists?)
        Never sync           │
        automatically   ┌────┴────┐
        in automation.  NO         YES
                         │           │
              print a hint    is_interactive()?
              to run login,   (stdin AND stdout
              return.         both real TTYs?)
                                │
                          ┌─────┴─────┐
                         YES           NO
                          │             │
                   ASK first     Sync WITHOUT asking.
                   (default:     This is deliberate: a
                   yes). If      real logged-in student
                   declined,     on Git Bash / MinTTY /
                   skip.         most IDE terminals has
                                 stdin.isatty() == False
                                 EVEN THOUGH they're right
                                 there watching the
                                 terminal. An earlier
                                 version of this code
                                 treated non-TTY as "skip
                                 silently," which is the
                                 exact bug (#1849) that
                                 left real students'
                                 dashboards permanently
                                 out of sync with no
                                 error ever shown.
```

### 6.2 What the sync request actually contains, and how honesty is enforced

The payload is a JSON POST to a hardcoded Supabase Edge Function URL, containing the user's email (from stored credentials), completed module list + count + percentage, and unlocked-milestone summary. Read `.tren/progress.json` and `.tren/milestones.json`, assemble, send, no telemetry beyond what's already tracked locally, nothing collected that isn't already visible to `tren module status`.

The response handling is deliberately stricter than a normal "2xx = success" check, because of a previously-real, previously-invisible bug: a `SyncResult` has *two* separate booleans, `ok` and `accepted`. A 2xx HTTP response where the server's own `synced_modules` count is null or zero is reported as a **yellow warning** ("accepted, but not confirmed persisted"), not a green success, because that exact combination is what silently desynced dashboards before. A 401 triggers one automatic token-refresh-and-retry; if the refresh itself fails (400/401/403), stored credentials are deleted outright, forcing a genuine re-login rather than leaving a dead token sitting on disk indefinitely.

---

## Part 7: The Test Gatekeeper, Why `conftest.py` Exists At All

This is the single most important defensive mechanism in the whole codebase, and it exists because of a specific, structural danger in how `tinytorch/__init__.py` is written:

```python
try:
    from .core.tensor import Tensor
except ImportError:
    Tensor = None
```text

Every one of the 20 module imports in `tinytorch/__init__.py` follows this exact pattern. It has to: a student who has only completed 3 of 20 modules needs `import tinytorch` to work at all, not crash because module 15 doesn't exist yet. But the cost of that design is real: **if a module's export is broken or missing, `Tensor` silently becomes `None` instead of raising an error.** A test that does `assert Tensor is not None` correctly catches this, but a test that does something like `x = Tensor([1,2,3])` when `Tensor` is `None` raises a plain `TypeError: 'NoneType' object is not callable`, which is a confusing failure that doesn't point at the real cause. Worse, a badly-written test that doesn't actually exercise the imported symbol can pass vacuously while testing nothing.

`tests/conftest.py`'s `pytest_configure` hook runs **before any test in the whole suite**. As of the current `dev` branch, here is exactly what it checks, no more and no less:

```
┌─────────────────────────────────────────────────────────────────┐
│ Check 1: do these four specific files exist?                      │
│   tinytorch/core/tensor.py                                        │
│   tinytorch/core/activations.py                                   │
│   tinytorch/core/layers.py                                        │
│   tinytorch/core/losses.py                                        │
│                                                                     │
│ Check 2: `from tinytorch import Tensor`, is Tensor None?            │
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

This can be bypassed entirely with `TINYTORCH_SKIP_EXPORT_CHECK=1`, used by the codebase's own test suite so that testing other things doesn't trigger this gate recursively.

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
│ tren community login    │ low  │ write  │ HTTP    │ opens a local port,       │
│                         │      │ (creds)│ (OAuth- │ waits up to 300s          │
│                         │      │        │ style)  │                           │
│ tren benchmark baseline │ med  │ write  │ none    │ real numpy tensor ops,    │
│                         │      │ (JSON  │         │ timed on the actual CPU,  │
│                         │      │ result)│         │ not simulated             │
└────────────────────────┴──────┴────────┴─────────┴──────────────────────────┘
```text

Nothing in this system uses a GPU. `numpy` is the only numerical dependency (`requirements.txt`), and every tensor operation a student implements runs on the CPU via NumPy's own (typically multi-threaded, BLAS-backed) array operations, the CPU cost scales with whatever NumPy operations a student's own code calls, not anything TinyTorch adds on top.

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
│ jupyter/jupyterlab installed?  │ `tren system jupyter` and `_open_jupyter`  │
│                                │ fail cleanly with an install hint if the   │
│                                │ `jupyter` binary isn't resolvable on PATH  │
│                                │ (this can happen even when the Python      │
│                                │ PACKAGES are installed, if the venv's      │
│                                │ Scripts/bin directory isn't on PATH for    │
│                                │ whatever process is invoking tren)         │
├───────────────────────────────┼───────────────────────────────────────────┤
│ nbgrader installed?            │ Entirely optional add-on (not in           │
│                                │ requirements.txt). `tren nbgrader init`    │
│                                │ checks explicitly and fails with an        │
│                                │ install hint rather than a crash; other    │
│                                │ nbgrader subcommands that shell out to     │
│                                │ external `nbgrader` binaries return exit   │
│                                │ code 127 by deliberate design when it's    │
│                                │ missing (FileNotFoundError is caught and   │
│                                │ converted, not left to crash raw)          │
├───────────────────────────────┼───────────────────────────────────────────┤
│ Module tracking vs. disk       │ started_modules/completed_modules in       │
│ desync                         │ .tren/progress.json can go out of sync     │
│                                │ with modules/ on disk (e.g. `tren system   │
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
  │ curl ... | bash               │                                 │
  ├──────────────────────────────>│                                 │
  │                               │  fetch_latest_version() ───────>│  GitHub tags API
  │                               │<─────────────────────────────── │
  │                               │  check_prerequisites()          │
  │                               │  (git, python 3.10+, venv mod)  │
  │                               │  check_internet() ─────────────>│  git ls-remote
  │                               │<─────────────────────────────── │
  │ [confirms install location]   │                                 │
  ├──────────────────────────────>│                                 │
  │                               │  git clone --sparse ────────────>│  the tinytorch/
  │                               │<──────────────────────────────── │  subtree only
  │                               │  rm dev-only files, clear        │
  │                               │  modules/, clear core/*.py       │
  │                               │  python -m venv .venv            │
  │                               │  pip install -r requirements.txt │
  │                               │  pip install -e .                │
  │                               │  [~300 MB now on disk]           │
  │                               │                                 │
  │ cd tinytorch && activate       │                                 │
  │ tren setup                    │                                 │
  ├──────────────────────────────>│  venv guard PASSES (activated)  │
  │                               │  create profile, verify env      │
  │                               │  offer community login ─────?──>│  (optional, OAuth)
  │                               │                                 │
  │ tren module start 01          │                                 │
  ├──────────────────────────────>│  01 not started, no prereqs      │
  │                               │  needed (module 1)               │
  │                               │  notebook doesn't exist →         │
  │                               │  jupytext subprocess writes       │
  │                               │  modules/01_tensor/tensor.ipynb  │
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
  │                               │  REAL tinytorch/core/tensor.py   │
  │                               │  from the student's cells        │
  │                               │  Step 3: pytest against the      │
  │                               │  JUST-EXPORTED package           │
  │                               │  (conftest.py's gatekeeper runs  │
  │                               │  first, Part 7)                  │
  │                               │  Step 4: completed_modules       │
  │                               │  gains "01"                      │
  │                               │  milestone-unlock check           │
  │                               │  IF logged in AND interactive:   │
  │                               │  ask to sync ───────?────────────>│  POST to Supabase
  │                               │<──────────────────────────────── │  edge function
  │                               │                                 │
  │  [... repeat for modules      │                                 │
  │      02 through 20 ...]       │                                 │
  │                               │                                 │
  │ tren milestone run 01         │                                 │
  ├──────────────────────────────>│  prereqs met (from completed set)│
  │                               │  subprocess.run() the actual      │
  │                               │  milestone Python script,         │
  │                               │  importing student's REAL, now-  │
  │                               │  exported tinytorch package       │
  │                               │  update .tren/milestones.json    │
  │                               │                                 │
  │ [after module 20 completes]   │                                 │
  │                               │  20/20 completed, all 6           │
  │                               │  milestones unlockable            │
  │                               │  student now has a real,          │
  │                               │  importable `tinytorch` package,  │
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
6. **Network calls are rare and optional**: install itself, an optional login, an optional progress sync, and an optional update check, the entire 20-module curriculum works completely offline.
7. **The test gatekeeper exists because of a specific danger**: `tinytorch/__init__.py`'s `try/except ImportError: X = None` pattern means a broken export can silently become `None` instead of an error, so `conftest.py` hard-fails the whole test session if the four foundational modules aren't properly exported before any test runs; modules 05-20 aren't covered by this check yet (a fix that would extend it to all 20 is open, unmerged).
8. **No GPU is used anywhere**; every operation is either pure Python/JSON bookkeeping, a subprocess (`jupytext`, `pytest`, a plain `python` script, `jupyter lab`), or NumPy math on the CPU.
