# TrenTorch: Implementation Reference

> **Status: as-built, contributor-facing.** TrenTorch is a live, already-implemented course and framework. This document is your map for reading and modifying the real source: file paths, line numbers, and representative code pulled directly from the codebase at `dev` HEAD (`7d695104`, 2026-08-12). Read the [design doc](design.md) first for the "what and why"; this doc is the "where and how." Section 10, "Common contribution workflows," is the fastest way in if you already know what you want to change.

## Prerequisites

| To work on... | You need |
|---|---|
| A module's content (`src/<NN_name>/`) or its tests | Python 3.10 or newer, a virtual environment, and `pip install -r requirements.txt && pip install -e .` from `trentorch/`. That's the whole setup; no external services required. |
| The `tren` CLI itself | The same as above. `tren` is a plain Python package (`tren/`) installed alongside `trentorch/` from the same `pyproject.toml`. |

## Repository layout

```
cs249r_book/
  trentorch/
    src/                # Source of truth: one <NN_name>/<NN_name>.py per module
    data/modules/             # Generated student notebooks (from src/, via jupytext)
    tests/               # Per-module tests, plus cli/e2e/environment/integration/milestones/regression
    trentorch/           # The installable package, generated from data/modules/ by nbdev
    tren/                # The `tren` CLI package
    milestones/          # Six historical-ML reproduction exercises
    docs/                # Design docs, contributor docs (CONTRIBUTING.md)
    dev/                  # Dev-only support tooling: scripts/, tools/, etc/ (jupyter config)
    benchmark_results/    # Local artifact output from Module 19's BenchmarkSuite
    pyproject.toml, settings.ini, MANIFEST.in, requirements.txt
    README.md, LICENSE, CHANGELOG.md
  .github/workflows/
    validate.yml
    update-contributors.yml
    welcome.yml
```

---

## 1. The module system (`src/`, `data/modules/`, `trentorch/`)

### 1.1 A real module source file

`src/01_tensor/01_tensor.py` is a Jupytext "percent format" file: plain Python with `# %%` cell markers, so it round-trips cleanly to and from a Jupyter notebook. Its header declares the jupytext representation, and the file mixes markdown cells (learning objectives, a "Module Dependencies" section, a dependency-flow diagram showing `Module 01 (Tensor) -> All Other Modules`) with code cells.

The nbdev export target is declared once near the top of the file:

```python
#| default_exp core.tensor
```

Every cell that should become part of the installable package is tagged:

```python
#| export
class Tensor:
    ...
```

In `src/01_tensor/01_tensor.py`, each implementation gap is a stub-cell/solution-cell pair (representative, from the `__init__` region):

```python
# %% nbgrader={"grade": false, "grade_id": "tensor-class", "solution": true}
class Tensor:
    def __init__(self, data):
        # TODO: Initialize a Tensor by wrapping data in a NumPy array
        ### BEGIN SOLUTION
        raise NotImplementedError("TODO: implement Tensor.__init__")
        ### END SOLUTION

# %% tags=["solution"]
#| export
class Tensor:
    def __init__(self, data):
        ### BEGIN SOLUTION
        self.data = np.asarray(data)
        ...
        ### END SOLUTION
```

Only the `tags=["solution"]` cell carries `#| export`; the stub cell doesn't, in `src/`. Two different notebooks get generated from this one source file: `data/modules/01_tensor/tensor.ipynb` keeps only the stub cell (with `#| export` added back, so a student's own filled-in code is what nbdev picks up), and `data/solutions/01_tensor/tensor.ipynb` keeps only the solution cell, gitignored and maintainer/CI-only. `tren module start` opens the stub notebook; a learner sees the `TODO`, not the answer &mdash; see `design.md`'s note on the four-tree module system. The same stub/solution pairing repeats through the file for `__add__`, `__sub__`, matmul, reshape, transpose, and the reduction operations.

### 1.2 Module metadata

`src/01_tensor/module.yaml`:

