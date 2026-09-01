# TrenTorch CLI: File Organization Reference

Machine-readable map of `platforms/cli/` (the `tren` CLI package), written
so an agent working on one file doesn't have to re-derive where everything
else lives. If you're about to add a command, fix a bug, or trace a call
path, check here before grepping the whole tree.

**Ground truth over this doc**: file layout changes faster than docs get
updated. If something here doesn't match what you find on disk, trust the
disk and, if you have a moment, fix this file.

## The two-compartment split

`platforms/cli/` has two top-level compartments, plus shared plumbing:

- **`cli_platform/`**: the CLI's own bootstrap and maintainer-only tooling.
  Setup, environment/system commands, package/nbdev internals, dev-only
  rebuild/verify commands. Nothing here is part of a student's daily
  workflow.
- **`processes/`**: the student-facing workflow. Module lifecycle,
  milestones, benchmarking, olympics, format conversion. This is what
  `tren module start` / `tren module complete` / `tren milestone run`
  actually run.
- **`core/` + `commands/`**: genuinely cross-cutting code both
  compartments depend on (config, console, error types, the base command
  class, the Jupyter server lifecycle, notebook↔package export helpers).
  Nothing here should import from `cli_platform/` or `processes/`.

Entry points: `main.py` (imports and wires up `TrenTorchCLI`) and
`jupyter_magic.py` (the `%tren`/`%exit` in-kernel magics, deliberately
outside every compartment, see the Gotchas section).

`data/` (curriculum content: `data/src/`, `data/modules/`,
`data/solutions/`, `data/trentorch/`, `data/milestones/`, `data/datasets/`)
is a sibling directory to `platforms/`, not part of the CLI package at
all. The CLI reads and writes it; it doesn't live inside `platforms/cli/`.

## `platforms/cli/cli_platform/` — bootstrap and maintainer tooling

