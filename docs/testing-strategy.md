# Testing Strategy

This document explains how TrenTorch is tested, why it's tested that way, and where the real risk in this codebase actually lives. It's modeled loosely on SQLite's own testing writeup (a widely-cited example of a project being honest and specific about what it verifies and why), but scoped to what actually matters here. TrenTorch is a 20-module educational framework maintained by a handful of people, not an embedded database deployed on billions of devices, and this document tries not to pretend otherwise. Where SQLite's practices don't transfer, section 7 says so directly instead of copying them for appearance's sake.

## 1. What's actually at risk here

Most testing writeups for a codebase this size would just list "we run pytest in CI" and stop. That undersells two things that make TrenTorch's risk profile different from an ordinary application:

**Wrong output here isn't just a bug, it's a wrong lesson.** A student who runs a subtly incorrect backward pass and gets a plausible-looking gradient doesn't get an error message, they get a wrong mental model of how autograd works, and it doesn't surface until much later, if ever. Correctness in the reference solutions matters more than usual because the code itself is the teaching material.

**The export pipeline is fragile machinery that can silently corrupt correct source.** `data/src/<NN>/<NN>.py` files use jupytext `# %%` markers as structural cell boundaries, not decoration, and `platforms/cli/commands/export_utils.py` pairs adjacent stub/solution cells by a simple lookahead with no verification that the first cell isn't itself already a solution. This is not hypothetical: in this repo's own history, running `ruff format` against these files (a supposedly safe, purely cosmetic operation) repositioned a `# %%` marker relative to an import statement and silently dropped that import from the exported package. A second incident dropped an entire class (`MSEBackward`) because two adjacent solution-tagged cells got misidentified as a disposable stub. Both bugs passed local testing clean and only surfaced in CI, because the local venv was testing a stale prebuilt package rather than a fresh export. Section 3 exists because of these two incidents specifically.

As of this writing: 20 curriculum modules, ~53K lines of curriculum source, ~13K lines of CLI source, 90 test files, roughly 1,080 test functions, and a baseline of 897 passing / 2 known-failing / 33 skipped on a clean run. The 2 are: `test_pip_available`, which fails on any dev machine whose venv lacks a `pip` module (an environment fact, not a code defect), and `test_milestone_run_checks_prerequisites`, whose 5-second timeout assumes the local package is unimplemented and times out instead if a maintainer already has full solutions exported, a real test-isolation gap, tracked but not yet fixed. Until 2026-08-31 this baseline was 858 passing / 41 known-failing; see section 6's newest entry for what closed that gap.

## 2. Test harnesses

Three genuinely different layers, each catching a different failure mode:

**pytest, per-module.** Every curriculum module (`data/src/<NN>/tests/`) and the CLI (`platforms/cli/tests/`) has its own pytest suite. This is the fast, developer-facing layer: run it locally against a freshly exported package (see the pitfall in section 3.2) and it catches ordinary logic bugs the same way any application's unit tests would.