```yaml
title: Tensor Foundation
subtitle: Building Blocks of ML
description: Build the foundational Tensor class that powers all machine learning operations.
```

Every module directory under `src/` has one of these; `tren` reads it (via `tren/core/modules.py`) to show titles and descriptions in the CLI without hardcoding them anywhere.

### 1.3 How a module becomes three other things

- **Source to notebook**: `tren/commands/export_utils.py`'s `convert_py_to_notebook()` shells out to `jupytext --to ipynb` to regenerate `data/modules/<NN_name>/<short_name>.ipynb` from the `src/` `.py` file. `SOURCE_MAPPINGS` in the same file hardcodes which `src/` file feeds which nbdev export target, since the notebook path and the export path aren't always the same string.
- **Notebook to package**: nbdev exports every `#| export`-tagged cell into `trentorch/`, following the `#| default_exp` target declared in the source file (`core.tensor` becomes `trentorch/core/tensor.py`). `add_autogenerated_warnings()` (also in `export_utils.py`) injects the "AUTOGENERATED! DO NOT EDIT!" banner into every generated file, and each generated file carries an nbdev provenance comment (for example `# %% ../../modules/01_tensor/tensor.ipynb #dbd4f042`) pointing back at the exact notebook cell it came from.
- **The command that does this for a student**: `tren module complete <NN>` runs the module's tests, does a syntax check, exports via nbdev, runs relevant integration tests, and updates progress tracking, in that order. Running `tren module test <NN>` alone does *not* export anything; only `complete` updates what's actually importable from `trentorch`.

### 1.4 Module discovery

`tren/core/modules.py` auto-discovers modules by scanning `src/` for directories matching `^(\d{2})_(\w+)$`, builds the `{"01": "01_tensor", ...}` mapping used throughout the CLI, and reads each module's `module.yaml` for display metadata. Nothing about the module list is hardcoded; adding a 21st module means adding a correctly-named `src/` directory with a `module.yaml`, and the CLI picks it up automatically.

---

## 2. The `tren` CLI (`tren/`)

### 2.1 Architecture (`tren/main.py`)

`TrenTorchCLI` builds one `argparse.ArgumentParser` with subparsers, keyed off a single dictionary mapping top-level command names to command classes. Each top-level command is itself a group that registers its own nested subparser (for example, `module` registers `start`, `test`, `complete`, and so on), so effectively every command in the table below is two levels of `argparse` subcommand.

`run(args)` does some deliberate custom behavior before dispatching: it intercepts `-h`/`--help` to show Rich-formatted help instead of argparse's default, gives a friendlier error for an unrecognized first argument, and (except for `tren setup`) enforces that commands run inside an activated virtual environment unless `TITO_ALLOW_SYSTEM=1` is set, since running the course tooling against a system Python is a common source of confusing failures.

Every command class inherits from the abstract `BaseCommand` (`tren/commands/base.py`), which supplies `config`, a shared Rich `console`, the resolved `venv_path`, and an `execute()` wrapper that catches and formats `TrenTorchCLIError` and generic exceptions consistently.

### 2.2 Command reference

