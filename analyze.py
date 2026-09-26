"""Build the results table from every scored DarkBench log.

Usage (from the DarkBench/ directory):
    .venv/bin/python ../analyze.py

Reads data/raw/inspect-logs/*-scored-<judge>.eval, writes data/results/rates.csv and
data/results/judge_agreement.csv (pairwise agreement + Cohen's kappa pooled over the current
models, 2024 anchors excluded), and prints a model x category table per judge plus pairwise
judge agreement. Never touches data/raw/.
"""

import csv
import glob
import itertools
import os
import re
from collections import defaultdict

from inspect_ai.log import read_eval_log

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(HERE, "data", "raw", "inspect-logs")
OUT_DIR = os.path.join(HERE, "data", "results")

CATEGORIES = [
    "anthropomorphization",
    "brand-bias",
    "harmful-generation",
    "sneaking",
    "sycophancy",
    "user-retention",
]

# the three surviving 2024 models run as era anchors (WRITEUP §4c); excluded from pooled judge stats
ANCHORS = {"gpt-3.5-turbo-0125", "gpt-4-turbo-2024-04-09", "gpt-4o-2024-08-06"}


def kappa(a, b):
    """Cohen's kappa for two equal-length lists of booleans."""
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def short_model(model: str) -> str:
    return model.split("/")[-1]


def load_verdicts():
    """Return {(model, judge): {sample_id: (category, value)}} over all scored logs."""
    verdicts = {}
    for path in sorted(glob.glob(os.path.join(LOG_DIR, "*-scored-*.eval"))):
        m = re.search(r"-scored-([a-z0-9]+)\.eval$", path)
        if not m:
            continue
        judge = m.group(1)
        log = read_eval_log(path)
        model = short_model(log.eval.model)
        if len(log.samples) != 660:
            print(f"skipping {os.path.basename(path)}: {len(log.samples)} samples, not a full run")
            continue
        per_sample = {}
        for s in log.samples:
            score = (s.scores or {}).get("overseer")
            if score is None:
                continue
            per_sample[s.id] = (s.target, score.value)
        verdicts[(model, judge)] = per_sample
    return verdicts


def is_flagged(value) -> bool:
    return value is True or value == 2


def is_egregious(value) -> bool:
    return value == 2


def is_invalid(value) -> bool:
    return value == -1


def build_rows(verdicts):
    rows = []
    for (model, judge), per_sample in sorted(verdicts.items()):
        for cat in CATEGORIES:
            vals = [v for (c, v) in per_sample.values() if c == cat]
            n_invalid = sum(is_invalid(v) for v in vals)
            n_valid = len(vals) - n_invalid
            n_flagged = sum(is_flagged(v) for v in vals)
            n_egregious = sum(is_egregious(v) for v in vals)
            rows.append(
                {
                    "model": model,
                    "judge": judge,
                    "category": cat,
                    "n": len(vals),
                    "n_invalid": n_invalid,
                    "n_valid": n_valid,
                    "n_flagged": n_flagged,
                    "n_egregious": n_egregious,
                    "rate": round(n_flagged / n_valid, 4) if n_valid else "",
                    "egregious_rate": round(n_egregious / n_valid, 4) if n_valid else "",
                }
            )
    return rows


def print_tables(rows):
    judges = sorted({r["judge"] for r in rows})
    models = sorted({r["model"] for r in rows})
    for judge in judges:
        print(f"\n=== judge: {judge} === (flagged rate, -1 excluded; [n invalid] where nonzero)")
        header = f"{'model':28}" + "".join(f"{c[:14]:>16}" for c in CATEGORIES) + f"{'overall':>10}"
        print(header)
        for model in models:
            cells = []
            tot_flag = tot_valid = 0
            for cat in CATEGORIES:
                r = next((x for x in rows if x["model"] == model and x["judge"] == judge and x["category"] == cat), None)
                if r is None or r["n"] == 0:
                    cells.append(f"{'-':>16}")
                    continue
                tot_flag += r["n_flagged"]
                tot_valid += r["n_valid"]
                cell = f"{100 * r['rate']:.1f}%"
                if r["n_invalid"]:
                    cell += f" [{r['n_invalid']}]"
                cells.append(f"{cell:>16}")
            overall = f"{100 * tot_flag / tot_valid:.1f}%" if tot_valid else "-"
            print(f"{model:28}" + "".join(cells) + f"{overall:>10}")


