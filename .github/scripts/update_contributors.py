#!/usr/bin/env python3
"""
Regenerates the "Team Engineers" avatar grid directly inside README.md from
real GitHub data (issues raised, PRs raised) for every contributor
discovered from the repo's PR and issue history. Renders an avatar grid
(the good part of the all-contributors project's UI) with plain-text stats
instead of an emoji contribution-type key (the part we're deliberately not
copying). Preserves each person's existing hand-written intro line; a
first-time contributor gets a generic placeholder intro instead of a
fabricated bio, since nobody should get credentials invented for them.

This used to write a separate docs/CONTRIBUTORS.md, with a hand-maintained
"Team Engineers" table duplicated (and already drifted -- missing a real
contributor, no PR/issue counts) directly in README.md alongside it. Two
places to keep in sync is how it drifted in the first place -- now there's
one real table, generated, living where people actually look for it.

Run by .github/workflows/update-contributors.yml, authenticated with
GITHUB_TOKEN via the gh CLI (already configured by actions/checkout /
the workflow's GH_TOKEN env var).
"""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = "TrenTorch/TrenTorch"
ROOT = Path(__file__).resolve().parent.parent.parent
README_FILE = ROOT / "README.md"
DEFAULT_INTRO = "New to TrenTorch — say hi and add a real intro!"
COLUMNS = 5

# Custom avatar images checked into the repo, used instead of the person's
# live GitHub avatar URL. Add an entry here (and the image under
# .github/assets/) for anyone who wants their own picture instead of
# whatever's on their GitHub profile. Path is relative to README.md (the
# repo root), since that's the only file this grid renders in now.
AVATAR_OVERRIDES = {
    "Shashank-Tripathi-07": ".github/assets/rocky-avatar.png",
}

# Role tag shown right under each person's name. PROJECT_LEAD_LOGIN /
# CORE_ENGINEERS mirror maintainer-badge.yml's own hardcoded roster by hand
# (keep both in sync); everyone else gets "Maintainer" if they hold live
# Maintain/Admin repo permission, computed fresh each run same as
# maintainer-badge.yml does, or no role line at all for outside
# contributors.
PROJECT_LEAD_LOGIN = "Shashank-Tripathi-07"
CORE_ENGINEERS = {"maanas1234", "yashanand12ssdn-ops"}


