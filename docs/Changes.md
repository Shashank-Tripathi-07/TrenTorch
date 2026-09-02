# Changes

User-facing log of new features, bots, and rules added to this project. Not a full commit history (see `maintainer_use/CHANGELOG.md` for that) -- this is the "what's new for me" version, kept short and current.

## 2026-09-02

**Bots (automatic, no action needed from you)**
- PRs and issues get auto-labeled by file path / keyword.
- ruff lint/format issues on your PR get auto-fixed and pushed to your branch. No manual `ruff format` needed.
- Your PR gets auto-updated with its base branch if it falls behind.
- New CodeQL security alerts auto-open a tracking issue.
- `settings.ini` vs `pyproject.toml` version mismatch gets flagged on your PR automatically.
- Merged branches get auto-deleted (`delete_branch_on_merge`).
- Dependabot PRs (patch/minor version bumps) get auto-approved and auto-merged once CI passes. Major bumps get flagged for manual review instead.
- Weekly OpenSSF Scorecard scan reports supply-chain/process risk (unpinned actions, token permissions, branch protection gaps) to the Security tab, same place CodeQL results show.
- Every PR gets checked for a known-vulnerable or copyleft-licensed dependency before it can merge.
- An issue assigned to someone with no PR referencing it after 7 days gets a warning comment; after 7 more days of silence it's auto-unassigned so someone else can pick it up.
- The Contributors table (name, role, PR/issue counts) is generated directly into README's "Team Engineers" section every night from real activity -- no separate file to go stale.

**New rules**
- 1 approving review required before any PR merges (except admin).
- First-time / external contributors: open an issue first, get it assigned to you, then open the PR referencing it (`Fixes #N`). A bot flags PRs that skip this.
- Anyone can open a PR now -- was broken (collaborators-only), fixed.
- PR titles must follow Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, etc.) -- checked automatically on open/edit.
- New default branch: `dev`. Target your PRs at `dev`, not `main`. `main` is now the protected, stable branch, only updated by merging `dev` into it periodically. Same 1-review rule applies to both.

**Labels you'll see**
- `Maintainer`, `Core Engineer` -- auto-applied by who opens the PR.
- `cli`, `dev-tools`, `curriculum`, `milestones`, `tests`, `security`, `dependencies`, `documentation`, `github_actions` -- auto-applied by what the PR touches.

**Other**
- Version reset: `0.1.13` -> `0.0.1`.
- CLI docs (`docs/*.md`) are validated against the real CLI automatically (pre-commit + CI) -- a doc mentioning a command that doesn't exist fails the check.
- Full repo-wide rename: every leftover `tinytorch`/`tito` reference (code, docs, config, kernel name, env vars) is now `trentorch`/`tren`. No more legacy names anywhere in our own surface.

---

Bug-fix/security details from this pass: see the linked PRs, or the full history in `maintainer_use/CHANGELOG.md`.
