# TrenTorch: Contributor Docs

Technical design and implementation documentation for the codebase in this repo. Adapted from the [`cs249r-docs`](https://github.com/Shashank-Tripathi-07/cs249r-docs) project's `tinytorch/` documentation set, which was written for the upstream [`harvard-edge/cs249r_book`](https://github.com/harvard-edge/cs249r_book) monorepo that TinyTorch (and by extension TrenTorch) originates from.

## What's here

| Doc | What it's for |
|---|---|
| [`design.md`](design.md) | What TrenTorch's codebase is, why it's built the way it is, and the full technology stack. Start here. |
| [`implementation.md`](implementation.md) | The file map and real code walkthroughs for the module system and the `tren` CLI. Read this when you're ready to touch code. |
| [`system_design.md`](system_design.md) | How the `tren` CLI and the module pipeline actually work end to end, dependencies, data flow, error handling. |
| [`command-reference.md`](command-reference.md) | Every `tren` CLI command and flag. |
| [`deep-dive.md`](deep-dive.md) | A first-principles walkthrough of what happens from `install.sh` through module export to grading. |
| [`coding-style.md`](coding-style.md) | The honest answer to "what linter applies here." |

## What's not here, and why

Two upstream docs were dropped rather than adapted:

- **`ci-workflows.md`**: covered five GitHub Actions workflows (validate, preview, publish, PDF builds) tied to the `harvard-edge/cs249r_book` repository's own secrets and deploy targets. None of that CI/CD exists in this fork.
- **`perspective.md`**: recorded the upstream maintainer's governance decisions (what gets accepted into core modules, branch/PR policy for that repo). Specific to that project's own maintainership, not this one.

Within the docs that are here, anything describing the **community dashboard, progress sync, or `tren community`/`tren login`** is marked inline as upstream-only: that code shipped with the codebase we forked from, but the backend it talks to (`mlsysbook.ai`, Netlify, Supabase) belongs to the original TinyTorch project, not TrenTorch. It's documented because the code is still physically present, not because it works standalone here.

## A note on "TinyTorch" in these docs

These docs still say "TinyTorch" throughout, because that's the actual name of the package, CLI banner text, and class names in this codebase (`import tinytorch`, the `tren` CLI, `src/`, `tinytorch/core/`). That's accurate, not a leftover to clean up. "TrenTorch" is the name of this project and this repo; "TinyTorch" is still the name of the software it builds.
