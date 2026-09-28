"""Paired, prompt-level contrasts and a matched intra/inter judge comparison.

Usage (from project root, no API calls, reads only saved outputs):
    python3 paired_analysis.py

Why this exists (CORRECTIONS.md, findings D and E).

1. The earlier analysis compared two models by asking whether their Wilson intervals
   overlapped. Interval overlap is not a test of a difference: two overlapping intervals can
   still correspond to a difference whose own interval excludes zero. It also threw away the
   pairing. Every model answers the *same* 110 prompts per category, so the right quantity is
   the difference on matched prompts, with uncertainty from resampling prompts.

   This script therefore reports, for each headline contrast, the paired difference in flag
   rate with a 95% bootstrap interval obtained by resampling prompt ids with replacement
   (10,000 draws, fixed seed). Resampling prompts rather than responses keeps each prompt's
   vector of model outcomes together, which is what the shared-prompt design requires.

   A difference whose interval excludes zero is evidence of a difference *on this prompt set
   under this judge*. It is not a claim about models in general, and an interval containing
   zero means the data do not settle the question, not that the models are equal.

2. Pooled inter-judge kappa was computed over nine models while self-agreement was measured on
   two. Kappa depends on the prevalence and item mix, so those two numbers were not comparable.
   This script recomputes inter-judge agreement restricted to exactly the response sets used
   for the retest, giving a matched comparison.

Writes data/results/paired_contrasts.csv and data/results/judge_agreement_matched.csv.
"""

import csv
import os
import random
from collections import defaultdict

# Scripts live in scripts/; every data path below is relative to the repository root.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "results")
VERDICTS = os.path.join(OUT_DIR, "verdicts.csv")

JUDGES = ["gpt55", "opus46", "gemini31pro"]
RETEST_MODELS = ["gemini-3.8-flash", "gpt-5.5-2026-04-23"]
N_BOOT = 10000
SEED = 20260927

# The contrasts the writeups actually make. Each is (label, model_a, model_b, category or None).
# None means all categories pooled, still paired at the prompt level.
CONTRASTS = [
    ("Opus 5 vs Sonnet 5, anthropomorphization",
     "claude-opus-5", "claude-sonnet-5", "anthropomorphization"),
    ("Gemini 3.1 Pro vs Sonnet 5, user retention",
     "gemini-3.1-pro-preview", "claude-sonnet-5", "user-retention"),
    ("GPT-6 Astra vs GPT-5.5, overall",
     "gpt-6-astra", "gpt-5.5-2026-04-23", None),
    ("gpt-3.5-turbo (2024) vs GPT-6 Astra, sneaking",
     "gpt-3.5-turbo-0125", "gpt-6-astra", "sneaking"),
    ("gpt-3.5-turbo (2024) vs GPT-5.5, sycophancy",
     "gpt-3.5-turbo-0125", "gpt-5.5-2026-04-23", "sycophancy"),
    ("gpt-3.5-turbo (2024) vs Gemini 3.1 Pro, sycophancy",
     "gpt-3.5-turbo-0125", "gemini-3.1-pro-preview", "sycophancy"),
    ("gpt-4-turbo (2024) vs GPT-5.5, user retention",
     "gpt-4-turbo-2024-04-09", "gpt-5.5-2026-04-23", "user-retention"),
    ("Sonnet 5 vs GPT-6 Astra, overall",
     "claude-sonnet-5", "gpt-6-astra", None),
]


def load():
    """{(model, judge): {sample_id: (category, flagged, valid, excluded)}}"""
    d = defaultdict(dict)
    for r in csv.DictReader(open(VERDICTS)):
        d[(r["model"], r["judge"])][r["sample_id"]] = (
            r["category"], r["flagged"] == "1", r["valid"] == "1", r["excluded"] == "1"
        )
    return d


def paired_diff(data, ma, mb, judge, category):
    """Return (ids, a_flags, b_flags) over prompts both models have valid, non-excluded."""
    A, B = data.get((ma, judge), {}), data.get((mb, judge), {})
    ids, fa, fb = [], [], []
    for sid in sorted(A.keys() & B.keys()):
        ca, flag_a, va, xa = A[sid]
        cb, flag_b, vb, xb = B[sid]
        if category is not None and ca != category:
            continue
        if xa or xb or not va or not vb:
            continue
        ids.append(sid)
        fa.append(flag_a)
        fb.append(flag_b)
    return ids, fa, fb


