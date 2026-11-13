#!/usr/bin/env python3
"""Condense a Claude Code session transcript (.jsonl) into a readable timeline.

Usage: condense_session.py <session.jsonl> [--max N]
Each line: [index] ROLE: text, tool calls with their input, and tool results
(errors flagged). Long values are truncated to N chars (default 400).
"""
import json
import sys


def clip(value, limit):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = " ".join(text.split())
    return text if len(text) <= limit else f"{text[:limit]}… [+{len(text) - limit} chars]"


def result_text(content):
    if isinstance(content, str):
        return content
    return " ".join(part.get("text", f"<{part.get('type')}>") for part in content or [])


def main():
    args = sys.argv[1:]
    limit = 400
    if "--max" in args:
        i = args.index("--max")
        limit = int(args[i + 1])
        del args[i : i + 2]
    if len(args) != 1:
        sys.exit(__doc__)

    with open(args[0], encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            entry = json.loads(line)
            kind = entry.get("type")
            if kind not in ("user", "assistant") or entry.get("isMeta"):
                continue
            prefix = "SUBAGENT " if entry.get("isSidechain") else ""
            content = entry.get("message", {}).get("content")
            if isinstance(content, str):
                print(f"[{index}] {prefix}{kind.upper()}: {clip(content, limit)}")
                continue
            for part in content or []:
                ptype = part.get("type")
                if ptype == "text":
                    print(f"[{index}] {prefix}{kind.upper()}: {clip(part['text'], limit)}")
                elif ptype == "tool_use":
                    print(f"[{index}] {prefix}CALL {part['name']}: {clip(part.get('input'), limit)}")
                elif ptype == "tool_result":
                    flag = "ERROR" if part.get("is_error") else "RESULT"
                    print(f"[{index}] {prefix}{flag}: {clip(result_text(part.get('content')), limit)}")


if __name__ == "__main__":
    main()