**The 7-stage CI pipeline** (`.github/workflows/validate.yml`), the closest thing this repo has to SQLite's "multiple independent harnesses": inline build, unit, integration, CLI, E2E, fresh install (a real Docker-based install from a clean clone), and user journey (a destructive full progressive-build-and-milestone run). These aren't redundant with local pytest, they run on both Linux and Windows, which matters more than it sounds: a real bug this session only reproduced on Windows (an emoji/unicode encoding crash from the console's legacy codepage, see section 4.1). A Linux-only CI run would never have caught it.

**Stub-variant / solution-variant equivalence**, which has no real SQLite analog and is TrenTorch-specific: `data/src/` is the one source of truth, and `tren dev export` derives two different things from it (`data/modules/`, the student-facing stub, and `data/solutions/`, the maintainer/CI reference). Whatever a student ends up running once they correctly fill in a stub has to behave identically to the solution variant. This equivalence is currently checked only implicitly, by both variants passing the same test suite; section 3.2 proposes making it an explicit, direct check.

## 3. Structural integrity: the actual malformed-input problem

SQLite's fuzz and malformed-database testing exists because SQLite has to survive adversarial or corrupted input. TrenTorch's equivalent risk isn't adversarial, it's *well-intentioned tooling that doesn't understand the jupytext convention*. Both real incidents in section 1 were caused by a formatter doing exactly what formatters are supposed to do, just on a file whose structure it couldn't see.

### 3.1. What exists today

`pyproject.toml` permanently excludes all 20 `data/src/<NN>/<NN>.py` files from ruff (lint and format), with a comment explaining why. This is a real fix, but it's a static allowlist: it stops ruff specifically, and it stops it by exclusion rather than by detecting the actual failure mode. It does nothing if someone runs a different formatter, hand-edits a `# %%` line, or if the exclusion list itself gets edited by someone who doesn't know why it's there.

### 3.2. What's missing: a structural verification script

The actual invariant that needs checking is narrower and more mechanical than "don't reformat these files": for every curriculum module, every solution-tagged cell must be immediately preceded by exactly one non-solution stub cell, and the stub/solution split must produce a stub variant where every function body raises `NotImplementedError` (or is otherwise clearly incomplete) and a solution variant with no `NotImplementedError` left anywhere and no duplicate top-level definitions.

A script (`platforms/dev_tools/scripts/verify_cell_structure.py`, or similar) that walks `data/src/*/`, runs the same `_CELL_SPLIT`/`_is_solution_cell` logic `export_utils.py` uses, and asserts these two properties for every module would have caught both real incidents *before* a full CI run was needed to surface them, and it's cheap to run: no build, no package export, just parsing. This belongs as an early step in `validate.yml`'s Stage 1, not buried behind a full pytest run.

## 4. Anomaly testing, scoped to what's real

SQLite simulates OOM and I/O failures because it has to survive them in the field. TrenTorch doesn't have that exposure, but it has its own version of "things go wrong on some platforms and not others."

### 4.1. Encoding and platform tests

The Windows console's legacy codepage (not UTF-8) causing `UnicodeEncodeError` on ordinary emoji output (`platforms/cli/main.py`'s startup fix) is this project's actual "small embedded platform" analog: an environment class that behaves differently in a way that's easy to miss if development happens on Linux/Mac. The Windows leg of CI catches this at the pipeline level, but there's no fast, targeted test that would catch a regression here without waiting on a full Stage 1-5 run. A dedicated smoke test that imports `platforms.cli.main` and prints a string containing emoji, run first on the Windows CI leg, would isolate this class of bug in seconds instead of minutes.

### 4.2. Interrupted / partial state

