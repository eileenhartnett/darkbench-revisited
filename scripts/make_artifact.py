"""Build the shareable web version of the writeup: data/results/artifact.html.

Usage (from project root): python3 make_artifact.py
Inputs: WRITEUP.md (from "# Part I" onward), artifact/head.html, artifact/tail.html,
data/results/rates.csv, data/results/judge_test_retest.csv, data/results/judge_agreement.csv,
data/results/rates.svg. The page renders the markdown client-side (marked.js) and draws three
charts from the JSON this script embeds: overall rate per model with Wilson 95% CIs (§3b),
judge self-consistency vs inter-judge kappa (§3), and the 2024→2026 anchor trajectories per
category (§4c). Publish the output with the Artifact tool; the same file path keeps the URL.
"""

import base64
import csv
import json
import math
import os
import re
import sys
from collections import defaultdict

# Scripts live in scripts/; every data path below is relative to the repository root.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from make_chart import CAT_TITLE, JUDGES, LABEL  # noqa: E402

RES = os.path.join(ROOT, "data", "results")
OUT = os.path.join(RES, "artifact.html")
ANCHORS = ["gpt-3.5-turbo-0125", "gpt-4-turbo-2024-04-09", "gpt-4o-2024-08-06"]
ANCHOR_LABEL = {"gpt-3.5-turbo-0125": "gpt-3.5-turbo (Jan 2024)",
                "gpt-4-turbo-2024-04-09": "gpt-4-turbo (Apr 2024)",
                "gpt-4o-2024-08-06": "gpt-4o (Aug 2024)"}
# Kran et al. (2025) Figure 4, "Average" column (mean over the paper's three annotators and six
# categories), transcribed from the arXiv 2503.10728 PDF on 2026-09-22. Percent. Paper snapshots
# (Table 5): gpt-3.5-turbo-0125, gpt-4-turbo-2024-04-09, gpt-4o-2024-05-13 — the first two are the
# exact IDs I ran; my gpt-4o is the 2024-08-06 snapshot.
PAPER_FIG4 = [
    ("Claude 3 Haiku", 36), ("Claude 3 Sonnet", 32), ("Claude 3 Opus", 33), ("Claude 3.5 Sonnet", 30),
    ("Gemini 1.0 Pro", 56), ("Gemini 1.5 Flash", 53), ("Gemini 1.5 Pro", 48),
    ("GPT-3.5 Turbo", 61), ("GPT-4", 49), ("GPT-4 Turbo", 48), ("GPT-4o", 55),
    ("Llama 3 70B", 61), ("Mistral 7B", 59), ("Mixtral 8x7B", 56),
]
# Verified against the PDF on 2026-09-27: Figure 4 is cell-for-cell identical to the GPT-4o
# panel of Figure 5 ("Top = Claude-3.5-Sonnet, middle = Gemini-1.5-Pro, bottom = GPT-4o"), so
# 48% is that one annotator's average, NOT a mean over the paper's three annotators. The other
# two panels average 32% (Claude 3.5 Sonnet) and 43% (Gemini 1.5 Pro).
PAPER_AVG = 48
PAPER_PANEL_AVGS = {"Claude 3.5 Sonnet": 32, "Gemini 1.5 Pro": 43, "GPT-4o": 48}
PAPER_TO_ANCHOR = {"GPT-3.5 Turbo": "gpt-3.5-turbo-0125", "GPT-4 Turbo": "gpt-4-turbo-2024-04-09", "GPT-4o": "gpt-4o-2024-08-06"}
JUDGE_LABEL = {jid: name for jid, name, _ in JUDGES}
JUDGE_COLOR = {jid: col for jid, _, col in JUDGES}

# The page renders METHODS_PAPER.md. Its front matter (title, abstract, takeaway) is hand-built in
# head.html, so the rendered body starts at the case study. Image references to the exported chart
# PNGs are swapped for the live SVG charts drawn in tail.html.
SOURCE_MD = os.path.join("docs", "METHODS_PAPER.md")
BODY_START = "## Why re-run an older benchmark?"
CHART_IMAGES = {"hero.png": "hero", "ci.png": "ci", "anchors.png": "anchors", "kappa.png": "kappa"}


