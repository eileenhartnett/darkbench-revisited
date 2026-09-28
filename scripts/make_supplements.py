"""Regenerate the numerical supplement tables in docs/METHODS_PAPER.md from the CSVs.

Usage (from project root, no API calls):
    python3 scripts/make_supplements.py            # rewrite the tables in place
    python3 scripts/make_supplements.py --check    # fail if any table is stale

Why this exists (re-audit 2026-09-27, finding 1).

S1 to S5 and S7 were maintained by hand. When the contaminated brand-bias cells were re-scored,
the case-study table was updated and the supplements were not, so the report carried superseded
Kimi and GLM values, presented as current results, alongside the corrected ones. Hand-maintained
duplicates of generated numbers drift; the fix is to stop maintaining them by hand.

Each generated table sits between a matched pair of HTML comments:

    <!-- GENERATED:S1 -->
    ...table...
    <!-- /GENERATED:S1 -->

Everything outside those markers, including all prose and the hand-written supplements, is left
exactly as written. `--check` is the guard: it regenerates into memory and reports any table
whose content no longer matches the data, so a stale supplement fails loudly instead of being
published.
"""

import argparse
import csv
import math
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "data", "results")
PAPER = os.path.join(ROOT, "docs", "METHODS_PAPER.md")

JUDGES = [("gpt55", "GPT-5.5"), ("opus46", "Opus 4.6"), ("gemini31pro", "Gemini Pro")]
CATS = ["anthropomorphization", "brand-bias", "harmful-generation",
        "sneaking", "sycophancy", "user-retention"]
ANCHORS = ["gpt-3.5-turbo-0125", "gpt-4-turbo-2024-04-09", "gpt-4o-2024-08-06"]
LABEL = {
    "gpt-6-astra": "GPT-6 Astra", "claude-sonnet-5": "Claude Sonnet 5",
    "kimi-k3": "Kimi K3", "gemini-3.8-flash": "Gemini 3.8 Flash",
    "claude-opus-5": "Claude Opus 5", "glm-5p3": "GLM 5.3",
    "gpt-5.5-2026-04-23": "GPT-5.5", "gpt-5.4-mini-2026-03-17": "GPT-5.4-mini",
    "gemini-3.1-pro-preview": "Gemini 3.1 Pro",
    "gpt-3.5-turbo-0125": "*gpt-3.5-turbo (2024)*",
    "gpt-4-turbo-2024-04-09": "*gpt-4-turbo (2024)*",
    "gpt-4o-2024-08-06": "*gpt-4o (2024)*",
}


def wilson(k, n, z=1.959963985):
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * p, 100 * max(0.0, c - h), 100 * min(1.0, c + h)


def kappa(a, b):
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def load():
    rates = [r for r in csv.DictReader(open(os.path.join(RES, "rates.csv")))]
    verdicts = [r for r in csv.DictReader(open(os.path.join(RES, "verdicts.csv")))]
    return rates, verdicts


def cell(rates, m, j, c):
    r = [x for x in rates if x["model"] == m and x["judge"] == j and x["category"] == c]
    return r[0] if r else None


def overall(rates, m, j):
    sel = [x for x in rates if x["model"] == m and x["judge"] == j and x["excluded"] != "1"]
    k = sum(int(x["n_flagged"]) for x in sel)
    n = sum(int(x["n_valid"]) for x in sel)
    return k, n


def ordered_models(rates):
    models = sorted({r["model"] for r in rates})
    current = [m for m in models if m not in ANCHORS]

    def mean3(m):
        return sum(overall(rates, m, j)[0] / overall(rates, m, j)[1] for j, _ in JUDGES) / 3
    return sorted(current, key=mean3), ANCHORS


def table_s1(rates, verdicts):
    cur, anch = ordered_models(rates)
    out = ["| model | " + " | ".join(["anthro.", "brand", "harmful", "sneaking",
                                      "sycoph.", "retention", "**avg**"]) + " |",
           "|---|---|---|---|---|---|---|---|"]
    for m in cur + anch:
        cells = []
        for c in CATS:
            vals = []
            for j, _ in JUDGES:
                r = cell(rates, m, j, c)
                vals.append(float("nan") if r is None or r["excluded"] == "1"
                            else 100 * int(r["n_flagged"]) / int(r["n_valid"]))
            cells.append("quarantined" if any(math.isnan(v) for v in vals)
                         else f"{sum(vals)/3:.0f}%")
        avg = sum(100 * overall(rates, m, j)[0] / overall(rates, m, j)[1] for j, _ in JUDGES) / 3
        out.append(f"| {LABEL.get(m, m)} | " + " | ".join(cells) + f" | **{avg:.0f}%** |")
    return "\n".join(out)


def table_perjudge(rates, judge):
    cur, anch = ordered_models(rates)
    out = ["| model | anthro. | brand | harmful | sneaking | sycoph. | retention | overall |",
           "|---|---|---|---|---|---|---|---|"]
    for m in cur + anch:
        cells = []
        for c in CATS:
            r = cell(rates, m, judge, c)
            if r is None:
                cells.append("-")
            elif r["excluded"] == "1":
                cells.append("quarantined")
            else:
                pct = 100 * int(r["n_flagged"]) / int(r["n_valid"])
                inv = int(r["n_invalid"])
                cells.append(f"{pct:.0f}%" + (f" ({inv})" if inv else ""))
        k, n = overall(rates, m, judge)
        out.append(f"| {LABEL.get(m, m)} | " + " | ".join(cells) + f" | **{100*k/n:.0f}%** |")
    return "\n".join(out)


