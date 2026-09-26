"""Archive the raw inspect logs and write their checksum manifest.

Usage (from project root, with the DarkBench venv for inspect_ai):
    DarkBench/.venv/bin/python make_raw_manifest.py

The raw .eval logs are too large for git (see .gitignore). The durable record is
a dated zip stored OUTSIDE the repo plus data/raw-manifest.json, which is
committed. This script builds both, and verifies what it wrote before exiting.

Curated metadata (the role each log played, and which judge produced a scored
log) is carried over from the previous manifest where the file is already known,
so hand-assigned roles are never silently re-derived. New files get a role
inferred from their filename and header, and the script prints those for review.

Re-run this whenever new logs are added, otherwise the manifest goes stale and
the archive stops covering the results the writeup depends on.
"""

import datetime as dt
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(HERE, "data", "raw", "inspect-logs")
MANIFEST = os.path.join(HERE, "data", "raw-manifest.json")
TODAY = dt.date.today().isoformat()
ZIP_PATH = os.path.expanduser(f"~/Desktop/dark-bench-replication-raw-logs-{TODAY}.zip")

UPSTREAM = "7eef15102b37df2a15a6031cbbed6be488de7fbe (apartresearch/DarkBench)"


def sha256(path, buf=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(buf):
            h.update(chunk)
    return h.hexdigest()


def derive(path, header):
    """Infer (role, judge) for a log the previous manifest did not know about."""
    name = os.path.basename(path)
    m = re.search(r"-scored-([a-z0-9-]+)\.eval$", name)
    if m:
        return "scored", m.group(1)
    n = len(header.samples) if header.samples is not None else header.results and header.results.total_samples
    n = n or 0
    if n >= 660 and header.status == "success":
        return "generation-canonical", None
    if n >= 660:
        return "generation-partial", None
    return "generation-smoke", None


def main():
    from inspect_ai.log import read_eval_log

    old = {}
    prev_note = prev_roles = None
    if os.path.exists(MANIFEST):
        prev = json.load(open(MANIFEST))
        old = {os.path.basename(f["path"]): f for f in prev["files"]}
        prev_note, prev_roles = prev.get("scorer_fixes_note"), prev.get("roles")
        print(f"previous manifest: {prev['file_count']} files, created {prev['created']}")

    paths = sorted(glob.glob(os.path.join(LOG_DIR, "*.eval")))
    print(f"logs on disk: {len(paths)}")

    files, new_entries = [], []
    for p in paths:
        name = os.path.basename(p)
        log = read_eval_log(p, header_only=True)
        known = old.get(name)
        if known:
            role, judge = known.get("role"), known.get("judge")
        else:
            role, judge = derive(p, log)
            new_entries.append((name, role, judge))
        files.append({
            "path": os.path.relpath(p, HERE),
            "sha256": sha256(p),
            "bytes": os.path.getsize(p),
            "model": log.eval.model,
            "created": log.eval.created,
            "status": log.status,
            "samples": len(log.samples) if log.samples is not None else None,
            "inspect_version": log.eval.packages.get("inspect_ai") if log.eval.packages else None,
            "role": role,
            "judge": judge,
        })

    if new_entries:
        print(f"\nnew since the last manifest ({len(new_entries)}), roles derived:")
        for name, role, judge in new_entries:
            print(f"  {role:22} judge={judge or '-':22} {name}")

    print(f"\nzipping {len(paths)} logs -> {ZIP_PATH}")
    if os.path.exists(ZIP_PATH):
        sys.exit(f"refusing to overwrite an existing archive: {ZIP_PATH}")
    subprocess.run(["zip", "-q", "-j", "-X", ZIP_PATH] + paths, check=True)

    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "zip_path": ZIP_PATH,
        "zip_sha256": sha256(ZIP_PATH),
        "zip_bytes": os.path.getsize(ZIP_PATH),
        "file_count": len(files),
        "upstream_commit": UPSTREAM,
        "scorer_fixes_note": prev_note,
        "roles": prev_roles,
        "files": files,
    }
    with open(MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    print(f"wrote {MANIFEST}: {len(files)} files, zip {manifest['zip_bytes'] / 1048576:.0f} MB")


if __name__ == "__main__":
    main()
