#!/usr/bin/env python3
"""Read and update the retro files retro-with-docs writes under ~/.skill-docs/retros/.

Usage:
  retros.py collect [--all] [--skipped-days 28] [--root <dir>]
      Prints a JSON list of findings, each with ref (<project>/<file>#R<n>), date, its fields
      and weight (blocker 4, high 3, medium 2, low 1; 1 without a severity). Without --all,
      only open, rejected and skipped ones, and no skipped one older than --skipped-days:
      a one-off that has not recurred in that long is not a pattern.
  retros.py batches --out <dir> [--size 40] [--skipped-days 28] [--root <dir>]
      Splits what collect prints into <dir>/batch-<n>.json, sorted by where each change would
      land so related findings share a batch, each field clipped. Prints the batch files.
  retros.py merge <dir> [--merges <file.json>]
      Reads <dir>/batch-<n>.json and the cluster subagents' <dir>/clusters-<n>.json, ids each
      cluster <n>.<i>, merges each group in --merges ([{"ids": ["<id>", ...], "owner"?, "cause"?,
      "proposal"?}], text defaulting to the first id's), and writes <dir>/merged.json, highest score first, and <dir>/index.txt, one line per
      cluster sorted by owner, for spotting the clusters batches split. Refuses, naming every
      offender, a batch without clusters, a cluster without owner, cause, proposal or members, an
      unknown ref or id, and a finding placed in no cluster or in more than one.
  retros.py set <ref> <status> [--root <dir>]
  retros.py set --from <file.json> [--root <dir>]       {"<ref>": "<status>", ...}
      Rewrites each finding's `- status:` line. A status is `applied (<where>)`,
      `rejected (<reason>)`, `skipped (<reason>)`, `duplicate of <ref>` or `open`; anything
      else is refused.
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from retro_file import ROOT, WEIGHT, collect, is_skipped, set_status  # noqa: E402

BATCH_FIELDS = ["ref", "date", "status", "severity", "category", "kind", "target", "title", "evidence",
                "cause", "proposal", "matches"]
CLIP = 300


def digestible(root, skipped_days, today=None):
    cutoff = ((today or datetime.date.today()) - datetime.timedelta(days=skipped_days)).isoformat()
    return [f for f in collect(root) if not (is_skipped(f) and (f.get("date") or "") < cutoff)]


def owner(target):
    """Where a change would land, coarsely: a skill, an app or package, else the file's name."""
    token = (target or "").split(" ")[0].strip("`,;()")
    if not token or token in ("unknown", "guess:"):
        return "~unknown"
    parts = Path(re.sub(r":\d+(-\d+)?$", "", token)).parts
    if "scripts" in parts[1:-1]:
        return parts[parts.index("scripts") - 1]
    if len(parts) > 1 and parts[-1] == "SKILL.md":
        return parts[-2]
    for marker in ("apps", "packages", "services"):
        if marker in parts[:-1]:
            return parts[parts.index(marker) + 1]
    return parts[-1].lower() if parts else "~unknown"


def batches(findings, size):
    ordered = sorted(findings, key=lambda f: (owner(f.get("target")), f.get("category", ""), f.get("date") or ""))
    clipped = [{k: (f[k] if len(str(f[k])) <= CLIP else str(f[k])[:CLIP] + "…") for k in BATCH_FIELDS if f.get(k)}
               for f in ordered]
    return [clipped[i:i + size] for i in range(0, len(clipped), size)]


def numbered(directory, prefix):
    found = {}
    for path in Path(directory).glob(f"{prefix}-*.json"):
        number = path.stem[len(prefix) + 1:]
        if number.isdigit():
            found[int(number)] = path
    return dict(sorted(found.items()))


def load_clusters(directory):
    """Returns (findings by ref, clusters by id, problems)."""
    findings, clusters, problems = {}, {}, []
    batch_files, cluster_files = numbered(directory, "batch"), numbered(directory, "clusters")
    for n, path in batch_files.items():
        for finding in json.loads(path.read_text()):
            findings[finding["ref"]] = finding
        if n not in cluster_files:
            problems.append(f"batch-{n}.json: no clusters-{n}.json")
    for n, path in cluster_files.items():
        try:
            returned = json.loads(path.read_text())
        except json.JSONDecodeError as error:
            problems.append(f"{path.name}: not valid JSON ({error})")
            continue
        for i, cluster in enumerate(returned, 1):
            cid = f"{n}.{i}"
            missing = [k for k in ("owner", "cause", "proposal", "members") if not cluster.get(k)]
            if missing:
                problems.append(f"{cid}: no {', '.join(missing)}")
            clusters[cid] = {"owner": "", "cause": "", "proposal": "", "members": [], **cluster}
    return findings, clusters, problems


