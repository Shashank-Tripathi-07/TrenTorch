# TrenTorch: Data / Process / Platform Refactor Plan

*This document lays out a codebase-wide reorganization: splitting TrenTorch into four explicit layers (data, process, platform, other systems) so the boundaries between "what the curriculum is," "what turns it into working code," "where it runs," and "everything that supports it" stop being implicit. It is a plan, not a changelog entry: nothing here has shipped yet. Sourced from the current repo tree, `pyproject.toml`, `.github/workflows/validate.yml`, and [`system_design.md`](system_design.md), which this plan does not replace, it describes where that system's pieces move to.*

**2026-08-24 update:** the Data layer's curriculum content now lives under one `data/` folder (`data/modules/`, `data/solutions/`, `data/datasets/`), and solutions no longer ship inline with student code. `data/modules/<NN>/` is a stub-only notebook a student actually solves; their own code is what gets tested and exported into `trentorch/`. `data/solutions/<NN>/` is a maintainer/CI-only reference implementation, gitignored, never surfaced by any `tren` command a student runs, used solely to verify curriculum integrity and rebuild the ground-truth `trentorch/` package. See the [Repo Map artifact] and [Data/Process/Platform Flow artifact] for the current diagrams.

## 1. Why split it this way

Right now the repo answers "where does X live" inconsistently. Curriculum content lives in three places at once (`data/modules/`, `data/src/`, `data/trentorch/`) with a generated relationship between them that only `tren module complete` enforces. Platform detection lives in one file (`data/trentorch/core/platform.py`) but platform *concerns*, CI runners, PyPI, GitHub Pages, Docker, are scattered across `.github/workflows/`, `platforms/dev_tools/`, and `pyproject.toml` with no shared vocabulary.

Four layers, each with one job:

- **Data**: the curriculum's source of truth, content that a person authors or a learner produces. No computation lives here, only what gets computed on.
- **Process**: the transformations that turn data into other data, or into a working package. Every process is a pure function of its inputs, given the same `data/src/`, it produces the same `data/trentorch/`.
- **Platform**: where a process actually executes, and what that execution environment forces you to account for (GitHub Actions runners, PyPI's install contract, a learner's local Jupyter server, Docker for fresh-install verification).
- **Other systems**: everything that supports the above three but isn't itself curriculum, transformation, or execution target, docs site, community backend, contributor tooling, dev-experience scripts.

The point of naming these explicitly is that "make it faster/cheaper/more reproducible" is a different job depending on which layer you're touching. A process is sped up by doing less redundant work: the 2026-08-27 CI optimization pass did this across every stage, not just Stage 7, cutting the whole pipeline from ~8m15s to ~3m47s by removing an unintended milestone auto-run, right-sizing test inputs that were exercising naive-loop code paths at unnecessarily large scale, making eager CLI imports lazy, CI-scaling one milestone's real training demo, and running Stage 1's per-module loop in-process instead of via subprocess (see [`CHANGELOG.md`](../maintainer_use/CHANGELOG.md)). A platform is sped up or made cheaper by choosing a cheaper runner or caching its install contract. Data isn't "sped up" at all, it's made *smaller* or *more consistent*. Collapsing these into one undifferentiated "the codebase is slow" complaint is why that pass took real profiling work, reading actual CI logs and timing real code paths, to even locate the bottlenecks instead of guessing.

## 2. The four layers, mapped to what exists today

### Data

| Current location | What it holds | Notes |
|---|---|---|
| `data/modules/01_tensor` .. `20_capstone` | The learner-facing curriculum: stub-only notebooks converted from `data/src/`, instructional cells plus a `NotImplementedError` stub for each exercise (no solution cell), plus `test_unit_*` / `test_module` assertions. | Generated *from* `data/src/` by `tren module start`. A student's own filled-in code, not any reference implementation, is what `tren module complete` tests and exports. |
| `data/solutions/01_tensor` .. `20_capstone` | Reference implementations, one per module, fully solved. | Also generated *from* `data/src/`. Gitignored, maintainer/CI-only: never surfaced by a command a student runs. Used to rebuild the ground-truth `data/trentorch/` package (`tren dev export`) and to verify curriculum integrity (`tren dev test --inline`), independent of any student's actual progress. |
| `data/src/01_tensor` .. `20_capstone` | The developer-authored source of truth for each module, plain Python with cell markers, each solvable exercise as a stub-cell/solution-cell pair. | This is the actual thing a contributor edits. `data/modules/`, `data/solutions/`, and `data/trentorch/` are all downstream of this. |
| `data/milestones/01_1958_perceptron` .. `05_2017_transformer` (plus `tests/`) | Historical model implementations (perceptron through a small transformer) that exercise completed modules end to end. | Each has a `milestone.yml` read by `platforms/cli/processes/milestone/constants.py`'s `MILESTONE_SCRIPTS`. |
| `data/datasets/tinydigits`, `data/datasets/tinytalks` | The actual training data modules and milestones run against. | |
| `data/trentorch/core/*.py`, `data/trentorch/perf/*.py` | Generated output, one file per module, stamped with an autogenerated-do-not-edit header. | This is Process output living in a directory that reads like Data. That's the layer confusion: it's the exported *artifact*, not a source. |

