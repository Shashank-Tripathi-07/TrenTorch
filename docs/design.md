# TrenTorch: Design

*This is the contributor-facing design document for TrenTorch, a sub-project of `harvard-edge/cs249r_book` (the "Machine Learning Systems" repository), living at `trentorch/` in that repo. It explains what TrenTorch is, why it exists, how its pieces fit together, and what every technology in the stack is for. Read this before your first contribution; read [the implementation reference](implementation.md) when you're ready to touch code. Both documents describe the project as it actually exists on `dev` HEAD (commit `7d695104`, 2026-08-12). "Project history" at the end covers real bugs and design decisions that shaped the current architecture, and "Known issues" lists documented gaps and things still in progress, both good places to look for a first contribution.*

## Problem

Most machine learning courses and tutorials teach students to *use* a framework: import PyTorch, call `.backward()`, train a model. Very few teach students to *build* one. That leaves a gap: engineers who can call `nn.Linear` fluently but have never implemented backpropagation by hand, never had to reason about why a matmul is memory-bound, and have no intuition for what a framework is actually doing underneath the API.

TrenTorch is a hands-on systems course structured as 20 progressive modules in which students build their own ML framework, using only NumPy, from a tensor class through a working transformer with attention, autograd, training loops, quantization, and performance optimization. The explicit goal is "AI bricks": the stable engineering foundations that transfer to any real framework, learned by building rather than importing.

## Goals

