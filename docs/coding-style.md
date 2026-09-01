# TrenTorch: Coding Style

Python style is enforced by [ruff](https://docs.astral.sh/ruff/), both locally and in CI. `pyproject.toml` has a `[tool.ruff]` section: `line-length = 110`, `target-version = "py310"`, lint rules `E`/`F`/`I`/`W`/`UP` (pycodestyle, pyflakes, import sorting, pyupgrade), deliberately with no docstring-content rules, no complexity/argument-count limits (this codebase's intentionally naive nested-loop `Conv2d` and similar are curriculum content, not bugs to flag), and no type-annotation requirements. Style and real correctness footguns only, not an educational-code straitjacket.

```bash
ruff check .           # lint
ruff format --check .  # format check (use `ruff format .` to actually apply)
```

Both run as a required CI job (`Ruff`, `.github/workflows/lint.yml`) on every PR, and both run locally via `.pre-commit-config.yaml`'s `ruff` and `ruff-format` hooks (`pre-commit install` once, or `pre-commit run --all-files` on demand).

**`data/src/<NN>_*/​<NN>_*.py` files are excluded from ruff entirely** (`extend-exclude` in `pyproject.toml`), along with the generated `data/trentorch/`, `data/modules/`, and `data/solutions/` trees. The curriculum source files use jupytext percent-format `# %%` cell markers that ruff has no notion of and will happily reorder relative to surrounding code, confirmed the hard way once, when `ruff format` alone silently merged an import into the wrong cell and dropped it from the exported package. Their own `tests/` subdirectories are ordinary Python and stay linted normally.

That same pre-commit config also runs two content checks that aren't style at all: `collapse_blank_lines.py` (markdown/Python, collapses 2+ blank lines to one) and a currently-disabled `validate_cli_docs.py` (predates the `data/` restructuring and the `tren` → `platforms/cli` reorg; see the comment in `.pre-commit-config.yaml` for what needs updating before it's safe to re-enable — [`cli_file_organization.md`](cli_file_organization.md) is the accurate command/file map in the meantime).

**Practical implication**: `ruff format`'s output is the actual target, not just "match the surrounding module's style by eye" — run it (or let pre-commit run it) before opening a PR. For a new module under `data/src/`, ruff won't touch it either way, so look at an adjacent module (`06_autograd`, `09_convolutions`) for the prevailing convention.
