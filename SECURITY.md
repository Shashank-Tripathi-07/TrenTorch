# Security Policy

TrenTorch is an educational ML framework: a local CLI and a from-scratch NumPy-based library, not a hosted service. There's no user data, no network-facing component beyond what `pip`/`git` themselves touch, and no production deployment. That said, real security issues can still exist here — arbitrary code execution via a crafted input, a path-traversal bug in the CLI's file handling, a dependency with a known CVE, or a workflow misconfiguration that leaks a secret — and are worth reporting properly rather than as a public issue.

## Reporting a Vulnerability

**Please don't open a public GitHub issue for a security vulnerability.**

Instead, use GitHub's private reporting flow:

1. Go to the [Security tab](https://github.com/TrenTorch/TrenTorch/security)
2. Click **"Report a vulnerability"**
3. Describe the issue: what's affected, how to reproduce it, and its impact

This opens a private advisory only the maintainer (and anyone you add) can see, so the issue isn't public until there's a fix.

## What's in scope

- The `tren` CLI and everything under `platforms/cli/`
- The `trentorch` package generated from the curriculum (`data/src/` → `data/trentorch/`)
- This repository's own GitHub Actions workflows (`.github/workflows/`) and their permissions/secrets handling

## What's out of scope

- The educational curriculum content itself being *pedagogically* naive or slow on purpose (e.g. the deliberately naive nested-loop `Conv2d` implementation) — that's the point of the course, not a bug
- Issues that only reproduce by running arbitrary untrusted code you've written yourself inside a module (this is a learn-by-building framework; a student's own in-progress code isn't a trust boundary)

## Response

This is a solo/small-team-maintained project, not a company with a security team or an SLA. Reports will be acknowledged and looked at as soon as reasonably possible, but there's no guaranteed response time.

## Supported versions

There's no formal release/versioning cadence yet (see `docs/CONTRIBUTING.md`) — security fixes land on `main`, which is always the version to use.
