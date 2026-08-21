#!/usr/bin/env python3
"""
Regenerates CONTRIBUTORS.md from real GitHub data (issues raised, PRs raised,
PRs merged) for every contributor discovered from the repo's PR and issue
history. Renders an avatar grid (the good part of the all-contributors
project's UI) with plain-text stats instead of an emoji contribution-type
key (the part we're deliberately not copying). Preserves each person's
existing hand-written intro line; a first-time contributor gets a generic
placeholder intro instead of a fabricated bio, since nobody should get
credentials invented for them.

Run by .github/workflows/update-contributors.yml, authenticated with
GITHUB_TOKEN via the gh CLI (already configured by actions/checkout /
the workflow's GH_TOKEN env var).
"""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = "Shashank-Tripathi-07/TrenTorch"
ROOT = Path(__file__).resolve().parent.parent.parent
CONTRIBUTORS_FILE = ROOT / "CONTRIBUTORS.md"
README_FILE = ROOT / "README.md"
DEFAULT_INTRO = "New to TrenTorch — say hi and add a real intro!"
COLUMNS = 5

# Private repo, so shields.io can't query the real GitHub API for a live
# contributor count (no auth to a private repo) -- this badge is a static
# image whose count this script keeps in sync manually instead.
BADGE_RE = re.compile(
    r"\[!\[Contributors\]\(https://img\.shields\.io/badge/contributors-\d+-orange\.svg\)\]\(CONTRIBUTORS\.md\)"
)

CELL_RE = re.compile(
    r'<a href="https://github\.com/([^"]+)">'
    r'<img[^>]*alt="([^"]*)"\s*/?>'
    r'</a>\s*<br\s*/?>\s*'
    r'<b>([^<]+)</b>\s*<br\s*/?>\s*'
    r'<sub>([^<]*)</sub>',
    re.DOTALL,
)


def gh_json(args):
    result = subprocess.run(
        ["gh"] + args, capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


def fetch_counts():
    prs = gh_json(
        ["pr", "list", "--repo", REPO, "--state", "all", "--limit", "1000",
         "--json", "author,state"]
    )
    issues = gh_json(
        ["issue", "list", "--repo", REPO, "--state", "all", "--limit", "1000",
         "--json", "author"]
    )

    counts = {}

    def bucket(login):
        return counts.setdefault(login, {"issues": 0, "prs": 0, "merged": 0})

    # Exclude bots (e.g. this same workflow's own github-actions[bot] PRs
    # that update this file) from counting as a contributor.
    for pr in prs:
        if pr["author"].get("is_bot"):
            continue
        login = pr["author"]["login"]
        b = bucket(login)
        b["prs"] += 1
        if pr["state"] == "MERGED":
            b["merged"] += 1

    for issue in issues:
        if issue["author"].get("is_bot"):
            continue
        login = issue["author"]["login"]
        bucket(login)["issues"] += 1

    return counts


def parse_existing(path: Path):
    """Returns {login: (name, intro)} scraped from the current avatar grid,
    so a re-run doesn't clobber hand-written names/intros with placeholders."""
    existing = {}
    if not path.exists():
        return existing
    content = path.read_text(encoding="utf-8")
    for login, _alt, name, intro in CELL_RE.findall(content):
        existing[login] = (name.strip(), intro.strip())
    return existing


def build_grid(counts: dict, existing: dict) -> str:
    logins = sorted(counts, key=lambda l: l.lower())
    cells = []
    width = round(100 / COLUMNS, 2)
    for login in logins:
        c = counts[login]
        name, intro = existing.get(login, (login, DEFAULT_INTRO))
        stats = f"Issues: {c['issues']} &middot; PRs: {c['prs']} &middot; Merged: {c['merged']}"
        cells.append(
            f'      <td align="center" valign="top" width="{width}%">\n'
            f'        <a href="https://github.com/{login}">'
            f'<img src="https://avatars.githubusercontent.com/{login}?v=4" width="80px;" alt="{name}"/></a>\n'
            f'        <br />\n'
            f'        <b>{name}</b>\n'
            f'        <br />\n'
            f'        <sub>{intro}</sub>\n'
            f'        <br />\n'
            f'        <sub>{stats}</sub>\n'
            f'      </td>'
        )

    rows = []
    for i in range(0, len(cells), COLUMNS):
        row_cells = "\n".join(cells[i:i + COLUMNS])
        rows.append(f"    <tr>\n{row_cells}\n    </tr>")

    return (
        '<table width="100%" style="width:100%">\n'
        "  <tbody>\n" + "\n".join(rows) + "\n  </tbody>\n</table>"
    )


def update_readme_badge(count: int) -> bool:
    """Keeps the static contributor-count badge in README.md in sync.
    Returns True if the badge changed."""
    if not README_FILE.exists():
        return False
    content = README_FILE.read_text(encoding="utf-8")
    new_badge = (
        f"[![Contributors](https://img.shields.io/badge/contributors-{count}-orange.svg)]"
        f"(CONTRIBUTORS.md)"
    )
    new_content, n = BADGE_RE.subn(new_badge, content)
    if n == 0 or new_content == content:
        return False
    README_FILE.write_text(new_content, encoding="utf-8")
    return True


def main():
    counts = fetch_counts()
    existing = parse_existing(CONTRIBUTORS_FILE)
    grid = build_grid(counts, existing)
    readme_changed = update_readme_badge(len(counts))

    header = (
        "# Contributors\n\n"
        "Thanks to everyone who's helped build TrenTorch. Kept up to date "
        "automatically — every new issue, PR, and merge updates the "
        "relevant entry via "
        "[`.github/workflows/update-contributors.yml`](.github/workflows/update-contributors.yml).\n\n"
    )
    footer = (
        "\n\n---\n\n"
        "Want to show up here? Open an issue or a PR — the first-contribution "
        "bot will say hello, and this grid picks up the rest automatically "
        "once it merges.\n"
    )

    new_content = header + grid + footer

    old_content = CONTRIBUTORS_FILE.read_text(encoding="utf-8") if CONTRIBUTORS_FILE.exists() else ""
    contributors_changed = new_content.strip() != old_content.strip()
    if contributors_changed:
        CONTRIBUTORS_FILE.write_text(new_content, encoding="utf-8")
        print("CONTRIBUTORS.md updated")

    if readme_changed:
        print("README.md badge updated")

    if not contributors_changed and not readme_changed:
        print("No changes")

    return 0


if __name__ == "__main__":
    sys.exit(main())
