"""Verify the 2026-09-27 brand-bias re-score against the actually saved judge requests.

Usage (from project root, needs the raw logs and inspect_ai; no model calls):
    DarkBench/.venv/bin/python scripts/verify_rescore_provenance.py

An earlier version of this script overstated what it checked, and the closure review of
2026-09-27 was right about all four defects:

  1. it rebuilt the rubric with today's identity resolver and called that verification. Correct
     code now does not prove what was sent then.
  2. `judge_model_recorded` came from `log.eval.model`, which is the *response-generating*
     model (Kimi/GLM). The judge was only inferred from the filename.
  3. coverage was checked over six (model, judge) cells, not the 660 expected sample ids, so a
     partial log would have passed.
  4. log status was printed but never failed the run, and verdict validity was tested only
     against -1.

All four are fixed here. The logs do retain what is needed: each scored sample carries two
ModelEvents, the generation call and the judge call. The judge call records the judge model and
its configuration, and its user message resolves through the sample's attachments to the exact
prompt text that was sent. So this script reads the real request rather than reconstructing it.

Checks, per (model, judge) cell:
  A. judge identity      the judge ModelEvent's model and temperature, as recorded
  B. rubric as sent      the developer named in the rubric *portion* of the saved request,
                         read before the conversation delimiter, since the user prompt and the
                         response may legitimately mention other companies
  C. response integrity  every scored response byte-identical to the canonical generation
  D. coverage            every expected brand-bias sample id present exactly once, for every
                         judge, and each verdict equal to the one in the final export
  E. verdict validity    scores present, in the allowed value set, and the log status success

Writes data/results/rescore_provenance.csv.
"""

import csv
import glob
import hashlib
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "DarkBench"))
LOG_DIR = os.path.join(ROOT, "data", "raw", "inspect-logs")
RESCORE_DIR = os.path.join(ROOT, "data", "raw", "inspect-logs-rescore")
RES = os.path.join(ROOT, "data", "results")
OUT = os.path.join(RES, "rescore_provenance.csv")

EXPECT_DEV = {"kimi-k3": "Moonshot AI", "glm-5p3": "Zhipu AI"}
EXPECT_JUDGE = {"gpt55": "openai/gpt-5.5-2026-04-23",
                "opus46": "anthropic/claude-opus-4-6",
                "gemini31pro": "google/gemini-3.1-pro-preview"}
ALLOWED = {True, False, 2, -1}
DELIM = "=== CONVERSATION START ==="


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def judge_event(sample):
    """The scoring call: the last ModelEvent, after the generation call."""
    evs = [e for e in (sample.events or []) if type(e).__name__ == "ModelEvent"]
    return evs[-1] if len(evs) >= 2 else None


def request_text(sample, ev):
    """Resolve the judge request, following an attachment reference when present."""
    if not ev or not ev.input:
        return ""
    raw = str(ev.input[-1].content)
    m = re.match(r"attachment://(\w+)", raw.strip())
    if m:
        return (sample.attachments or {}).get(m.group(1), "")
    return raw


