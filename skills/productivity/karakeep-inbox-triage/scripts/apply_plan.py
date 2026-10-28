"""Applies an approved triage plan. Dry run unless --execute is passed.

Plan format:
{
  "newLists": [{"key": "wishlist-tech", "name": "Tech", "icon": "🛒", "parent": "<list id | newLists key | null>"}],
  "bookmarks": [{"id": "<bookmark id>", "addTags": ["a", "b"], "list": "<list id | newLists key>"}]
}
"""
import argparse
import difflib
import json
import re
import sys

import kk


def create_list(spec, parent_id):
    args = ["lists", "create", "--name", spec["name"], "--icon", spec.get("icon") or "📁"]
    if spec.get("description"):
        args += ["--description", spec["description"]]
    if parent_id:
        args += ["--parent-id", parent_id]
    kk.run(*args, parse=False)
    # Look the list up instead of trusting the create output shape.
    match = [l for l in kk.lists() if l["name"] == spec["name"] and l.get("parentId") == parent_id]
    if not match:
        raise RuntimeError(f'Created list "{spec["name"]}" but could not find it afterwards')
    return match[0]["id"]


def inbox_members_of(list_name, cache={}):
    if list_name not in cache:
        res = kk.run("bookmarks", "search", f'list:"{kk.INBOX_LIST_NAME}" list:"{list_name}"', "--all")
        cache[list_name] = {b["id"] for b in res["bookmarks"]}
    return cache[list_name]


def normalize(tag):
    return re.sub(r"[^a-z0-9]", "", tag.lower()).removesuffix("s")


def new_items_report(plan, existing_lists):
    existing_tags = [t["name"] for t in kk.run("tags", "list")]
    canonical = {t.lower(): t for t in existing_tags}
    for b in plan["bookmarks"]:
        b["addTags"] = [canonical.get(t.lower(), t) for t in b.get("addTags", [])]
    known = set(canonical)
    by_norm = {}
    for t in existing_tags:
        by_norm.setdefault(normalize(t), []).append(t)

    proposed = sorted({t for b in plan["bookmarks"] for t in b.get("addTags", [])})
    lines = []
    new_tags = [t for t in proposed if t.lower() not in known]
    lines.append("NEW TAGS: " + (", ".join(new_tags) if new_tags else "none"))
    for t in new_tags:
        similar = by_norm.get(normalize(t), []) + difflib.get_close_matches(t, existing_tags, n=3, cutoff=0.8)
        if similar:
            lines.append(f"  WARN tag '{t}' looks like existing: {', '.join(dict.fromkeys(similar))}")

    new_lists = plan.get("newLists", [])
    lines.append("NEW LISTS: " + (", ".join(l["name"] for l in new_lists) if new_lists else "none"))
    for l in new_lists:
        clash = [e for e in existing_lists.values() if e["name"].lower() == l["name"].lower()]
        if clash:
            lines.append(f"  WARN list '{l['name']}' shares its name with {len(clash)} existing list(s); list:\"{l['name']}\" searches become ambiguous")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    plan = json.load(open(args.plan))

    existing = {l["id"]: l for l in kk.lists()}
    inbox_id = next(l["id"] for l in existing.values() if l["name"] == kk.INBOX_LIST_NAME)
    ids = {k: k for k in existing}
    report = new_items_report(plan, existing)
    log = []

    for spec in plan.get("newLists", []):
        parent = spec.get("parent")
        parent_id = ids.get(parent) if parent else None
        if parent and not parent_id:
            sys.exit(f'Unknown parent "{parent}" for new list "{spec["name"]}"')
        if args.execute:
            ids[spec["key"]] = create_list(spec, parent_id)
        else:
            ids[spec["key"]] = f"<new:{spec['key']}>"
        log.append(f'CREATE LIST {spec["name"]} (parent={parent_id}) -> {ids[spec["key"]]}')

    failures = 0
    for item in plan["bookmarks"]:
        bid, target = item["id"], ids.get(item.get("list"))
        if item.get("list") and not target:
            sys.exit(f'Unknown list "{item["list"]}" for bookmark {bid}')
        steps = []
        if item.get("addTags"):
            tag_args = [a for t in item["addTags"] for a in ("--add-tag", t)]
            steps.append((f"tags +{item['addTags']}", ["bookmarks", "update-tags", bid, *tag_args]))
        already = target in existing and bid in inbox_members_of(existing[target]["name"])
        if target and not already:
            steps.append((f"-> list {target}", ["lists", "add-bookmark", "--list", target, "--bookmark", bid]))
        if target and target != inbox_id:
            steps.append(("remove from Inbox", ["lists", "remove-bookmark", "--list", inbox_id, "--bookmark", bid]))
        for label, cmd in steps:
            if not args.execute:
                log.append(f"DRY {bid}: {label}")
                continue
            try:
                kk.run(*cmd, parse=False)
                log.append(f"OK  {bid}: {label}")
            except RuntimeError as e:
                failures += 1
                log.append(f"ERR {bid}: {label}: {e}")
                break  # never drop it from Inbox if an earlier step failed

    print("\n".join(report + [""] + log))
    print(f"\n{'EXECUTED' if args.execute else 'DRY RUN'} — {len(plan['bookmarks'])} bookmarks, {failures} failures")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
