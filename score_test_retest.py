"""Judge test–retest: how often does each judge agree with itself on identical responses?

Usage (from project root): python3 score_test_retest.py
Looks for pairs <log>-scored-<judge>.eval and <log>-scored-<judge>-retest.eval in
data/raw/inspect-logs/, writes data/results/judge_test_retest.csv, prints per-judge and
per-category self-agreement and Cohen's kappa. When all three judges have both passes for a
log, also scores the ensemble rules (majority-of-3, any-of-3, all-of-3): the vote over the three
first-pass files vs the vote over the three retest files. Never touches data/raw/ contents.
"""

import csv
import glob
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze import LOG_DIR, is_flagged, is_invalid, short_model  # noqa: E402
from inspect_ai.log import read_eval_log  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "results", "judge_test_retest.csv")
CATS = ["anthropomorphization", "brand-bias", "harmful-generation", "sneaking", "sycophancy", "user-retention"]


def kappa(a, b):
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def verdicts(path):
    log = read_eval_log(path)
    return short_model(log.eval.model), {s.id: (s.target, s.scores["overseer"].value) for s in log.samples if s.scores}


def main():
    rows = []
    for retest in sorted(glob.glob(os.path.join(LOG_DIR, "*-scored-*-retest.eval"))):
        first = retest.replace("-retest.eval", ".eval")
        if not os.path.exists(first):
            print("no first-pass file for", os.path.basename(retest))
            continue
        judge = retest.rsplit("-scored-", 1)[1].replace("-retest.eval", "")
        model, a = verdicts(first)
        _, b = verdicts(retest)
        common = [sid for sid in a if sid in b and not is_invalid(a[sid][1]) and not is_invalid(b[sid][1])]
        print(f"\n=== {judge} on {model}: {len(common)} responses scored twice ===")
        print(f"  {'scope':22}{'n':>5}{'same flag':>11}{'same value':>12}{'kappa':>8}{'rate 1st':>10}{'rate 2nd':>10}  flips 0->1 / 1->0")
        for scope in ["ALL"] + CATS:
            ids = [s for s in common if scope == "ALL" or a[s][0] == scope]
            if not ids:
                continue
            fa = [is_flagged(a[s][1]) for s in ids]
            fb = [is_flagged(b[s][1]) for s in ids]
            same_flag = sum(x == y for x, y in zip(fa, fb)) / len(ids)
            same_val = sum(str(a[s][1]) == str(b[s][1]) for s in ids) / len(ids)
            k = kappa(fa, fb)
            up = sum((not x) and y for x, y in zip(fa, fb))
            down = sum(x and (not y) for x, y in zip(fa, fb))
            rows.append(dict(judge=judge, model=model, scope=scope, n=len(ids), same_flag=round(same_flag, 4),
                             same_value=round(same_val, 4), kappa=round(k, 4), rate_first=round(sum(fa) / len(ids), 4),
                             rate_second=round(sum(fb) / len(ids), 4), flips_0_to_1=up, flips_1_to_0=down))
            print(f"  {scope:22}{len(ids):5}{100*same_flag:10.1f}%{100*same_val:11.1f}%{k:8.2f}{100*sum(fa)/len(ids):9.1f}%{100*sum(fb)/len(ids):9.1f}%   {up} / {down}")
    # --- ensemble rules: majority-of-3 and any-of-3, pass 1 vs pass 2, where all three judges have both passes
    by_log = defaultdict(dict)
    for retest in glob.glob(os.path.join(LOG_DIR, "*-scored-*-retest.eval")):
        first = retest.replace("-retest.eval", ".eval")
        if not os.path.exists(first):
            continue
        base = retest.rsplit("-scored-", 1)[0]
        judge = retest.rsplit("-scored-", 1)[1].replace("-retest.eval", "")
        by_log[base][judge] = (verdicts(first)[1], verdicts(retest)[1])
    for base, judges in by_log.items():
        if len(judges) < 3:
            print(f"\n(ensemble test–retest waits for all 3 judges; have {sorted(judges)})")
            continue
        model = short_model(read_eval_log(base + ".eval", header_only=True).eval.model)
        ids = [s for s in next(iter(judges.values()))[0]
               if all(s in p1 and s in p2 and not is_invalid(p1[s][1]) and not is_invalid(p2[s][1]) for p1, p2 in judges.values())]
        cat_of = {s: next(iter(judges.values()))[0][s][0] for s in ids}
        for rule_name, rule in [("majority-of-3", lambda v: sum(v) >= 2), ("any-of-3", any), ("all-of-3", all)]:
            print(f"\n=== {rule_name} on {model}: pass 1 vs pass 2, {len(ids)} responses ===")
            print(f"  {'scope':22}{'n':>5}{'same flag':>11}{'kappa':>8}{'rate 1st':>10}{'rate 2nd':>10}  flips 0->1 / 1->0")
            for scope in ["ALL"] + CATS:
                sub = [s for s in ids if scope == "ALL" or cat_of[s] == scope]
                if not sub:
                    continue
                fa = [rule([is_flagged(judges[j][0][s][1]) for j in judges]) for s in sub]
                fb = [rule([is_flagged(judges[j][1][s][1]) for j in judges]) for s in sub]
                same = sum(x == y for x, y in zip(fa, fb)) / len(sub)
                k = kappa(fa, fb)
                up = sum((not x) and y for x, y in zip(fa, fb)); down = sum(x and (not y) for x, y in zip(fa, fb))
                rows.append(dict(judge=rule_name, model=model, scope=scope, n=len(sub), same_flag=round(same, 4),
                                 same_value=float("nan"), kappa=round(k, 4), rate_first=round(sum(fa) / len(sub), 4),
                                 rate_second=round(sum(fb) / len(sub), 4), flips_0_to_1=up, flips_1_to_0=down))
                print(f"  {scope:22}{len(sub):5}{100*same:10.1f}%{k:8.2f}{100*sum(fa)/len(sub):9.1f}%{100*sum(fb)/len(sub):9.1f}%   {up} / {down}")

    if rows:
        with open(OUT, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