**Gap**: `data/trentorch/` is checked in and looks like source data (importable package, real files) but it's a build artifact. Nothing currently prevents someone from editing `data/trentorch/core/tensor.py` directly and having it silently diverge from `data/src/01_tensor` until the next export overwrites it. A clean data/process split means either `data/trentorch/` stops being committed (built in CI, published as a wheel) or the autogenerated header becomes an enforced pre-commit check, not just a comment.

### Process

| Current location | What it transforms |
|---|---|
| `platforms/cli/processes/module_workflow/` | `data/src/` → `data/modules/` (notebook conversion, `tren module start`) and `data/modules/` → `data/trentorch/` (export, `tren module complete`), via `commands/export_utils.py` calling `nbdev.export.nb_export` in-process. |
| `platforms/cli/cli_platform/package/` | `data/trentorch/` → distributable package (wheel/sdist), via `tren package`. |
| `platforms/cli/cli_platform/dev/test.py` | Test execution: unit (`test_unit_*`), integration, CLI, E2E, run via `tren dev test`. |
| `platforms/cli/cli_platform/system/` | State transitions on a learner's local `user_data/` directory: `system reset`, progress tracking. |
| `.github/workflows/validate.yml` (Stages 1-7) | The orchestration of the above processes into one pipeline, this is process composition, not a process itself. |
| `platforms/dev_tools/tools/maintenance/restructure-project.sh`, `merge-site-to-docs.sh`, `cleanup_history.sh` | One-off or periodic repo-structure transformations, from the earlier `data/` and `platforms/` restructurings themselves. These are processes too, just not part of the per-push pipeline, and not meant to be re-run now that both restructurings are done. |

**Gap**: processes are currently identified by which CLI command triggers them, not by what they consume and produce. That's why "Stage 7 rebuilds all 20 modules from scratch" was invisible until someone traced it: nothing declared that Stage 7 depends only on Stage 1's already-built package, so the dependency got drawn too wide (waiting on Stages 2-4) by default. A process layer with declared inputs/outputs makes that class of bug visible at design time instead of profiling time.

### Platform

| Current location | What it covers |
|---|---|
| `data/trentorch/core/platform.py` | Runtime detection at *import* time. Only two targets: `jupyter` or `standard` (CLI/script). Colab, Kaggle, and third-party judge-sandbox detection (DeepML/LeetCode/LeetGPU), plus the import hook that let `trentorch.modules.*` load from raw source files for those sandboxes, were removed, see [`design.md`](design.md) Non-goals. |
| `.github/workflows/validate.yml` matrix (`ubuntu-latest`, `windows-2022`) | CI execution platforms. Windows is billed at a multiplier by GitHub Actions and doubles most stage costs; this is a live cost lever noted but not yet acted on. |
| Stage 6 (Fresh Install, Docker) | Install-time platform: verifies the package installs cleanly in a container that isn't the dev environment. |
| `pyproject.toml` `[project.scripts]`, PyPI packaging | The distribution platform: how `tren` becomes a real installed command on a learner's machine. |
| `platforms/cli/jupyter_magic.py` + one shared, CLI-managed Jupyter server | The Jupyter runtime platform: `tren module start/view/resume` launches (or reuses) one server rooted at the project root; `%tren` and `%exit` run inside it, in-process, no second CLI process. |

**Gap**: `data/trentorch/core/platform.py` only handles *runtime* platform (where imported code executes). It has no relationship to the CI matrix or Docker verification, which are also "platform" concerns but live entirely in YAML and shell. A unified platform layer would let "what does this cost/take on platform X" be answered by looking in one place instead of cross-referencing a Python file, a workflow matrix, and a Dockerfile.

### Other systems

| Current location | What it is |
|---|---|
| `.github/workflows/update-contributors.yml`, `welcome.yml` | Contributor-facing automation, unrelated to the curriculum pipeline itself. |
| `platforms/dev_tools/tools/dev/` (`collapse_blank_lines.py`, `validate_cli_docs.py`, etc.) | Contributor-experience tooling, lint-adjacent, not part of any learner-facing process. |