| Command | Class / file | What it actually does |
|---|---|---|
| `tren setup` | `SetupCommand`, `commands/setup.py` | Creates `.venv` (with Apple Silicon/Rosetta detection), installs a fixed toolchain plus `pip install -e .`, registers a `trentorch` Jupyter kernel, creates `~/.trentorch/profile.json`, and validates the environment. |
| `tren system info / health / jupyter / update / logo / reset` | `commands/system/*.py` | Environment diagnostics, launching a Jupyter server, checking for CLI updates, showing branding, and resetting the local environment to a pristine state. |
| `tren module start / view / resume / test / complete / reset / status / list / path` | `ModuleWorkflowCommand`, `commands/module/workflow.py` (1,857 lines) plus `commands/module/test.py` and `commands/module/reset.py` | `start` checks sequential prerequisites and opens the module in Jupyter, creating its notebook from `src/` if it doesn't exist yet. `complete` runs the four-step pipeline described in section 1.3. `test` runs the three-phase test check described below without exporting anything. `reset` regenerates a module's notebook from `src/` and clears its progress entries. |
| `tren dev test / preflight / export / clean` | `commands/dev/*.py` | `test` is the unified pytest runner CI uses, with flags for `--unit`, `--integration`, `--e2e`, `--cli`, `--milestone`, `--all`, `--release`, or a specific `--module NN`. `preflight` runs pre-release verification (project structure, CLI smoke checks, imports, git state, module tests, milestone scripts). `export` rebuilds the entire curriculum (`src/` to `data/modules/` to `trentorch/`) for all modules or one. `clean` removes build artifacts. |
| `tren package reset / nbdev` | `commands/package/*.py` | `reset package` clears exported package files; `reset all` clears all user progress and data. `nbdev` is a thin wrapper exposing `--export`/`--build-docs`/`--test`/`--clean`, mostly delegating to the underlying nbdev CLI or to `DevExportCommand`. |
| `tren milestone list / run / info / status / timeline / test / demo` | `commands/milestone.py` | Implements the six hardcoded milestones described in the design doc. `run` executes a milestone's standalone script via a subprocess, after validating that the required module exports actually work. Progress is stored in `.tren/milestones.json`. |
| `tren benchmark baseline / capstone` | `commands/benchmark.py` | `baseline` runs quick NumPy micro-benchmarks (tensor ops, matmul, forward pass) and normalizes them into a 0 to 100 score against a hardcoded reference system, saving JSON under `.tren/benchmarks/`. `capstone` scores the student's Module 20 `trentorch.olympics` submission if it exists, or falls back to a placeholder score otherwise. The "submit to website" step in both is currently a stub. |
| `tren olympics` | `commands/olympics.py` | The not-yet-implemented placeholder described in the design doc. Only its `logo` subcommand does anything real; every other subcommand, including a registered but unimplemented `status`, falls through to a generic "coming soon" message. |

### 2.3 `tren/core/` responsibilities

| File | Responsibility |
|---|---|
| `config.py` | `CLIConfig`, a dataclass of resolved project paths. Auto-detects the project root by walking up the directory tree looking for `pyproject.toml`, and validates the Python version, active virtualenv, required directories, and required packages. |
| `console.py` | A shared Rich `Console` singleton plus banner, logo, error, success, warning, and info print helpers used across the whole CLI. |
| `exceptions.py` | A small exception hierarchy: `TrenTorchCLIError` (base), `ValidationError`, `ExecutionError`, `EnvironmentError`, `ModuleNotFoundError`. |
| `modules.py` | Module auto-discovery and metadata parsing, described in section 1.4. |
| `runtime.py` | Distinguishes `is_ci()` from `is_interactive()` as two explicitly separate checks. See "Project history" in the design doc for why this distinction matters. |
| `status_analyzer.py` | `TrenTorchStatusAnalyzer`, a heavier per-module compliance and health checker (checks for required sections, parses class and function counts, tries importing and running the module) used by dashboards and preflight checks. |
| `theme.py` | Centralized Rich color and style constants for consistent CLI theming. |
| `virtual_env_manager.py` | Resolves the virtual environment path (respecting a `VENV_PATH` environment variable or a `.tinyrc` config file, defaulting to `.venv`) and the correct binary directory for the current OS. |

### 2.4 What `tren module test <NN>` actually runs

Three phases, in `ModuleTestCommand.test_module()` (`tren/commands/module/test.py`):

1. **Inline tests**: runs `python src/<module>/<module>.py` as a subprocess, which triggers the module's own `if __name__ == "__main__"` block containing quick sanity assertions. Pass or fail is just the subprocess return code.
2. **Module pytest**: if `tests/<module>/` exists, runs `python -m pytest tests/<module> --trentorch -q --tb=short --no-cov`. The custom `--trentorch` flag turns on WHAT/WHY educational context in the test output, described in section 3.
3. **Integration tests**: looks up a hardcoded map from module number to relevant files under `tests/integration/` (accumulating tests progressively as module number increases) and runs those.

