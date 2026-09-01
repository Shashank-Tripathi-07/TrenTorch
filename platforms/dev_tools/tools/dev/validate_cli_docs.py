#!/usr/bin/env python3
"""
Validate that `tren ...` commands referenced in docs/*.md actually exist,
by introspecting the real CLI's argparse structure directly -- not a
hand-maintained parallel list of "valid commands" that drifts out of sync
with the code the moment a command is added, renamed, or removed. That's
exactly what made the previous version of this script unusable after the
data/ and platforms/ restructurings: its DOCS_DIRS pointed at directories
that no longer exist (site/, modules/, tests/, milestones/) and its
VALID_COMMANDS dict was a frozen snapshot missing tui/serve/convert,
still listing removed groups (grade, community), and wrong on several
subcommand lists. Ground truth here is the live parser, so it can't go
stale the same way again.

Usage:
    python platforms/dev_tools/tools/dev/validate_cli_docs.py [--verbose]

Exit codes:
    0 - every `tren ...` reference in docs/*.md matches a real command
    1 - one or more references don't match anything the CLI actually has
"""

import argparse
import re
import sys
from pathlib import Path


def _project_root() -> Path:
    # This file lives at platforms/dev_tools/tools/dev/validate_cli_docs.py,
    # four levels below the repo root.
    return Path(__file__).resolve().parents[4]


# tree[path] is a set of valid next-word subcommand names if `path` is a
# dispatch level (has its own subparsers), or None if `path` is a leaf
# that takes ordinary positional args instead (a module number, a
# milestone id, ...) rather than a further named subcommand.
CommandTree = dict[str, "set[str] | None"]


def _collect_subparser_tree(parser: argparse.ArgumentParser, prefix: str, tree: CommandTree) -> None:
    """Recursively map every `tren <...>` command path a real argparse
    parser actually accepts, by walking its subparsers. Uses argparse's
    private `_actions`/`_SubParsersAction` structure -- not public API, but
    stable enough for a dev-tooling script, and the only way to get ground
    truth without re-declaring the command tree by hand a second time."""
    subparsers_action = next((a for a in parser._actions if isinstance(a, argparse._SubParsersAction)), None)
    if subparsers_action is None:
        tree[prefix] = None
        return
    children = set(subparsers_action.choices.keys())
    tree[prefix] = children
    for name, subparser in subparsers_action.choices.items():
        _collect_subparser_tree(subparser, f"{prefix} {name}", tree)


def get_valid_command_tree(project_root: Path) -> CommandTree:
    """Ground truth: introspect the real, live CLI rather than hand-listing it."""
    root_str = str(project_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    from platforms.cli.main import TrenTorchCLI

    cli = TrenTorchCLI()
    parser = cli.create_parser()

    subparsers_action = next((a for a in parser._actions if isinstance(a, argparse._SubParsersAction)), None)
    tree: CommandTree = {"tren": set(subparsers_action.choices.keys()) if subparsers_action else set()}
    if subparsers_action is None:
        return tree
    for name, subparser in subparsers_action.choices.items():
        _collect_subparser_tree(subparser, f"tren {name}", tree)
    return tree


# Matches a `tren <word> [<word>] [<word>]` command inside a backtick code
# span, or at the start of a (possibly indented) bash code-block line.
# Only lowercase alphanumeric/hyphen/underscore words count as command
# path segments -- module numbers, NN placeholders, and similar args
# naturally fall outside that and just don't extend the match.
CODE_SPAN_PATTERN = re.compile(r"`(tren(?:\s+[a-z][a-z0-9_-]*){1,3})`")
BASH_LINE_PATTERN = re.compile(r"^\s*\$?\s*(tren(?:\s+[a-z][a-z0-9_-]*){1,3})\b", re.MULTILINE)


def extract_commands(text: str) -> list[str]:
    found = []
    for pattern in (CODE_SPAN_PATTERN, BASH_LINE_PATTERN):
        found.extend(m.group(1) for m in pattern.finditer(text))
    return found


def matches_real_command(cmd: str, tree: CommandTree) -> bool:
    """Walk the reference word by word against the real command tree. At a
    dispatch level (tree[path] is a set), the next word MUST be one of
    that level's real subcommands -- an unrecognized word here is a wrong
    subcommand, not a droppable arg, exactly like real argparse would
    reject it. At a leaf (tree[path] is None), anything remaining is
    ordinary positional args (a module number, a milestone id, ...) and
    the reference is valid regardless of what those words are."""
    parts = cmd.split()
    path = parts[0]
    if path not in tree:
        return False
    for word in parts[1:]:
        children = tree[path]
        if children is None:
            return True  # leaf: remaining words are just positional args
        if word not in children:
            return False  # not a real subcommand at this dispatch level
        path = f"{path} {word}"
    return True


def main() -> int:
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    root = _project_root()

    tree = get_valid_command_tree(root)
    if verbose:
        print(f"Introspected {len(tree)} valid command paths from the real, live CLI.")

    md_files = sorted((root / "docs").rglob("*.md")) + sorted(root.glob("*.md"))

    # Words that mean "this command is being discussed as history, not
    # claimed as currently working" -- checked in a window around the
    # reference, not just the exact line, since a doc's framing sentence
    # ("Upstream had X. This fork inherited it. It has since been
    # removed.") is often a line or two away from the code span itself.
    HISTORICAL_MARKERS = re.compile(
        r"\bremoved\b|\bno longer\b|\bused to (exist|work)\b|\bhas never existed\b|\bdeleted\b",
        re.IGNORECASE,
    )

    errors: list[tuple[Path, str]] = []
    seen_per_file: dict[Path, set[str]] = {}

    # Headings that mark a section as explicitly-disclaimed history of a
    # *different* repo (design.md's own top-of-section note), not a claim
    # about this fork's live command set -- skip everything under one
    # until the next same-or-higher-level heading.
    NON_CURRENT_SECTION_HEADINGS = {"project history"}

    for md_file in md_files:
        try:
            text = md_file.read_text(encoding="utf-8")
        except Exception:
            continue
        lines = text.split("\n")

        skip_from = None
        for line_idx, line in enumerate(lines):
            heading_match = re.match(r"^(#{1,6})\s+(.*)$", line)
            if heading_match:
                level, title = len(heading_match.group(1)), heading_match.group(2).strip().lower()
                if skip_from is not None and level <= skip_from:
                    skip_from = None
                if skip_from is None and title in NON_CURRENT_SECTION_HEADINGS:
                    skip_from = level
            if skip_from is not None:
                continue

            for raw_cmd in extract_commands(line):
                if matches_real_command(raw_cmd, tree):
                    continue
                window = "\n".join(lines[max(0, line_idx - 2) : line_idx + 3])
                if HISTORICAL_MARKERS.search(window):
                    continue
                already_flagged = seen_per_file.setdefault(md_file, set())
                if raw_cmd in already_flagged:
                    continue
                already_flagged.add(raw_cmd)
                errors.append((md_file.relative_to(root), raw_cmd))

    if errors:
        print(f"\n{'=' * 60}")
        print("Docs reference a `tren` command that doesn't exist")
        print(f"{'=' * 60}\n")
        for path, cmd in errors:
            print(f"  {path}: `{cmd}` -- no real command matches this")
        print(f"\n{len(errors)} reference(s) don't match the real CLI.")
        print("Run `tren --help` (or the relevant subcommand's --help) to see what actually")
        print("exists, and fix the docs -- or fix this script's extraction/matching logic if")
        print("it's what's wrong, not the docs.\n")
        return 1

    if verbose:
        print(f"All `tren ...` references across {len(md_files)} markdown files match a real command.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
