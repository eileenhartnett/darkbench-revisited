"""Render data/results/rates.svg from data/results/rates.csv.

Small multiples: one panel per dark-pattern category, one row per model,
one dot per judge. Run: python3 make_chart.py
"""

import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "data", "results", "rates.csv")
OUT = os.path.join(HERE, "data", "results", "rates.svg")

JUDGES = [("gpt55", "GPT-5.5", "#2a78d6"), ("opus46", "Claude Opus 4.6", "#eb6834"), ("gemini31pro", "Gemini 3.1 Pro", "#1baf7a")]
LABEL = {
    "claude-sonnet-5": "Claude Sonnet 5",
    "claude-opus-5": "Claude Opus 5",
    "gpt-5.4-mini-2026-03-17": "GPT-5.4-mini",
    "gpt-5.5-2026-04-23": "GPT-5.5",
    "gpt-6-astra": "GPT-6 Astra",
    "gemini-3.8-flash": "Gemini 3.8 Flash",
    "gemini-3.1-pro-preview": "Gemini 3.1 Pro",
    "kimi-k3": "Kimi K3",
    "glm-5p3": "GLM 5.3",
}
CAT_TITLE = {
    "user-retention": "User retention",
    "anthropomorphization": "Anthropomorphization",
    "brand-bias": "Brand bias",
    "sneaking": "Sneaking",
    "harmful-generation": "Harmful generation",
    "sycophancy": "Sycophancy",
}

SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"

PAD_L, PAD_T = 22, 0
LABEL_W, PLOT_W, ROW_H = 118, 208, 21
PANEL_GAP_X, PANEL_GAP_Y = 34, 46
HEAD_H, PANEL_TITLE_H, AXIS_H = 84, 22, 26


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;")


def main():
    rows = list(csv.DictReader(open(CSV)))
    rate = {(r["model"], r["judge"], r["category"]): float(r["rate"]) * 100 for r in rows if r["rate"]}

    models = sorted(LABEL, key=lambda m: sum(rate[(m, j, c)] for j, _, _ in JUDGES for c in CAT_TITLE) / 18)
    cats = sorted(CAT_TITLE, key=lambda c: -sum(rate[(m, j, c)] for m in models for j, _, _ in JUDGES))

    n_rows = len(models)
    panel_h = PANEL_TITLE_H + n_rows * ROW_H + AXIS_H
    width = PAD_L + LABEL_W + 3 * PLOT_W + 2 * PANEL_GAP_X + 22
    height = HEAD_H + 2 * panel_h + PANEL_GAP_Y + 40

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="{FONT}">']
    s.append(f'<rect width="{width}" height="{height}" fill="{SURFACE}"/>')

    s.append(f'<text x="{PAD_L}" y="30" font-size="16" font-weight="600" fill="{INK}">DarkBench flagged rate, by category, model and judge</text>')
    s.append(f'<text x="{PAD_L}" y="50" font-size="11.5" fill="{INK2}">660 prompts (110 per category), one response each. Every dot is one judge&#8217;s rate for that model; the grey bar spans the three judges&#8217; disagreement.</text>')

    lx = PAD_L
    for jid, jname, col in JUDGES:
        s.append(f'<circle cx="{lx + 5}" cy="68" r="4.5" fill="{col}" stroke="{SURFACE}" stroke-width="2"/>')
        s.append(f'<text x="{lx + 15}" y="72" font-size="11.5" fill="{INK2}">{esc(jname)} judge</text>')
        lx += 22 + len(jname) * 6.4 + 34

    for idx, cat in enumerate(cats):
        col_i, row_i = idx % 3, idx // 3
        px = PAD_L + LABEL_W + col_i * (PLOT_W + PANEL_GAP_X)
        py = HEAD_H + row_i * (panel_h + PANEL_GAP_Y)

        s.append(f'<text x="{px}" y="{py + 13}" font-size="12.5" font-weight="600" fill="{INK}">{CAT_TITLE[cat]}</text>')

        top = py + PANEL_TITLE_H
        bot = top + n_rows * ROW_H
        for t in (0, 25, 50, 75, 100):
            gx = px + PLOT_W * t / 100
            s.append(f'<line x1="{gx:.1f}" y1="{top}" x2="{gx:.1f}" y2="{bot}" stroke="{GRID if t else AXIS}" stroke-width="1"/>')
            s.append(f'<text x="{gx:.1f}" y="{bot + 16}" font-size="10" fill="{MUTED}" text-anchor="middle" font-variant-numeric="tabular-nums">{t}%</text>')

        for mi, m in enumerate(models):
            cy = top + mi * ROW_H + ROW_H / 2
            if col_i == 0:
                s.append(f'<text x="{px - 10}" y="{cy + 3.8}" font-size="11" fill="{INK2}" text-anchor="end">{esc(LABEL[m])}</text>')
            vals = [rate[(m, j, cat)] for j, _, _ in JUDGES]
            lo, hi = min(vals), max(vals)
            if hi - lo > 0.6:
                s.append(f'<line x1="{px + PLOT_W * lo / 100:.1f}" y1="{cy:.1f}" x2="{px + PLOT_W * hi / 100:.1f}" y2="{cy:.1f}" stroke="{AXIS}" stroke-width="2.5" stroke-linecap="round"/>')
            for (jid, _, colr), v in sorted(zip(JUDGES, vals), key=lambda z: -z[1]):
                s.append(f'<circle cx="{px + PLOT_W * v / 100:.1f}" cy="{cy:.1f}" r="4.5" fill="{colr}" stroke="{SURFACE}" stroke-width="2"/>')

    s.append(f'<text x="{PAD_L}" y="{height - 14}" font-size="10.5" fill="{MUTED}">Models ordered by three-judge mean flag rate (lowest first). Rates exclude unscoreable (&#8722;1) verdicts. Full values in the tables above.</text>')
    s.append("</svg>")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write("\n".join(s))
    print(f"wrote {OUT} ({width}x{height})")


if __name__ == "__main__":
    main()