def wilson(k, n, z=1.96):
    """Wilson 95% interval for k successes in n trials, as percentages."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * (c - h), 100 * (c + h))


def point(k, n):
    lo, hi = wilson(k, n)
    return {"rate": round(100 * k / n, 1), "lo": round(lo, 1), "hi": round(hi, 1), "n": n}


def read_csv(name):
    with open(os.path.join(RES, name)) as f:
        return list(csv.DictReader(f))


def chart_data():
    rates = read_csv("rates.csv")
    judges = [jid for jid, _, _ in JUDGES]
    # (model, judge) -> summed counts over categories; (model, judge, cat) -> counts
    tot = defaultdict(lambda: [0, 0])
    cell = {}
    # Categories that have to be dropped from the *overall* total for every model, so the
    # averages compare like with like instead of mixing models scored on different category
    # sets. This is empty whenever nothing is quarantined, which is the case since the
    # brand-bias cells were re-scored on 2026-09-27 (A.14).
    drop_from_overall = {r["category"] for r in rates if r["excluded"] == "1"}
    if drop_from_overall:
        print(f"  note: dropping {sorted(drop_from_overall)} from overall totals "
              f"(quarantined cells present)")
    for r in rates:
        if r["judge"] not in judges:
            continue
        k, n = int(r["n_flagged"]), int(r["n_valid"])
        # A quarantined cell never enters an aggregate or a plotted point.
        if r["excluded"] != "1":
            cell[(r["model"], r["judge"], r["category"])] = (k, n)
        if r["excluded"] == "1" or r["category"] in drop_from_overall:
            continue
        tot[(r["model"], r["judge"])][0] += k
        tot[(r["model"], r["judge"])][1] += n
    models = sorted({m for m, _ in tot})
    current = [m for m in models if m not in ANCHORS]
    assert set(current) == set(LABEL), f"model list differs from make_chart.LABEL: {sorted(set(current) ^ set(LABEL))}"

    # --- chart 1: overall rate per model with CI, per judge
    def mean_rate(m):
        return sum(tot[(m, j)][0] / tot[(m, j)][1] for j in judges) / len(judges)
    ci_rows = []
    for m in sorted(current, key=mean_rate) + ANCHORS:
        row = {"model": m, "label": LABEL.get(m, ANCHOR_LABEL.get(m, m)), "anchor": m in ANCHORS}
        for j in judges:
            k, n = tot[(m, j)]
            row[j] = point(k, n)
        ci_rows.append(row)

    # --- chart 2: self kappa (test-retest) vs inter-judge kappa
    retest = read_csv("judge_test_retest.csv")
    agree = read_csv("judge_agreement.csv")

    # The chart used to pair a two-model self-kappa against a nine-model pooled inter-kappa,
    # which are not comparable: kappa depends on the item mix. Both sides now come from
    # reliability_common_mask.csv, where each response set has ONE mask, the items every judge
    # scored validly in both passes, so a row's two dots share a denominator.
    mask = read_csv("reliability_common_mask.csv")
    sets = sorted({r["response_set"] for r in mask})

    def self_kappa(jid):
        ks = [float(r["kappa"]) for r in mask
              if r["comparison"].startswith("intra-judge") and r["judge_a"] == jid]
        assert ks, f"no intra-judge rows for {jid}"
        return round(sum(ks) / len(ks), 3)

    def inter_kappa(jid):
        ks = [float(r["kappa"]) for r in mask
              if r["comparison"] == "inter-judge (pass 1)"
              and jid in (r["judge_a"], r["judge_b"])]
        assert ks, f"no inter-judge rows for {jid}"
        return round(sum(ks) / len(ks), 3)

    kappa_rows = [{"id": j, "label": JUDGE_LABEL[j], "color": JUDGE_COLOR[j],
                   "self": self_kappa(j), "inter": inter_kappa(j)} for j in judges]
    # Majority-of-3 self-agreement is not in the common-mask table (it is a derived rule, not a
    # judge), so it keeps its test-retest value and has no inter-judge counterpart.
    maj = [float(r["kappa"]) for r in retest
           if r["judge"] == "majority-of-3" and r["scope"] == "ALL"]
    kappa_rows.append({"id": "majority-of-3", "label": "Majority of 3", "color": None,
                       "self": round(sum(maj) / len(maj), 3), "inter": None})
    inter_range = [min(float(r["kappa"]) for r in mask
                       if r["comparison"] == "inter-judge (pass 1)"),
                   max(float(r["kappa"]) for r in mask
                       if r["comparison"] == "inter-judge (pass 1)")]
    mask_ns = sorted({(r["response_set"], r["n"]) for r in mask})

    # --- chart 3: 2024 anchors -> current models, per category and judge
    gens = [{"id": m, "label": lab} for m, lab in
            [("gpt-3.5-turbo-0125", "Jan 2024"), ("gpt-4-turbo-2024-04-09", "Apr 2024"),
             ("gpt-4o-2024-08-06", "Aug 2024"), ("current", "2026")]]
    cats = []
    for c in CAT_TITLE:
        series = {}
        for j in judges:
            pts = []
            for g in gens:
                if g["id"] == "current":
                    # Quarantined cells are absent from `cell`, so the pooled 2026 brand-bias
                    # point covers only the models with a usable verdict (A.14).
                    have = [m for m in current if (m, j, c) in cell]
                    k = sum(cell[(m, j, c)][0] for m in have)
                    n = sum(cell[(m, j, c)][1] for m in have)
                else:
                    k, n = cell[(g["id"], j, c)]
                # The pooled 2026 point is nine models answering the same 110 prompts, so a
                # binomial interval on ~990 would treat clustered responses as independent.
                # Plot the rate without a whisker; the cluster-aware contrasts are in
                # anchor_contrasts.csv and S12 (re-audit 2026-09-27, finding 3).
                pt = point(k, n)
                if g["id"] == "current":
                    pt = {**pt, "lo": None, "hi": None}
                pts.append(pt)
            series[j] = pts
        cats.append({"id": c, "title": CAT_TITLE[c], "series": series})

    # --- hero: every model's average rate — the paper's 14 (its judges) and my 12 (my judges)
    def three_judge_mean(m):
        return round(100 * mean_rate(m), 1)
    maj_tot = defaultdict(lambda: [0, 0])
    for r in read_csv("majority_rates.csv"):
        if r.get("excluded") == "1" or r["category"] in drop_from_overall:
            continue
        maj_tot[r["model"]][0] += int(r["n_flagged_majority"])
        maj_tot[r["model"]][1] += int(r["n_valid"])

    def majority(m):
        k, n = maj_tot[m]
        return round(100 * k / n, 1)
    with open(os.path.join(RES, "paper_figure4.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["model", "average_pct", "source"])
        for name, v in PAPER_FIG4:
            w.writerow([name, v, "Kran et al. 2025, Figure 4 = the GPT-4o annotator panel of Figure 5, Average column"])
    # HERO_STAT: "mean" = three-judge mean; "majority" = majority-of-3 vote (the reporting rule
    # §5 recommends). Note this is NOT the same statistic as the paper's Figure 4 average, which
    # comes from a single annotator (GPT-4o); the panels are labelled accordingly in the chart.
    HERO_STAT = "mean"
    stat = three_judge_mean if HERO_STAT == "mean" else majority
    hero = {
        "stat": HERO_STAT,
        "paper": [{"label": n, "paper": v,
                   "mine": stat(PAPER_TO_ANCHOR[n]) if n in PAPER_TO_ANCHOR else None,
                   "mean": three_judge_mean(PAPER_TO_ANCHOR[n]) if n in PAPER_TO_ANCHOR else None,
                   "majority": majority(PAPER_TO_ANCHOR[n]) if n in PAPER_TO_ANCHOR else None}
                  for n, v in PAPER_FIG4],
        "current": [{"label": LABEL[m], "mine": stat(m), "mean": three_judge_mean(m), "majority": majority(m)}
                    for m in sorted(current, key=stat)],
        "paper_avg": PAPER_AVG,
        "my_avg": round(sum(stat(m) for m in current) / len(current), 1),
    }

    return {
        "judges": [{"id": jid, "label": name, "color": col} for jid, name, col in JUDGES],
        "hero": hero,
        "ci": ci_rows,
        "kappa": kappa_rows,
        "inter_range": [round(x, 3) for x in inter_range],
        "anchors": {"gens": gens, "cats": cats, "n_current": len(current)},
    }


def body_markdown():
    with open(os.path.join(ROOT, SOURCE_MD)) as f:
        lines = f.read().split("\n")
    start = next(i for i, l in enumerate(lines) if l.startswith(BODY_START))
    lines = lines[start:]
    found = {k: 0 for k in CHART_IMAGES.values()}
    out = []
    for line in lines:
        m = re.match(r"!\[.*\]\(\.\./data/results/figures/([a-z]+\.png)\)\s*$", line)
        if m and m.group(1) in CHART_IMAGES:
            key = CHART_IMAGES[m.group(1)]
            out.extend(["", f'<div data-chart="{key}"></div>', ""])
            found[key] += 1
        else:
            out.append(line)
    missing = [k for k, n in found.items() if n != 1]
    assert not missing, f"chart image references not found exactly once in {SOURCE_MD}: {missing} ({found})"
    md = "\n".join(out)
    assert "</script" not in md, "markdown body contains '</script', which would break the embed"
    return md


def main():
    with open(os.path.join(ROOT, "artifact", "head.html")) as f:
        head = f.read()
    with open(os.path.join(ROOT, "artifact", "tail.html")) as f:
        tail = f.read()
    with open(os.path.join(RES, "rates.svg"), "rb") as f:
        svg_b64 = base64.b64encode(f.read()).decode("ascii")
    data = chart_data()
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    md = body_markdown()

    html = (head
            + '\n<script type="text/markdown" id="content-md">\n' + md + '\n</script>\n'
            + '\n<script type="text/plain" id="chart-svg-b64">' + svg_b64 + '</script>\n'
            + '\n<script type="application/json" id="chart-data">' + data_json + '</script>\n'
            + tail)
    with open(OUT, "w") as f:
        f.write(html)
    n_pts = sum(len(s) for c in data["anchors"]["cats"] for s in c["series"].values())
    print(f"wrote {OUT} ({len(html) / 1024:.0f} KB): {len(data['ci'])} CI rows, "
          f"{len(data['kappa'])} kappa rows, {n_pts} anchor points")
    a = next(r for r in data["ci"] if r["model"] == "gpt-6-astra")["gpt55"]
    print(f"  spot-check gpt-6-astra under gpt-5.5: {a['rate']} [{a['lo']}, {a['hi']}]")
    print(f"  spot-check Opus 4.6 self kappa: {next(r for r in data['kappa'] if r['id'] == 'opus46')['self']}")
    s = next(c for c in data["anchors"]["cats"] if c["id"] == "sycophancy")["series"]["opus46"][0]
    print(f"  spot-check gpt-3.5-turbo sycophancy under Opus: {s['rate']} [{s['lo']}, {s['hi']}]")


if __name__ == "__main__":
    main()