| File | Lines | What it does |
|---|---|---|
| `setup.py` | 591 | `tren setup`. First-time env setup: `.venv` creation (incl. Apple Silicon/Rosetta handling), package install, user profile, Jupyter kernel registration, environment validation. |
| `system/system.py` | 125 | `tren system` dispatcher (info/health/jupyter/update/logo/reset subcommands). |
| `system/info.py` | 172 | `tren system info`. Python version, platform, venv status, package versions, disk/memory. |
| `system/health.py` | 317 | `tren system health`. Quick pass/fail environment check, no version detail. |
| `system/jupyter.py` | 52 | `tren system jupyter`. Starts a bare Jupyter server (Notebook or Lab). Distinct from `commands/jupyter.py`, which is the shared-server logic `tren module start` uses. |
| `system/update.py` | 446 | `tren system update`. Checks GitHub for a newer tag, updates in place, preserves `data/modules/`, `trentorch/core/`, `user_data/`, `.venv/`. **Known issue, bigger than it looks**: `REPO_URL`/`TAG_PREFIX`/`SPARSE_PATH` still point at the upstream `harvard-edge/cs249r_book` repo's own `tinytorch-v*` tags and `tinytorch/` sparse path, not this fork's, and worse, `_update_tinytorch_package` writes the downloaded package to `project_root/tinytorch` instead of `data/trentorch` (this fork's actual package location since the `data/` restructuring) -- meaning a real run wouldn't just fetch from the wrong upstream, it would drop files somewhere this fork never reads from. Flagged in PR #86, not yet fixed. |
| `system/logo.py` | 144 | `tren system logo`. Explains the logo's symbolism. |
| `system/reset.py` | 163 | `tren system reset`. Wipes to pristine state: clears `data/modules/`, `trentorch/core/*.py`, optionally progress. |
| `package/package.py` | 75 | `tren package` dispatcher (nbdev/reset subcommands). |
| `package/nbdev.py` | 94 | `tren package nbdev`. Thin wrapper running raw nbdev CLI commands. |
| `package/reset.py` | 408 | `tren package reset`. Resets package + user data (broader than `system/reset.py`, includes package-level state). |
| `dev/dev.py` | 122 | `tren dev` dispatcher (test/export/preflight/clean subcommands). Maintainer-only. |
| `dev/test.py` | 1104 | `tren dev test`. The primary CI/local test entry point: unit/integration/e2e/cli/inline/user-journey/milestone test types, `--ci` for JSON output + strict exit codes. |
| `dev/export.py` | 319 | `tren dev export`. Rebuilds the whole curriculum: `data/src/*.py` → `data/modules/*.ipynb` (stub) + `data/solutions/*.ipynb` (reference) → `trentorch` package, built from `data/solutions/`. Overwrites student notebooks; students use `tren module complete` instead. |
| `dev/preflight.py` | 858 | `tren dev preflight`. Release/CI verification checks (`--quick`/`--full`/`--release`). |
| `dev/clean.py` | 58 | `tren dev clean`. Wraps the project's make-based clean target. |

## `platforms/cli/processes/` — student-facing workflow

| File | Lines | What it does |
|---|---|---|
| `module_workflow/workflow.py` | 1408 | `ModuleWorkflowCommand`. `tren module start/view/resume/complete`, progress tracking (`get_progress_data`/`save_progress_data`), `list`/`status`/`path`. The largest file in the CLI; a further split (progress-tracking methods into their own file) was flagged but not done. |
| `module_workflow/test.py` | 580 | `tren module test`. Standalone test-running command, separate from the testing `complete` does inline. **Known duplication**: overlaps with `test_runner.py` below, not yet reconciled. |
| `module_workflow/test_runner.py` | 440 | `run_inline_unit_tests`, `run_integration_tests`, `check_notebook_syntax`. The test-running logic `tren module complete` actually calls (extracted out of `workflow.py`). |
| `module_workflow/reset.py` | 306 | `tren module reset`. Resets one or all modules to a clean state, regenerating the notebook from `data/src/`. |
| `milestone/` | 1682 (5 files) | `tren milestone` — see its own section below. |
| `benchmark.py` | 663 | `tren benchmark`. Runs baseline/capstone benchmarks with submission prompts. |
| `olympics.py` | 121 | `tren olympics`. Not a working feature yet — prints a "coming soon" placeholder for planned competitive tracks. Don't confuse with `trentorch.olympics`, the real Module 20 capstone code students build. |
| `convert.py` | 110 | `tren convert`. Converts a source module to `.qmd`, `.ipynb`, `.yaml`, or sanitized `.txt`/`.py`. |

### `platforms/cli/processes/milestone/` — split by concern (5 files, 1682 lines)

Split from one 1644-line file. `__init__.py` re-exports everything so no
import path outside this package changed.

| File | Lines | What it does |
|---|---|---|
| `constants.py` | 190 | Pure data: `MILESTONE_SCRIPTS` (which scripts back each milestone, required modules, historical context), `MILESTONE_ALIASES` (name→ID), `MILESTONE_ACHIEVEMENT_HIGHLIGHTS`, `MODULE_EXPORT_CHECKS` (which symbol each module must export). No logic. |
| `system.py` | 419 | `MilestoneSystem` (unlock/completion state, prerequisite checks against `user_data/progress.json` and `user_data/milestones.json`), `check_and_run_milestone_unlocks` (the hook `module_workflow/workflow.py` calls right after a module completes, auto-runs any milestone that just became unlockable). |
| `display.py` | 374 | All status/timeline/list/info rendering: `show_status`, `show_timeline`, `show_list`, `show_info`, plus the private tree/horizontal-timeline renderers. Pure output, standalone functions taking `config`/`console` explicitly (not methods on a class). |
| `command.py` | 670 | `MilestoneCommand`, the `tren milestone` argparse dispatcher. Delegates status/timeline/list/info to `display.py`; owns `run`/`test`/`demo` execution and progress-tracking (`_mark_milestone_complete` etc., which delegate to `MilestoneSystem` rather than duplicating file I/O). |
| `__init__.py` | 29 | Re-exports `MilestoneCommand`, `MilestoneSystem`, `check_and_run_milestone_unlocks`, and the constants/helpers that `module_workflow/workflow.py`, `dev/test.py`, and the CLI test suite import directly. |

## `platforms/cli/core/` + `commands/` — shared plumbing

| File | Lines | What it does |
|---|---|---|
| `core/config.py` | 138 | `CLIConfig`. Project root resolution, path config. |
| `core/console.py` | 172 | Rich console singleton, banners, ASCII logo, panel helpers. |
| `core/theme.py` | 56 | Color palette constants used by `console.py` and throughout the CLI. |
| `core/exceptions.py` | 23 | `TinyTorchCLIError` and the exception hierarchy every command catches. |
| `core/modules.py` | 251 | Auto-discovers modules by scanning `data/src/` for `^(\d{2})_(\w+)$` directories, reads each `module.yaml`. Nothing about the module list is hardcoded. |
| `core/runtime.py` | 65 | `is_interactive()` / `is_ci()`. Single source of truth for whether it's safe to prompt. |
| `core/status_analyzer.py` | 499 | Comprehensive module/environment compliance analysis (used by `preflight.py` and others). |
| `core/virtual_env_manager.py` | 30 | Resolves the active `.venv` path, reads `maintainer_use/.tinyrc`. |
| `commands/base.py` | 91 | `BaseCommand`, the abstract base every command class inherits: `config`, `console`, `venv_path`, `execute()` error-wrapping. |
| `commands/export_utils.py` | 425 | Shared notebook/export helpers used by both `dev/export.py` and `module_workflow/workflow.py`: `convert_py_to_notebook`, nbdev export calls, `add_autogenerated_warnings`, `SOURCE_MAPPINGS` (which `data/src/` file feeds which nbdev export target). |
| `commands/jupyter.py` | 227 | The Jupyter component's whole process logic: `resolve_jupyter_ui` (Notebook vs Lab prompt), `find_running_jupyter_server`/`start_jupyter_server` (one shared server per project, not one per launch), `open_jupyter`, `register_jupyter_magic`. |

## Root-level files

| File | Lines | What it does |
|---|---|---|
| `main.py` | 459 | `TrenTorchCLI`. Builds the single `argparse` parser, the top-level command-name → command-class dict (the actual source of truth for what commands exist), custom help/error handling, venv enforcement. |
| `jupyter_magic.py` | 133 | `%tren` and `%exit` IPython magics. **Deliberately outside every compartment** — it has to import cleanly inside a bare Jupyter kernel with no `tren` CLI context available, so it can't depend on anything in `cli_platform/` or `processes/`. |
| `__init__.py` | 24 | Package init. |

## Gotchas an agent should know before touching this code

- **`trentorch` lives at `data/trentorch/`, not the repo root**, but every
  piece of student/curriculum code still does `import trentorch` /
  `from trentorch.core.tensor import Tensor` unchanged. This works via a
  `pyproject.toml` package-dir remap for a real `pip install -e .`, *and*
  via explicit `sys.path` entries for `data/` in both `bin/tren` and the
  root `conftest.py` (needed because CI never runs an editable install,
  it relies on bare `sys.path` bootstrapping). If you add a new bootstrap
  entry point that imports `trentorch` without going through one of
  those two files, it will break exactly the way `main` briefly did
  after the `data/` restructuring, silently, only in CI.
- **`milestone/system.py` imports `MilestoneCommand` from `command.py`
  lazily, inside `check_and_run_milestone_unlocks`, not at module level.**
  A top-level import there would be circular (`command.py` imports
  `system.py` for `MilestoneSystem`; `system.py` needs `MilestoneCommand`
  to auto-run a newly-unlocked milestone). Keep it lazy if you touch this.
- **Two Jupyter-related files, deliberately separate**: `commands/jupyter.py`
  (shared-server lifecycle, used by `tren module start`) vs.
  `cli_platform/system/jupyter.py` (`tren system jupyter`, a bare server
  launch) vs. `jupyter_magic.py` (the in-kernel magic). Don't merge them;
  each has a different execution context.
- **`data/modules/` vs `data/solutions/`**: `data/modules/` is stub-only
  (what a student opens and edits); `data/solutions/` is the fully-solved
  reference, gitignored, maintainer/CI-only. `tren module complete` tests
  and exports from `data/modules/` (the student's own code); `tren dev
  export`/`tren dev test --inline` (maintainer-only) build from
  `data/solutions/`. Don't let student-facing code read from
  `data/solutions/`, that would leak answers.
- **Known duplication, not yet reconciled**: `module_workflow/test.py`
  (`tren module test`) and `module_workflow/test_runner.py` (what
  `tren module complete` calls inline) both run tests, with overlapping
  but not identical logic.
- **`workflow.py` at 1408 lines is the largest file left.** A further
  split (extracting `get_progress_data`/`save_progress_data` and related
  progress-tracking methods into their own file, mirroring the
  `milestone/` package's `system.py`) was identified but not done.
