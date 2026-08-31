# TrenTorch: Contributor Docs

Technical design and implementation documentation for the codebase in this repo. Adapted from the [`cs249r-docs`](https://github.com/Shashank-Tripathi-07/cs249r-docs) project's `trentorch/` documentation set, which was written for the upstream [`harvard-edge/cs249r_book`](https://github.com/harvard-edge/cs249r_book) monorepo that TrenTorch (and by extension TrenTorch) originates from.

## What's here

| Doc | What it's for |
|---|---|
| [`design.md`](design.md) | What TrenTorch's codebase is, why it's built the way it is, and the full technology stack. Start here. |
| [`implementation.md`](implementation.md) | The file map and real code walkthroughs for the module system and the `tren` CLI. Read this when you're ready to touch code. |
| [`system_design.md`](system_design.md) | How the `tren` CLI and the module pipeline actually work end to end, dependencies, data flow, error handling. |
| [`command-reference.md`](command-reference.md) | Every `tren` CLI command and flag. |
| [`deep-dive.md`](deep-dive.md) | A first-principles walkthrough of what happens from `pip install -e .` through module export to grading. |
| [`coding-style.md`](coding-style.md) | The honest answer to "what linter applies here." |
| [`testing-strategy.md`](testing-strategy.md) | What's tested, why, and where the real risk actually lives, with the export pipeline's known fragility as the central case. |

## What's not here, and why

Two upstream docs were dropped rather than adapted:

- **`ci-workflows.md`**: covered five GitHub Actions workflows (validate, preview, publish, PDF builds) tied to the `harvard-edge/cs249r_book` repository's own secrets and deploy targets. None of that CI/CD exists in this fork.
- **`perspective.md`**: recorded the upstream maintainer's governance decisions (what gets accepted into core modules, branch/PR policy for that repo). Specific to that project's own maintainership, not this one.

This fork also inherited a community dashboard, progress-sync path, and `tren community`/`tren login` commands from the codebase we forked from; the backend they talked to (`mlsysbook.ai`, Netlify, Supabase) belonged to the original TrenTorch project, not TrenTorch, so they never worked standalone here. That code, along with the Quarto-based docs site it shipped alongside, has since been removed rather than kept as dead code pointing at someone else's infrastructure. Where the docs below still reference this history, it's marked as removed, not upstream-only.

## A note on "TrenTorch" in these docs

These docs still say "TrenTorch" throughout, because that's the actual name of the package, CLI banner text, and class names in this codebase (`import trentorch`, the `tren` CLI, `src/`, `trentorch/core/`). That's accurate, not a leftover to clean up. "TrenTorch" is the name of this project and this repo; "TrenTorch" is still the name of the software it builds.
