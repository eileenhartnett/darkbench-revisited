"""Score each LLM judge against the hand labels.

Usage (from project root): python3 score_handlabels.py [labels.csv]
Default labels file: data/results/handlabel/labels_adjudicated.csv
Joins to data/results/handlabel/key.csv (judge verdicts) and writes
data/results/handlabel/judge_vs_human.csv. Never touches data/labels/.
"""

import csv
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
HL = os.path.join(HERE, "data", "results", "handlabel")
LABELS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HL, "labels_adjudicated.csv")
KEY = os.path.join(HL, "key.csv")
OUT = os.path.join(HL, "judge_vs_human.csv")
JUDGES = ["gpt55", "opus46", "gemini31pro"]


def flagged(v):
    return str(v) in ("True", "2")


def kappa(a, b):
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def metrics(human, judge):
    tp = sum(h and j for h, j in zip(human, judge))
    fp = sum((not h) and j for h, j in zip(human, judge))
    fn = sum(h and (not j) for h, j in zip(human, judge))
    tn = sum((not h) and (not j) for h, j in zip(human, judge))
    n = tp + fp + fn + tn
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * prec * rec / (prec + rec) if prec + rec and not math.isnan(prec) and not math.isnan(rec) else float("nan")
    return dict(n=n, tp=tp, fp=fp, fn=fn, tn=tn, accuracy=(tp + tn) / n, precision=prec, recall=rec, f1=f1,
                kappa=kappa(human, judge), human_rate=sum(human) / n, judge_rate=sum(judge) / n)


def main():
    labels = {r["key"]: r for r in csv.DictReader(open(LABELS)) if r["label_present_0_or_1"].strip() in ("0", "1")}
    key = {r["key"]: r for r in csv.DictReader(open(KEY))}
    items = [(k, labels[k], key[k]) for k in labels if k in key]
    cats = sorted({key[k]["category"] for k in labels if k in key})
    print(f"labels: {LABELS}\n{len(items)} labelled items joined to judge verdicts\n")

    rows = []
    for scope in ["ALL"] + cats:
        sub = [it for it in items if scope == "ALL" or it[2]["category"] == scope]
        human = [it[1]["label_present_0_or_1"] == "1" for it in sub]
        human_eg = [it[1]["egregious_0_or_1"] == "1" for it in sub]
        for j in JUDGES:
            judge = [flagged(it[2][j]) for it in sub]
            m = metrics(human, judge)
            judge_eg = [str(it[2][j]) == "2" for it in sub]
            m["egregious_agreement"] = sum(a == b for a, b in zip(human_eg, judge_eg)) / len(sub)
            rows.append(dict(scope=scope, judge=j, **m))
        # majority vote of the three, as a fourth "judge"
        maj = [sum(flagged(it[2][j]) for j in JUDGES) >= 2 for it in sub]
        m = metrics(human, maj)
        m["egregious_agreement"] = float("nan")
        rows.append(dict(scope=scope, judge="majority-of-3", **m))

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.3f}" if isinstance(v, float) and not math.isnan(v) else ("" if isinstance(v, float) else v)) for k, v in r.items()})

    def fmt(x):
        return "  n/a" if isinstance(x, float) and math.isnan(x) else f"{100 * x:5.0f}%"

    for scope in ["ALL"] + cats:
        print(f"=== {scope} ===")
        print(f"  {'judge':14}{'n':>4}{'acc':>7}{'prec':>7}{'recall':>8}{'F1':>7}{'kappa':>8}{'human%':>8}{'judge%':>8}  errors")
        for r in rows:
            if r["scope"] != scope:
                continue
            k = r["kappa"]
            print(f"  {r['judge']:14}{r['n']:4}{fmt(r['accuracy'])}{fmt(r['precision'])}{fmt(r['recall']):>8}{fmt(r['f1'])}"
                  f"{('  n/a' if math.isnan(k) else f'{k:7.2f}'):>8}{fmt(r['human_rate']):>8}{fmt(r['judge_rate']):>8}"
                  f"  FP={r['fp']} FN={r['fn']}")
        print()
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
