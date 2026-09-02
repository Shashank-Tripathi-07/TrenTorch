# TrenTorch: `tren` CLI Command Reference

*A complete inventory of every `tren` command, grepped directly from `platforms/cli/main.py` and every file under `platforms/cli/`, not from any existing documentation. Command groups are dict entries in `TrenTorchCLI.commands` (`platforms/cli/main.py`); each group's own `add_arguments` defines its subcommands via `argparse` subparsers. See [`system_design.md`](system_design.md) for how these map onto the underlying module lifecycle.*

There are 12 dict entries (`tui`, `dashboard`, `serve`, `setup`, `system`, `module`, `dev`, `package`, `milestone`, `benchmark`, `olympics`, `convert`) resolving to 10 distinct commands, since `tui` and `dashboard` are both aliases for the same `TUICommand`. This is the single source of truth per `platforms/cli/main.py`'s own comment. A `community` group and standalone `login`/`logout` commands used to exist here, talking to the original TinyTorch project's own hosted backend; they have been removed (see [`design.md`](design.md#community-dashboard-and-progress-sync-removed)). An `nbgrader` group also used to exist, wrapping multi-student assignment staging and grading (`nbgrader init/generate/release/collect/autograde/feedback/report/analytics`); it has been removed as dead weight for a self-use install with no other students to grade &mdash; nothing about a solo `tren module start`/`complete` workflow depended on it.

## `tren setup`

First-time environment setup (`platforms/cli/cli_platform/setup.py`). Idempotent: safe to re-run, skips steps already done.

| Flag | Effect |
|---|---|
| `--skip-venv` | Skip virtual environment creation |
| `--skip-packages` | Skip package installation |
| `--skip-profile` | Skip user profile creation (`~/.trentorch/profile.json`) |
| `--force` | Prompt to recreate existing components (venv, profile) instead of silently reusing them |

Runs four steps in order: create `.venv`, install packages (numpy, jupyter, jupyterlab, jupytext, ipykernel, nbdev, rich, pyyaml, psutil, then `pip install -e .` for the project itself), create the user profile, validate the environment. Ends by registering a Jupyter kernel named `trentorch` (the kernel identifier, kept distinct from the `trentorch` package name and `tren` CLI name; `tren system health` checks for this exact kernel).

## `tren tui` / `tren dashboard`

Interactive Textual TUI dashboard, launched by `platforms/cli/tui/command.py`, an alias of the same command under two names.

| Flag | Effect |
|---|---|
| `--module`/`-m` | Pre-select a specific module in the dashboard (e.g. `01`, `06`) |

Needs the optional `textual` dependency (`pip install trentorch[tui]`); prints a clear install hint and exits 1 rather than a raw traceback if it's missing.

## `tren serve`

Launches the TrenTorch Companion Server (`platforms/cli/server/command.py` + `platforms/cli/server/handler.py`): a local HTTP + Server-Sent-Events server backing a browser-based visualizer (autograd DAG, attention/Conv2D visualizers, live test streaming).

| Flag | Effect |
|---|---|
| `--port`/`-p` | Port to bind (default `8080`) |
| `--host`/`-H` | Host interface to bind (default `127.0.0.1`). Binding non-loopback exposes the code-running API to the network and prints a security warning. |
| `--no-browser` | Don't auto-open the web browser on startup |

Security model, since this server can run pytest and export code on request: only answers API calls whose `Host` header is a loopback name and whose `Origin` (when present) is a loopback origin, blocking DNS-rebinding and cross-site calls; module ids from the URL are resolved against the real discovered-module set before anything executes, so an unknown id 404s before touching a subprocess; no wildcard CORS. See `platforms/cli/server/handler.py`'s own module docstring for the current detail, and `maintainer_use/CHANGELOG.md`'s 2026-09-01 entries for the CodeQL-flagged CORS header-injection fix.

## `tren system` (developer/student mixed)

Environment and configuration tooling. Dispatcher: `platforms/cli/cli_platform/system/system.py`.

| Subcommand | File | Purpose |
|---|---|---|
| `info` | `system/info.py` | Show system/environment info (Python version, platform, venv status, TrenTorch/NumPy versions, disk space, memory). `--json` for machine-readable output. |
| `health` | `system/health.py` | Quick environment health check (status-only table, no version numbers). No arguments. |
| `jupyter` | `system/jupyter.py` | Start a Jupyter server. `--notebook` (classic) or `--lab` (JupyterLab, otherwise classic notebook is default); `--port N` (default 8888). |
| `update` | `system/update.py` | Check GitHub for a newer `tinytorch-v*` tag and update in place. `--check` (check only, don't install), `--yes`/`-y` (skip confirmation). Preserves `data/modules/`, `trentorch/core/`, `user_data/`, `.venv/`. **Known issue, bigger than it looks**: `REPO_URL`/`TAG_PREFIX`/`SPARSE_PATH` still point at the upstream `harvard-edge/cs249r_book` repo, not this fork, and the downloaded package is written to `project_root/tinytorch` instead of `data/trentorch` (this fork's actual package location) &mdash; a real run wouldn't just fetch from the wrong upstream, it would drop files somewhere this fork never reads from. See [`cli_file_organization.md`](cli_file_organization.md) and PR #86. |
| `logo` | `system/logo.py` | Explains the TrenTorch logo's symbolism and founding story. `--image` shows the path to the actual logo PNG. |
| `reset` | `system/reset.py` | Reset TrenTorch to a pristine state: clears `data/modules/` and `trentorch/core/*.py`, optionally resets progress. `--force`/`-f` (skip confirmation), `--keep-progress` (only reset code, not tracking), `--ci` (no prompts, plain-text `RESET OK`/`RESET FAILED` output for automation). |

Running `tren system` with no subcommand prints a summary panel rather than an error.

## `tren module` (primary student workflow)

The core lifecycle command. Dispatcher and most logic live in `platforms/cli/processes/module_workflow/workflow.py` (~1370 lines); `test` and `reset` subcommands each delegate to their own command classes (`module_workflow/test.py`'s `ModuleTestCommand`, `module_workflow/reset.py`'s `ModuleResetCommand`).

| Subcommand | Arguments | Purpose |
|---|---|---|
| `start` | `module_number` (required); `--no-jupyter` | Start working on a module for the first time. Opens Jupyter unless `--no-jupyter` (used for CI/testing). |
| `view` | `module_number` (required) | Open a module's notebook in Jupyter with no status updates. |
| `resume` | `module_number` (optional, defaults to last worked) | Continue working on a module. |
| `complete` | `module_number` (optional, defaults to current); `--skip-tests`, `--skip-export`, `--all` | Test, export, and update progress for a module. `--all` completes every module. This is the only subcommand that actually exports to the `trentorch` package (see [`system_design.md`](system_design.md#5-data-flow-from-a-students-edit-to-a-real-symbol)); `module test` alone does not export. |
| `test` | `module_number` (optional); `--all`, `--verbose`/`-v`, `--stop-on-fail`, `--unit-only`, `--no-integration` | Four-phase testing: Phase 0 checks the notebook itself for unsolved stubs (issue #71, so a fully-mocked/unimplemented notebook can no longer report a false pass), then Phase 1 inline → Phase 2 pytest → Phase 3 integration. `--stop-on-fail` only applies with `--all`. |
| `reset` | `module_number` (optional); `--all`, `--force` | Reset a module (or all modules with `--all`) to a clean state, recreating the notebook from `data/src/`. |
| `status` | (none) | Show module completion status and progress. |
| `list` | `--json` | List all available modules; `--json` for IDE integrations. |
| `path` | `module_number` (required); one of `--notebook`, `--source`, `--guide` (mutually exclusive, required) | Get a specific file path for a module, for IDE integrations. |

## `tren dev` (developer/instructor tooling, not for students)

Dispatcher: `platforms/cli/cli_platform/dev/dev.py`. Four subcommands, each its own file.

### `tren dev test`
`platforms/cli/cli_platform/dev/test.py`. The primary CI/local test entry point.

| Flag | Effect |
|---|---|
| `--unit`/`-u` | Unit tests (module-level) |
| `--integration`/`-i` | Integration tests |
| `--e2e`/`-e` | End-to-end tests |
| `--cli` | CLI tests |
| `--all`/`-a` | Run every test type |
| `--user-journey` | Full destructive user-journey validation: resets all modules, runs milestones at checkpoints |
| `--release` | Alias for `--user-journey` (same `dest`) |
| `--milestone` | Run milestone script tests |
| `--inline` | Inline tests from `data/src/`, progressive: test + export each module in sequence |
| `--module`/`-m N` | Restrict to one module |
| `--verbose`/`-v` | Detailed output |
| `--ci` | CI mode: JSON output, strict exit codes; this is the flag that hard-skips the progress-sync network call (see [`system_design.md`](system_design.md#7-how-the-pieces-connect)) |
| `--no-build` | Skip package build, assume already exported |

With no flags, defaults to unit tests only.

### `tren dev preflight`
`platforms/cli/cli_platform/dev/preflight.py`. Release/CI verification checks.

| Flag | Effect |
|---|---|
| `--quick` | Quick checks only (~10 seconds) |
| `--full` | Full validation including module tests (~2-5 minutes) |
| `--release` | Release validation, comprehensive (~10-30 minutes) |
| `--ci` | Non-interactive, structured output, strict exit codes |
| `--json` | JSON output (implies `--ci`) |
| `--fix` | Attempt to auto-fix common issues |
| `--verbose`/`-v` | Show commands as they execute |

### `tren dev export`
`platforms/cli/cli_platform/dev/export.py`. **Developer-only**, rebuilds the whole curriculum: `data/src/*.py` → `data/modules/*.ipynb` (stub-only) + `data/solutions/*.ipynb` (reference) → `trentorch` package files, built from `data/solutions/` so the package always reflects fully-working code. This overwrites student notebooks; students should use `tren module complete` instead, which never touches the notebook file itself, tests the student's own filled-in code, and never reads `data/solutions/`.

| Argument/Flag | Effect |
|---|---|
| `modules` (positional, `nargs='*'`) | Specific module names to export (e.g. `01` or `01_tensor`) |
| `--all` | Export every module |
| `--test-checkpoint` | Run a checkpoint test after a successful export |

### `tren dev clean`
`platforms/cli/cli_platform/dev/clean.py`. Wraps `make clean` at the project root. Note: `make` is not bundled with Git Bash on Windows, unlike git/python; this is a documented reachable `FileNotFoundError` for a Windows user without WSL or a separate `make` install.

| `target` (positional, optional, default `all`) | Effect |
|---|---|
| `all` | `make clean` at the project root |

## `tren package`

Package management and nbdev integration. Dispatcher: `platforms/cli/cli_platform/package/package.py`.

### `tren package reset`
`platforms/cli/cli_platform/package/reset.py` (`ResetCommand`). Five sub-subcommands (`package reset <subcommand>`), all under `dest='reset_command'`:

| Sub-subcommand | Flags | Effect |
|---|---|---|
| `package` | `--force` | Remove all exported `.py` files from the `trentorch` package (notebooks preserved) |
| `all` | `--backup`, `--force` | Reset all user progress: module completion + milestones + config |
| `progress` | `--backup`, `--force` | Reset module completion tracking only |
| `milestones` | `--backup`, `--force` | Reset milestone achievements only |
| `config` | `--force` | Reset `user_data/config.json` to defaults |

`--backup` (where available) copies `user_data/` to a timestamped `user_data_backup_<timestamp>/` directory first (not a hidden `.tren_backup_*` name).

### `tren package nbdev`
`platforms/cli/cli_platform/package/nbdev.py`. Runs nbdev's own tooling.

| Flag | Effect |
|---|---|
| `--export` | Export notebooks to the Python package (delegates internally to the same logic as `tren dev export`) |
| `--build-docs` | Build documentation from notebooks (`nbdev-docs`) |
| `--test` | Run notebook tests (`nbdev-test`) |
| `--clean` | Clean notebook outputs (`nbdev-clean`) |
| `--all` | Used with `--export`: export all modules |
| `module` (positional, optional) | Used with `--export`: export one specific module |

## `tren milestone`

Achievement/capability-unlock tracking, gated on completed modules. `platforms/cli/processes/milestone/command.py` (dispatcher; split into a 5-file package alongside `constants.py`/`system.py`/`display.py`, see [`cli_file_organization.md`](cli_file_organization.md)).

| Subcommand | Arguments | Purpose |
|---|---|---|
| `list` | `--simple` | List available milestones and status; `--simple` for less detail |
| `run` | `milestone_id` (required, e.g. `03` or `perceptron`/`xor`/`mlp`/`cnn`/`transformer`/`mlperf`); `--part N`; `--skip-checks` | Run a milestone with prerequisite checking; `--part` runs only one part of a multi-part milestone |
| `info` | `milestone_id` (required) | Show detailed information about a milestone |
| `status` | `--detailed` | View milestone progress and achievements |
| `timeline` | `--horizontal` | View milestone timeline; `--horizontal` shows a progress bar instead of a tree |
| `test` | `milestone_id` (optional, defaults to next available) | Test milestone achievement requirements |
| `demo` | `milestone_id` (required) | Run a milestone capability demonstration |

## `tren benchmark`

Baseline and capstone performance benchmarks, with an optional submission prompt. `platforms/cli/processes/benchmark.py`.

| Subcommand | Arguments | Purpose |
|---|---|---|
| `baseline` | `--skip-submit` | Lightweight setup-validation benchmark (tensor ops, matmul, forward pass), normalized to a reference-system score out of 100 |
| `capstone` | `--track {speed,compression,accuracy,efficiency,all}` (default `all`); `--skip-submit` | Full Module 20 performance evaluation. Falls back to a simplified benchmark if Module 20's `trentorch.olympics.generate_submission` isn't importable yet (i.e. Module 20 not completed) |

Both save JSON results under `user_data/benchmarks/`, and (unless `--skip-submit`) interactively offer to save a submission under `user_data/submissions/`; actual website submission is a stubbed no-op pending a live API.

## `tren olympics`

Competition events, currently a "coming soon" placeholder. `platforms/cli/processes/olympics.py`.

| Subcommand | Purpose |
|---|---|
| `logo` | Display the Neural Networks Olympics ASCII-art logo |
| `status` | Check Olympics participation status (currently just shows the same coming-soon panel) |

Running `tren olympics` with no subcommand shows the coming-soon panel with a preview of planned event types (Speed Challenges, Compression Competitions, Accuracy Leaderboards, Innovation Awards, Team Events).

## Global options (apply to `tren` itself, before any subcommand)

| Flag | Effect |
|---|---|
| `--version` | Print `Tren⚡️Torch v<version>` (version read from `pyproject.toml`) |
| `--verbose`/`-v` | Enable verbose (DEBUG-level) logging |
| `--no-color` | Disable colored/Rich output |
| `--help`/`-h` | Rich-formatted custom help screen (`TrenTorchCLI._show_help`), not argparse's default |

A virtual-environment guard applies to every command except `setup` (and no command at all): `tren` refuses to run unless `sys.prefix != sys.base_prefix` (or `VIRTUAL_ENV` is set), or the escape hatch `TREN_ALLOW_SYSTEM=1` is set in the environment.
