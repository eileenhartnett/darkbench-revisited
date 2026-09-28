"""Regression check: an incomplete rescore must not clear a quarantine.

Usage (from project root, no API calls, no raw logs needed):
    python3 scripts/test_quarantine_guard.py

Why this exists. The first version of the guard cleared exclusion at (model, category) level
as soon as any replacement loaded. Loading one judge's 110 replacements for Kimi brand bias
therefore released all 330 judgments in that cell, letting 220 contaminated verdicts back into
every aggregate. The independent re-audit of 2026-09-27 demonstrated this with a counterexample.

The guard now tracks coverage per (model, judge, sample_id) and repairs a cell only when every
contaminated judgment has a replacement. This script asserts that property directly, with
stub data, so the fix cannot silently regress.
"""

import importlib.util
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_analyze():
    """Import analyze.py without requiring inspect_ai, which is only needed to read logs."""
    for name in ("inspect_ai", "inspect_ai.log"):
        if name not in sys.modules:
            sys.modules[name] = types.ModuleType(name)
    sys.modules["inspect_ai.log"].read_eval_log = lambda *a, **k: None
    spec = importlib.util.spec_from_file_location("analyze", os.path.join(ROOT, "scripts", "analyze.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fake_verdicts(model, judges, n_per_cat=4):
    """{(model, judge): {sample_id: (category, value)}} over two categories."""
    out = {}
    for j in judges:
        cells = {}
        for cat in ("brand-bias", "sneaking"):
            for i in range(n_per_cat):
                cells[f"{cat}-{i:03d}"] = (cat, False)
        out[(model, j)] = cells
    return out


def run_case(label, replace, expect_repaired):
    az = load_analyze()
    judges = ["gpt55", "opus46", "gemini31pro"]
    model = "kimi-k3"
    verdicts = fake_verdicts(model, judges)
    az.QUARANTINE.clear()
    az.QUARANTINE[(model, "brand-bias")] = "test"
    az.RESCORED_KEYS.clear()
    az.REPAIRED.clear()
    for j, sid in replace(verdicts, model, judges):
        az.RESCORED_KEYS.add((model, j, sid))
    # Re-run only the coverage half of load_rescored, since there are no logs on disk here.
    for (m, cat) in az.QUARANTINE:
        expected = {(m, j, sid) for j in judges
                    for sid, (c, _) in verdicts[(m, j)].items() if c == cat}
        az.REPAIRED[(m, cat)] = not (expected - az.RESCORED_KEYS)
    got = not az.quarantined(model, "brand-bias")
    ok = got == expect_repaired
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}: repaired={got}, expected={expect_repaired}")
    return ok


def main():
    print("quarantine guard, incomplete-rescore regression check")
    results = [
        run_case(
            "no replacements at all",
            lambda v, m, js: [],
            expect_repaired=False),
        run_case(
            "one judge fully replaced, two judges missing",
            lambda v, m, js: [(js[0], sid) for sid, (c, _) in v[(m, js[0])].items() if c == "brand-bias"],
            expect_repaired=False),
        run_case(
            "all judges but one sample short",
            lambda v, m, js: [(j, sid) for j in js
                              for sid, (c, _) in v[(m, j)].items() if c == "brand-bias"][:-1],
            expect_repaired=False),
        run_case(
            "complete coverage across every judge and sample",
            lambda v, m, js: [(j, sid) for j in js
                              for sid, (c, _) in v[(m, j)].items() if c == "brand-bias"],
            expect_repaired=True),
        run_case(
            "replacements for the wrong category only",
            lambda v, m, js: [(j, sid) for j in js
                              for sid, (c, _) in v[(m, j)].items() if c == "sneaking"],
            expect_repaired=False),
    ]
    print(f"\n{sum(results)} of {len(results)} passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
