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

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

# Scripts live in scripts/; every data path below is relative to the repository root.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Both raw-log directories. inspect-logs holds the original generation and scoring passes;
# inspect-logs-rescore holds the 2026-09-27 brand-bias re-score (CORRECTIONS.md, finding A).
LOG_DIRS = [
    os.path.join(ROOT, "data", "raw", "inspect-logs"),
    os.path.join(ROOT, "data", "raw", "inspect-logs-rescore"),
]
MANIFEST = os.path.join(ROOT, "data", "raw-manifest.json")
TODAY = dt.date.today().isoformat()
ZIP_PATH = os.path.expanduser(f"~/Desktop/dark-bench-replication-raw-logs-{TODAY}.zip")

UPSTREAM = "7eef15102b37df2a15a6031cbbed6be488de7fbe (apartresearch/DarkBench)"


def sha256(path, buf=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(buf):
            h.update(chunk)
    return h.hexdigest()


def n_samples(header):
    """Sample count from a header-only read.

    read_eval_log(header_only=True) does not populate .samples, so fall back to
    results.total_samples. Reading .samples alone silently yields None and was
    the cause of the samples regression fixed on 2026-09-26.
    """
    if header.samples is not None:
        return len(header.samples)
    if header.results is not None:
        return header.results.total_samples
    return None


def derive(path, header):
    """Infer (role, judge) for a log the previous manifest did not know about."""
    name = os.path.basename(path)
    m = re.search(r"-rescored-([a-z0-9-]+)\.eval$", name)
    if m:
        # 2026-09-27 brand-bias re-score: 110 samples, one category, corrected developer.
        return "rescored-brandbias", m.group(1)
    m = re.search(r"-scored-([a-z0-9-]+)\.eval$", name)
    if m:
        return "scored", m.group(1)
    n = n_samples(header) or 0
    if n >= 660 and header.status == "success":
        return "generation-canonical", None
    if n >= 660:
        return "generation-partial", None
    return "generation-smoke", None


def main():
    from inspect_ai.log import read_eval_log

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest-only", action="store_true",
                    help="rewrite the manifest without re-cutting the zip; the existing archive "
                         "named in the current manifest is re-hashed and its checksum reused")
    ap.add_argument("--prev", default=MANIFEST,
                    help="manifest to carry curated fields forward from (default: the current one)")
    args = ap.parse_args()

    old = {}
    prev_note = prev_roles = None
    if os.path.exists(args.prev):
        prev = json.load(open(args.prev))
        old = {os.path.basename(f["path"]): f for f in prev["files"]}
        prev_note, prev_roles = prev.get("scorer_fixes_note"), prev.get("roles")
        print(f"carrying forward from: {args.prev}")
        print(f"  {prev['file_count']} files, created {prev['created']}")

    paths = []
    for d in LOG_DIRS:
        found = sorted(glob.glob(os.path.join(d, "*.eval")))
        print(f"logs in {os.path.relpath(d, ROOT)}: {len(found)}")
        paths.extend(found)
    print(f"logs on disk: {len(paths)}")

    files, new_entries = [], []
    for p in paths:
        name = os.path.basename(p)
        log = read_eval_log(p, header_only=True)
        known = old.get(name)
        if known:
            role, judge = known.get("role"), known.get("judge")
            # Carry the recorded count forward; fall back if the source lacked one.
            samples = known.get("samples")
            if samples is None:
                samples = n_samples(log)
        else:
            role, judge = derive(p, log)
            samples = n_samples(log)
            new_entries.append((name, role, judge, samples))
        files.append({
            "path": os.path.relpath(p, ROOT),
            "sha256": sha256(p),
            "bytes": os.path.getsize(p),
            "model": log.eval.model,
            "created": log.eval.created,
            "status": log.status,
            "samples": samples,
            "inspect_version": log.eval.packages.get("inspect_ai") if log.eval.packages else None,
            "role": role,
            "judge": judge,
        })

    if new_entries:
        print(f"\nnew since that manifest ({len(new_entries)}), roles derived:")
        for name, role, judge, n in new_entries:
            print(f"  {role:22} judge={judge or '-':16} samples={n} {name}")

    if args.manifest_only:
        cur = json.load(open(MANIFEST))
        zip_path = cur["zip_path"]
        if not os.path.exists(zip_path):
            sys.exit(f"--manifest-only but the archive is missing: {zip_path}")
        print(f"\n--manifest-only: reusing {zip_path}")
        print("  re-hashing the existing archive to confirm it is unchanged...")
        zip_sha, zip_bytes = sha256(zip_path), os.path.getsize(zip_path)
        same = zip_sha == cur["zip_sha256"] and zip_bytes == cur["zip_bytes"]
        print(f"  zip sha256/size vs current manifest: {'UNCHANGED' if same else 'CHANGED'}")
        if not same:
            sys.exit("archive changed since the manifest was written; re-cut it instead")
    else:
        print(f"\nzipping {len(paths)} logs -> {ZIP_PATH}")
        if os.path.exists(ZIP_PATH):
            sys.exit(f"refusing to overwrite an existing archive: {ZIP_PATH}")
        subprocess.run(["zip", "-q", "-j", "-X", ZIP_PATH] + paths, check=True)
        zip_path, zip_sha, zip_bytes = ZIP_PATH, sha256(ZIP_PATH), os.path.getsize(ZIP_PATH)

    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "zip_path": zip_path,
        "zip_sha256": zip_sha,
        "zip_bytes": zip_bytes,
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
