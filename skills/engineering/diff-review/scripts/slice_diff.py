#!/usr/bin/env python3
"""Write a review diff as patch files small enough for the reviewer to read in one call each.

Usage: slice_diff.py (<range> | --worktree) --out <dir> [--repo <dir>] [--budget <bytes>]

Files are packed in diff order into <dir>/diff-NN.patch, each under the budget; a file larger than
the budget is split at hunk boundaries, and a hunk larger than it into smaller hunks with their
own @@ headers. --worktree diffs uncommitted work against HEAD, untracked files included.
Prints one line per patch file with the paths it holds. Exit 1: the diff is empty. Exit 2: git failed.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

BUDGET = 20_000
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")


def git_diff(repo, rng):
    base = ["git", "-C", str(repo), "-c", "core.quotePath=false"]
    flags = ["--no-color", "--no-ext-diff"]
    if rng:
        return run(base + ["diff", *flags, rng])
    text = run(base + ["diff", *flags, "HEAD"])
    untracked = run(base + ["ls-files", "--others", "--exclude-standard", "-z"]).split("\0")
    for path in filter(None, untracked):
        text += run(base + ["diff", *flags, "--no-index", "--", "/dev/null", path], ok=(0, 1))
    return text


def run(argv, ok=(0,)):
    result = subprocess.run(argv, capture_output=True, text=True, errors="replace")
    if result.returncode not in ok:
        raise RuntimeError(result.stderr.strip() or f"{' '.join(argv)} exited {result.returncode}")
    return result.stdout


def file_sections(text):
    sections, current = [], None
    for line in text.splitlines(keepends=True):
        if line.startswith("diff --git "):
            current = [line]
            sections.append(current)
        elif current is not None:
            current.append(line)
    return sections


def path_of(section):
    for prefix, strip in (("+++ ", "b/"), ("--- ", "a/")):
        for line in section:
            if line.startswith(prefix) and line.strip() != f"{prefix}/dev/null":
                return line[4:].strip().removeprefix(strip)
    return section[0].split(" b/", 1)[-1].strip()


def split_section(section):
    """(header lines, [hunk line lists])."""
    header, hunks = [], []
    for line in section:
        if line.startswith("@@"):
            hunks.append([line])
        elif hunks:
            hunks[-1].append(line)
        else:
            header.append(line)
    return header, hunks


def split_hunk(hunk, budget):
    """Cut an oversized hunk into hunks under the budget, each with a correct @@ header."""
    match = HUNK.match(hunk[0].rstrip("\n"))
    if not match:
        return [hunk]
    old, new, tail = int(match[1]), int(match[3]), match[5]
    budget -= len(hunk[0]) + 16
    out, body, size, o_start, n_start, o_count, n_count = [], [], 0, old, new, 0, 0

    def flush():
        out.append([f"@@ -{o_start},{o_count} +{n_start},{n_count} @@{tail}\n", *body])

    for line in hunk[1:]:
        if body and size + len(line) > budget:
            flush()
            o_start, n_start = o_start + o_count, n_start + n_count
            body, size, o_count, n_count = [], 0, 0, 0
        body.append(line)
        size += len(line)
        mark = line[:1]
        o_count += mark in (" ", "-", "\n")
        n_count += mark in (" ", "+", "\n")
    if body:
        flush()
    return out


def pieces(section, budget):
    """The section whole, or cut at hunk boundaries into pieces under the budget."""
    if sum(map(len, section)) <= budget:
        return [section]
    header, hunks = split_section(section)
    room = budget - sum(map(len, header))
    small = [h for hunk in hunks for h in (split_hunk(hunk, room) if sum(map(len, hunk)) > room else [hunk])]
    out, current = [], []
    for hunk in small:
        if current and sum(map(len, current)) + sum(map(len, hunk)) > room:
            out.append(header + current)
            current = []
        current += hunk
    if current or not out:
        out.append(header + current)
    return out


def counts(lines):
    added = sum(1 for l in lines if l.startswith("+") and not l.startswith("+++ "))
    removed = sum(1 for l in lines if l.startswith("-") and not l.startswith("--- "))
    return f"+{added} -{removed}"


def slice_diff(text, budget=BUDGET):
    """[(patch text, [label, ...])], packed in diff order."""
    slices = []
    for section in file_sections(text):
        path = path_of(section)
        parts = pieces(section, budget)
        for i, part in enumerate(parts, 1):
            label = f"{path} ({counts(part)})" + (f" part {i}/{len(parts)}" if len(parts) > 1 else "")
            body = "".join(part)
            if slices and len(slices[-1][0]) + len(body) <= budget:
                slices[-1][0] += body
                slices[-1][1].append(label)
            else:
                slices.append([body, [label]])
    return slices


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("range", nargs="?", help="the range as given, e.g. base...head")
    scope.add_argument("--worktree", action="store_true", help="uncommitted work (scope `diff`)")
    parser.add_argument("--out", required=True)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--budget", type=int, default=BUDGET)
    args = parser.parse_args(argv)

    try:
        text = git_diff(Path(args.repo), args.range)
    except RuntimeError as error:
        print(f"git failed: {error}", file=sys.stderr)
        return 2
    slices = slice_diff(text, args.budget)
    if not slices:
        print("the diff is empty", file=sys.stderr)
        return 1
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("diff-*.patch"):
        stale.unlink()
    for n, (body, labels) in enumerate(slices, 1):
        path = out / f"diff-{n:02d}.patch"
        path.write_text(body)
        print(f"{path}: {', '.join(labels)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
