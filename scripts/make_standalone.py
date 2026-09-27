"""Wrap data/results/artifact.html into a standalone, shareable HTML page.

Usage (from project root):
    python3 make_standalone.py            # uses the cached copy of marked.js
    python3 make_standalone.py --fetch    # re-download marked.js first

`make_artifact.py` writes a *fragment*: it starts at <title> and has no doctype,
<html>, <head> or <body>, because the Artifact tool supplies that skeleton at
publish time. Opened directly from disk or served from an ordinary web host, the
fragment still renders in most browsers, but it is not a valid document and it
depends on a CDN for the markdown renderer. If that script fails to load, the
whole body stays blank, because the paper is markdown rendered in the browser.

This script produces a proper document instead:
  - adds the doctype, <html lang>, <head>, <body> and the same small reset the
    Artifact host applies, so the published page and this file look identical;
  - inlines marked.js, so the page renders with no network at all.

Google Fonts stays a link. If it fails the page falls back to the system stacks
already declared in the CSS, which costs some polish and nothing else.

Output: data/results/darkbench-revisited.html, a single file to email, drop on a
static host, or commit to GitHub Pages.
"""

import argparse
import os
import sys
import urllib.request

# Scripts live in scripts/; every data path below is relative to the repository root.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "results", "artifact.html")
OUT = os.path.join(ROOT, "data", "results", "darkbench-revisited.html")
VENDOR = os.path.join(ROOT, "artifact", "marked.min.js")

MARKED_URL = "https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js"
MARKED_TAG = f'<script src="{MARKED_URL}"></script>'

# The reset the Artifact host injects, reproduced so the standalone file matches
# the published page. The artifact's own <style> overrides the body rule.
RESET = (
    ":root{color-scheme:light}"
    "body{margin:0;padding:0;font:14px -apple-system,BlinkMacSystemFont,sans-serif;"
    "background:#faf9f5;color:#141413}"
    "img{max-width:100%}"
    "[hidden]:not([hidden=until-found]){display:none!important}"
)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fetch", action="store_true",
                    help="re-download marked.js into artifact/ before building")
    args = ap.parse_args()

    if args.fetch or not os.path.exists(VENDOR):
        print(f"fetching {MARKED_URL}")
        with urllib.request.urlopen(MARKED_URL, timeout=60) as r:
            js = r.read().decode("utf-8")
        with open(VENDOR, "w") as f:
            f.write(js)
        print(f"  wrote {VENDOR} ({len(js) / 1024:.0f} KB)")
    js = open(VENDOR).read()
    if "marked" not in js[:400]:
        sys.exit(f"{VENDOR} does not look like marked.js; re-run with --fetch")

    body = open(SRC).read()
    if MARKED_TAG not in body:
        sys.exit(f"did not find the marked.js script tag in {SRC};\n"
                 f"expected exactly: {MARKED_TAG}")
    # Inline the library in place, so it still loads before the inline script
    # further down the file that calls marked.parse().
    body = body.replace(MARKED_TAG, f"<script>\n{js}\n</script>", 1)

    doc = (
        '<!doctype html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f"<style>{RESET}</style>\n"
        "</head>\n<body>\n"
        f"{body}\n"
        "</body>\n</html>\n"
    )
    with open(OUT, "w") as f:
        f.write(doc)

    print(f"wrote {OUT} ({os.path.getsize(OUT) / 1024:.0f} KB)")
    print("  doctype + head/body added; marked.js inlined")
    print("  remaining network dependency: Google Fonts (cosmetic, has fallbacks)")


if __name__ == "__main__":
    main()