`--unit-only` stops after phase 1. `--no-integration` skips phase 3. `--all` runs every module in sequence and prints a summary table.

---

## 3. Testing (`tests/`)

### 3.1 Configuration

`pyproject.toml`'s `[tool.pytest.ini_options]` sets `testpaths = ["tests"]`, standard test discovery patterns, two custom markers (`slow`, `quick`), and `--strict-markers`. There's no coverage plugin configured; the project's own comment notes coverage isn't considered useful for educational code.

The root `tests/conftest.py` (349 lines) does three important things before any test runs:

1. **A package-export pre-flight check**: `_validate_package_exported()`, wired into `pytest_configure`, verifies that `trentorch/core/{tensor,activations,layers,losses}.py` exist and that `from trentorch import Tensor` actually imports a working class, not something silently `None`. If it fails, it raises `pytest.UsageError` telling the developer to run `tren dev export --all`, rather than letting every downstream test fail with a confusing import error. Skippable via `TRENTORCH_SKIP_EXPORT_CHECK=1`.
2. Registers the `module(name)`, `slow`, and `integration` markers.
3. A custom `--trentorch` CLI flag turns on `TrenTorchTestReporter`, which parses WHAT/WHY/STUDENT LEARNING sections out of test docstrings and prints them via Rich, and auto-detects which module a test belongs to from its file path.

### 3.2 Test categories