def group_clusters(clusters, merges):
    """Returns (groups of cluster ids, problems): each --merges group, every other cluster alone.

    Equal owner and cause text is no ground to merge: cluster subagents give unrelated skipped
    singletons the same placeholder owner and cause.
    """
    groups, problems, taken = [], [], {}
    for g, merge in enumerate(merges, 1):
        ids = merge.get("ids") or []
        for cid in ids:
            if cid not in clusters:
                problems.append(f"merges[{g}]: unknown cluster {cid}")
            elif cid in taken:
                problems.append(f"merges[{g}]: {cid} is already in merges[{taken[cid]}]")
            else:
                taken[cid] = g
        groups.append([cid for cid in ids if taken.get(cid) == g])
    return [g for g in groups if g] + [[cid] for cid in clusters if cid not in taken], problems


def merge(directory, merges=()):
    """Returns (merged clusters, problems)."""
    findings, clusters, problems = load_clusters(directory)
    groups, merge_problems = group_clusters(clusters, list(merges))
    problems += merge_problems
    placed = {}
    for cid, cluster in clusters.items():
        for ref in cluster["members"]:
            if ref not in findings:
                problems.append(f"{cid}: {ref} is in no batch")
            placed.setdefault(ref, []).append(cid)
    problems += [f"{ref}: in {', '.join(ids)}" for ref, ids in placed.items() if len(ids) > 1]
    problems += [f"{ref}: in no cluster" for ref in findings if ref not in placed]
    if problems:
        return [], problems

    text = {m["ids"][0]: m for m in merges if m.get("ids")}
    merged = []
    for ids in groups:
        first = clusters[ids[0]]
        override = text.get(ids[0], {})
        members = sorted({ref for cid in ids for ref in clusters[cid]["members"]},
                         key=lambda ref: (findings[ref].get("date") or "", ref))
        statuses = {}
        for ref in members:
            word = findings[ref].get("status", "").split(" ")[0]
            statuses[word] = statuses.get(word, 0) + 1
        weight = max(WEIGHT.get(findings[ref].get("severity"), 1) for ref in members)
        merged.append({
            "id": ids[0], "src": ids,
            **{k: override.get(k) or first[k] for k in ("owner", "cause", "proposal")},
            "members": members, "canonical": members[0], "statuses": statuses,
            "weight": weight, "score": len(members) * weight,
            "projects": sorted({ref.split("/")[0] for ref in members}),
            "rejected": [ref for ref in members if findings[ref].get("status", "").startswith("rejected")],
            "forward": set(statuses) != {"skipped"} or len(members) >= 3,
        })
    merged.sort(key=lambda c: (-c["score"], c["id"]))
    return merged, []


def index_lines(merged):
    rows = sorted(merged, key=lambda c: (owner(c["owner"]), c["owner"].lower(), c["id"]))
    return [f"{c['id']} | {' '.join(f'{v} {k}' for k, v in c['statuses'].items())} | {c['owner']} | {c['cause']}"
            for c in rows]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--all", action="store_true")
    c.add_argument("--skipped-days", type=int, default=28)
    c.add_argument("--root", default=str(ROOT))
    b = sub.add_parser("batches")
    b.add_argument("--out", required=True)
    b.add_argument("--size", type=int, default=40)
    b.add_argument("--skipped-days", type=int, default=28)
    b.add_argument("--root", default=str(ROOT))
    m = sub.add_parser("merge")
    m.add_argument("dir")
    m.add_argument("--merges")
    s = sub.add_parser("set")
    s.add_argument("ref", nargs="?")
    s.add_argument("status", nargs="?")
    s.add_argument("--from", dest="from_file")
    s.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)

    if args.command == "collect":
        found = collect(args.root, everything=True) if args.all else digestible(args.root, args.skipped_days)
        print(json.dumps(found, indent=2, ensure_ascii=False))
        return 0
    if args.command == "batches":
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        for i, batch in enumerate(batches(digestible(args.root, args.skipped_days), args.size), 1):
            path = out / f"batch-{i}.json"
            path.write_text(json.dumps(batch, indent=1, ensure_ascii=False))
            print(f"{path} ({len(batch)} findings)")
        return 0
    if args.command == "merge":
        merges = json.loads(Path(args.merges).read_text()) if args.merges else []
        merged, problems = merge(args.dir, merges)
        if problems:
            print("\n".join(problems), file=sys.stderr)
            return 1
        out = Path(args.dir)
        (out / "merged.json").write_text(json.dumps(merged, indent=1, ensure_ascii=False))
        (out / "index.txt").write_text("\n".join(index_lines(merged)) + "\n")
        forward = [c for c in merged if c["forward"]]
        print(f"{out / 'merged.json'}: {len(merged)} clusters, {len(forward)} forward "
              f"({sum(1 for c in forward if c['rejected'])} with a rejected member); index in {out / 'index.txt'}")
        return 0
    if args.from_file:
        updates = json.loads(Path(args.from_file).read_text())
    elif args.ref and args.status:
        updates = {args.ref: args.status}
    else:
        parser.error("set needs <ref> <status> or --from <file.json>")
    failed = False
    for ref, status in updates.items():
        try:
            set_status(args.root, ref, status)
            print(f"{ref}: {status}")
        except ValueError as error:
            print(error, file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
