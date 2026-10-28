import json
import os
import subprocess
from pathlib import Path

CONFIG_FILE = Path("~/.config/moisesrj97-skills/karakeep.json").expanduser()
KEY_FILE = Path("~/.karakeep").expanduser()
INBOX_LIST_NAME = "Inbox"


def env():
    e = dict(os.environ)
    if not e.get("KARAKEEP_API_KEY"):
        if not KEY_FILE.exists():
            raise RuntimeError(f"missing {KEY_FILE}: run the skill's first-run setup")
        e["KARAKEEP_API_KEY"] = KEY_FILE.read_text().strip()
    if not e.get("KARAKEEP_SERVER_ADDR"):
        if not CONFIG_FILE.exists():
            raise RuntimeError(f"missing {CONFIG_FILE}: run the skill's first-run setup")
        e["KARAKEEP_SERVER_ADDR"] = json.loads(CONFIG_FILE.read_text())["server"]
    return e


def run(*args, parse=True):
    proc = subprocess.run(["karakeep", "--json", *args], capture_output=True, text=True, env=env())
    if proc.returncode != 0:
        raise RuntimeError(f"karakeep {' '.join(args)} failed: {proc.stderr.strip() or proc.stdout.strip()}")
    return json.loads(proc.stdout) if parse and proc.stdout.strip() else proc.stdout


def lists():
    return run("lists", "list")["lists"]


def list_path(lst, by_id):
    parts = [lst["name"]]
    parent = lst.get("parentId")
    while parent and parent in by_id:
        parts.insert(0, by_id[parent]["name"])
        parent = by_id[parent].get("parentId")
    return " / ".join(parts)