- 20 progressive modules, each with a clear prerequisite chain, taking a student from a bare `Tensor` class (Module 01) to a working, trainable CNN and GPT-style transformer (by Module 13), then into systems-level optimization: profiling, quantization, compression, acceleration, memoization, and benchmarking (Modules 14 through 19), ending in a capstone competition (Module 20).
- A framework built entirely from scratch on top of NumPy, with no dependency on PyTorch or TensorFlow, so every operation a student uses was implemented by that same student.
- Historical-ML "milestones": six standalone exercises (from the 1958 Perceptron through 2018 MLPerf-style benchmarking) that recreate pivotal moments in ML history using the student's own module implementations, gated on having completed the modules each milestone depends on.
- A single CLI, `tren`, that is the primary interface for the whole course: starting and testing modules, running milestones, and benchmarking a finished framework, plus a `%tren` magic (`tren/jupyter_magic.py`) that runs the same commands from inside a Jupyter cell, no terminal round-trip required.
- A local `pip install`-based workflow, running on a CLI-managed Jupyter server (Lab or classic Notebook, a learner's choice, `tren module start` asks) or a plain terminal. Deliberately not multi-cloud: mybinder.org, Google Colab, and third-party judge-sandbox support (DeepML/LeetCode/LeetGPU) were removed 2026-08-23, see Non-goals.
- Free and open source (MIT license for the `trentorch`/`tren` packages), deployable and forkable by anyone.

## Non-goals

- Not a production or performance-competitive ML framework. It is deliberately small enough to read end to end and run on modest hardware (the project's own framing: "small enough to learn from, big enough to matter").
- No GPU acceleration. Everything runs on NumPy on the CPU; that's a deliberate simplicity choice, not a missing feature.
- The "Olympics" competitive leaderboard (`tren olympics`) is not a working feature yet. As of this document it is a "coming soon" placeholder that prints planned tracks (speed, compression, accuracy, and similar) and does nothing else. Don't confuse it with `trentorch.olympics`, the actual Python module students build in the Module 20 capstone; that part is real and functional.
- No grading or multi-student release pipeline. `tren nbgrader` and its solution-stripping (built on nbgrader) have been removed: this fork is a self-use install with no other students to grade, so that infrastructure was dead weight, not a working feature scoped out. Every module's `### BEGIN SOLUTION` / `### END SOLUTION` markers still exist in `src/` as an authoring convention, but nothing in the codebase acts on them anymore.
- No zero-install or third-party-cloud runtime. `binder/` (the mybinder.org launch config) is removed, and `trentorch/core/platform.py`'s runtime detection no longer recognizes Colab, Kaggle, or the DeepML/LeetCode/LeetGPU judge sandboxes it used to special-case, along with the import hook (`TrenTorchImportHook`) that let `trentorch.modules.*` load directly from raw `src/` files for those sandboxes, all removed 2026-08-23 since this fork is CLI-and-local-Jupyter-first, not a multi-platform one, and none of it had a real caller left once traced.
- Server-side benchmark submission is not fully wired up. `tren benchmark` computes real local scores and can offer to submit them, but the actual submission call is a stub; results are only ever saved locally as of this document.

## Technology stack

Everything TrenTorch uses, what it is, and why it's the right tool for this project.

### Core framework and language

| Technology | What it is | How TrenTorch uses it |
|---|---|---|
| Python | A general-purpose programming language. | The language the entire framework, CLI, and test suite are written in. Supports Python 3.10 through 3.13. |
| NumPy | A numerical computing library for array operations. | The *only* numerical dependency of the framework itself. Every operation students implement (tensors, layers, autograd, convolutions, attention) is built directly on NumPy arrays, with no other ML library involved. |
| Rich | A Python library for formatted terminal output. | Powers essentially all of `tren`'s console output: banners, progress panels, colored status messages, and the educational WHAT/WHY test-output mode. |
| PyYAML | A YAML parsing library. | Reads each module's `module.yaml` metadata file (title, subtitle, description) and other YAML-based configuration. |

### The module authoring and release pipeline

| Technology | What it is | How TrenTorch uses it |
|---|---|---|
| Jupytext | A tool that keeps Jupyter notebooks and plain-text scripts in sync. | Each module's source of truth is a plain `.py` file in "percent format" (`src/<NN_name>/<NN_name>.py`). Jupytext converts that file into the `.ipynb` notebook that students actually open and edit in `modules/<NN_name>/`. |
| nbdev | A literate-programming toolkit (originally from fastai) that compiles annotated notebook cells into an installable Python package. | Reads `#| export`-tagged cells out of the module notebooks and compiles them into the real, importable `trentorch/` package (for example, `trentorch.core.tensor`). Configured via `settings.ini` at the `trentorch/` root. |
| YAML-based `module.yaml` | A small per-module metadata file. | Supplies the title, subtitle, and description shown for each module in the CLI and docs. |

### The `tren` CLI

| Technology | What it is | How TrenTorch uses it |
|---|---|---|
| `argparse` (Python standard library) | Python's built-in command-line argument parser. | `tren` is built entirely on `argparse`, with two levels of subcommands (for example `tren module test`), rather than a third-party CLI framework like Click or Typer. |
| pytest | Python's standard test framework. | Runs every category of test in the project: per-module unit tests, integration tests, CLI tests, end-to-end tests, environment checks, and regression tests. `tren module test` and `tren dev test` are wrappers around pytest invocations. |

### Editor tooling

| Technology | What it is | How TrenTorch uses it |
|---|---|---|
| Docker | A containerization tool. | Used in CI (Stage 6, Fresh Install) to simulate a brand-new student machine installing the package from scratch. |

## Architecture

### The three-tree module system

Every module lives in three parallel locations, all keyed by the same `NN_name` directory name (for example `01_tensor`):

- **`src/<NN_name>/`**: the source of truth, written and maintained by instructors and contributors. Contains `<NN_name>.py`, a Jupytext "percent format" Python file mixing `# %% [markdown]` prose cells (learning objectives, prerequisites, dependency diagrams) with `# %%` code cells, plus `module.yaml` (title, subtitle, description).
- **`modules/<NN_name>/`**: the generated notebook a student actually opens in Jupyter. It's produced from `src/` by Jupytext and is not meant to be hand-edited directly; running `tren dev export` regenerates it.
- **`tests/<NN_name>/`**: the pytest suite for that module.
- **`trentorch/`**: the final, installable package. nbdev reads `#| export`-tagged cells out of the module notebook and compiles them into real Python modules (for example, `#| default_exp core.tensor` plus `#| export` in `src/01_tensor/01_tensor.py` produces `trentorch/core/tensor.py`). Every generated file carries an auto-inserted "AUTOGENERATED! DO NOT EDIT!" banner and nbdev provenance comments pointing back at the source notebook.

Within a module's source file, implementation gaps are marked with `TODO:` comments and delimited by `### BEGIN SOLUTION` / `### END SOLUTION` blocks, a convention left over from when a removed `tren nbgrader` command could strip that code out for a separate student-facing release. Nothing in the codebase acts on those markers anymore: the plain `jupytext` conversion `tren module start` uses to produce `modules/<NN_name>/` has no awareness of them, so the notebook a learner opens already contains the full solution, unstripped, by design (`tren/main.py`'s own first-run welcome text: "Solutions are included in the notebooks. This is intentional!"). The honor-system model &mdash; blank it out yourself if you want the exercise &mdash; is not a fallback for a missing feature; it is the only model this fork ships.

### The `tren` CLI

`tren` (entry point `tren.main:main`, declared in `pyproject.toml`) is a hand-built `argparse` application, not built on a third-party CLI framework. `TrenTorchCLI` (`tren/main.py`) keeps a single dictionary mapping top-level command names to command classes, and each top-level command is itself a command group that registers its own nested subcommands. Every command inherits from an abstract `BaseCommand` that provides consistent error handling and console access.

Top-level command groups:

| Command | What it's for |
|---|---|
| `tren setup` | First-time environment setup: creates a virtual environment, installs the fixed toolchain (NumPy, Jupyter, Jupytext, nbdev, Rich, PyYAML, psutil), registers a `trentorch` Jupyter kernel, and prompts to create a local profile and (optionally) join the community. |
| `tren system` | Environment tools: `info`, `health`, `jupyter` (launch a notebook/lab server), `update`, `logo`, `reset`. |
| `tren module` | The core student workflow: `start`, `view`, `resume`, `test`, `complete`, `reset`, `status`, `list`, `path`. This is what a student runs on nearly every module. |
| `tren dev` | Developer and CI tooling, gated behind the `dev` group: `test` (the unified pytest runner used by CI), `preflight` (pre-release verification), `export` (rebuild the whole curriculum from `src/`), `clean`. |
| `tren package` | nbdev/package management: `reset` (clear exported package files or all user progress), `nbdev` (a thin wrapper around the underlying nbdev CLI). |
| `tren milestone` | Historical-ML milestone exercises: `list`, `run`, `info`, `status`, `timeline`, `test`, `demo`. |
| `tren community` | Account and social features: `login`/`logout`, `profile`, `status`, `map`, `sync`. |
| `tren benchmark` | Performance scoring: `baseline` (quick NumPy micro-benchmarks) and `capstone` (scores a student's finished Module 20 framework, or falls back to a placeholder if it isn't built yet). |
| `tren olympics` | The not-yet-implemented competitive leaderboard placeholder described in "Non-goals" above. |

A module's `test` and `complete` commands are not the same operation. `tren module test NN` runs a three-phase check (inline sanity assertions, the module's own pytest suite, and relevant integration tests) without touching the installed package. `tren module complete NN` runs that same testing, then additionally exports the module's code into the real `trentorch/` package via nbdev and records progress; only `complete` actually updates what a student can `import`.

