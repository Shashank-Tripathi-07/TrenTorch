# Changelog

| Date | Description | Done by | Reviewed by | Merged by |
|---|---|---|---|---|
| 2026-08-21 | Imported TinyTorch from the cs249r_book dev branch as the fork base | Rocky | Rocky | Rocky |
| 2026-08-21 | Rewrote README with TrenTorch's own pitch, bolt mark, and Team Engineers section | Rocky | Rocky | Rocky |
| 2026-08-21 | Added contributor docs, adapted from cs249r-docs | Rocky | Rocky | Rocky |
| 2026-08-21 | Added GitHub Actions CI, adapted from TinyTorch's dev-branch validate workflow | Rocky | Rocky | Rocky |
| 2026-08-21 | Sped up CI: cached pip deps, shared Stage 1's build across Stages 2-5 | Rocky | Rocky | Rocky |
| 2026-08-21 | Fixed .gitignore swallowing bin/tito, which broke every CI stage | Rocky | Rocky | Rocky |
| 2026-08-21 | Fixed CI not tracking datasets/ and dropped an unsupported flag | Rocky | Rocky | Rocky |
| 2026-08-21 | Fixed Stage 6 auth against the private repo using GITHUB_TOKEN | Rocky | Rocky | Rocky |
| 2026-08-21 | Added multi-platform conversion pipeline (qmd, ipynb, txt, yaml) and CLI integration (PR #1) | Shivtej Gaikwad | Rocky | Rocky |
| 2026-08-21 | Aligned nbdev lib_path and removed an orphaned tito command | Shivtej Gaikwad | Rocky | Rocky |
| 2026-08-21 | Added dynamic path fix to pass CI Stage 6 on forks (PR #2) | Shivtej Gaikwad | Rocky | Rocky |
| 2026-08-21 | Renamed tito CLI to tren and tinytorch package to trentorch (PR #6) | Aadityansha | Rocky | Rocky |
| 2026-08-21 | Fixed concurrency race that cancelled main-branch CI on rapid merges, added status badge | Rocky | Rocky | Rocky |
| 2026-08-21 | Added multi-platform conversion pipeline and platform runtime adapter (own implementation) | Rocky | Rocky | Rocky |
| 2026-08-21 | Removed dangling tito entry point left after the tren rename merge | Rocky | Rocky | Rocky |
| 2026-08-21 | Restored correct TinyTorch/TrenTorch attribution broken by the blanket rename (PR #10) | Rocky | Rocky | Rocky |
| 2026-08-21 | Added bin/tren wrapper and fixed dangling tito imports left by the rename | Rocky | Rocky | Rocky |
| 2026-08-22 | Fixed test_06_autograd_progressive.py failing when run standalone | Rocky | Rocky | Rocky |
| 2026-08-22 | Fixed hardcoded tinytorch paths breaking every real export and check | Rocky | Rocky | Rocky |
| 2026-08-22 | Fixed CLI branding regressions blocking tests/cli/ collection | Rocky | Rocky | Rocky |
| 2026-08-22 | Fixed scripts/test-fresh-install.sh calling the deleted tito command | Rocky | Rocky | Rocky |
| 2026-08-22 | Fixed the real installed tren command being completely broken for every user | Rocky | Rocky | Rocky |
| 2026-08-22 | Renamed .tito/ to .tren/ for real, with a one-time migration, not a shim | Rocky | Rocky | Rocky |
| 2026-08-22 | Fixed Stage 7: preserved hand-written package files, fixed a stale test gate and a short milestone timeout | Rocky | Rocky | Rocky |
| 2026-08-22 | Removed tagline from README | Rocky | Rocky | Rocky |
| 2026-08-22 | Added Aadityansha to the Team Engineers section | Rocky | Rocky | Rocky |
| 2026-08-22 | Added contributor welcome bot and a live-updating CONTRIBUTORS.md | Rocky | Rocky | Rocky |
| 2026-08-22 | Added workflow_dispatch trigger to update-contributors.yml for manual runs | Rocky | Rocky | Rocky |
| 2026-08-22 | Fixed update-contributors.yml missing issues:read permission (PR #13) | github-actions bot | Rocky | github-actions bot |
| 2026-08-22 | Stopped the contributors bot from auto-merging its own PRs | Rocky | Rocky | Rocky |
| 2026-08-22 | Restored auto-merge for CONTRIBUTORS.md update PRs (PR #14) | github-actions bot | Rocky | github-actions bot |
| 2026-08-22 | Redesigned CONTRIBUTORS.md as an avatar grid, no emoji contribution-key | Rocky | Rocky | Rocky |
| 2026-08-22 | Used Rocky's custom avatar instead of the GitHub profile picture everywhere it appears | Rocky | Rocky | Rocky |
| 2026-08-22 | Added CHANGELOG.md covering full commit and merge history | Rocky | Rocky | Rocky |
| 2026-08-22 | SHA-pinned every third-party GitHub Action and added path filters to skip full CI runs on doc-only changes | Rocky | Rocky | Rocky |
| 2026-08-22 | Replaced duplicated per-stage checkout and setup steps across 6 jobs with one reusable workflow | Rocky | Rocky | Rocky |
| 2026-08-22 | Fixed a shell injection pattern in Stage 6 by moving a branch name out of an inline script and into an env var | Rocky | Rocky | Rocky |
| 2026-08-22 | Added Dependabot config for the github-actions ecosystem, then merged the 5 version-bump PRs it opened | Rocky | Rocky | Rocky |
| 2026-08-22 | Cached installed pip dependencies across CI jobs; first attempt broke jupyter by only caching site-packages, fixed by caching the scripts directory too | Rocky | Rocky | Rocky |
| 2026-08-22 | Scoped pytest-xdist parallelism to CLI and E2E tests only, after measuring no benefit for unit tests and a new failure under parallel integration tests | Rocky | Rocky | Rocky |
| 2026-08-22 | Restructured Stage 7 to stop rebuilding all 20 modules a second time and instead run milestones against Stage 1's already-built package | Rocky | Rocky | Rocky |
| 2026-08-22 | Fixed tren system reset silently never clearing progress, a leftover from the incomplete tito to tren rename | Rocky | Rocky | Rocky |
| 2026-08-22 | Decoupled Stages 5, 6, and 7 from Stages 2 to 4 so they run in parallel instead of waiting on the slowest of the three | Rocky | Rocky | Rocky |
| 2026-08-22 | Guarded 37 expensive analyze and benchmark demo blocks across 17 modules behind a CI check, kept full output for anyone running a module file directly | Rocky | Rocky | Rocky |
| 2026-08-22 | Ran module unit tests in process instead of spawning a subprocess per module, cutting Stage 1's real subprocess overhead | Rocky | Rocky | Rocky |
| 2026-08-27 | Fixed trentorch import failing for every `python -m platforms.cli.main` invocation, not just bin/tren, and several test-discovery paths silently reporting "0 tests, passed" after the data/ restructuring | Rocky | Rocky | Rocky |
| 2026-08-27 | Fixed CI build-artifact download landing in the wrong directory, a side effect of upload-artifact's least-common-ancestor path stripping | Rocky | Rocky | Rocky |
| 2026-08-27 | Found the real root cause of modules 08/09 being slow in CI: completing either one crossed a milestone's required-modules threshold and silently auto-ran a full real milestone during the maintainer's curriculum-verification loop; guarded it off for that loop only | Rocky | Rocky | Rocky |
| 2026-08-27 | Shrunk naive-Conv2d integration test inputs to full MNIST/CIFAR scale where only output shape was under test, cutting Stage 3 CI time 82-88% | Rocky | Rocky | Rocky |
| 2026-08-27 | Made command-module imports (numpy, trentorch, yaml) lazy: they were being paid on every single CLI invocation via main.py's eager instantiation of all 9 commands, regardless of which subcommand actually ran; cut `tren --help` from 2.7s to 0.8s | Rocky | Rocky | Rocky |
| 2026-08-27 | CI-scaled milestone 04's default training demo from 50 to 5 epochs; the milestone has no accuracy/epoch assertions of its own, pass/fail is just the return code, so this was the single largest line item in Stage 7 (164 of ~180 seconds) with zero real students affected (they still get the full 50-epoch experience) | Rocky | Rocky | Rocky |
| 2026-08-27 | Removed a duplicate nbdev re-export in Stage 1's inline test loop: `dev export` already exports each module to the package before `module complete` redundantly re-exported the same notebook to the same destination | Rocky | Rocky | Rocky |
| 2026-08-27 | Ran Stage 1's per-module export/complete calls in-process instead of spawning two subprocesses per module, cutting Stage 1 wall time roughly in half | Rocky | Rocky | Rocky |
| 2026-08-27 | Shrunk test/param scope across every remaining algorithmically-expensive test found by timing every module's unit tests: gradient-existence checks, dependency-integration checks, and a fusion-speedup benchmark with a 2000x2000 tensor and no assertion that actually needed it | Rocky | Rocky | Rocky |
| 2026-08-27 | End-to-end CI pipeline time: ~8m15s to ~3m47s (54% reduction), verified live on GitHub Actions after every fix | Rocky | Rocky | Rocky |
| 2026-09-01 | Fixed `tren module test` reporting a full pass on a completely unsolved notebook: Phase 1 runs data/src/ (which already contains the solution) and Phase 2 tests the installed trentorch package (which ships pre-built), neither reads the student's notebook. Added a Phase 0 that does (issue #71) | Maanas Tyagi | TBD | TBD |
| 2026-09-01 | Fixed `tren module complete` showing a truncated traceback with no actual error message on a failed unit test: `_parse_test_output()` kept the first 5 lines of the traceback instead of the last 5, so it always showed call-stack frames and cut off exactly before the real exception message. Verified with the real before/after traceback on an unsolved module 01 (issue #76) | Maanas Tyagi | TBD | TBD |
| 2026-09-01 | Follow-up on the above: the `_parse_test_output()` fix alone didn't actually resolve #76, since `run_inline_unit_tests`'s verbose console-print loop -- the code path `tren module complete` actually prints through -- re-sliced the already-fixed error string with the identical first-N-instead-of-last-N bug a second time. Fixed both display sites (`run_inline_unit_tests`, `run_integration_tests`) plus a third, untouched instance of the same bug in `run_integration_tests`'s collection-error path. Verified live: the exact repro from #76 still showed zero exception-message lines with only the first fix applied; now shows the real `NotImplementedError` message end to end. Added a regression test asserting on the actual printed console output, not just `_parse_test_output`'s return value, since that gap is exactly how the incomplete first fix passed review | Rocky | Rocky | Rocky |
| 2026-09-01 | Fixed `tren --version` always printing "vunknown": `_get_version()` looked for pyproject.toml one folder too shallow (platforms/ instead of the repo root), so the file was never found and it silently fell back to "unknown" (issue #80) | Maanas Tyagi | TBD | TBD |
| 2026-09-01 | Fixed `tren olympics` telling students to run `tito community login`, a command that was fully removed, not renamed. Removed the dead instruction, and fixed two more lines on the same screen still telling students to run `tito module status` / `tito milestone status` instead of `tren` -- the tito to tren rename never reached this file (issue #81) | Maanas Tyagi | Rocky | Rocky |
| 2026-09-01 | Expanded `test_server.py` from 4 to 19 test cases covering every `tren serve` REST endpoint, SSE stream wire format, and security guards; also finished the `tito` to `tren` cleanup in `tren system health` and other CLI status output | Shivtej Gaikwad | Rocky | Rocky |
| 2026-09-01 | Fixed a typo in the new PR's own rebrand pass that dropped `  t` from one `tren dev export` hint (rendered as `ren dev export 01`), and fixed the real bug the new tests surfaced: `handler.py`'s subprocess calls used `text=True` with no explicit encoding, which falls back to `cp1252` on Windows and crashes on Rich's UTF-8 output -- hanging `tren serve`'s module-test SSE stream and module-complete response for any Windows user | Rocky | Rocky | Rocky |
| 2026-09-01 | Full-repo survey for leftover `tito`/`tinytorch` references after the rename. Found the celebration panel every student sees after `tren module complete` telling them to `from tinytorch import X`, a package that has been `trentorch` since PR #6 -- copy-pasting it crashes with ModuleNotFoundError. Fixed it, plus a dead `tito` quick-commands block in the dev setup script. Everything else found (jupyter kernel name, `.tinytorch` profile dir, `tren system update`'s stale directory layout, product-narrative branding) is either self-consistent internal naming or a separate, larger issue -- documented, not silently patched | Rocky | Rocky | Rocky |
