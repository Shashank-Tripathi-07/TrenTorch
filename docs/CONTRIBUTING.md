# Contributing to TrenTorch 🔥

Thanks for your interest in contributing! TrenTorch is an educational ML framework, so every contribution should make things clearer for someone learning, not just more "correct" in the abstract:

- **Enhance learning** — make concepts clearer for students
- **Preserve the learning progression** — don't skip ahead of what a module has taught by that point
- **Keep it simple** — educational clarity over production complexity

## Getting started

```bash
git clone https://github.com/TrenTorch/TrenTorch.git
cd TrenTorch
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e ./
```

Then verify it works:

```bash
tren --version
tren system health
tren module status
```

Also worth a look: `docs/design.md` (educational context and teaching approach), `README.md` (repo structure), and the [wiki](https://github.com/TrenTorch/TrenTorch/wiki) (curriculum overview, CLI reference, architecture).

## Workflow

```bash
git checkout main
git pull origin main
git checkout -b your-github-username/your-improvement

# make your changes, then test them
pytest tests/
tren module test 01

git add <specific-files>    # not `git add .` — stage files explicitly
git commit -m "Fix tensor broadcasting bug in Module 02"
git push origin your-github-username/your-improvement
# then open a PR on GitHub targeting main
```

- **Branch names**: `<github-username>/<feature-name>`, lowercase, hyphens (e.g. `shivtej/fix-attention-mask`). Not `feature/`, not a bare description — your username first, always.
- **Never work directly on `main`.**
- **Always use the virtual environment.**

## Testing

```bash
tren module test NN         # e.g. tren module test 01 -- one module's own tests
pytest tests/integration/    # cross-module integration tests
pytest tests/                # everything: integration, regression, e2e
pytest platforms/cli/tests/  # the tren CLI's own test suite
```

CI (`.github/workflows/validate.yml`) has to be green before a PR merges — see it run on your own PR rather than only trusting local results.

## Code standards

**Students** (using the framework): work in `data/modules/NN_name/name.ipynb` in Jupyter; export with `tren module complete N`.

**Contributors** (improving the framework itself): edit `data/src/NN_name/NN_name.py` (the source of truth); notebooks are generated from it via `tren dev export`. Include:

- immediate tests after each implementation
- memory/performance analysis where it's relevant to the module's own systems focus
- clear explanations — clarity is the actual point of this codebase

## Opening an issue

**Bug report**: what happened vs. what you expected, exact steps to reproduce (the `tren` commands or notebook cells), the error output, and your OS + `tren --version` / `python --version`.

**Feature request**: what's missing or confusing, what you'd want instead, and any alternatives you considered.

Security issues should **not** go through a public issue — see [`SECURITY.md`](../SECURITY.md) for the private reporting flow.

## Opening a pull request

Describe what changed and why, how you tested it, and confirm `ruff check` / `ruff format --check` pass locally. Keep PRs scoped to one thing — a bug fix and an unrelated refactor in the same PR is harder to review and harder to revert if something's wrong.

## Releases (maintainers)

[Semantic versioning](https://semver.org/) — patch for fixes, minor for new features/modules, major for breaking changes. There's no automated release pipeline yet: `pyproject.toml`'s version is bumped by hand, and changes land by merging to `main` once CI is green. Contributors don't need to think about version bumps.

---

**Questions?** Open a GitHub Discussion, or check the wiki.