### Milestones

Milestones are historical-ML reproductions, separate from the 20 numbered modules, living in their own `milestones/<NN_year_name>/` directories at the project root. Each one recreates a specific pivotal moment in ML history using the student's own module implementations, and is gated on having completed a specific set of prerequisite modules:

| Milestone | Year | Requires modules | Task |
|---|---|---|---|
| Perceptron | 1958 | 01 to 03 | Rosenblatt's perceptron forward pass |
| XOR Crisis | 1969 | 01 to 03 | Demonstrate that a single layer can't solve XOR |
| MLP Revival | 1986 | 01 to 08 | Train a multi-layer perceptron on XOR and digit recognition |
| CNN Revolution | 1998 | 01 to 09 | Build a LeNet-style convolutional network |
| Transformer Era | 2017 | 01 to 08, 11 to 13 | Attention on reversal, copy, and mixed-sequence tasks |
| MLPerf Benchmarks | 2018 | 01 to 08, 14 to 19 | Optimize and benchmark a trained model |

Run via `tren milestone run <NN>`, `tren milestone list`, and `tren milestone info <NN>`. Each milestone's own scripts import the student's real Tensor, Layers, and other module classes directly, so a milestone only works once the student's own implementations are correct; it functions as an integration test for the whole course arc up to that point, and in practice has caught real API-drift bugs between milestone scripts and module implementations (see "Project history").

