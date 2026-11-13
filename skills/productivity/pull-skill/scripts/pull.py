#!/usr/bin/env python3
"""Copy skills from a GitHub repo into this repo and record where they came from in upstream.json."""
import argparse
import io
import json
import re
import subprocess
import sys
import tarfile
from pathlib import PurePosixPath, Path

ROOT = Path(__file__).resolve().parents[4]
MANIFEST = "upstream.json"
LICENSE_NAME = re.compile(r"(?i)licen[cs]e(\.md|\.txt)?")
MIT_GRANT = "Permission is hereby granted, free of charge"


def gh(*args, raw=False):
    out = subprocess.run(["gh", "api", *args], check=True, capture_output=True).stdout
    return out if raw else json.loads(out)


def load_manifest(root):
    path = root / MANIFEST
    return json.loads(path.read_text()) if path.exists() else {"skills": {}}


def save_manifest(root, manifest):
    (root / MANIFEST).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def local_skill_names(root):
    return {p.parent.name for p in (root / "skills").glob("*/*/SKILL.md")}


def read_tarball(data):
    """Map each regular file to its bytes, keyed by its path inside the repo (GitHub prefixes a top dir)."""
    files = {}
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        for member in tar.getmembers():
            if not member.isfile() or "/" not in member.name:
                continue
            rel = member.name.split("/", 1)[1]
            parts = PurePosixPath(rel).parts
            if ".." in parts or rel.startswith("/"):
                continue
            files[rel] = tar.extractfile(member).read()
    return files


def skill_files(files, path):
    prefix = path.rstrip("/") + "/"
    return {rel[len(prefix):]: data for rel, data in files.items() if rel.startswith(prefix)}


def nearest_license(files, path):
    """The LICENSE closest to the skill, walking up from its folder to the repo root."""
    folder = PurePosixPath(path)
    for directory in [folder, *folder.parents]:
        base = "" if str(directory) == "." else f"{directory}/"
        for rel, data in files.items():
            if rel.startswith(base) and "/" not in rel[len(base):] and LICENSE_NAME.fullmatch(rel[len(base):]):
                return rel, data
    return None, None


def detect_spdx(repo, text):
    if MIT_GRANT in text:
        return "MIT"
    spdx = (gh(f"repos/{repo}/license").get("license") or {}).get("spdx_id")
    return spdx if spdx and spdx != "NOASSERTION" else None


def rename_skill(skill_md, name):
    text = skill_md.decode()
    renamed, count = re.subn(r"(?m)^name:.*$", f"name: {name}", text, count=1)
    if not count:
        raise SystemExit("SKILL.md has no `name:` line to rename")
    return renamed.encode()


def pull(repo, paths, ref, category, as_name, license_override, root=ROOT):
    if as_name and len(paths) != 1:
        raise SystemExit("--as renames a single skill; pass one path")
    manifest = load_manifest(root)
    taken = local_skill_names(root) | set(manifest["skills"])
    sha = gh(f"repos/{repo}/commits/{ref}")["sha"]
    files = read_tarball(gh(f"repos/{repo}/tarball/{sha}", raw=True))

    planned = []
    for path in paths:
        path = path.strip("/")
        name = as_name or PurePosixPath(path).name
        contents = skill_files(files, path)
        if "SKILL.md" not in contents:
            raise SystemExit(f"{repo}@{sha[:7]} has no SKILL.md under {path}")
        if name in taken:
            raise SystemExit(f"a skill named {name} already exists here; pick another with --as")
        license_rel, license_data = nearest_license(files, path)
        spdx = license_override or (license_data and detect_spdx(repo, license_data.decode(errors="replace")))
        if not spdx:
            raise SystemExit(f"no license found for {repo}/{path}; it may not allow redistribution")
        if as_name:
            contents["SKILL.md"] = rename_skill(contents["SKILL.md"], name)
        taken.add(name)
        planned.append((name, path, contents, license_rel, license_data, spdx))

    summary = []
    for name, path, contents, license_rel, license_data, spdx in planned:
        dest = root / "skills" / category / name
        for rel, data in contents.items():
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        license_file = None
        if license_data:
            owner_repo = repo.replace("/", "-")
            folder = str(PurePosixPath(license_rel).parent)
            suffix = "" if folder == "." else "-" + folder.replace("/", "-")
            license_file = f"licenses/{owner_repo}{suffix}"
            (root / "licenses").mkdir(exist_ok=True)
            (root / license_file).write_bytes(license_data)
        manifest["skills"][name] = {
            "repo": repo, "path": path, "ref": ref, "imported": sha, "checked": sha,
            "license": spdx, "license_file": license_file,
        }
        summary.append({"name": name, "dest": str(dest.relative_to(root)), "files": len(contents),
                        "license": spdx, "renamed_from": PurePosixPath(path).name if as_name else None})
    save_manifest(root, manifest)
    return {"repo": repo, "sha": sha, "skills": summary}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", help="owner/repo on GitHub")
    parser.add_argument("paths", nargs="+", help="skill folder inside the repo, e.g. skills/engineering/tdd")
    parser.add_argument("--ref", default="main")
    parser.add_argument("--category", required=True, help="folder under skills/ to place them in")
    parser.add_argument("--as", dest="as_name", help="local name, for a single skill")
    parser.add_argument("--license", dest="license_override",
                        help="SPDX id, only when you checked the license by hand and the script can't find it")
    args = parser.parse_args(argv)
    print(json.dumps(pull(args.repo, args.paths, args.ref, args.category, args.as_name, args.license_override),
                     indent=2))


if __name__ == "__main__":
    sys.exit(main())