def print_agreement(verdicts):
    print("\n=== pairwise judge agreement on flagged / not flagged (samples both judges scored validly) ===")
    by_model = defaultdict(dict)
    for (model, judge), per_sample in verdicts.items():
        by_model[model][judge] = per_sample
    for model, judges in sorted(by_model.items()):
        for j1, j2 in itertools.combinations(sorted(judges), 2):
            a, b = judges[j1], judges[j2]
            agree = total = both_flag = 0
            for sid in a.keys() & b.keys():
                va, vb = a[sid][1], b[sid][1]
                if is_invalid(va) or is_invalid(vb):
                    continue
                total += 1
                fa, fb = is_flagged(va), is_flagged(vb)
                agree += fa == fb
                both_flag += fa and fb
            if total:
                print(f"  {model:28} {j1:12} vs {j2:12}: {100 * agree / total:.1f}% agree (n={total}, both flagged {both_flag})")


def majority_rates(verdicts):
    """Per model x category: responses flagged by at least two of the three judges (all models)."""
    by_model = defaultdict(dict)
    for (model, judge), per_sample in verdicts.items():
        by_model[model][judge] = per_sample
    rows = []
    for model, js in sorted(by_model.items()):
        if len(js) != 3:
            continue
        judges = sorted(js)
        for cat in CATEGORIES:
            n = k = 0
            for sid in set.intersection(*(set(js[j]) for j in judges)):
                if js[judges[0]][sid][0] != cat:
                    continue
                vals = [js[j][sid][1] for j in judges]
                if any(is_invalid(v) for v in vals):
                    continue
                n += 1
                k += sum(is_flagged(v) for v in vals) >= 2
            rows.append({"model": model, "category": cat, "n_valid": n, "n_flagged_majority": k,
                         "rate_majority": round(k / n, 4) if n else ""})
    return rows


def pooled_agreement(verdicts):
    """Pairwise agreement and kappa over all current-model responses every judge scored validly."""
    by_model = defaultdict(dict)
    for (model, judge), per_sample in verdicts.items():
        if model not in ANCHORS:
            by_model[model][judge] = per_sample
    judges = sorted({j for js in by_model.values() for j in js})
    flags = {j: [] for j in judges}
    for model, js in by_model.items():
        if set(js) != set(judges):
            continue
        for sid in set.intersection(*(set(js[j]) for j in judges)):
            vals = [js[j][sid][1] for j in judges]
            if any(is_invalid(v) for v in vals):
                continue
            for j, v in zip(judges, vals):
                flags[j].append(is_flagged(v))
    rows = []
    for j1, j2 in itertools.combinations(judges, 2):
        a, b = flags[j1], flags[j2]
        rows.append({"judge_a": j1, "judge_b": j2, "n": len(a),
                     "agreement": round(sum(x == y for x, y in zip(a, b)) / len(a), 4),
                     "kappa": round(kappa(a, b), 4)})
    return rows


def main():
    verdicts = load_verdicts()
    if not verdicts:
        print("no scored logs found")
        return
    rows = build_rows(verdicts)
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "rates.csv")
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print_tables(rows)
    print_agreement(verdicts)
    print(f"\nwrote {out} ({len(rows)} rows from {len(verdicts)} model/judge logs)")
    agree = pooled_agreement(verdicts)
    out2 = os.path.join(OUT_DIR, "judge_agreement.csv")
    with open(out2, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(agree[0].keys()))
        writer.writeheader()
        writer.writerows(agree)
    print(f"wrote {out2} (pooled over current models, anchors excluded):")
    for r in agree:
        print(f"  {r['judge_a']:12} vs {r['judge_b']:12}: {100 * r['agreement']:.1f}% agree, κ {r['kappa']:.2f} (n={r['n']})")
    maj = majority_rates(verdicts)
    out3 = os.path.join(OUT_DIR, "majority_rates.csv")
    with open(out3, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(maj[0].keys()))
        writer.writeheader()
        writer.writerows(maj)
    print(f"wrote {out3} ({len(maj)} rows: majority-of-3 flag rate per model x category)")


if __name__ == "__main__":
    main()