def main():
    from inspect_ai.log import read_eval_log

    canon = {}
    for p in sorted(glob.glob(os.path.join(LOG_DIR, "*.eval"))):
        if "-scored-" in os.path.basename(p):
            continue
        log = read_eval_log(p)
        m = log.eval.model.split("/")[-1]
        if m in EXPECT_DEV and len(log.samples or []) == 660:
            canon[m] = (os.path.basename(p),
                        {s.id: s.output.completion for s in log.samples})
    print(f"canonical generation logs: {sorted(canon)}")

    export = {}
    for r in csv.DictReader(open(os.path.join(RES, "verdicts.csv"))):
        if r["category"] == "brand-bias" and r["model"] in EXPECT_DEV:
            export[(r["model"], r["judge"], r["sample_id"])] = r["raw_value"]

    rows, failures = [], []
    for p in sorted(glob.glob(os.path.join(RESCORE_DIR, "*-rescored-*.eval"))):
        judge_tag = re.search(r"-rescored-([a-z0-9]+)\.eval$", p).group(1)
        name = os.path.basename(p)
        log = read_eval_log(p)
        model = log.eval.model.split("/")[-1]
        src_name, src = canon[model]

        judge_models, judge_temps, rubric_devs, rubric_bad = set(), set(), set(), 0
        drift, bad_score, ids = [], [], []
        for s in log.samples:
            ids.append(s.id)
            ev = judge_event(s)
            if ev is None:
                bad_score.append(f"{s.id}: no judge ModelEvent")
                continue
            judge_models.add(ev.model)
            cfg = getattr(ev, "config", None)
            judge_temps.add(getattr(cfg, "temperature", None) if cfg else None)

            # B: developer named in the rubric portion only
            req = request_text(s, ev)
            head = req.split(DELIM)[0] if DELIM in req else ""
            if not head:
                rubric_bad += 1
            else:
                for dev in set(EXPECT_DEV.values()) | {"OpenAI"}:
                    if dev in head:
                        rubric_devs.add(dev)

            if src.get(s.id) != s.output.completion:
                drift.append(s.id)
            sc = (s.scores or {}).get("overseer")
            if sc is None or sc.value not in ALLOWED:
                bad_score.append(f"{s.id}: {None if sc is None else sc.value}")

        dup = [k for k, v in Counter(ids).items() if v > 1]
        expected = {sid for sid, _ in
                    [(k, v) for k, v in src.items() if k.startswith("brand-bias-")]}
        missing = sorted(expected - set(ids))
        unexpected = sorted(set(ids) - expected)
        mismatch = [s.id for s in log.samples
                    if str(list(s.scores.values())[0].value)
                    != export.get((model, judge_tag, s.id))]

        judge_ok = judge_models == {EXPECT_JUDGE[judge_tag]}
        rubric_ok = rubric_devs == {EXPECT_DEV[model]} and rubric_bad == 0

        rows.append({
            "model": model, "judge_tag": judge_tag,
            "rescored_log": name, "source_generation_log": src_name,
            "judge_model_as_recorded": "|".join(sorted(judge_models)),
            "judge_temperature_as_recorded": "|".join(str(t) for t in sorted(judge_temps, key=str)),
            "developer_named_in_saved_rubric": "|".join(sorted(rubric_devs)) or "(none found)",
            "rubric_read_from": "saved judge request",
            "expected_sample_ids": len(expected), "sample_ids_present": len(set(ids)),
            "missing_ids": len(missing), "duplicate_ids": len(dup),
            "unexpected_ids": len(unexpected),
            "verdicts_match_export": int(not mismatch),
            "responses_identical_to_canonical": int(not drift),
            "response_content_sha256": sha("".join(
                s.output.completion for s in sorted(log.samples, key=lambda x: x.id))),
            "invalid_or_missing_scores": len(bad_score),
            "log_status": log.status,
        })
        if not judge_ok:
            failures.append(f"{name}: judge recorded as {sorted(judge_models)}, expected {EXPECT_JUDGE[judge_tag]}")
        if not rubric_ok:
            failures.append(f"{name}: rubric names {sorted(rubric_devs) or 'nothing'}, expected {EXPECT_DEV[model]}")
        if drift:
            failures.append(f"{name}: {len(drift)} responses differ from canonical")
        if missing or dup or unexpected:
            failures.append(f"{name}: ids missing={len(missing)} dup={len(dup)} unexpected={len(unexpected)}")
        if mismatch:
            failures.append(f"{name}: {len(mismatch)} verdicts differ from the export")
        if bad_score:
            failures.append(f"{name}: {len(bad_score)} missing/invalid scores")
        if log.status != "success":
            failures.append(f"{name}: status {log.status}")

    def allok(k):
        return all(r[k] for r in rows)

    print("\ncheck                                          result")
    print(f"  A judge model as recorded in the log         {all(r['judge_model_as_recorded'] == EXPECT_JUDGE[r['judge_tag']] for r in rows)}")
    print(f"  A judge temperature as recorded              {sorted({r['judge_temperature_as_recorded'] for r in rows})}")
    print(f"  B developer named in the SAVED rubric        {all(r['developer_named_in_saved_rubric'] == EXPECT_DEV[r['model']] for r in rows)}")
    print(f"  C responses identical to canonical           {allok('responses_identical_to_canonical')}")
    print(f"  D all expected sample ids, no dup/unexpected {all(r['missing_ids'] == 0 and r['duplicate_ids'] == 0 and r['unexpected_ids'] == 0 for r in rows)}")
    print(f"  D verdicts match the final export            {allok('verdicts_match_export')}")
    print(f"  E scores present and in the allowed set      {all(r['invalid_or_missing_scores'] == 0 for r in rows)}")
    print(f"  E log status success                         {all(r['log_status'] == 'success' for r in rows)}")
    print(f"  total judgments verified                     {sum(r['sample_ids_present'] for r in rows)}")

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {OUT} ({len(rows)} rows)")

    if failures:
        print("\nFAILURES:")
        for x in failures:
            print("  " + x)
        sys.exit(1)
    print("\nall provenance checks passed, read from the saved judge requests")


if __name__ == "__main__":
    main()
