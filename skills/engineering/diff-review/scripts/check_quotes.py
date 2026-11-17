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
LINE_NUMBER = re.compile(r"^\s*\d+(?:\s*[|:]\s?|\t)")
BLOCKQUOTE = re.compile(r"^(?:>\s?)+")
INLINE_ELISION = re.compile(r"\.\.\.|…")
LABEL = re.compile(r"^\s*[`*]*(?P<path>[\w@.-]*[./][\w@./-]*):\d+(?:\s*[-–—]\s*\d+)?[`*]*:?\s*$")
LABEL_PREFIX = re.compile(r"^\s*[\w@./-]+:\d+(?:-\d+)?[\t ]+")
LOOSE = "matched after normalising whitespace"


def parse_round(text):
    """Return (sealed, findings). Each finding: {n, path, line, title, quotes: [(label, segment), ...]}.

    A label is the `<path>:<line>` a reviewer wrote on its own line before a quote block, inside the
    quote or out; it names the file that block quotes, until the next label.
    """
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
        elif current is None:
            continue
        elif line.startswith(">"):
            quoted = BLOCKQUOTE.sub("", line)
            label = LABEL.match(quoted)
            current["quote_lines"].append(("label", label["path"]) if label else quoted)
        elif label := LABEL.match(line):
            current["quote_lines"].append(("label", label["path"]))
        elif current["quote_lines"] and current["quote_lines"][-1] is not None:
            current["quote_lines"].append(None)
    for finding in findings:
        finding["quotes"] = segments(finding.pop("quote_lines"))
    return sealed, findings


def segments(quote_lines):
    """Split a finding's quoted lines on elisions, labels and gaps between quote blocks."""
    out, current, label = [], [], None
    for line in quote_lines:
        if line is None or isinstance(line, tuple) or ELISION.match(line):
            if current:
                out.append((label, current))
            current = []
            if isinstance(line, tuple):
                label = line[1].removeprefix("./")
        else:
            current.append(line)
    if current:
        out.append((label, current))
    return [(label, s) for label, s in out if any(l.strip() for l in s)]


def normalize(lines):
    return "\n".join(l.strip() for l in lines).strip()


def variants(segment):
    yield segment
    unfenced = [l for l in segment if not FENCE.match(l)]
    if len(unfenced) < len(segment):
        yield unfenced
        segment = unfenced
    yield [LINE_NUMBER.sub("", l) for l in segment]
    yield [LABEL_PREFIX.sub("", l) for l in segment]
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


def locate_loose(segment, source_lines):
    """Like locate, ignoring all whitespace and treating `...`/`…` inside a line as a gap.

    Catches statements a formatter split or joined, and quotes with inline elisions.
    """
    chars, line_of = [], []
    for number, line in enumerate(source_lines, 1):
        for ch in line:
            if not ch.isspace():
                chars.append(ch)
                line_of.append(number)
    haystack = "".join(chars)
    for candidate in variants(segment):
        parts = [p for p in (re.sub(r"\s+", "", part) for part in INLINE_ELISION.split("\n".join(candidate))) if p]
        if not parts:
            continue
        start, end = None, 0
        for part in parts:
            at = haystack.find(part, end)
            if at < 0:
                break
            start = at if start is None else start
            end = at + len(part)
        else:
            return line_of[start], line_of[end - 1]
    return None


def find(segment, source_lines):
    """(first, last, loose) for the segment in the source, or None."""
    span = locate(segment, source_lines)
    if span:
        return (*span, False)
    span = locate_loose(segment, source_lines)
    return (*span, True) if span else None


def find_elsewhere(segment, path, ref, repo):
    """(path, first line) of another file holding the segment, or None."""
    lines = [l.strip().lstrip("+-").strip() for l in segment if not FENCE.match(l)]
    probe = max((INLINE_ELISION.split(l)[0].strip() for l in lines), key=len, default="")
    if len(probe) < 8:
        return None
    command = ["git", "grep", "-F", "-l", "-e", probe] + ([ref] if ref else []) + ["--"]
    result = subprocess.run(command, cwd=repo, capture_output=True, text=True, errors="replace")
    for hit in result.stdout.splitlines()[:20]:
        other = hit.removeprefix(f"{ref}:") if ref else hit
        if other == path:
            continue
        span = find(segment, read_source(other, ref, repo) or [])
        if span:
            return other, span[0]
    return None


def read_source(path, ref, repo):
    if ref is None:
        file = Path(repo) / path
        return file.read_text(errors="replace").splitlines() if file.is_file() else None
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"], cwd=repo, capture_output=True, text=True, errors="replace"
    )
    return result.stdout.splitlines() if result.returncode == 0 else None


def resolve_label(label, ref, repo):
    """The tracked path a label names, exactly or as a unique path suffix, else None."""
    command = ["git", "ls-tree", "-r", "--name-only", ref] if ref else ["git", "ls-files"]
    tracked = subprocess.run(command, cwd=repo, capture_output=True, text=True, errors="replace").stdout.splitlines()
    if label in tracked:
        return label
    matches = [path for path in tracked if path.endswith("/" + label)]
    return matches[0] if len(matches) == 1 else None


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
        in_header, in_labelled, missing = [], 0, []
        for i, (quote_label, segment) in enumerate(f["quotes"]):
            home = resolve_label(quote_label, ref, repo) if quote_label else None
            if home and home != f["path"] and find(segment, read_source(home, ref, repo) or []):
                in_labelled += 1
                continue
            span = find(segment, source)
            if span:
                in_header.append(span)
            else:
                missing.append((i + 1, home or f["path"]))
        if not in_header and not in_labelled:
            elsewhere = next(filter(None, (find_elsewhere(s, f["path"], ref, repo) for _, s in f["quotes"])), None)
            if elsewhere:
                results.append(("CONFIRMED", label, f"quote found in {elsewhere[0]}:{elsewhere[1]}, not {f['path']}"))
            else:
                results.append(("DISCARDED", label, f"quote matches nothing in {where}{f['path']}"))
            continue
        notes = []
        if any(loose for _, _, loose in in_header):
            notes.append(LOOSE)
        if in_header and not any(first <= f["line"] <= last for first, last, _ in in_header):
            notes.append(f"quote found at line {in_header[0][0]}")
        for n, path in missing:
            notes.append(f"quote block {n} of {len(f['quotes'])} is not in {path}: check it quotes another file")
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