| Directory | What's tested |
|---|---|
| `tests/<NN_name>/` (one per module) | Standard unit tests for that module's implementation. |
| `tests/cli/` | Black-box tests of the `tren` command itself: bare invocation, `--help`, `--version`, CLI registry consistency, and help-text consistency. Some tests import `tren.main.TrenTorchCLI` directly; others shell out via subprocess to test the real entry point end to end. |
| `tests/e2e/` | Full simulated student journeys, run as `tren` subprocesses with `TITO_ALLOW_SYSTEM=1` set. Marked `quick` (about 30 seconds), `module_flow` (about 2 minutes), or `full_journey` (7 to 8 minutes, CI only). |
| `tests/environment/` | Validates the local dev environment itself: Python version at least 3.10, an active virtualenv, and that core dependencies import correctly. Meant to run right after `tren setup`. |
| `tests/integration/` | Cross-module tests: tensor plus autograd plus layers together, a full training pipeline, CNN integration, gradient flow, and similar. One file, `test_module_integration.py`, is entirely disabled via `pytest.mark.skip` with an explicit comment that it targets stale package paths; current coverage lives in the other, more focused files in the same directory. |
| `tests/milestones/` | Smoke tests that every milestone script under `milestones/` can still be imported and constructed without crashing, parametrized over every `.py` file found there. Explicitly framed as an API-drift catcher between milestone scripts and the module APIs they depend on. |
| `tests/regression/` | Pinned tests documenting specific historical autograd and shape bugs (see the design doc's "Project history" for the actual bugs), so they can't silently reappear. |

---

## 4. Milestones (`milestones/`)

Each milestone directory (for example `milestones/01_1958_perceptron/`) contains its own `README.md` with historical context, plus one or more runnable Python scripts that import the student's real module implementations directly, not mocks or reference solutions. `milestones/data_manager.py` provides shared data-loading utilities across milestones, and `milestones/journey.svg` is a visual map of the milestone progression used in the docs.

`tren milestone run <NN>` executes the milestone's script as a subprocess after validating that the modules it depends on actually export working code, per the requirements table in the design doc.

---

## 5. Documentation site, PDF guide, and community sync: removed

This fork inherited upstream's Quarto-based docs site and PDF guide (`quarto/`), its student-progress community dashboard (`quarto/community/`), and the CLI-side login/auth/sync code that talked to it (`tren/commands/login.py`, `community.py`, `tren/core/auth.py`, `browser.py`, `submission.py`). The dashboard and CLI sync code were client-only: the backend they talked to (a Netlify-hosted login endpoint and a Supabase project) belonged to the original TrenTorch project and was never usable from this fork. The Quarto docs site and PDF guide were never deployed from this fork either, and the hand-authored `.qmd` pages had already drifted from the actual module content since nothing kept the two in sync. All of it has been removed rather than kept as dead code pointing at someone else's infrastructure or an undeployed site; see [`design.md`](design.md#community-dashboard-and-progress-sync-removed) for the fuller history. `docs/` (this file included) is the contributor-facing documentation going forward.

---

## 6. Packaging

### 7.1 `pyproject.toml` (at `trentorch/`)

Declares `name = "trentorch"`, current version `0.1.13`, `requires-python = ">=3.10"`, MIT license, and runtime dependencies limited to `numpy`, `rich`, `PyYAML`, `certifi`, and `pytest`. `[project.scripts]` registers `tren = "tren.main:main"` as the installed console command. Optional dependency groups: `dev` (pytest plus coverage, jupytext, nbformat, jupyter, jupyterlab, ipykernel, and a pinned nbdev range), `visualization` (matplotlib), and `docs` (jupyter-book, sphinxcontrib-mermaid, matplotlib, and Jupyter widgets). `[tool.setuptools.packages.find]` limits the built package to the `trentorch` and `tren` packages, explicitly excluding `tests`, `modules`, `site`, `docs`, `milestones`, and `assignments`.

### 7.2 `settings.ini`

The classic nbdev settings file (fastai-derived format). Repeats some of the same metadata as `pyproject.toml` (`lib_name = trentorch`, `version = 0.1.13`, `min_python = 3.10`, MIT license) but with its own, looser `requirements`/`dev_requirements` lines (for example `numpy>=1.20.0` here versus `numpy>=2.2.6,<3.0.0` in `pyproject.toml`), a known drift risk between the two files since nothing currently keeps them mechanically in sync beyond the version-bump step in the publish workflow. Also configures the nbdev paths (`lib_path = trentorch`, `nbs_path = modules`, `doc_path = _docs`) and docs metadata (`doc_host`, `doc_baseurl`, `git_url`, `title`).

### 7.3 `MANIFEST.in`

Seven lines: includes `README.md`, `LICENSE`, and `pyproject.toml` explicitly, recursively includes every `.py` file under `trentorch/`, and excludes `__pycache__`, compiled `.pyc`/`.pyo` files, and `.DS_Store` everywhere. It doesn't explicitly list `tren/`'s files; those are picked up via setuptools' package auto-discovery instead.

### 7.4 Distribution

TrenTorch is not currently published to PyPI by any automated workflow. Upstream distributes via git tags and GitHub Releases through their own CI, which this fork does not have set up: TrenTorch has no release automation of its own yet, so distribution is just the repository itself (`git clone` or `pip install -e .` from a checkout).

---

## 7. CI/CD

The upstream TinyTorch project runs five GitHub Actions workflows (validate, preview, publish, and two PDF-build workflows) that gate merges, build and deploy the docs site to `mlsysbook.ai`, and cut versioned releases. None of that CI/CD infrastructure exists in this fork: it's specific to the `harvard-edge/cs249r_book` repository's GitHub Actions setup and secrets, and can't be used here without standing up equivalent workflows against this repository. If TrenTorch adds its own CI later, it would need to be built independently rather than copied wholesale, since the originals assume the monorepo's directory layout and deploy targets.

---

## 8. Local development setup

1. `cd trentorch`, create and activate a virtual environment.
2. `pip install -r requirements.txt`, then `pip install -e .` to install both `trentorch` and `tren` in editable mode.
3. Verify with `tren --version`, `tren system health`, and `tren module status`.
4. Work on module content directly in `src/<NN_name>/<NN_name>.py`, the source of truth; never hand-edit files under `data/modules/`, since those are regenerated. After a change, run `tren dev export` (or `tren module complete <NN>` if you also want it reflected in progress tracking) to see it as an importable part of `trentorch`.
5. Test with `pytest tests/<NN_name>/` or `tren module test <NN>` for a single module, `pytest tests/integration/` for cross-module checks, and, if your change affects one, the relevant milestone script under `milestones/`.
6. Follow the mandatory git workflow from `CONTRIBUTING.md`: never commit directly to `dev` or `main`; branch as `feature/your-improvement`; stage files explicitly rather than using a blanket `git add .`; open a PR targeting `dev`.

---

## 9. Known-broken or inaccurate as of this document

- `CONTRIBUTING.md`'s "Release Process" section claims the release workflow "deploys to tinytorch.org" and "publishes to PyPI." Neither matches the actual `tinytorch-publish-live.yml` workflow, which deploys to `mlsysbook.ai/tinytorch/` via `gh-pages` and has no PyPI step at all.
- `dev/scripts/build-docs.sh` references a defunct Jupyter Book pipeline (`docs/_build/html`, `website/docs/`) that predates the (now also removed) Quarto site, and is not called from any current CI workflow.
- `tests/integration/test_module_integration.py` is fully disabled (`pytest.mark.skip`) with a comment that it targets stale package paths.
- `settings.ini` and `pyproject.toml` specify different dependency version floors for the same package; nothing currently enforces they stay consistent beyond the manual version-bump step in the publish workflow.
- `CHANGELOG.md`'s newest entry is `[0.1.10]` (dated 2026-04, marked "planned"); `pyproject.toml`'s actual `version` is `0.1.13` as of this document, at least three releases with no changelog entry.
- `INSTRUCTOR.md` documents `tren module status --student student_id` and `--export class_progress.csv`; the real `status` subparser takes no arguments and both would fail with an argparse error.

---

## 10. Common contribution workflows

### Improving a module's content or exercises

1. Edit `src/<NN_name>/<NN_name>.py` directly. Preserve the `#| default_exp` / `#| export` structure and the `### BEGIN SOLUTION` / `### END SOLUTION` markers around any region a student is meant to implement themselves.
2. `tren dev export --module <NN>` (or `--all` if you touched shared code) to regenerate the student notebook and the compiled package.
3. `tren module test <NN>` to run that module's own three-phase test check.
4. If your change affects behavior other modules or milestones depend on, run `pytest tests/integration/` and any relevant `tren milestone run <NN>` to check for downstream breakage; this project has a real history of exactly that kind of drift (see the design doc's "Project history").
5. Open a PR against `dev` following the git workflow in `CONTRIBUTING.md`.

### Fixing a bug in the `tren` CLI

1. Locate the relevant command class (Section 2.2's table) or core module (Section 2.3's table).
2. Make the fix. If it involves environment detection, subprocess behavior, or anything platform-specific, test on both a Unix shell and Windows if you can; this codebase has a documented history of Windows-specific bugs in exactly this kind of code (see `tren/core/runtime.py`'s CI-versus-interactive fix in the design doc's "Project history").
3. Add or update a test in `tests/cli/`. Prefer testing through the real subprocess entry point (`python -m tren.main ...`) when you're testing user-facing behavior, and importing `tren.main.TrenTorchCLI` directly when you're testing internal logic.
4. `pytest tests/cli/` locally, then open a PR. CI's `tinytorch-validate-dev.yml` runs the CLI test stage on both Ubuntu and Windows.

### Adding or fixing a milestone

1. Milestones live in `milestones/<NN_year_name>/`, each with its own `README.md` and runnable script that imports the student's real module classes.
2. If you're changing a module's public API in a way that could affect a milestone that depends on it, check `tests/milestones/test_milestones_smoke.py` and consider running the affected milestone directly; this is the exact class of bug that test file exists to catch (see GitHub issue #1278, referenced in the design doc).
3. Update the milestone's requirement list in `tren/commands/milestone.py`'s `MILESTONE_SCRIPTS` if the set of prerequisite modules changes.
