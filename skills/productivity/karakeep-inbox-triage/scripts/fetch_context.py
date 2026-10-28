"""Prints a compact JSON snapshot: Inbox bookmarks, lists (with paths and sample titles) and tags."""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor

import kk


def bookmark_view(b):
    c = b.get("content") or {}
    return {
        "id": b["id"],
        "type": c.get("type"),
        "title": b.get("title") or c.get("title") or c.get("fileName"),
        "url": c.get("url"),
        "publisher": c.get("publisher"),
        "description": (c.get("description") or c.get("text") or "")[:300],
        "note": b.get("note"),
        "summary": b.get("summary"),
        "tags": [t if isinstance(t, str) else t["name"] for t in b.get("tags", [])],
        "crawlStatus": c.get("crawlStatus"),
    }


def samples(lst, n):
    res = kk.run("bookmarks", "search", f'list:"{lst["name"]}"', "--limit", str(n), "--sort-order", "desc")
    views = [bookmark_view(b) for b in res["bookmarks"][:n]]
    return [{"title": v["title"] or v["url"], "tags": v["tags"]} for v in views]


def inbox_ids_in(lst):
    res = kk.run("bookmarks", "search", f'list:"{kk.INBOX_LIST_NAME}" list:"{lst["name"]}"', "--all")
    return {b["id"] for b in res["bookmarks"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=5, help="sample titles per list (0 to skip)")
    args = ap.parse_args()

    all_lists = kk.lists()
    by_id = {l["id"]: l for l in all_lists}
    manual = [l for l in all_lists if l["type"] == "manual"]
    inbox = next((l for l in manual if l["name"] == kk.INBOX_LIST_NAME), None)
    if inbox is None:
        raise SystemExit(f'No manual list named "{kk.INBOX_LIST_NAME}" found')

    with ThreadPoolExecutor(8) as pool:
        sample_map = dict(zip(
            [l["id"] for l in manual],
            pool.map(lambda l: samples(l, args.samples) if args.samples else [], manual),
        ))
        overlap = dict(zip(
            [l["id"] for l in manual if l["id"] != inbox["id"]],
            pool.map(inbox_ids_in, [l for l in manual if l["id"] != inbox["id"]]),
        ))
        inbox_res = pool.submit(kk.run, "bookmarks", "search", f'list:"{kk.INBOX_LIST_NAME}"', "--all").result()
        tags = pool.submit(kk.run, "tags", "list").result()

    out = {
        "inboxListId": inbox["id"],
        "inbox": [
            {**bookmark_view(b), "alsoInLists": [kk.list_path(by_id[lid], by_id) for lid, ids in overlap.items() if b["id"] in ids]}
            for b in inbox_res["bookmarks"]
        ],
        "lists": [
            {"id": l["id"], "path": kk.list_path(l, by_id), "icon": l["icon"], "samples": sample_map[l["id"]]}
            for l in manual if l["id"] != inbox["id"]
        ],
        "tagsInUse": {t["name"]: t["numBookmarks"] for t in sorted(tags, key=lambda t: -t["numBookmarks"]) if t["numBookmarks"] > 0},
        "tagsUnused": sorted(t["name"] for t in tags if t["numBookmarks"] == 0),
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
