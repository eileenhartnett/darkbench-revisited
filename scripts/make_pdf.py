"""Print the technical report to PDF for reviewers who want a static copy.

Usage (from project root, after make_standalone.py):
    python3 scripts/make_pdf.py

The standalone HTML is the better artefact: it has live charts and collapsible supplements.
This exists because a submission often needs something attachable and commentable.

Two things have to be handled or the PDF loses content. The supplements render inside
<details> elements, which print collapsed and would silently drop fourteen sections. And the
sticky sidebar navigation repeats on every page. So this injects a small print stylesheet and
a script that opens every <details> before printing, then drives headless Chrome.

Writes data/results/darkbench-revisited.pdf.
"""

import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "results", "darkbench-revisited.html")
OUT = os.path.join(ROOT, "data", "results", "darkbench-revisited.pdf")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

PRINT_CSS = """
<style id="print-fixes">
@media print {
  nav.toc { display: none !important; }
  .shell { display: block !important; max-width: none !important; }
  .reading { max-width: none !important; padding: 0 !important; }
  details.supp { border: none !important; page-break-inside: auto; }
  /* Tables clip in print: cells are nowrap inside a horizontally scrollable wrapper, and
     paper cannot scroll. Let them wrap and fit the page instead (closure review, finding A). */
  .table-wrap { overflow: visible !important; border: none !important; }
  #content table { width: 100% !important; min-width: 0 !important; table-layout: auto;
                   font-size: 0.78rem !important; }
  #content th, #content td { white-space: normal !important; overflow-wrap: anywhere;
                             min-width: 0 !important; padding: 5px 7px !important; }
  #content td:first-child, #content th:first-child { min-width: 0 !important; }
  details.supp summary { font-weight: 700; }
  details.supp summary::before { content: "" !important; }
  figure.chart, .table-wrap { page-break-inside: avoid; }
  h1, h2, h3 { page-break-after: avoid; }
  a { text-decoration: none; }
  body { background: #fff !important; }
}
</style>
<script id="expand-for-print">
  window.addEventListener('load', function () {
    document.querySelectorAll('details').forEach(function (d) { d.open = true; });
  });
</script>
"""


def main():
    if not os.path.exists(CHROME):
        sys.exit(f"headless Chrome not found at {CHROME}; edit CHROME at the top of this file")
    if not os.path.exists(SRC):
        sys.exit(f"{SRC} not found; run scripts/make_standalone.py first")

    html = open(SRC).read()
    if "</body>" not in html:
        sys.exit("unexpected standalone structure: no </body>")
    html = html.replace("</body>", PRINT_CSS + "\n</body>", 1)

    with tempfile.TemporaryDirectory() as tmp:
        staged = os.path.join(tmp, "print.html")
        open(staged, "w").write(html)
        subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
             "--virtual-time-budget=20000", f"--print-to-pdf={OUT}", f"file://{staged}"],
            check=True, capture_output=True)

    size = os.path.getsize(OUT)
    with open(OUT, "rb") as f:
        pages = len(re.findall(rb"/Type\s*/Page[^s]", f.read()))
    print(f"wrote {OUT}")
    print(f"  {size // 1024} KB, {pages} pages, supplements expanded, sidebar hidden")
    print("  note: charts are rasterised by the print engine; the HTML keeps them interactive")


if __name__ == "__main__":
    main()
