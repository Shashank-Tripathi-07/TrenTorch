#!/usr/bin/env python3
"""
Regenerates CONTRIBUTORS.md from real GitHub data (issues raised, PRs raised,
PRs merged) for every contributor discovered from the repo's PR and issue
history. Preserves each person's existing hand-written intro line; a
first-time contributor gets a generic placeholder intro instead of a
fabricated bio, since nobody should get credentials invented for them.

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
CONTRIBUTORS_FILE = Path(__file__).resolve().parent.parent.parent / "CONTRIBUTORS.md"
DEFAULT_INTRO = "New to TrenTorch — say hi and add a real intro!"

ROW_RE = re.compile(
    r"\|\s*\[([^\]]+)\]\(https://github\.com/([^)]+)\)\s*\|\s*(.*?)\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*\d+\s*\|"
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

    for pr in prs:
        login = pr["author"]["login"]
        b = bucket(login)
        b["prs"] += 1
        if pr["state"] == "MERGED":
            b["merged"] += 1

    for issue in issues:
        login = issue["author"]["login"]
        bucket(login)["issues"] += 1

    return counts


def parse_existing_intros(path: Path):
    intros = {}
    if not path.exists():
        return intros
    for line in path.read_text(encoding="utf-8").splitlines():
        m = ROW_RE.match(line.strip())
        if m:
            _, login, intro = m.groups()
            intros[login] = intro
    return intros


def display_name(login: str, existing_intros: dict) -> str:
    # Prefer whatever name was already in the table (e.g. "Shivtej Gaikwad"
    # instead of the raw handle); fall back to the raw handle for anyone new.
    return login


def build_table(counts: dict, existing_names: dict, existing_intros: dict) -> str:
    lines = [
        "| Contributor | Intro | Issues Raised | PRs Raised | PRs Merged |",
        "|---|---|---|---|---|",
    ]
    for login in sorted(counts, key=lambda l: l.lower()):
        c = counts[login]
        name = existing_names.get(login, login)
        intro = existing_intros.get(login, DEFAULT_INTRO)
        lines.append(
            f"| [{name}](https://github.com/{login}) | {intro} | "
            f"{c['issues']} | {c['prs']} | {c['merged']} |"
        )
    return "\n".join(lines)


def parse_existing_names(path: Path):
    names = {}
    if not path.exists():
        return names
    for line in path.read_text(encoding="utf-8").splitlines():
        m = ROW_RE.match(line.strip())
        if m:
            name, login, _ = m.groups()
            names[login] = name
    return names


def main():
    counts = fetch_counts()
    existing_names = parse_existing_names(CONTRIBUTORS_FILE)
    existing_intros = parse_existing_intros(CONTRIBUTORS_FILE)
    table = build_table(counts, existing_names, existing_intros)

    header = (
        "# Contributors\n\n"
        "Thanks to everyone who's helped build TrenTorch. This table is kept "
        "up to date automatically — every new issue, PR, and merge updates "
        "the relevant row via "
        "[`.github/workflows/update-contributors.yml`](.github/workflows/update-contributors.yml).\n\n"
    )
    footer = (
        "\n\n---\n\n"
        "Want to show up here? Open an issue or a PR — the first-contribution "
        "bot will say hello, and this table picks up the rest automatically "
        "once it merges.\n"
    )

    new_content = header + table + footer

    old_content = CONTRIBUTORS_FILE.read_text(encoding="utf-8") if CONTRIBUTORS_FILE.exists() else ""
    if new_content.strip() == old_content.strip():
        print("No changes to CONTRIBUTORS.md")
        return 0

    CONTRIBUTORS_FILE.write_text(new_content, encoding="utf-8")
    print("CONTRIBUTORS.md updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
