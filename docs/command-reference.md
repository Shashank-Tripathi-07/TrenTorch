# TrenTorch: `tren` CLI Command Reference

*A complete inventory of every `tren` command, grepped directly from `tren/main.py` and every file under `tren/commands/`, not from any existing documentation. Command groups are dict entries in `TrenTorchCLI.commands` (`tren/main.py`); each group's own `add_arguments` defines its subcommands via `argparse` subparsers. See [`system_design.md`](system_design.md) for how these map onto the underlying module lifecycle.*

There are 10 top-level command groups, registered in this exact dict (the single source of truth per `tren/main.py`'s own comment): `setup`, `system`, `module`, `dev`, `package`, `nbgrader`, `milestone`, `community`, `benchmark`, `olympics`. A `login`/`logout` pair also exists as a standalone `BaseCommand` (`tren/commands/login.py`) but is never registered directly in the top-level dict; it is only reachable by delegation, through `tren community login` / `tren community logout`.

## `tren setup`

First-time environment setup (`tren/commands/setup.py`). Idempotent: safe to re-run, skips steps already done.

| Flag | Effect |
|---|---|
| `--skip-venv` | Skip virtual environment creation |
| `--skip-packages` | Skip package installation |
| `--skip-profile` | Skip user profile creation (`~/.trentorch/profile.json`) |
| `--force` | Prompt to recreate existing components (venv, profile) instead of silently reusing them |

Runs four steps in order: create `.venv`, install packages (numpy, jupyter, jupyterlab, jupytext, ipykernel, nbdev, rich, pyyaml, psutil, then `pip install -e .` for the project itself), create the user profile, validate the environment. Ends by registering a Jupyter kernel named `trentorch` and prompting to join the community (delegates to `LoginCommand`).

## `tren system` (developer/student mixed)

Environment and configuration tooling. Dispatcher: `tren/commands/system/system.py`.

| Subcommand | File | Purpose |
|---|---|---|
| `info` | `system/info.py` | Show system/environment info (Python version, platform, venv status, TrenTorch/NumPy versions, disk space, memory). `--json` for machine-readable output. |
| `health` | `system/health.py` | Quick environment health check (status-only table, no version numbers). No arguments. |
| `jupyter` | `system/jupyter.py` | Start a Jupyter server. `--notebook` (classic) or `--lab` (JupyterLab, otherwise classic notebook is default); `--port N` (default 8888). |
| `update` | `system/update.py` | Check GitHub for a newer `trentorch-v*` tag and update in place. `--check` (check only, don't install), `--yes`/`-y` (skip confirmation). Preserves `modules/`, `trentorch/core/`, `.tren/`, `.venv/`; overwrites `src/`, `tren/`, `tests/`, `milestones/`, `datasets/`, `bin/`, and a few root files. **As inherited, this still points at the upstream repo's tags**, not this fork's, so it would check/update against the wrong project until repointed. |
| `logo` | `system/logo.py` | Explains the TrenTorch logo's symbolism. `--image` shows the path to the actual logo PNG. |
| `reset` | `system/reset.py` | Reset TrenTorch to a pristine state: clears `modules/` and `trentorch/core/*.py`, optionally resets progress. `--force`/`-f` (skip confirmation), `--keep-progress` (only reset code, not tracking), `--ci` (no prompts, plain-text `RESET OK`/`RESET FAILED` output for automation). |

Running `tren system` with no subcommand prints a summary panel rather than an error.

## `tren module` (primary student workflow)

The core lifecycle command. Dispatcher and most logic live in `tren/commands/module/workflow.py` (~1900 lines); `test` and `reset` subcommands each delegate to their own command classes (`module/test.py`'s `ModuleTestCommand`, `module/reset.py`'s `ModuleResetCommand`).

| Subcommand | Arguments | Purpose |
|---|---|---|
| `start` | `module_number` (required); `--no-jupyter` | Start working on a module for the first time. Opens Jupyter unless `--no-jupyter` (used for CI/testing). |
| `view` | `module_number` (required) | Open a module's notebook in Jupyter with no status updates. |
| `resume` | `module_number` (optional, defaults to last worked) | Continue working on a module. |
| `complete` | `module_number` (optional, defaults to current); `--skip-tests`, `--skip-export`, `--all` | Test, export, and update progress for a module. `--all` completes every module. This is the only subcommand that actually exports to the `trentorch` package (see [`system_design.md`](system_design.md#5-data-flow-from-a-students-edit-to-a-real-symbol)); `module test` alone does not export. |
| `test` | `module_number` (optional); `--all`, `--verbose`/`-v`, `--stop-on-fail`, `--unit-only`, `--no-integration` | Three-phase testing: inline → pytest → integration. `--stop-on-fail` only applies with `--all`. |
| `reset` | `module_number` (optional); `--all`, `--force` | Reset a module (or all modules with `--all`) to a clean state, recreating the notebook from `src/`. |
| `status` | (none) | Show module completion status and progress. |
| `list` | `--json` | List all available modules; `--json` for IDE integrations. |
| `path` | `module_number` (required); one of `--notebook`, `--source`, `--guide` (mutually exclusive, required) | Get a specific file path for a module, for IDE integrations. |

## `tren dev` (developer/instructor tooling, not for students)

Dispatcher: `tren/commands/dev/dev.py`. Five subcommands, each its own file.

### `tren dev test`
`tren/commands/dev/test.py`. The primary CI/local test entry point.

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
| `--inline` | Inline tests from `src/`, progressive: test + export each module in sequence |
| `--module`/`-m N` | Restrict to one module |
| `--verbose`/`-v` | Detailed output |
| `--ci` | CI mode: JSON output, strict exit codes; this is the flag that hard-skips the progress-sync network call (see [`system_design.md`](system_design.md#7-how-the-pieces-connect)) |
| `--no-build` | Skip package build, assume already exported |

With no flags, defaults to unit tests only.

### `tren dev preflight`
`tren/commands/dev/preflight.py`. Release/CI verification checks.

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
`tren/commands/dev/export.py`. **Developer-only**, rebuilds the whole curriculum: `src/*.py` → `modules/*.ipynb` → `trentorch` package files. This overwrites student notebooks; students should use `tren module complete` instead, which never touches the notebook file itself.

| Argument/Flag | Effect |
|---|---|
| `modules` (positional, `nargs='*'`) | Specific module names to export (e.g. `01` or `01_tensor`) |
| `--all` | Export every module |
| `--test-checkpoint` | Run a checkpoint test after a successful export |

### `tren dev build`
`tren/commands/dev/build.py`. Thin wrapper over the site's `make` targets (so tools like the VS Code extension can call `tren` instead of raw `make`).

| `target` (positional, required) | Runs |
|---|---|
| `html` | `make html` in `site/` |
| `serve` | `make serve` in `site/` |
| `pdf` | `make pdf` in `site/` |
| `paper` | `make paper` in `site/` |

Note: `make` is not bundled with Git Bash on Windows, unlike git/python; this is a documented reachable `FileNotFoundError` for a Windows user without WSL or a separate `make` install.

### `tren dev clean`
`tren/commands/dev/clean.py`. Same Windows-`make` caveat as `build`.

| `target` (positional, optional, default `all`) | Effect |
|---|---|
| `all` | `make clean` at the project root |
| `site` | `make clean` inside `site/` |

## `tren package`

Package management and nbdev integration. Dispatcher: `tren/commands/package/package.py`.

### `tren package reset`
`tren/commands/package/reset.py` (`ResetCommand`). Five sub-subcommands (`package reset <subcommand>`), all under `dest='reset_command'`:

| Sub-subcommand | Flags | Effect |
|---|---|---|
| `package` | `--force` | Remove all exported `.py` files from the `trentorch` package (notebooks preserved) |
| `all` | `--backup`, `--force` | Reset all user progress: module completion + milestones + config |
| `progress` | `--backup`, `--force` | Reset module completion tracking only |
| `milestones` | `--backup`, `--force` | Reset milestone achievements only |
| `config` | `--force` | Reset `.tren/config.json` to defaults |

`--backup` (where available) copies `.tren/` to a timestamped `.tren_backup_<timestamp>/` directory first.

### `tren package nbdev`
`tren/commands/package/nbdev.py`. Runs nbdev's own tooling.

| Flag | Effect |
|---|---|
| `--export` | Export notebooks to the Python package (delegates internally to the same logic as `tren dev export`) |
| `--build-docs` | Build documentation from notebooks (`nbdev-docs`) |
| `--test` | Run notebook tests (`nbdev-test`) |
| `--clean` | Clean notebook outputs (`nbdev-clean`) |
| `--all` | Used with `--export`: export all modules |
| `module` (positional, optional) | Used with `--export`: export one specific module |

## `tren nbgrader` (instructor/developer, assignment staging + grading)

`tren/commands/nbgrader.py`. TrenTorch owns module discovery and staging; nbgrader itself owns release, collection, autograding, feedback, and export.

| Subcommand | Arguments | Purpose |
|---|---|---|
| `init` | (none) | Initialize nbgrader directories (`assignments/{source,release,submitted,autograded,feedback}`) and a default `nbgrader_config.py` |
| `generate` | `module` (positional, optional); `--all`; `--range` (e.g. `01-04`); `--tier {student,challenge,instructor}` (hidden via `SUPPRESS`, default `student`) | Stage TrenTorch notebooks as nbgrader source assignments |
| `release` | `assignment` (positional, optional); `--all` | Create student release notebooks with nbgrader |
| `collect` | `assignment` (positional, optional); `--all`; `--student` | Collect student submissions |
| `autograde` | `assignment` (positional, optional); `--all`; `--student`; `--force` | Auto-grade submissions |
| `feedback` | `assignment` (positional, optional); `--all`; `--student` | Generate feedback for students |
| `status` | (none) | Show local assignment status (counts per directory) |
| `analytics` | `assignment` (positional, required) | Show local submission/grading counts for one assignment |
| `report` | `--format {csv}` (default `csv`); `--assignment`/`--module` (same dest); `--student` | Export a grades report via nbgrader |

Notable internal behavior: `generate` never overwrites the student-facing notebook a student would open with `tren module start`/`resume`; if that notebook already exists, it stages a fresh jupytext conversion into a private `.nbgrader_staging/` cache instead, specifically so a routine `git pull` bumping a source file's mtime can't silently clobber in-progress student work.

## `tren milestone`

Achievement/capability-unlock tracking, gated on completed modules. `tren/commands/milestone.py`.

| Subcommand | Arguments | Purpose |
|---|---|---|
| `list` | `--simple` | List available milestones and status; `--simple` for less detail |
| `run` | `milestone_id` (required, e.g. `03` or `perceptron`/`xor`/`mlp`/`cnn`/`transformer`/`mlperf`); `--part N`; `--skip-checks` | Run a milestone with prerequisite checking; `--part` runs only one part of a multi-part milestone |
| `info` | `milestone_id` (required) | Show detailed information about a milestone |
| `status` | `--detailed` | View milestone progress and achievements |
| `timeline` | `--horizontal` | View milestone timeline; `--horizontal` shows a progress bar instead of a tree |
| `test` | `milestone_id` (optional, defaults to next available) | Test milestone achievement requirements |
| `demo` | `milestone_id` (required) | Run a milestone capability demonstration |

## `tren community`

Login/profile/status tooling. `tren/commands/community.py`. **Talks to the upstream TrenTorch project's own hosted backend** (`mlsysbook.ai`, Netlify, Supabase), not anything TrenTorch hosts; the commands below run without erroring but won't do anything meaningful from this fork.

| Subcommand | Delegates to / does | Notes |
|---|---|---|
| `login` | `LoginCommand` (`tren/commands/login.py`) | Opens a browser for OAuth-style login; also offers to sync any progress completed while logged out |
| `logout` | `LogoutCommand` | Clears stored credentials via a browser-confirmed logout flow |
| `profile` | Opens `mlsysbook.ai/trentorch/community/?action=profile&community=true` in a browser | |
| `status` | Shows an "ID card" panel: online/authenticated + email, or a not-authenticated panel | |
| `map` | Opens `mlsysbook.ai/trentorch/community/community.html` in a browser | |
| `sync` | `SubmissionHandler.sync_progress()` | Explicit recovery path: pushes the current `progress.json` on demand, for a student who completed modules before logging in or whose automatic sync was skipped |

`login`/`logout` are only reachable through `tren community login`/`tren community logout` (or by direct instantiation of `LoginCommand`/`LogoutCommand` in other files like `setup.py`); there is no bare top-level `tren login`.

## `tren benchmark`

Baseline and capstone performance benchmarks, with an optional submission prompt. `tren/commands/benchmark.py`.

| Subcommand | Arguments | Purpose |
|---|---|---|
| `baseline` | `--skip-submit` | Lightweight setup-validation benchmark (tensor ops, matmul, forward pass), normalized to a reference-system score out of 100 |
| `capstone` | `--track {speed,compression,accuracy,efficiency,all}` (default `all`); `--skip-submit` | Full Module 20 performance evaluation. Falls back to a simplified benchmark if Module 20's `trentorch.olympics.generate_submission` isn't importable yet (i.e. Module 20 not completed) |

Both save JSON results under `.tren/benchmarks/`, and (unless `--skip-submit`) interactively offer to save a submission under `.tren/submissions/`; actual website submission is a stubbed no-op pending a live API.

## `tren olympics`

Competition events, currently a "coming soon" placeholder. `tren/commands/olympics.py`.

| Subcommand | Purpose |
|---|---|
| `logo` | Display the Neural Networks Olympics ASCII-art logo |
| `status` | Check Olympics participation status (currently just shows the same coming-soon panel) |

Running `tren olympics` with no subcommand shows the coming-soon panel with a preview of planned event types (Speed Challenges, Compression Competitions, Accuracy Leaderboards, Innovation Awards, Team Events).

## Global options (apply to `tren` itself, before any subcommand)

| Flag | Effect |
|---|---|
| `--version` | Print `Tren🔥Torch v<version>` (version read from `pyproject.toml`) |
| `--verbose`/`-v` | Enable verbose (DEBUG-level) logging |
| `--no-color` | Disable colored/Rich output |
| `--help`/`-h` | Rich-formatted custom help screen (`TrenTorchCLI._show_help`), not argparse's default |

A virtual-environment guard applies to every command except `setup` (and no command at all): `tren` refuses to run unless `sys.prefix != sys.base_prefix` (or `VIRTUAL_ENV` is set), or the escape hatch `TITO_ALLOW_SYSTEM=1` is set in the environment.