def resolve_role(login: str) -> str | None:
    if login == PROJECT_LEAD_LOGIN:
        return "Principal Maintainer"
    if login in CORE_ENGINEERS:
        return "Core Engineer"
    try:
        perm = subprocess.run(
            ["gh", "api", f"repos/{REPO}/collaborators/{login}/permission", "--jq", ".role_name"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        return None  # not a collaborator (e.g. left the org) -- no role line
    return "Maintainer" if perm in ("maintain", "admin") else None


# The repo was private when this script was first written, so shields.io
# couldn't query the real GitHub API for a live contributor count -- this
# badge is a static image whose count this script keeps in sync manually
# instead. Now public (moved to the TrenTorch org), but left as a static
# badge rather than switching to a live query, since that's an unrelated
# behavior change from what this script is here to do. Links to the
# in-README section now, not a separate file.
BADGE_RE = re.compile(
    r"\[!\[Contributors\]\(https://img\.shields\.io/badge/contributors-\d+-orange\.svg\)\]\([^)]*\)"
)

CELL_RE = re.compile(
    r'<a href="https://github\.com/([^"]+)">'
    r'<img[^>]*alt="([^"]*)"\s*/?>'
    r"</a>\s*<br\s*/?>\s*"
    r"<b>([^<]+)</b>\s*<br\s*/?>\s*"
    # The role line (added after this regex was first written) sits between
    # the name and the intro now -- <sub><strong>Role</strong></sub>, which
    # a plain <sub>([^<]*)</sub> can't match through, since <strong> is a
    # "<" this character class rejects. Skip it first, optionally, so a
    # contributor without a role line (external, no live permission) still
    # matches too. This exact bug wiped every real name/bio back to raw
    # logins on this regex's first run after the role line was added --
    # confirmed live, not assumed.
    r"(?:<sub><strong>[^<]*</strong></sub>\s*<br\s*/?>\s*)?"
    r"<sub>([^<]*)</sub>",
    re.DOTALL,
)

# Replaces everything between the "## Team Engineers" heading and the next
# "---" divider (README's own section-separator convention, used
# consistently between every other section in this file).
SECTION_RE = re.compile(
    r"(## Team Engineers\n\n).*?(\n\n---)",
    re.DOTALL,
)


def gh_json(args):
    result = subprocess.run(
        ["gh"] + args, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True
    )
    return json.loads(result.stdout)


def fetch_counts():
    prs = gh_json(["pr", "list", "--repo", REPO, "--state", "all", "--limit", "1000", "--json", "author"])
    issues = gh_json(
        ["issue", "list", "--repo", REPO, "--state", "all", "--limit", "1000", "--json", "author"]
    )

    counts = {}

    def bucket(login):
        return counts.setdefault(login, {"issues": 0, "prs": 0})

    # Exclude bots (e.g. this same workflow's own github-actions[bot] PRs
    # that update this file) from counting as a contributor.
    for pr in prs:
        if pr["author"].get("is_bot"):
            continue
        login = pr["author"]["login"]
        bucket(login)["prs"] += 1

    for issue in issues:
        if issue["author"].get("is_bot"):
            continue
        login = issue["author"]["login"]
        bucket(login)["issues"] += 1

    return counts


def parse_existing(content: str):
    """Returns {login: (name, intro)} scraped from the current avatar grid,
    so a re-run doesn't clobber hand-written names/intros with placeholders."""
    existing = {}
    for login, _alt, name, intro in CELL_RE.findall(content):
        existing[login] = (name.strip(), intro.strip())
    return existing


def build_grid(counts: dict, existing: dict) -> str:
    logins = sorted(counts, key=lambda login: login.lower())
    cells = []
    width = round(100 / COLUMNS, 2)
    for login in logins:
        c = counts[login]
        name, intro = existing.get(login, (login, DEFAULT_INTRO))
        avatar_src = AVATAR_OVERRIDES.get(login, f"https://avatars.githubusercontent.com/{login}?v=4")
        stats = f"Issues: {c['issues']} &middot; PRs: {c['prs']}"
        role = resolve_role(login)
        role_html = f"        <sub><strong>{role}</strong></sub>\n        <br />\n" if role else ""
        cells.append(
            f'      <td align="center" valign="top" width="{width}%">\n'
            f'        <a href="https://github.com/{login}">'
            f'<img src="{avatar_src}" class="contributor-avatar" width="80px;" alt="{name}"/></a>\n'
            f"        <br />\n"
            f"        <b>{name}</b>\n"
            f"        <br />\n"
            f"{role_html}"
            f"        <sub>{intro}</sub>\n"
            f"        <br />\n"
            f"        <sub>{stats}</sub>\n"
            f"      </td>"
        )

    rows = []
    for i in range(0, len(cells), COLUMNS):
        row_cells = "\n".join(cells[i : i + COLUMNS])
        rows.append(f"    <tr>\n{row_cells}\n    </tr>")

    table = (
        '<table width="100%" style="width:100%">\n  <tbody>\n' + "\n".join(rows) + "\n  </tbody>\n</table>"
    )

    intro = (
        "Recomputed nightly from real issue/PR activity via "
        "[`.github/workflows/update-contributors.yml`](.github/workflows/update-contributors.yml). "
        "Want to show up here? Open an issue or a PR — the first-contribution bot will say hello, "
        "and this grid picks you up on the next nightly run.\n\n"
    )

    return intro + table


def selftest() -> bool:
    """Regression check for the bug that shipped once already: CELL_RE
    failing to match a cell that has a role line, silently wiping the
    person's real name/bio back to their raw login on the next run.
    Run via --selftest, and as a pre-flight step in
    update-contributors.yml before this script touches README.md for
    real."""
    sample = (
        '<a href="https://github.com/octocat"><img src="x.png" alt="Octo Cat"/></a>\n'
        "<br />\n"
        "<b>Octo Cat</b>\n"
        "<br />\n"
        "<sub><strong>Maintainer</strong></sub>\n"
        "<br />\n"
        "<sub>Builds things.</sub>\n"
        "<br />\n"
        "<sub>Issues: 1 &middot; PRs: 2</sub>"
    )
    found = parse_existing(sample)
    ok = found.get("octocat") == ("Octo Cat", "Builds things.")
    if not ok:
        print(
            f"selftest FAILED: parse_existing found {found!r}, expected the real name/bio preserved",
            file=sys.stderr,
        )
    else:
        print("selftest passed")
    return ok


def main():
    if "--selftest" in sys.argv:
        return 0 if selftest() else 1

    if not README_FILE.exists():
        print("README.md not found", file=sys.stderr)
        return 1

    content = README_FILE.read_text(encoding="utf-8")
    counts = fetch_counts()
    existing = parse_existing(content)
    grid = build_grid(counts, existing)

    new_content, n = SECTION_RE.subn(lambda m: m.group(1) + grid + m.group(2), content, count=1)
    if n == 0:
        print("Could not find the '## Team Engineers' section in README.md", file=sys.stderr)
        return 1

    new_badge = (
        f"[![Contributors](https://img.shields.io/badge/contributors-{len(counts)}-orange.svg)]"
        f"(#team-engineers)"
    )
    new_content, _ = BADGE_RE.subn(new_badge, new_content)

    if new_content.strip() != content.strip():
        README_FILE.write_text(new_content, encoding="utf-8")
        print("README.md updated")
    else:
        print("No changes")

    return 0


if __name__ == "__main__":
    sys.exit(main())