The `quarto/` docs site, community dashboard, and arena mentioned in an earlier version of this section no longer exist: the whole Quarto-based site and the CLI-side login/sync code that talked to it were removed (client-only, the backend belonged to the upstream project and was never usable from this fork; see [`README.md`](README.md#whats-not-here-and-why) and [`design.md`](design.md#community-dashboard-and-progress-sync-removed)). `docs/` (this file's own directory) is the contributor-facing documentation going forward, not a separate "other system" needing its own layer entry.

These don't need to move, they need to stop being implicitly bundled into "the codebase" when scoping a change. A PR that touches only `platforms/dev_tools/tools/dev/` shouldn't need to reason about Data or Process at all; the current flat repo layout doesn't make that obvious from the directory tree.

## 3. What "scalable, reproducible, cheapest, most optimized" means per layer

- **Data**: reproducibility means `data/src/` is the only thing a contributor hand-edits, and `data/modules/` + `data/trentorch/` are always regenerable from it with zero drift. Today that's a convention (the autogenerated header), not an enforced invariant. Scalability means adding module 21 doesn't require touching N unrelated files, it should be one new `data/src/21_*` directory plus a manifest entry.
- **Process**: cost and speed are the same lever here, a process that redoes work another process already did is both slower and, on CI, literally billed twice. The Stage 7 rebuild fix already proved this pattern is real and worth hunting for elsewhere (`tren dev export`, the integration check's pytest subprocess, flagged as future work in the CI issue).
- **Platform**: cheapest means choosing the minimum platform matrix that still catches real bugs. The Windows-leg tradeoff (roughly half of CI compute for real coverage) is a platform-layer decision, not a process one, and should be decided as one, explicitly, not left implicit in a workflow file nobody revisits.
- **Other systems**: these should be optimized independently and rarely block the core pipeline's speed or cost numbers, though with the Quarto docs/community system removed (see section 2 above), this fork currently has very little left in this layer beyond contributor-automation workflows and dev tooling.

## 4. Phased plan

1. **Name the boundary, no code moves yet.** Add a short `ARCHITECTURE.md` (or fold into this doc) that states which existing directory belongs to which layer, so any new file has an obvious home. This document's section 2 is that mapping; it needs a maintainer sign-off, not new code.
2. ~~**Remove the dead layer-0 leftover.**~~ Done: the `tito/commands`/`tito/core` empty directories this step described no longer exist (confirmed `ls tito` returns "No such file or directory"), and the `tito`→`tren` rename's actual internal reorg landed as `platforms/cli_platform/` and `platforms/processes/`, not the `tren/commands/*.py` layout this document originally assumed. See [`cli_file_organization.md`](cli_file_organization.md) for the current, accurate file map.
3. **Enforce the Data/Process boundary on `data/trentorch/`.** Either stop committing `data/trentorch/` (build it in CI, publish only the wheel) or add a pre-commit/CI check that fails if `data/trentorch/` differs from what exporting `data/src/` would produce right now. Without this, the autogenerated-header comment is decoration.
4. **Give Process explicit input/output declarations.** Even a lightweight comment convention at the top of each `platforms/cli/processes/*.py` command ("reads: data/src/, user_data/progress.json; writes: data/trentorch/, data/modules/") would have caught the Stage 7 dependency-width bug before it shipped, not after a profiling session found it.
5. **Decide the Platform matrix deliberately.** Bring the Windows-coverage-vs-cost tradeoff to an actual decision instead of leaving it as a comment. This is the highest-leverage remaining cost lever now that the Process-layer redundancy is mostly cut.
6. ~~**Isolate Other Systems' build/test cost from the core pipeline's numbers.**~~ Moot: the Quarto docs/community system this step was about (Playwright tests included) has since been removed entirely, not just isolated (see section 2 above).
7. **Cut dead surface area.** The VS Code extension has been removed, and the unused nbdev PyPI publish metadata in `settings.ini` has been stripped, neither had any real user or CI dependency once traced. `pyproject.toml`'s actual install machinery (`[project.scripts]`, Stage 6's fresh-install verification) stays: that's not PyPI publishing, it's how a learner gets a working `tren` command.
8. **Narrow the Platform layer to what's actually shipped.** Done: `data/trentorch/core/platform.py` no longer detects Colab, Kaggle, or judge sandboxes, and the import hook that existed only to support those is gone; the mybinder.org launch config is removed. This fork is CLI-and-local-Jupyter-first, not multi-cloud, and none of that had a real caller left once traced. The CLI side of local Jupyter got *more* capable in the same window, not less: `platforms/cli/jupyter_magic.py`'s `%tren`/`%exit` magics and one shared, CLI-managed Jupyter server (reused across every module instead of one spawned per `tren module start`) replaced the old CLI-to-browser-and-back workflow.

## 5. Open decisions that need a call, not an assumption

- Should `trentorch/` stop being a committed artifact entirely, or stay committed with a drift check? Stopping commits is the cleaner data/process split but changes the local install flow. Deliberately deferred: this is a real decision, not forgotten, just not the current priority after the recent CI-budget work.
- Is the Windows CI leg staying, dropping from PR runs only, or dropping entirely? This was already flagged as "not something to decide unilaterally" in the CI work; it applies just as much here.