def table_s5(rates):
    cur, anch = ordered_models(rates)
    out = ["| model | GPT-5.5 | Opus 4.6 | Gemini Pro |", "|---|---|---|---|"]
    for m in cur + anch:
        cells = []
        for j, _ in JUDGES:
            k, n = overall(rates, m, j)
            p, lo, hi = wilson(k, n)
            cells.append(f"{p:.1f} [{lo:.1f}, {hi:.1f}]")
        out.append(f"| {LABEL.get(m, m)} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def table_s7(verdicts):
    """Common-valid subset across all three judges, current models only."""
    by = defaultdict(dict)
    for v in verdicts:
        if v["model"] in ANCHORS or v["excluded"] == "1":
            continue
        by[(v["model"], v["sample_id"])][v["judge"]] = v
    common = [d for d in by.values()
              if len(d) == 3 and all(x["valid"] == "1" for x in d.values())]
    n = len(common)
    out = [f"Common-valid subset: **{n:,}** current-model responses that all three judges "
           "scored validly. These margins are computed on that subset, so they differ slightly "
           "from the per-judge headline rates, which use each judge's own full denominator.",
           "",
           "| | GPT-5.5 | Opus 4.6 | Gemini Pro |", "|---|---|---|---|"]
    rates_row = []
    for j, _ in JUDGES:
        k = sum(1 for d in common if d[j]["flagged"] == "1")
        rates_row.append(f"{100*k/n:.2f}%")
    out.append("| flag rate on the common subset | " + " | ".join(rates_row) + " |")
    out += ["", "| pair | agreement | Cohen's κ |", "|---|---|---|"]
    for i in range(3):
        for k2 in range(i + 1, 3):
            j1, j2 = JUDGES[i][0], JUDGES[k2][0]
            a = [d[j1]["flagged"] == "1" for d in common]
            b = [d[j2]["flagged"] == "1" for d in common]
            agr = sum(x == y for x, y in zip(a, b)) / n
            out.append(f"| {JUDGES[i][1]} vs {JUDGES[k2][1]} | {100*agr:.1f}% | {kappa(a,b):.2f} |")
    # Per-category flag rates AND agreement, on the same common subset, in one generated
    # table. An earlier version kept a second hand-written copy of these rates below the
    # generated block; it drifted after the brand-bias rescore and showed superseded values
    # (re-audit 2026-09-28). Generating both together removes that failure mode.
    out += ["", "| category | n | Gemini Pro | GPT-5.5 | Opus 4.6 | mean pairwise κ |",
            "|---|---|---|---|---|---|"]
    order = ["user-retention", "anthropomorphization", "brand-bias", "sneaking",
             "harmful-generation", "sycophancy"]
    for c in order:
        sub = [d for d in common if d[JUDGES[0][0]]["category"] == c]
        rates = {}
        for jid, _ in JUDGES:
            rates[jid] = 100 * sum(1 for d in sub if d[jid]["flagged"] == "1") / len(sub)
        ks = []
        for i in range(3):
            for k2 in range(i + 1, 3):
                a = [d[JUDGES[i][0]]["flagged"] == "1" for d in sub]
                b = [d[JUDGES[k2][0]]["flagged"] == "1" for d in sub]
                ks.append(kappa(a, b))
        out.append(f"| {c} | {len(sub)} | {rates['gemini31pro']:.0f}% | {rates['gpt55']:.0f}% "
                   f"| {rates['opus46']:.0f}% | {sum(ks)/3:.2f} |")
    lo = []
    for c in order:
        sub = [d for d in common if d[JUDGES[0][0]]["category"] == c]
        r = {jid: sum(1 for d in sub if d[jid]["flagged"] == "1") for jid, _ in JUDGES}
        lo.append(min(r, key=r.get))
    n_gem = sum(1 for x in lo if x == "gemini31pro")
    out += ["", f"Gemini Pro flags the fewest responses in {n_gem} of the six categories; "
                "GPT-5.5 flags fewest on user retention. Rates here use the common-valid "
                "subset, so they differ slightly from each judge's own-denominator rates in "
                "S2 to S4."]
    return "\n".join(out)


def build(rates, verdicts):
    return {
        "S1": table_s1(rates, verdicts),
        "S2": table_perjudge(rates, "gpt55"),
        "S3": table_perjudge(rates, "opus46"),
        "S4": table_perjudge(rates, "gemini31pro"),
        "S5": table_s5(rates),
        "S7": table_s7(verdicts),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="report stale tables and exit non-zero instead of rewriting")
    args = ap.parse_args()

    rates, verdicts = load()
    tables = build(rates, verdicts)
    text = open(PAPER).read()
    stale, written = [], []
    for key, body in tables.items():
        start, end = f"<!-- GENERATED:{key} -->", f"<!-- /GENERATED:{key} -->"
        if start not in text or end not in text:
            sys.exit(f"marker pair for {key} not found in {PAPER}; add {start} / {end}")
        i, jx = text.index(start) + len(start), text.index(end)
        current = text[i:jx].strip("\n")
        if current == body:
            continue
        stale.append(key)
        text = text[:i] + "\n" + body + "\n" + text[jx:]
        written.append(key)

    if args.check:
        if stale:
            print("STALE supplement tables: " + ", ".join(stale))
            sys.exit(1)
        print("all generated supplement tables match the data")
        return
    if written:
        open(PAPER, "w").write(text)
        print("regenerated: " + ", ".join(written))
    else:
        print("all generated supplement tables already match the data")


if __name__ == "__main__":
    main()
