#!/usr/bin/env python3
"""Check that every finding in a diff-review round file quotes code that exists.

Usage: check_quotes.py <round file> (--ref <git ref> | --worktree) [--repo <dir>]

A quote is a `<path>:<start>-<end>` label line followed by a fenced block; the block is compared,
whitespace-normalised, with those lines of that file. Prints one line per finding, CONFIRMED,
DISCARDED or UNPARSED (no quote or header in that shape: check it by hand) with the reason, then a
count line. Exit 0 when the round is sealed (even with discards), 2 when it is not sealed or not readable.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

SEAL = "END OF ROUND"
HEADER = re.compile(r"^###\s+(\d+)\.\s+(?:`([^`]+)`|([^\s:`]+)):(\d+)(?:\s*[-–—]\s*\d+)?:?\s*(.*)$")
LABEL = re.compile(r"^`(?P<path>[^`]+?):(?P<start>\d+)(?:-(?P<end>\d+))?`:?\s*$")
FENCE = re.compile(r"^(`{3,}|~{3,})")
READ_PREFIX = re.compile(r"^\s*\d+(?:→|\t)")
SHAPE = "`<path>:<start>-<end>` + fenced block"


def closes(line, fence):
    stripped = line.rstrip()
    return stripped.startswith(fence) and set(stripped) == {fence[0]}


def parse_round(text):
    """Return (sealed, findings). Each finding: {n, path, line, title, quotes: [(path, start, end, lines)]}."""
    lines = text.rstrip().splitlines()
    sealed = bool(lines) and lines[-1].strip() == SEAL
    findings, current, i = [], None, 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if line.startswith("### "):
            header = HEADER.match(line)
            current = {"n": None, "path": None, "line": None, "title": line[4:].strip(), "quotes": []}
            if header:
                current.update(n=int(header[1]), path=(header[2] or header[3]).removeprefix("./"),
                               line=int(header[4]), title=header[5])
            findings.append(current)
            continue
        label = LABEL.match(line)
        if current is None or not label:
            continue
        while i < len(lines) and not lines[i].strip():
            i += 1
        opening = FENCE.match(lines[i]) if i < len(lines) else None
        if not opening:
            continue
        body = []
        i += 1
        while i < len(lines) and not closes(lines[i], opening[1]):
            body.append(lines[i])
            i += 1
        i += 1
        end = int(label["end"]) if label["end"] else None
        current["quotes"].append((label["path"].removeprefix("./"), int(label["start"]), end, body))
    return sealed, findings


def normalize(line):
    return " ".join(line.split())


def clean(body):
    """The block's lines, without a Read `N→` prefix or `+` diff markers on every line, blank ends trimmed."""
    filled = [l for l in body if l.strip()]
    if filled and all(READ_PREFIX.match(l) for l in filled):
        body = [READ_PREFIX.sub("", l, count=1) for l in body]
        filled = [l for l in body if l.strip()]
    if filled and all(l[:1] in "+ " for l in filled) and any(l[:1] == "+" for l in filled):
        body = [l[1:] for l in body]
    body = [normalize(l) for l in body]
    while body and not body[0]:
        body.pop(0)
    while body and not body[-1]:
        body.pop()
    return body


def locate(body, source, start, end):
    """(first, last) lines the body matches: the labelled span when it does, else its first match in the file."""
    lines = [normalize(l) for l in source]
    last = end if end is not None else start + len(body) - 1
    if last - start + 1 == len(body) and lines[start - 1:last] == body:
        return start, last
    for first in range(len(lines) - len(body) + 1):
        if lines[first:first + len(body)] == body:
            return first + 1, first + len(body)
    return None


def read_source(path, ref, repo):
    if ref is None:
        file = Path(repo) / path
        return file.read_text(errors="replace").splitlines() if file.is_file() else None
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"], cwd=repo, capture_output=True, text=True, errors="replace"
    )
    return result.stdout.splitlines() if result.returncode == 0 else None


def check(findings, ref, repo):
    where = f"{ref}:" if ref else "the working tree: "
    results = []
    for f in findings:
        if f["path"] is None:
            results.append(("UNPARSED", f["title"], "header is not `### <n>. <file>:<line>: <summary>`; check it by hand"))
            continue
        label = f"{f['n']} {f['path']}:{f['line']}"
        if not f["quotes"]:
            results.append(("UNPARSED", label, f"no quote in the {SHAPE} shape; check it by hand"))
            continue
        if read_source(f["path"], ref, repo) is None:
            results.append(("DISCARDED", label, f"{f['path']} does not exist in {where.rstrip(': ')}"))
            continue
        notes, misses = [], []
        for path, start, end, body in f["quotes"]:
            cited = f"`{path}:{start}" + (f"-{end}`" if end else "`")
            source = read_source(path, ref, repo)
            lines = clean(body)
            if source is None:
                misses.append(f"{path} does not exist in {where.rstrip(': ')}")
            elif not lines:
                misses.append(f"{cited} has an empty block")
            elif span := locate(lines, source, start, end):
                if span[0] != start:
                    notes.append(f"{cited} found at lines {span[0]}-{span[1]}")
            else:
                misses.append(f"{cited} matches nothing in {where}{path}")
        if len(misses) == len(f["quotes"]):
            results.append(("DISCARDED", label, "; ".join(misses)))
            continue
        notes += [f"{miss}: check that block by hand" for miss in misses]
        results.append(("CONFIRMED", label, "; ".join(notes)))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("round_file")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--ref", help="the version the reviewer was told to read, e.g. the range's head")
    source.add_argument("--worktree", action="store_true", help="read files from disk (scope `diff`)")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args(argv)

    try:
        text = Path(args.round_file).read_text()
    except OSError as error:
        print(f"cannot read the round file: {error}", file=sys.stderr)
        return 2
    sealed, findings = parse_round(text)
    if not sealed:
        print(f"round not sealed: the last line is not {SEAL}; the round was cut", file=sys.stderr)
        return 2
    if not findings:
        print("NO FINDINGS" if "NO FINDINGS" in text else "no findings parsed: check the round's headers")
        return 0
    results = check(findings, args.ref, args.repo)
    for verdict, label, reason in results:
        print(f"{verdict} {label}" + (f": {reason}" if reason else ""))
    counts = {v: sum(1 for r in results if r[0] == v) for v in ("CONFIRMED", "DISCARDED", "UNPARSED")}
    print(", ".join(f"{n} {v.lower()}" for v, n in counts.items() if n or v != "UNPARSED"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
