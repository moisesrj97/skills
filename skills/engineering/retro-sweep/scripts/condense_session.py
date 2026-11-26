#!/usr/bin/env python3
"""Condense a Claude Code session transcript (.jsonl) into a readable timeline.

Usage: condense_session.py <session.jsonl> [--max N]
Each line: [index] ROLE: text, tool calls with their input, and tool results
(errors flagged). Long values are truncated to N chars (default 400).
"""
import json
import re
import sys

NO_MATCH_COMMANDS = re.compile(r"^(grep|egrep|fgrep|rg|git grep|which|test|\[\[?|ls)(?=\s|$)")
MISSING_FILE = re.compile(r"^ls: .+: No such file or directory$")


def clip(value, limit):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = " ".join(text.split())
    return text if len(text) <= limit else f"{text[:limit]}… [+{len(text) - limit} chars]"


def result_text(content):
    if isinstance(content, str):
        return content
    return " ".join(part.get("text", f"<{part.get('type')}>") for part in content or [])


def last_command(command):
    segments = [s.strip() for s in re.split(r"\|\||&&|[|;\n]", command or "") if s.strip()]
    if not segments:
        return ""
    return re.sub(r"^(\w+=\S*\s+)+", "", segments[-1])


def expected_no_match(call, text):
    """grep, rg, which and test exit 1 to answer "no", and ls for a missing path: that is not an error."""
    if not call or call.get("name") != "Bash":
        return False
    head, _, output = text.partition("\n")
    if head.strip() != "Exit code 1":
        return False
    command = last_command(call.get("input", {}).get("command"))
    match = NO_MATCH_COMMANDS.match(command)
    if not match:
        return False
    if match.group(1) != "ls":
        return True
    complaints = [line for line in output.splitlines() if line.startswith("ls:")]
    return bool(complaints) and all(MISSING_FILE.match(line) for line in complaints)


def main():
    args = sys.argv[1:]
    limit = 400
    if "--max" in args:
        i = args.index("--max")
        limit = int(args[i + 1])
        del args[i : i + 2]
    if len(args) != 1:
        sys.exit(__doc__)

    calls = {}
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
                    calls[part.get("id")] = part
                    print(f"[{index}] {prefix}CALL {part['name']}: {clip(part.get('input'), limit)}")
                elif ptype == "tool_result":
                    text = result_text(part.get("content"))
                    error = part.get("is_error") and not expected_no_match(calls.get(part.get("tool_use_id")), text)
                    print(f"[{index}] {prefix}{'ERROR' if error else 'RESULT'}: {clip(text, limit)}")


if __name__ == "__main__":
    main()
