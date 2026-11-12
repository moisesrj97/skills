#!/usr/bin/env python3
"""Fetch a GitHub PR comment from its URL, or reply to it in the right place.

Usage:
  comment.py fetch <url>                 JSON: kind, owner, repo, pr, id, author, body, base, head,
                                         head_sha; inline comments add path, line, outdated,
                                         diff_hunk and context (the file at head_sha around line)
  comment.py reply <url> <body file>     posts the body: in the comment's thread for an inline
                                         comment, as a new PR comment for a general one; prints its URL

URLs: .../pull/<n>#discussion_r<id> (inline review comment) or .../pull/<n>#issuecomment-<id>.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

URL = re.compile(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)[^#]*#(discussion_r|issuecomment-)(\d+)")
BYLINE = "> [!NOTE]"
CONTEXT = 20


def parse_url(url):
    match = URL.search(url)
    if not match:
        raise ValueError(f"not a PR comment URL (…/pull/<n>#discussion_r<id> or #issuecomment-<id>): {url}")
    owner, repo, pr, kind, comment_id = match.groups()
    return {"kind": "inline" if kind == "discussion_r" else "general",
            "owner": owner, "repo": repo, "pr": int(pr), "id": int(comment_id)}


def gh(*args, raw=False):
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"gh {' '.join(args)} failed")
    return result.stdout if raw else json.loads(result.stdout)


def numbered(text, line, radius=CONTEXT):
    lines = text.splitlines()
    start, end = max(1, line - radius), min(len(lines), line + radius)
    return "\n".join(f"{n:>5}{'>' if n == line else ' '} {lines[n - 1]}" for n in range(start, end + 1))


def fetch(url):
    ref = parse_url(url)
    slug = f"repos/{ref['owner']}/{ref['repo']}"
    endpoint = "pulls/comments" if ref["kind"] == "inline" else "issues/comments"
    comment = gh("api", f"{slug}/{endpoint}/{ref['id']}")
    pr = gh("pr", "view", str(ref["pr"]), "--repo", f"{ref['owner']}/{ref['repo']}",
            "--json", "baseRefName,headRefName,headRefOid")
    out = {**ref, "author": comment["user"]["login"], "body": comment["body"],
           "base": pr["baseRefName"], "head": pr["headRefName"], "head_sha": pr["headRefOid"]}
    if ref["kind"] == "inline":
        line = comment.get("line") or comment.get("original_line")
        out.update({"path": comment["path"], "line": line, "outdated": comment.get("line") is None,
                    "diff_hunk": comment.get("diff_hunk"), "in_reply_to_id": comment.get("in_reply_to_id")})
        try:
            text = gh("api", f"{slug}/contents/{quote(comment['path'])}?ref={pr['headRefOid']}",
                      "-H", "Accept: application/vnd.github.raw", raw=True)
            out["context"] = numbered(text, line) if line else None
        except RuntimeError as error:
            out["context"] = f"(file not readable at head: {error})"
    return out


def reply_endpoint(ref, in_reply_to_id=None):
    slug = f"repos/{ref['owner']}/{ref['repo']}"
    if ref["kind"] == "inline":
        # GitHub only takes replies to a thread's top comment; a reply's own id is refused.
        return f"{slug}/pulls/{ref['pr']}/comments/{in_reply_to_id or ref['id']}/replies"
    return f"{slug}/issues/{ref['pr']}/comments"


def reply(url, body_file):
    ref = parse_url(url)
    if not Path(body_file).read_text().startswith(BYLINE):
        raise ValueError(f"the body must open with the agent-byline callout ({BYLINE} …)")
    top = None
    if ref["kind"] == "inline":
        top = gh("api", f"repos/{ref['owner']}/{ref['repo']}/pulls/comments/{ref['id']}").get("in_reply_to_id")
    posted = gh("api", reply_endpoint(ref, top), "-X", "POST", "-F", f"body=@{body_file}")
    return posted["html_url"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("url")
    r = sub.add_parser("reply")
    r.add_argument("url")
    r.add_argument("body_file")
    args = parser.parse_args(argv)
    try:
        if args.command == "fetch":
            print(json.dumps(fetch(args.url), indent=2, ensure_ascii=False))
        else:
            print(reply(args.url, args.body_file))
    except (ValueError, RuntimeError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
