"""Intra- and inter-judge agreement on one exactly common valid-item mask.

Usage (from project root, needs the raw logs and inspect_ai, no API calls):
    DarkBench/.venv/bin/python scripts/reliability_matched.py

Why this exists (re-audit 2026-09-27, finding 2).

The earlier matched comparison in `paired_analysis.py` used only first-pass verdicts. It
restricted inter-judge agreement to the two response sets that were re-scored, which was an
improvement on the nine-model pool, but it did not restrict either side to the items that are
valid in *both* passes for *all three* judges. So the inter-judge n and the three self-agreement
n values differed (657 against 660/657/659 on the Flash set, for instance), and describing them
as "exactly the same responses" was wrong.

This script fixes that. For each re-scored response set it builds one mask: the sample ids that
every judge scored validly in the first pass and again in the retest. Both kinds of agreement
are then computed on that single mask, so every number in a row shares one denominator.

It also exports the second-pass item-level verdicts, which existed only inside the raw logs
before, so another reviewer can reproduce this table from CSVs alone.

Writes:
  data/results/verdicts_pass2.csv          item-level retest verdicts
  data/results/reliability_common_mask.csv the matched comparison
"""

import csv
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(ROOT, "data", "raw", "inspect-logs")
OUT_DIR = os.path.join(ROOT, "data", "results")
JUDGES = ["gpt55", "opus46", "gemini31pro"]


def is_flagged(v):
    return v is True or v == 2


def is_invalid(v):
    return v == -1


def kappa(a, b):
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def load_pass2():
    """{(model, judge): {sample_id: (category, value)}} from the *-retest.eval logs."""
    from inspect_ai.log import read_eval_log
    out = {}
    for path in sorted(glob.glob(os.path.join(LOG_DIR, "*-scored-*-retest.eval"))):
        m = re.search(r"-scored-([a-z0-9]+)-retest\.eval$", path)
        if not m:
            continue
        judge = m.group(1)
        log = read_eval_log(path)
        model = log.eval.model.split("/")[-1]
        per = {}
        for s in log.samples:
            score = (s.scores or {}).get("overseer")
            if score is not None:
                per[s.id] = (s.target, score.value)
        out[(model, judge)] = per
        print(f"  pass 2: {model:24} {judge:12} {len(per)} verdicts  {os.path.basename(path)}")
    return out


def load_pass1(models):
    """First-pass verdicts for the same models, from the canonical scored logs."""
    from inspect_ai.log import read_eval_log
    out = {}
    for path in sorted(glob.glob(os.path.join(LOG_DIR, "*-scored-*.eval"))):
        m = re.search(r"-scored-([a-z0-9]+)\.eval$", path)   # excludes -retest, -batchtest
        if not m:
            continue
        judge = m.group(1)
        log = read_eval_log(path)
        model = log.eval.model.split("/")[-1]
        if model not in models or len(log.samples) != 660:
            continue
        per = {}
        for s in log.samples:
            score = (s.scores or {}).get("overseer")
            if score is not None:
                per[s.id] = (s.target, score.value)
        out[(model, judge)] = per
    return out


def main():
    print("loading retest logs")
    p2 = load_pass2()
    models = sorted({m for (m, _) in p2})
    print(f"re-scored response sets: {models}")
    p1 = load_pass1(set(models))

    # --- export pass-2 verdicts so this is reproducible without the raw archive
    out2 = os.path.join(OUT_DIR, "verdicts_pass2.csv")
    n = 0
    with open(out2, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sample_id", "model", "judge", "pass", "category", "raw_value",
                    "flagged", "valid"])
        for (model, judge), per in sorted(p2.items()):
            for sid, (cat, v) in sorted(per.items()):
                w.writerow([sid, model, judge, 2, cat, v,
                            int(is_flagged(v)), int(not is_invalid(v))])
                n += 1
    print(f"wrote {out2} ({n} second-pass verdicts)")

    rows = []
    print("\nOne common mask per response set: items every judge scored validly in BOTH passes.")
    for model in models:
        # the mask
        sids = None
        for j in JUDGES:
            for src in (p1, p2):
                per = src.get((model, j), {})
                ok = {sid for sid, (_, v) in per.items() if not is_invalid(v)}
                sids = ok if sids is None else (sids & ok)
        sids = sorted(sids)
        n_mask = len(sids)

        # how much each side loses relative to its own unrestricted n, for transparency
        print(f"\n  {model}   common mask n = {n_mask}")
        for j in JUDGES:
            a = [is_flagged(p1[(model, j)][s][1]) for s in sids]
            b = [is_flagged(p2[(model, j)][s][1]) for s in sids]
            agr = sum(x == y for x, y in zip(a, b)) / n_mask
            rows.append({"response_set": model, "comparison": "intra-judge (pass 1 vs pass 2)",
                         "judge_a": j, "judge_b": j, "n": n_mask,
                         "agreement": round(agr, 4), "kappa": round(kappa(a, b), 4),
                         "prevalence_a": round(sum(a) / n_mask, 4),
                         "prevalence_b": round(sum(b) / n_mask, 4)})
            print(f"    self  {j:12} agreement {100*agr:6.2f}%  κ {kappa(a,b):.4f}  "
                  f"flag rate {100*sum(a)/n_mask:5.2f}% then {100*sum(b)/n_mask:5.2f}%")
        for i in range(len(JUDGES)):
            for k in range(i + 1, len(JUDGES)):
                j1, j2 = JUDGES[i], JUDGES[k]
                for label, src in (("inter-judge (pass 1)", p1), ("inter-judge (pass 2)", p2)):
                    a = [is_flagged(src[(model, j1)][s][1]) for s in sids]
                    b = [is_flagged(src[(model, j2)][s][1]) for s in sids]
                    agr = sum(x == y for x, y in zip(a, b)) / n_mask
                    rows.append({"response_set": model, "comparison": label,
                                 "judge_a": j1, "judge_b": j2, "n": n_mask,
                                 "agreement": round(agr, 4), "kappa": round(kappa(a, b), 4),
                                 "prevalence_a": round(sum(a) / n_mask, 4),
                                 "prevalence_b": round(sum(b) / n_mask, 4)})
                a = [is_flagged(p1[(model, j1)][s][1]) for s in sids]
                b = [is_flagged(p1[(model, j2)][s][1]) for s in sids]
                print(f"    pair  {j1:12} vs {j2:12} agreement {100*sum(x==y for x,y in zip(a,b))/n_mask:6.2f}%"
                      f"  κ {kappa(a,b):.4f}  (pass 1)")

    out = os.path.join(OUT_DIR, "reliability_common_mask.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
