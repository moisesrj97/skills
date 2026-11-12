#!/usr/bin/env python3
"""Check that every finding in a diff-review round file quotes code that exists.

Usage: check_quotes.py <round file> (--ref <git ref> | --worktree) [--repo <dir>]

Prints one line per finding, CONFIRMED, DISCARDED or UNPARSED with the reason, then a count line.
Exit 0 when the round is sealed (even with discards), 2 when it is not sealed or not readable.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

SEAL = "END OF ROUND"
HEADER = re.compile(r"^###\s+(\d+)\.\s+(?:`([^`]+)`|([^\s:`]+)):(\d+)(?:\s*[-–—]\s*\d+)?:?\s*(.*)$")
FENCE = re.compile(r"^\s*(```|~~~)")
ELISION = re.compile(r"^\s*(\.\.\.|…)\s*$")
LINE_NUMBER = re.compile(r"^\s*\d+\s*[|:]\s?")


def parse_round(text):
    """Return (sealed, findings). Each finding: {n, path, line, title, quotes: [segment, ...]}."""
    lines = text.rstrip().splitlines()
    sealed = bool(lines) and lines[-1].strip() == SEAL
    findings = []
    current = None
    for line in lines:
        header = HEADER.match(line)
        if line.startswith("### ") and not header:
            current = {"n": None, "path": None, "line": None, "title": line[4:].strip(), "quote_lines": []}
            findings.append(current)
            continue
        if header:
            current = {
                "n": int(header.group(1)),
                "path": (header.group(2) or header.group(3)).removeprefix("./"),
                "line": int(header.group(4)),
                "title": header.group(5),
                "quote_lines": [],
            }
            findings.append(current)
        elif current is not None and line.startswith(">"):
            current["quote_lines"].append(line[2:] if line.startswith("> ") else line[1:])
        elif current is not None and current["quote_lines"] and current["quote_lines"][-1] is not None:
            current["quote_lines"].append(None)
    for finding in findings:
        finding["quotes"] = segments(finding.pop("quote_lines"))
    return sealed, findings


def segments(quote_lines):
    """Split a finding's quoted lines on elisions and on gaps between quote blocks."""
    out, current = [], []
    for line in quote_lines:
        if line is None or ELISION.match(line):
            if current:
                out.append(current)
            current = []
        else:
            current.append(line)
    if current:
        out.append(current)
    return [s for s in out if any(l.strip() for l in s)]


def normalize(lines):
    return "\n".join(l.strip() for l in lines).strip()


def variants(segment):
    yield segment
    unfenced = [l for l in segment if not FENCE.match(l)]
    if len(unfenced) < len(segment):
        yield unfenced
        segment = unfenced
    yield [LINE_NUMBER.sub("", l) for l in segment]
    if all(l[:1] in "+- " for l in segment if l):
        yield [l[1:] for l in segment]


def locate(segment, source_lines):
    """1-based (first, last) lines the segment spans in the source, or None."""
    haystack = normalize(source_lines)
    for candidate in variants(segment):
        needle = normalize(candidate)
        if not needle:
            continue
        at = haystack.find(needle)
        if at >= 0:
            first = haystack.count("\n", 0, at) + 1
            return first, first + needle.count("\n")
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
        source = read_source(f["path"], ref, repo)
        if source is None:
            results.append(("DISCARDED", label, f"{f['path']} does not exist in {where.rstrip(': ')}"))
            continue
        if not f["quotes"]:
            results.append(("DISCARDED", label, "no quote"))
            continue
        spans = [locate(s, source) for s in f["quotes"]]
        found = [s for s in spans if s]
        missing = [str(i + 1) for i, s in enumerate(spans) if s is None]
        if not found:
            results.append(("DISCARDED", label, f"quote matches nothing in {where}{f['path']}"))
            continue
        notes = []
        if not any(first <= f["line"] <= last for first, last in found):
            notes.append(f"quote found at line {found[0][0]}")
        if missing:
            notes.append(f"quote block {', '.join(missing)} of {len(spans)} is not in {f['path']}: "
                         "check it quotes another file")
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
