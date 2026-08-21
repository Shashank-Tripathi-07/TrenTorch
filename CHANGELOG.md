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