`tren dev export` can leave a module directory that exists but is empty if a conversion attempt fails partway (jupytext not on PATH is the documented real case, `platforms/cli/processes/module_workflow/workflow.py`'s `start_module` already checks for the notebook file itself rather than trusting directory existence, specifically because of this). That's a real, already-handled edge case; it doesn't yet have a dedicated test that simulates the interruption and confirms the check works, which would be worth adding given it was clearly worth defending against in the first place.

### 4.3. Fresh-install and progressive-build order

Stage 6 (Docker-based fresh install) and Stage 7 (progressive module-by-module build) already exist and are the right shape for this category. Worth calling out explicitly as the load-bearing tests they are, since they're the ones that catch "works on my already-set-up machine, breaks for an actual new contributor."

## 5. Numerical correctness: the missing fuzz-testing analog

SQLite's fuzzers exist to find inputs that produce a crash or a wrong answer. TrenTorch's fixed-example unit tests (specific input tensors, specific expected outputs) verify correctness at the points someone thought to test, but they don't verify it *in general* the way property-based testing does. This is the one area where TrenTorch is currently weaker than a comparably-sized project should be, and it's the highest-value addition this document proposes.

**Proposal:** property-based tests (via Hypothesis) for the numerical core, specifically `Tensor`, `autograd`, and the layer/loss primitives. Generate random shapes, dtypes, and values within reasonable bounds, and check two things: forward-pass output matches numpy's equivalent operation within floating-point tolerance, and backward-pass gradients match a finite-difference numerical gradient check. This directly targets the actual failure mode a fixed-example test suite misses: an operation that's correct for the specific tensors someone happened to write a test for, but wrong for a shape or broadcast pattern nobody thought of. It's also realistically scoped: a few hundred lines of Hypothesis strategies covering the ~10-15 core tensor operations, not an open-ended fuzzing campaign.

## 6. Regression testing

Every bug fixed gets a permanent test, same policy SQLite states outright, and this repo's own recent history is the concrete seed list for it, not a hypothetical:

- The `# %%` marker misdetection that dropped `MSEBackward` from `data/trentorch/core/autograd.py` (module 06)
- The same misdetection dropping the `Profiler` import from module 19/20's export
- `check_tinytorch_package()` checking `import tito`, a package name that hasn't existed since the rename to `trentorch`, silently returning `False` on every run
- The Windows reinstall-skip check in `setup.py` calling `pip show tinytorch` for the same reason
- `display.py`'s dead `status_text` variable, whose `else` branches ended in a bare `"LOCKED"` string-literal statement instead of an assignment
- `welcome.yml` calling `actions/first-interaction` with hyphenated input names (`repo-token`) when the action's real inputs use underscores (`repo_token`), failing on every single run since it was added
- `subprocess.run(..., text=True)` and `Path.read_text()` across 9 test files defaulting to the system locale's preferred encoding (cp1252 on Windows without `PYTHONUTF8` set) instead of UTF-8, crashing on any captured `tren` output containing emoji. This was 39 of the 41 "known failures" referenced in section 1 turning out to be one bug, invisible in CI because `validate.yml` sets `PYTHONIOENCODING`/`PYTHONUTF8` globally but nothing in local dev setup does the same. A real, hands-on audit of the "41 known failures" baseline (not just trusting it as stable) found this in under an hour; it had been sitting there since before this document was written

None of these needed a new testing *category* to catch, they needed the specific regression test that would have failed loudly the first time, and didn't exist. Where one of these doesn't already have a matching test, adding it is higher priority than any of the proposals in sections 3-5.

## 7. What this project deliberately does not do

SQLite is explicit that 100% MC/DC coverage and billion-iteration fuzzing are justified for SQLite specifically, not for a typical application, and that over-investing here has a real cost (defensive code that MC/DC testing discourages is exactly the code that makes a project more fragile against real-world malformed input). TrenTorch should be equally explicit in the other direction:

- **No OOM or I/O-failure simulation.** TrenTorch isn't deployed on memory-constrained embedded hardware or expected to survive a full disk mid-write. This category doesn't apply.
- **No crash/power-loss testing.** There's no durability contract here comparable to a database's atomic commit guarantee.
- **No branch-coverage or MC/DC targets.** Chasing 100% branch coverage on a 20-module teaching codebase would mean writing tests for code paths that exist to demonstrate a concept once, not to be hardened against adversarial input. Coverage as a rough signal (which modules have thin test files) is useful; coverage as a target number is not.
- **No large-scale fuzzing infrastructure.** Section 5's Hypothesis-based proposal is deliberately scoped to the numerical core, not an open-ended campaign against the whole codebase. TrenTorch has no adversarial threat model that would justify more than that.

## 8. Pre-merge checklist

A short, concrete list, not a 200-item release checklist, scoped to the failure modes actually observed in this repo:

1. If curriculum source (`data/src/`) changed: re-run `tren dev export --all` and diff the result against the previous known-good export before trusting a local pytest run. A stale prebuilt package in the local venv gives a false "zero regressions" signal (this exact trap produced two of the incidents in section 6).
2. If any workflow file or `platforms/cli/` changed: confirm CI actually ran (not `[skip ci]`'d) and both the Linux and Windows legs of Stage 1 passed, not just Linux.
3. If a third-party GitHub Action's `with:` inputs changed or were copied from another workflow: verify the input names against the action's own `action.yml`, not against what "looks right" (see the `welcome.yml` entry in section 6, discovered by testing the exact same file on a separate throwaway repo before assuming a fix worked).
4. If a bug was just fixed: confirm a regression test for it exists before considering the fix done, per section 6's policy.
5. If any `.py` file changed: run `ruff format --check .` locally before pushing, not just a syntax check. A syntax-only check passes on code that's syntactically valid but not reformatted, and CI's separate `Lint` workflow will catch it anyway, just after a round-trip instead of before one.