def bootstrap_ci(fa, fb, rng):
    """95% percentile interval for mean(a) - mean(b), resampling prompt indices."""
    n = len(fa)
    if n == 0:
        return float("nan"), float("nan")
    diffs = []
    for _ in range(N_BOOT):
        idx = [rng.randrange(n) for _ in range(n)]
        da = sum(fa[i] for i in idx) / n
        db = sum(fb[i] for i in idx) / n
        diffs.append(100 * (da - db))
    diffs.sort()
    return diffs[int(0.025 * N_BOOT)], diffs[int(0.975 * N_BOOT) - 1]


def discordant(fa, fb):
    """McNemar's discordant pairs: prompts where exactly one of the two was flagged."""
    b = sum(1 for x, y in zip(fa, fb) if x and not y)
    c = sum(1 for x, y in zip(fa, fb) if y and not x)
    return b, c


def kappa(a, b):
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def run_contrasts(data):
    rng = random.Random(SEED)
    rows = []
    print("Paired prompt-level contrasts, 95% bootstrap interval on the difference")
    print("(difference = first model minus second, in percentage points)\n")
    for label, ma, mb, cat in CONTRASTS:
        print(f"  {label}")
        for j in JUDGES:
            ids, fa, fb = paired_diff(data, ma, mb, j, cat)
            if not ids:
                print(f"      {j:12} no paired items")
                continue
            ra, rb = 100 * sum(fa) / len(fa), 100 * sum(fb) / len(fb)
            lo, hi = bootstrap_ci(fa, fb, rng)
            bb, cc = discordant(fa, fb)
            excl = "excludes 0" if (lo > 0 or hi < 0) else "includes 0"
            print(f"      {j:12} n={len(ids):4}  {ra:5.1f} vs {rb:5.1f}  "
                  f"diff {ra - rb:+6.1f} [{lo:+.1f}, {hi:+.1f}]  {excl:11} "
                  f"discordant {bb}/{cc}")
            rows.append({"contrast": label, "model_a": ma, "model_b": mb,
                         "category": cat or "ALL", "judge": j, "n_pairs": len(ids),
                         "rate_a": round(ra, 2), "rate_b": round(rb, 2),
                         "diff_pp": round(ra - rb, 2), "ci_lo": round(lo, 2),
                         "ci_hi": round(hi, 2), "excludes_zero": int(lo > 0 or hi < 0),
                         "discordant_a_only": bb, "discordant_b_only": cc})
        print()
    return rows


def run_matched_agreement(data):
    """Inter-judge agreement on exactly the response sets used for the retest."""
    print("Matched inter-judge agreement, restricted to the two retest response sets")
    print("(same items the self-agreement figures come from)\n")
    rows = []
    for model in RETEST_MODELS:
        per = {j: data.get((model, j), {}) for j in JUDGES}
        common = set.intersection(*(set(per[j]) for j in JUDGES))
        usable = [sid for sid in sorted(common)
                  if all(per[j][sid][2] and not per[j][sid][3] for j in JUDGES)]
        print(f"  {model}  (n={len(usable)})")
        for i in range(len(JUDGES)):
            for k in range(i + 1, len(JUDGES)):
                j1, j2 = JUDGES[i], JUDGES[k]
                a = [per[j1][s][1] for s in usable]
                b = [per[j2][s][1] for s in usable]
                agr = sum(x == y for x, y in zip(a, b)) / len(a)
                kp = kappa(a, b)
                print(f"      {j1:12} vs {j2:12}  agreement {100 * agr:5.2f}%   kappa {kp:.4f}")
                rows.append({"model": model, "judge_a": j1, "judge_b": j2,
                             "n": len(usable), "agreement": round(agr, 4),
                             "kappa": round(kp, 4)})
        print()
    return rows


ANCHORS = ["gpt-3.5-turbo-0125", "gpt-4-turbo-2024-04-09", "gpt-4o-2024-08-06"]
CATEGORIES = ["anthropomorphization", "brand-bias", "harmful-generation",
              "sneaking", "sycophancy", "user-retention"]
N_BOOT_CLUSTER = 30000


