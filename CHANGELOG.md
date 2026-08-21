# Changelog

All notable changes to TrenTorch are recorded here, in chronological order.
This file is maintained by hand alongside every merge to `main`, so it stays
a reliable log of what shipped and why, not just what the commit messages
happened to say.

## 2026-08-22

### Contributor system

- Added a contributor welcome bot (`.github/workflows/welcome.yml`) that thanks
  first-time issue/PR authors and points them at `CONTRIBUTORS.md`.
- Added a live-updating `CONTRIBUTORS.md` and
  `.github/scripts/update_contributors.py`, which recomputes real issue/PR/merge
  counts per contributor from the GitHub API via
  `.github/workflows/update-contributors.yml`.
- Fixed the workflow's missing `issues: read` permission, which broke
  `gh issue list` in CI (PR #13).
- Filtered bot accounts (`is_bot`) out of the contributor stats so the bot's own
  update PRs don't count itself as a contributor.
- Iterated on auto-merge behavior for the bot's own data-update PRs: removed it
  after review, then restored it once confirmed safe (the data is deterministic,
  API-computed, not a judgment call) (PR #14).
- Redesigned `CONTRIBUTORS.md` from a plain table into an avatar grid matching
  the README's Team Engineers style, skipping the emoji contribution-key system.
- Added `AVATAR_OVERRIDES` support so a contributor can use a custom checked-in
  image (`.github/assets/`) instead of their live GitHub avatar; used for
  Rocky's avatar everywhere it appears in the repo.
- Added Aadityansha to the Team Engineers section in `README.md`.
- Added a `workflow_dispatch` trigger to `update-contributors.yml` for manual
  runs and testing.

### Governance

- Enabled branch protection on `main`: all changes must land via pull request
  (admin bypass retained for Rocky), force-pushes and branch deletion blocked.

### CI stabilization (fix/restore-upstream-attribution, PR #10)

- Fixed the real installed `tren` command being completely broken for every
  user: `pyproject.toml`'s console-script entry point pointed at the wrong,
  minimal `tren.cli:main` instead of the actual full CLI in `tren.main:main`.
  Found by testing a genuine `pip install -e .`, since local testing via
  `bin/tren` had been silently bypassing the installed entry point all along.
- Moved `tools/export_sanitizer.py` into the shipped package
  (`trentorch/export_sanitizer.py`); the dev-only `tools/` directory isn't
  installed, so every real install hit `ModuleNotFoundError` on import.
- Renamed `.tito/` to `.tren/` for real, with a one-time, safe migration on
  first run for existing progress data, not a compatibility shim.
- Fixed hardcoded `tinytorch` package paths that were silently writing module
  exports to a stale, gitignored `tinytorch/` directory instead of `trentorch/`.
- Fixed CLI branding regressions (`TinyTorchCLI` vs `TrenTorchCLI`, `tito`
  references in welcome screens, logs, and `prog=`) that were blocking
  `tests/cli/` collection.
- Fixed `test_06_autograd_progressive.py` failing when run standalone by
  making its `enable_autograd()` side effect explicit instead of relying on
  collection order.
- Fixed `scripts/test-fresh-install.sh` still calling the deleted `tito`
  command, breaking the Docker-based fresh-install CI stage.
- Fixed Stage 7 (User Journey): reset commands were deleting hand-written
  package files (`platform.py`, `export_sanitizer.py`), `conftest.py`'s package
  check was over-strict for progressive single-module builds, and the CNN
  milestone's subprocess timeout (300s) was too short for its real ~7.5 minute
  training run (raised to 900s).
- Verified the full fix end-to-end via `tren dev test --user-journey --ci`
  locally (20 modules, 6 milestones, all passing) before merging.
- Restored correct TinyTorch/TrenTorch attribution broken by the blanket
  tito-to-tren rename: TinyTorch is the real upstream project name and must
  stay TinyTorch wherever it's referenced as such; only our own fork's
  branding became TrenTorch.

## 2026-08-21

### Rename: tito/tinytorch → tren/trentorch (PR #6)

- Renamed the `tito` CLI to `tren` and the `tinytorch` package to `trentorch`
  across the codebase.
- Merged with 46 conflicts resolved on a first-touch-wins basis.
- Recreated `bin/tren` (deleted during the rename, never replaced) and fixed
  dangling `tito` imports left behind by the rename.
- Removed the dangling `tito` console-script entry point after the merge
  deleted the `tito/` package.
- Reconstructed `trentorch/__init__.py`'s full 20-module forward-export
  surface, lost during the merge and restored from git history.

### Feature: multi-platform conversion pipeline (PRs #1, #2)

- Added a multi-format conversion pipeline (qmd, ipynb, txt, yaml) and a
  platform runtime adapter, integrated into the `tren` CLI.

### CI

- Added GitHub Actions CI (`validate.yml`), adapted from TinyTorch's
  dev-branch validate workflow: Configure, Inline Build, Unit Tests,
  Integration, CLI Tests, E2E Tests, Fresh Install (Docker), and User Journey
  stages, matrixed across Ubuntu and Windows.
- Fixed a concurrency race that let a later merge cancel an earlier merge's
  in-flight run on `main` (reported as cancelled, not failed); added a status
  badge to `README.md`.
- Fixed `.gitignore` swallowing `bin/tito`, which broke every CI stage.
- Fixed CI not tracking `datasets/` properly and dropped an unsupported
  `--non-interactive` flag.
- Fixed Stage 6 (fresh install) failing to authenticate against the private
  repo; authenticated with `GITHUB_TOKEN` instead.
- Aligned the nbdev `lib_path` and removed an orphaned `tito` command
  reference.
- Added a dynamic path fix to pass CI Stage 6 on forks.
- Sped up CI by caching pip dependencies and sharing Stage 1's built package
  across Stages 2-5.

### Project setup

- Imported TinyTorch from the `cs249r_book` dev branch as the base for this
  fork.
- Added contributor docs, adapted from `cs249r-docs`.
- Rewrote `README.md` with TrenTorch's own pitch, added the pulsing bolt mark
  and night-shift log graphic, and added the Team Engineers section.

## Attribution

TrenTorch is built on the curriculum and foundation of
[TinyTorch](https://mlsysbook.ai/tinytorch) (Harvard CS249r), created by
Prof. Vijay Janapa Reddi and the ML Systems Book community. See
[README.md](README.md#credit-where-its-due) for full credit.
