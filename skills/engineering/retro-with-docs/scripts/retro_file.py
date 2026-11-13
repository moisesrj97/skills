"""The retro file format, shared by retro-with-docs and retro-digest.

retro-with-docs/scripts/retro_file.py and retro-digest/scripts/retro_file.py must stay
byte-identical (test_retros.py checks it): each skill installs on its own, so neither can
import from the other.
"""
import os
import re
from pathlib import Path

ROOT = Path(os.environ.get("SKILL_DOCS_DIR", Path.home() / ".skill-docs")) / "retros"
REQUIRED_META = ["date", "project", "session", "summary"]
FIELDS = ["status", "severity", "category", "kind", "target", "evidence", "expected", "cost", "cause",
          "proposal"]
SKIPPED_FIELDS = ["status", "evidence"]
SEVERITIES = ["blocker", "high", "medium", "low"]
ENUMS = {
    "severity": SEVERITIES,
    "category": ["flow", "skill", "verification", "navigation", "checks", "standards", "steering",
                 "wasted-context", "tool-economy", "information-access"],
    "kind": ["mechanical", "judgement"],
}
WEIGHT = {"blocker": 4, "high": 3, "medium": 2, "low": 1}
REF_PATTERN = r"[^/\s]+/[^#\s]+\.md#R\d+[a-z]?"
REF = re.compile(r"^([^/]+)/([^#]+\.md)#(R\d+[a-z]?)$")
STATUS = re.compile(rf"^(open|applied \(.+\)|rejected \(.+\)|skipped \(.+\)|duplicate of {REF_PATTERN})$")
STATUS_HELP = "open, applied (…), rejected (…), skipped (…) or duplicate of <project>/<file>#R<n>"
CAUSE = re.compile(r"^(unknown|suspicion: .+|.*\[\d+\].*)$")
LINE_RANGE = re.compile(r"\S+:\d+(-\d+)?")
FINDING = re.compile(r"^## (R\d+[a-z]?): (.+)$")
FIELD = re.compile(r"^- ([a-z-]+):\s*(.*)$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Files converted from the pre-friction format carry `migrated:` and may say `unrecorded`
# for the fields that format never asked for.
UNRECORDED = "unrecorded"


def is_skipped(finding):
    return finding.get("status", "").startswith("skipped")


def parse(text):
    """Return (meta, title, findings). A `## ` heading that is not `## R<n>: …` yields id None."""
    meta, body = {}, text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end >= 0:
            for line in text[4:end].splitlines():
                key, sep, value = line.partition(":")
                if sep:
                    meta[key.strip()] = value.strip()
            body = text[end + 5:]
    title = next((l[2:].strip() for l in body.splitlines() if l.startswith("# ")), None)
    findings, current, last = [], None, None
    for line in body.splitlines():
        header = FINDING.match(line)
        if line.startswith("## ") and not header:
            findings.append({"id": None, "title": line})
            current = None
            continue
        if header:
            current = {"id": header.group(1), "title": header.group(2)}
            findings.append(current)
            last = None
            continue
        field = FIELD.match(line)
        if current is not None and field and field.group(1) not in current:
            last = field.group(1)
            current[last] = field.group(2).strip()
        elif current is not None and last and line[:1].isspace() and line.strip():
            current[last] = f"{current[last]} {line.strip()}".strip()
        elif not line.strip() or not line[:1].isspace():
            last = None
    return meta, title, findings


def problems(text):
    meta, title, findings = parse(text)
    migrated = bool(meta.get("migrated"))
    out = []
    if not meta:
        out.append("no frontmatter between --- lines")
    for key in REQUIRED_META:
        if not meta.get(key):
            out.append(f"frontmatter: missing {key}")
    if meta.get("date") and not DATE.match(meta["date"]):
        out.append(f"frontmatter: date {meta['date']!r} is not YYYY-MM-DD")
    if not (title or "").startswith("Retro: "):
        out.append("missing the `# Retro: <topic>` heading")
    if "Dismissed as noise:" in text:
        out.append("`Dismissed as noise:` is the old format: write each one as a `skipped (<why>)` finding")
    seen = set()
    for f in findings:
        if f["id"] is None:
            out.append(f"heading {f['title']!r} is not `## R<n>: <problem>`")
            continue
        where = f["id"]
        if where in seen:
            out.append(f"{where}: duplicate id")
        seen.add(where)
        for key in SKIPPED_FIELDS if is_skipped(f) else FIELDS:
            if not f.get(key):
                out.append(f"{where}: missing `- {key}:`")
        for key, allowed in ENUMS.items():
            if f.get(key) and f[key] not in allowed:
                out.append(f"{where}: {key} {f[key]!r} is not one of {' | '.join(allowed)}")
        if f.get("status") and not STATUS.match(f["status"]):
            out.append(f"{where}: status {f['status']!r} is not {STATUS_HELP}")
        for key in ["expected", "cost", "cause"]:
            if f.get(key) == UNRECORDED and not migrated:
                out.append(f"{where}: {key} `unrecorded` is only for migrated files")
        cause = f.get("cause")
        if cause and cause != UNRECORDED and not CAUSE.match(cause):
            out.append(f"{where}: cause cites the evidence ([<index>]), starts with `suspicion: ` or is `unknown`")
        if f.get("category") == "wasted-context" and not LINE_RANGE.search(f.get("target", "")):
            out.append(f"{where}: a wasted-context target names the lines, as `path:start-end`")
        if f.get("matches") and not all(re.fullmatch(REF_PATTERN, ref) for ref in f["matches"].split()):
            out.append(f"{where}: matches {f['matches']!r} is not one or more <project>/<file>#R<n> refs")
    ranked = [f for f in findings if f["id"] and not is_skipped(f)]
    if any(is_skipped(a) and b in ranked for a, b in zip(findings, findings[1:])):
        out.append("skipped findings go after every other finding")
    order = [SEVERITIES.index(f["severity"]) for f in ranked if f.get("severity") in SEVERITIES]
    if order != sorted(order):
        out.append("findings are not ordered by severity")
    return out


def collect(root=ROOT, everything=False):
    """Every finding under <root>/<project>/*.md with its ref, date and weight.

    Without `everything`, only the ones a digest still acts on: open, rejected and skipped.
    """
    out = []
    for path in sorted(Path(root).glob("*/*.md")):
        meta, _, findings = parse(path.read_text(errors="replace"))
        for finding in findings:
            if finding["id"] is None:
                continue
            status = finding.get("status", "")
            if not everything and not (status == "open" or status.startswith(("rejected", "skipped"))):
                continue
            out.append({
                "ref": f"{path.parent.name}/{path.name}#{finding['id']}",
                "date": meta.get("date"),
                **finding,
                "weight": WEIGHT.get(finding.get("severity"), 1),
            })
    return out


def set_status(root, ref, status):
    match = REF.match(ref)
    if not match:
        raise ValueError(f"{ref}: not a <project>/<file>#R<n> ref")
    if not STATUS.match(status):
        raise ValueError(f"{ref}: status {status!r} is not {STATUS_HELP}")
    project, file, finding_id = match.groups()
    path = Path(root) / project / file
    if not path.exists():
        raise ValueError(f"{ref}: no file {path}")
    lines = path.read_text().splitlines(keepends=True)
    inside = False
    for i, line in enumerate(lines):
        header = FINDING.match(line.rstrip("\n"))
        if header:
            inside = header.group(1) == finding_id
        elif inside and line.startswith("- status:"):
            end = i + 1
            while end < len(lines) and lines[end][:1].isspace() and lines[end].strip():
                end += 1
            lines[i:end] = [f"- status: {status}\n"]
            path.write_text("".join(lines))
            return
    raise ValueError(f"{ref}: no `- status:` line under ## {finding_id}")