### Benchmark and Olympics

`tren benchmark` is the functional performance-scoring feature. `baseline` runs small, fast NumPy micro-benchmarks and normalizes the result against a hardcoded reference system into a 0 to 100 score. `capstone` scores whatever the student built in the Module 20 capstone (`trentorch.olympics`), or falls back to a simplified placeholder score if that module hasn't been completed yet. Both save their results as local JSON under `.tren/benchmarks/`; both can prompt to submit results to the website, but that submission call is currently a stub, so results only ever persist locally as of this document.

`tren olympics` is a different, separate command: a "coming soon" placeholder that prints an ASCII banner and a description of planned competitive tracks (speed, compression, accuracy, and similar). It is not connected to any real leaderboard yet.

### Community dashboard and progress sync: removed

Upstream TinyTorch has an optional social layer: `tito community login` opens a browser-based login flow against the upstream project's own hosted backend (Netlify web API plus a Supabase project), and completing a module or milestone can auto-upload progress to power a personal profile and community dashboard. This fork inherited that client-side code (`tren/commands/login.py`, `community.py`, `tren/core/auth.py`, `browser.py`, `submission.py`, and the dashboard frontend under `quarto/community/`) but never had access to the backend it talked to, so the feature was present but non-functional here from the start. It has since been removed entirely rather than left as dead, non-functional code pointing at someone else's infrastructure. Progress tracking is unaffected: it always lived locally first (`.tren/progress.json`, `.tren/milestones.json`) and never required an account.

### Documentation site and PDFs: removed

Upstream maintains a public docs site (`mlsysbook.ai/tinytorch/`) and a PDF course guide, both built with Quarto from hand-authored `.qmd` pages (one per module, independent prose that links out to the notebook and source rather than being generated from either). This fork inherited that Quarto source tree but never deployed it anywhere, and it had already drifted from the actual module content since nothing kept the two in sync. It has been removed; `docs/` in this repo (this file included) is the contributor-facing documentation going forward.

### Deployment environments

TrenTorch runs via a local `pip install` (the only supported path), either as a plain CLI or against a CLI-managed local Jupyter server. It no longer targets mybinder.org, Google Colab, or a hosted JupyterHub; `binder/` and the platform-detection code that special-cased those environments were removed 2026-08-23 (see Non-goals).

### CI/CD (upstream-only, not present in this fork)

The upstream project runs five GitHub Actions workflows covering validation, previews, production publishing, and PDF builds, tied to the `harvard-edge/cs249r_book` repository's own secrets and deploy targets (`mlsysbook.ai`, a `gh-pages` branch, `tinytorch-vX.Y.Z` release tags). None of that exists in this fork. Summarized here only as background for anyone who's read the upstream docs and is looking for the equivalent here, there isn't one yet:

- **`tinytorch-validate-dev.yml`**: the required gate. An 8-stage pipeline: configure, build the package from `src/`, unit tests, integration tests, CLI tests, end-to-end tests, a Docker-based fresh-install simulation, and a non-blocking link check over the docs site.
- **`tinytorch-preview-dev.yml`**: builds the docs site and PDFs, runs a visual smoke test, deploys to a dev-preview GitHub Pages site.
- **`tinytorch-publish-live.yml`**: bumps the version, merges `dev` into `main`, builds the site and PDFs, deploys to `mlsysbook.ai/tinytorch/`, tags a release.
- **`tinytorch-build-pdfs.yml`** / **`tinytorch-update-pdfs.yml`**: build and redeploy the PDF guide and paper.

### Testing

