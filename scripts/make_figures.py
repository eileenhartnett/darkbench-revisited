"""Re-export the four chart PNGs from the artifact's own chart code.

Usage (from project root, after make_artifact.py):
    python3 make_figures.py

NOTES 2026-09-23 records that data/results/figures/*.png were produced "via headless Chrome
from the artifact's own chart code". That step was never scripted, so when the charts changed
the PNGs went stale while SUBMISSION.md kept embedding them. This script makes it repeatable.

For each chart it builds a throwaway page containing the artifact's stylesheet, its chart data
and its chart JavaScript, and nothing else but one figure. It renders that page twice: once to
measure the figure's height, once at exactly that height so the PNG has no dead margin. Output
is 2x for legibility, matching the original exports.
"""

import base64
import json
import os
import re
import subprocess
import sys
import tempfile

# Scripts live in scripts/; every data path below is relative to the repository root.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "data", "results", "artifact.html")
OUT_DIR = os.path.join(ROOT, "data", "results", "figures")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CHARTS = ["hero", "ci", "kappa", "anchors"]
WIDTH = 900
SCALE = 2


def slice_artifact():
    """Return (styles, chart_data_script, chart_js) lifted from the built artifact."""
    html = open(ART).read()
    styles = "\n".join(m.group(0) for m in re.finditer(r"<style>.*?</style>", html, re.S))
    data = re.search(r'<script type="application/json" id="chart-data">.*?</script>', html, re.S)
    if not data:
        sys.exit("no #chart-data block in the artifact; run make_artifact.py first")
    # The chart code is the inline script that defines the drawer table.
    js = None
    for m in re.finditer(r"<script>(.*?)</script>", html, re.S):
        if "drawers" in m.group(1) and "drawAnchors" in m.group(1):
            js = m.group(1)
            break
    if js is None:
        sys.exit("could not find the chart script in the artifact")
    return styles, data.group(0), js


def page(styles, data, js, chart, height=None):
    size = f"height:{height}px;" if height else ""
    return f"""<!doctype html><html><head><meta charset="utf-8">{styles}
<style>body{{margin:0;padding:0;background:var(--paper);}}
 #wrap{{width:{WIDTH}px;padding:0;{size}}}
 figure.chart{{margin:0;}}</style></head>
<body><div id="wrap"><div data-chart="{chart}"></div></div>
{data}
<script>{js}</script>
<script>
  // Report the rendered height so the second pass can size the window exactly.
  window.addEventListener('load', function(){{
    var f = document.querySelector('#wrap figure.chart');
    document.title = f ? String(Math.ceil(f.getBoundingClientRect().height)) : 'ERR';
  }});
</script></body></html>"""


def render(path, out_png, height):
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    f"--force-device-scale-factor={SCALE}",
                    f"--window-size={WIDTH},{height}",
                    "--virtual-time-budget=6000",
                    f"--screenshot={out_png}", f"file://{path}"],
                   check=True, capture_output=True)


def measure(path):
    r = subprocess.run([CHROME, "--headless=new", "--disable-gpu",
                        f"--window-size={WIDTH},2400", "--virtual-time-budget=6000",
                        "--dump-dom", f"file://{path}"],
                       check=True, capture_output=True, text=True)
    m = re.search(r"<title>(\d+)</title>", r.stdout)
    return int(m.group(1)) if m else None


def main():
    if not os.path.exists(CHROME):
        sys.exit(f"headless Chrome not found at {CHROME}")
    styles, data, js = slice_artifact()
    os.makedirs(OUT_DIR, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for chart in CHARTS:
            probe = os.path.join(tmp, f"{chart}-probe.html")
            open(probe, "w").write(page(styles, data, js, chart))
            h = measure(probe)
            if not h:
                print(f"  {chart}: could not measure height, skipping")
                continue
            final = os.path.join(tmp, f"{chart}.html")
            open(final, "w").write(page(styles, data, js, chart, height=h))
            out = os.path.join(OUT_DIR, f"{chart}.png")
            render(final, out, h)
            print(f"  wrote {os.path.relpath(out, ROOT)}  ({WIDTH}x{h} at {SCALE}x, "
                  f"{os.path.getsize(out) // 1024} KB)")


if __name__ == "__main__":
    main()