def cluster_bootstrap(data, judge, anchor, current, rng, per_category=None):
    """Anchor rate minus the equally weighted mean of the current models' rates.

    Estimand. For one judge: the anchor's flag rate minus the unweighted mean of the nine
    current models' flag rates, on this fixed prompt set. With `per_category` set, both sides
    are restricted to that category; otherwise both are overall rates across all six, which
    keeps the benchmark's 110-per-category composition fixed.

    Uncertainty. Prompt ids are resampled with replacement *within each category*, and the same
    resampled ids are used for every model, so each prompt's vector of model outcomes stays
    together. That respects the shared-prompt design and the fixed category composition.
    Invalid judgments (value -1) are dropped from both numerator and denominator wherever they
    occur, exactly as the saved rates do, so a resampled draw can have slightly different
    denominators per model.

    This is exploratory and conditional on these nine models, these saved responses, this judge
    and this prompt set. It is not an estimate for models in general or for deployment traffic.
    """
    cats = [per_category] if per_category else CATEGORIES
    ids_by_cat = {}
    for c in cats:
        ids = [sid for sid, (cat, _, valid, excl) in data[(anchor, judge)].items()
               if cat == c]
        ids_by_cat[c] = sorted(ids)

    def rate(model, picks):
        k = n = 0
        d = data[(model, judge)]
        for c in cats:
            for sid in picks[c]:
                rec = d.get(sid)
                if rec is None:
                    continue
                _, flag, valid, excl = rec
                if not valid or excl:
                    continue
                n += 1
                k += flag
        return 100 * k / n if n else float("nan")

    point_picks = ids_by_cat
    obs = rate(anchor, point_picks) - sum(rate(m, point_picks) for m in current) / len(current)

    diffs = []
    for _ in range(N_BOOT_CLUSTER):
        picks = {c: [ids_by_cat[c][rng.randrange(len(ids_by_cat[c]))]
                     for _ in range(len(ids_by_cat[c]))] for c in cats}
        d = rate(anchor, picks) - sum(rate(m, picks) for m in current) / len(current)
        diffs.append(d)
    diffs.sort()
    lo = diffs[int(0.025 * N_BOOT_CLUSTER)]
    hi = diffs[int(0.975 * N_BOOT_CLUSTER) - 1]
    return obs, lo, hi


def run_anchor_contrasts(data):
    """Each historical anchor against the equally weighted current-model mean, by judge."""
    rng = random.Random(SEED + 1)
    models = sorted({m for (m, _) in data})
    current = [m for m in models if m not in ANCHORS]
    rows = []
    print("Historical anchor minus the equally weighted mean of the "
          f"{len(current)} current models, percentage points")
    print("Prompt-cluster bootstrap, resampled within category, "
          f"{N_BOOT_CLUSTER} draws; exploratory and unadjusted\n")
    for anchor in ANCHORS:
        print(f"  {anchor}")
        for j in JUDGES:
            obs, lo, hi = cluster_bootstrap(data, j, anchor, current, rng)
            excl = "excludes 0" if (lo > 0 or hi < 0) else "includes 0"
            print(f"      {j:12} {obs:+6.1f} [{lo:+.1f}, {hi:+.1f}]  {excl}")
            rows.append({"anchor": anchor, "judge": j, "category": "ALL",
                         "diff_pp": round(obs, 2), "ci_lo": round(lo, 2),
                         "ci_hi": round(hi, 2), "excludes_zero": int(lo > 0 or hi < 0)})
        print()
    print("Oldest anchor minus the current pool, by category "
          "(same cluster bootstrap; a category where every current model scores zero")
    print("cannot produce positives under resampling, so its interval is not evidence "
          "of certain absence)\n")
    for c in CATEGORIES:
        line = []
        for j in JUDGES:
            obs, lo, hi = cluster_bootstrap(data, j, ANCHORS[0], current, rng, per_category=c)
            line.append(f"{obs:+5.1f} [{lo:+.1f}, {hi:+.1f}]")
            rows.append({"anchor": ANCHORS[0], "judge": j, "category": c,
                         "diff_pp": round(obs, 2), "ci_lo": round(lo, 2),
                         "ci_hi": round(hi, 2), "excludes_zero": int(lo > 0 or hi < 0)})
        print(f"  {c:22} " + "   ".join(line))
    print()
    return rows


def main():
    data = load()
    contrasts = run_contrasts(data)
    matched = run_matched_agreement(data)

    p1 = os.path.join(OUT_DIR, "paired_contrasts.csv")
    with open(p1, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(contrasts[0].keys()))
        w.writeheader()
        w.writerows(contrasts)
    print(f"wrote {p1} ({len(contrasts)} rows)")

    anchors = run_anchor_contrasts(data)
    p3 = os.path.join(OUT_DIR, "anchor_contrasts.csv")
    with open(p3, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(anchors[0].keys()))
        w.writeheader()
        w.writerows(anchors)
    print(f"wrote {p3} ({len(anchors)} rows)")

    p2 = os.path.join(OUT_DIR, "judge_agreement_matched.csv")
    with open(p2, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(matched[0].keys()))
        w.writeheader()
        w.writerows(matched)
    print(f"wrote {p2} ({len(matched)} rows)")


if __name__ == "__main__":
    main()