Tests live under `tests/`, split by purpose: one directory per module (`tests/01_tensor` through `tests/20_capstone`) for unit tests, plus `tests/cli` (black-box tests of the `tren` command itself), `tests/e2e` (full simulated student journeys, run as `tren` subprocesses, tagged by speed from a roughly 30-second quick check up to a 7 to 8 minute full journey), `tests/environment` (validates the local dev environment itself: Python version, active virtualenv, core imports), `tests/integration` (cross-module tests: tensor plus autograd plus layers, a full training pipeline, CNNs, and similar), `tests/milestones` (smoke tests that every milestone script still imports and runs against the current module APIs), and `tests/regression` (pinned tests documenting specific historical autograd and shape bugs, so they can't silently return).

A root `conftest.py` runs a pre-flight check before any test executes: it verifies the `trentorch` package was actually exported and importable, and fails fast with an instruction to run `tren dev export --all` if not, rather than letting every downstream test fail with a confusing import error.

## Known issues

These are good starting points if you're looking for a first contribution.

- **`CONTRIBUTING.md`'s documented release process doesn't match the actual publish workflow.** It states the release process "deploys to tinytorch.org" and "publishes to PyPI." Neither is true as of this document: `tinytorch-publish-live.yml` deploys to `mlsysbook.ai/tinytorch/` via the `gh-pages` branch, and contains no PyPI publish step anywhere (grepped for `pypi`/`twine`, no matches). Distribution is currently via git tags and GitHub Releases, not PyPI, unlike the sibling `mlsysim` package, which does have its own `mlsysim-pypi-publish.yml`.
- **`tren olympics` is a placeholder with no real functionality**, as described above, distinct from the working `trentorch.olympics` capstone module.
- **`tren benchmark`'s server submission is a stub.** Both `baseline` and `capstone` compute and save real local scores, but the "submit to the community" call does not actually reach a server as of this document.
- **`settings.ini` and `pyproject.toml` specify different (looser versus pinned) dependency version ranges** for the same nbdev-managed project, a known source of potential drift between the two config files that both describe the same package.
- **`tests/integration/test_module_integration.py` is dead code**, explicitly marked `pytest.mark.skip` with a comment that it targets stale package paths; current integration coverage lives in the more focused test files alongside it.
- **`dev/scripts/build-docs.sh` is a stale script** referencing a defunct Jupyter Book documentation pipeline that predates the (now also removed) Quarto site. It is not invoked by any current CI workflow.
- **`CHANGELOG.md` is several releases behind the actual shipped version.** Its newest entry is `[0.1.10]`, dated 2026-04 and marked "planned," but `pyproject.toml`'s `version` field (the value `trentorch.__version__` actually reads at import time) is `0.1.13` as of this document, meaning at least three point releases have shipped with no changelog entry at all.
- **`INSTRUCTOR.md` documents two `tren module status` flags that don't exist.** Its "Tracking Progress" section shows `tren module status --student student_id` and `tren module status --export class_progress.csv` as working commands for checking individual or class-wide progress. The real `status` subparser (`tren/commands/module/workflow.py`) takes no arguments at all beyond the bare command; both examples would fail with an argparse "unrecognized arguments" error if an instructor actually typed them. There is no per-student or CSV-export progress view anywhere in the codebase.

## Project history

*Every entry below is sourced directly from the project's real git history, not from documentation or inference. Commit hashes are short-form; run `git show <hash>` against `trentorch/` in the monorepo to verify any of them independently.*

- **A repo-wide RNG migration silently broke a milestone a month after landing.** `d30257577c` (2026-04-03) migrated all 93 source modules, tests, and milestones from `np.random.seed()`/`randn`/`rand` to `np.random.default_rng(7)` for reproducible, isolated random state, a real architectural improvement. But `1aaf779070` (2026-04-30) had to fix Milestone 3 (XOR Solved): the migration turned the milestone's own seeding line into dead code, leaving the hidden layer's RNG at its default seed, which landed the 4-unit hidden layer in a dead-ReLU saddle point that stalled training at 75% accuracy instead of the documented 100%.
- **`Dropout` silently ignored its own module's seeded RNG.** `a9609d6475` (2026-06-17, issue #1869): `Dropout` called the global, unseeded `np.random.random()` instead of drawing from the module's own `rng = np.random.default_rng(7)`, making dropout masks non-reproducible across runs with an identical seed and causing training numerics to quietly diverge between otherwise-identical runs.
- **A silent tuple-length mismatch in `Conv2dBackward` was one refactor away from corrupting gradients.** `63aa703fa1` (2026-06-17, issue #1866): `Conv2dBackward.apply()` always returned a 3-tuple (`grad_input, grad_weight, grad_bias`) even when `bias=None` and only 2 tensors had actually been saved; a `zip()` in the backward walk silently truncated the mismatch instead of raising, so bias-free `Conv2d` only worked by accident of how `zip()` handles unequal lengths.
- **INT8 quantization silently corrupted large-magnitude constants, and the first attempted fix had the sign backward.** `acc31e411f` (2026-06-21) reapplies and corrects an earlier fix (issue #1874) to `quantize_int8`'s scale and zero-point formula: any constant tensor with a value beyond 127 in magnitude had its `zero_point` saturate, silently dequantizing to the wrong value (a value of 500 recovered as 128) with no error raised anywhere.
- **A numerically unstable sigmoid was passing tests only because the test suite suppressed the warning it triggered.** `ecee1841ea` (2026-06-21, based on issue #1870): the naive `1/(1+exp(-x))` sigmoid overflowed for large negative inputs, and the unit test masked the resulting `RuntimeWarning` by suppressing the entire warning category test-wide rather than fixing the formula. Replaced with the standard numerically stable piecewise form.
- **KV-cache generation crashed on literally the first token, because the cache excluded the token that had just been written to it.** `267a53476f` (2026-07-08, issue #1953): `_cached_generation_step()` wrote the new token into the cache via `update()`, then read back only what `advance()` made visible, which didn't yet include the token just written, crashing with a zero-size reduction error on the very first generation step. Fixed by concatenating the current step's own key/value tensors onto the cache history directly.
- **A benchmark comparison crashed specifically on the input it was supposed to handle: a broken baseline model.** `e027d8d1ee` (2026-07-15, issue #1954): `_calculate_improvements()` guarded latency, memory, and energy metrics against division by zero, but not `accuracy_retention`, so a baseline with 0.0 accuracy (exactly the kind of degenerate case a benchmarking suite exists to tolerate) crashed the whole comparison instead of degrading gracefully like its sibling metrics.
- **A missing `pyproject.toml` section broke every CI run's first pipeline stage.** `6984e2dbb5` (2026-06-17, issue #1876): `pyproject.toml` lacked the `[tool.nbdev]` section nbdev actually requires, so every `nb_export()` call fell through to nbdev's legacy settings-migration error path and hard-failed, breaking the inline-build CI stage and cascading to block every downstream stage behind it.
- **Progress sync between the CLI and the community dashboard was broken by three independent, compounding bugs at once.** `f0de9f970e` (2026-06-15, issue #1849): auto-sync silently no-op'd on any non-interactive shell, including Windows Git Bash and many IDE-integrated terminals, so `tren module complete` updated local progress but never uploaded it; a successful-looking HTTP response with a null or zero `synced_modules` count was reported as success using the local count instead, masking real backend failures; and there was no manual resync path, so progress completed before logging in was permanently unsynced. Fixed with a dedicated `tren community sync` command and 15 new regression tests.
- **Two dated security-remediation passes closed out a real batch of CodeQL findings in the community dashboard's auth path.** `d6d90aa2be` (2026-04-05) resolved 28 CodeQL alerts: a ReDoS-vulnerable regex, HTTP response splitting, an XSS/open-redirect path, insecure randomness, missing least-privilege permissions on a workflow, and CDN scripts loaded with no subresource-integrity hash. `ff5df70044` (2026-04-13) closed the remaining findings from the same audit: an HTML-comment tag-filter bypass, provider error detail leaking to clients instead of being logged server-side, incomplete tag-stripping sanitization, and an unchecked post-login redirect URL, fixed by validating it's same-origin before ever following it.
- **A version number was pre-bumped ahead of a release that never shipped, then had to be walked back to unblock the routine release process.** `2e6db57853` (2026-04-23): `pyproject.toml`, `settings.ini`, and the changelog had all been bumped to `0.10.0` ahead of a larger planned release that was never actually tagged, which then blocked the ordinary patch-release workflow's no-downgrade guard from letting a routine `0.1.9` to `0.1.10` release through. Reverted back to `0.1.9` so the standard release process could proceed; `CHANGELOG.md`'s own `[0.1.10]` entry documents the resulting deliberate `0.1.x`-to-`0.10.x` version-numbering decision.
- **The dashboard on the TrenTorch community site once had its "Acceleration" and "Memoization" module description and contributor fields swapped**, a straightforward data-entry bug in the hardcoded per-module dataset embedded in the page. Fixed by correcting the field assignment for the two entries (PR #1979, merged to `dev`).
- **The milestone smoke tests exist because milestone scripts and module APIs have drifted apart before.** `tests/milestones/test_milestones_smoke.py` cites a real example, a `pool_size` versus `kernel_size` naming mismatch, tracked as GitHub issue #1278, where a milestone script broke because the module API it depended on had changed underneath it without the milestone being updated to match.
- **A cluster of autograd and shape bugs from the transformer milestone are preserved as permanent regression tests** in `tests/regression/`: using `np.dot` instead of `np.matmul` silently produced wrong results for batched 3D tensors, `transpose()` was dropping `requires_grad` and breaking gradient flow, and several backward passes (`SubBackward`, `DivBackward`, and gradient paths through Softmax, Dropout, Embedding, Attention, and LayerNorm) were missing or incorrect. Each has a dedicated, permanently pinned test so the specific bug can't silently return.
- **`tren/core/runtime.py` documents a real, fixed bug about conflating "running in CI" with "running non-interactively."** The module's own comments describe a past incident where treating those two conditions as the same thing broke automatic progress-sync behavior specifically on Windows Git Bash; the file now keeps `is_ci()` and `is_interactive()` as two explicitly separate checks. (This is the same underlying class of non-interactive-shell bug independently confirmed above in the `f0de9f970e` progress-sync incident.)
- **A five-PR batch merged 2026-08-12 fixed a cluster of small but genuinely student-facing bugs, found by driving the whole `tren` CLI surface by hand rather than reading the source.** All five were verified live (not just read) against a fresh install before being fixed: `797a2ed901` fixed six separate places across `commands/community.py` and `core/submission.py` that told a student to run `tren login`, a command that has never existed (the real one is `tren community login`; running the printed instruction literally fails with "'login' is not a valid command"). `f262404573` fixed `tren system health`'s final "Module Status" section, which imported and reran the unrelated `InfoCommand` instead of showing per-module status, printing a second full System Details table (Python version, disk space, memory) in place of anything module-related. `a19da98b1d` fixed `tren benchmark baseline` crashing with a raw, unhandled `EOFError` traceback on any non-interactive invocation (no piped stdin), plus a second bug in the same function where the submission-creation block was indented as a sibling of `if submit:` rather than nested inside it, so answering "no" to the submit prompt crashed with `NameError` on variables only assigned in the "yes" branch. `b67c8382a9` fixed the milestone achievement panel showing the identical "What makes this special" text for every milestone, including "Every gradient: YOUR autograd" for Milestones 01 and 02, which only require modules 1 through 3 (forward pass only, no autograd module at all). `897bd4cc9c` fixed `tren milestone info` and the "What's Next" preview both rendering a milestone's year twice ("Perceptron (1958) (1958)"), since `milestone['name']` already includes the year and both call sites appended it a second time.

## Contributing

Once you understand the shape of the project from this document, the [implementation reference](implementation.md) is where you'll actually work: it has the full file map, real code from the module and CLI systems, local setup steps, and common contribution workflows. The "Known issues" list above is a reasonable place to find a first task, and the "Project history" section shows the kind of bug that tends to surface in this codebase (drift between the several parallel representations of the same module, and gradient or shape bugs that only show up once real training happens) so you know what to watch for when reviewing your own changes.
