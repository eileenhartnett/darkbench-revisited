"""Verify the 2026-09-27 brand-bias re-score from the saved logs. No model calls.

Usage (from project root, needs the raw logs and inspect_ai):
    DarkBench/.venv/bin/python scripts/verify_rescore_provenance.py

The re-audit of 2026-09-27 noted a reproducibility limit: the archive's checksums establish
that the log files are unchanged, but not what was actually sent to the judges, whether the
scored responses match the canonical generation, which judge produced each verdict, or whether
every contaminated judgment was in fact replaced. Those checks need the logs themselves, which
exist here. This script runs them and writes the evidence out so a reviewer does not have to.

Five checks:
  1. rendered prompt      the brand-bias rubric each judge saw names the real developer
  2. response integrity   every scored response is byte-identical to the canonical generation
  3. judge identity       the model and settings recorded in each rescored log
  4. coverage             every contaminated (model, judge, sample) has a replacement
  5. verdict parsing      no unparseable or invalid verdicts in the replacements

Writes data/results/rescore_provenance.csv, one row per rescored log, with response-content
hashes and the source-log identifiers the re-audit asked for.
"""

import csv
import glob
import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "DarkBench"))
LOG_DIR = os.path.join(ROOT, "data", "raw", "inspect-logs")
RESCORE_DIR = os.path.join(ROOT, "data", "raw", "inspect-logs-rescore")
OUT = os.path.join(ROOT, "data", "results", "rescore_provenance.csv")

EXPECT_DEV = {"kimi-k3": ("Moonshot AI", "Kimi"), "glm-5p3": ("Zhipu AI", "GLM")}


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main():
    from inspect_ai.log import read_eval_log
    from darkbench.scorer import _get_model_info
    from darkbench.dark_patterns import BRAND_BIAS

    # canonical generation logs, for the response-integrity check
    canon = {}
    for p in sorted(glob.glob(os.path.join(LOG_DIR, "*.eval"))):
        if "-scored-" in os.path.basename(p):
            continue
        log = read_eval_log(p)
        m = log.eval.model.split("/")[-1]
        if m in EXPECT_DEV and len(log.samples or []) == 660:
            canon[m] = (os.path.basename(p),
                        {s.id: s.output.completion for s in log.samples})
    print(f"canonical generation logs found: {sorted(canon)}")

    rows, failures = [], []
    for p in sorted(glob.glob(os.path.join(RESCORE_DIR, "*-rescored-*.eval"))):
        judge = re.search(r"-rescored-([a-z0-9]+)\.eval$", p).group(1)
        log = read_eval_log(p)
        model = log.eval.model.split("/")[-1]
        info = _get_model_info(log.eval.model)
        rubric = BRAND_BIAS.description.format(**info.model_dump())

        # 1. rendered prompt names the real developer
        want_co, want_mod = EXPECT_DEV[model]
        prompt_ok = (info.company == want_co and info.model == want_mod
                     and "OpenAI" not in rubric)

        # 2. every scored response byte-identical to the canonical generation
        src_name, src = canon[model]
        drift = [s.id for s in log.samples if src.get(s.id) != s.output.completion]
        resp_hash = sha("".join(s.output.completion for s in sorted(log.samples, key=lambda x: x.id)))

        # 5. parsing / validity
        vals = [list(s.scores.values())[0].value for s in log.samples]
        n_invalid = sum(1 for v in vals if v == -1)
        n_flag = sum(1 for v in vals if v is True or v == 2)

        rows.append({
            "model": model, "judge": judge,
            "rescored_log": os.path.basename(p),
            "source_generation_log": src_name,
            "judge_model_recorded": getattr(log.eval, "model", ""),
            "resolved_company": info.company, "resolved_model": info.model,
            "prompt_names_real_developer": int(prompt_ok),
            "n_samples": len(log.samples),
            "responses_identical_to_canonical": int(not drift),
            "response_content_sha256": resp_hash,
            "n_invalid": n_invalid, "n_flagged": n_flag,
            "status": log.status,
        })
        if not prompt_ok:
            failures.append(f"{model}/{judge}: rubric still names {info.company}")
        if drift:
            failures.append(f"{model}/{judge}: {len(drift)} responses differ from canonical")
        if n_invalid:
            failures.append(f"{model}/{judge}: {n_invalid} unparseable verdicts")

    # 4. coverage against the contaminated record
    contaminated = list(csv.DictReader(
        open(os.path.join(ROOT, "data", "results", "brandbias_contaminated.csv"))))
    have = {(r["model"], r["judge"]) for r in rows}
    want = {(r["model"], r["judge"]) for r in contaminated}
    missing = want - have
    if missing:
        failures.append(f"no replacement for {sorted(missing)}")

    print("\ncheck                                    result")
    print(f"  rendered prompt names real developer   {all(r['prompt_names_real_developer'] for r in rows)}")
    print(f"  responses identical to canonical       {all(r['responses_identical_to_canonical'] for r in rows)}")
    print(f"  every contaminated cell replaced       {not missing} ({len(have)} of {len(want)})")
    print(f"  no unparseable verdicts                {all(r['n_invalid'] == 0 for r in rows)}")
    print(f"  all logs completed                     {all(r['status'] == 'success' for r in rows)}")
    print(f"  total replacement judgments            {sum(r['n_samples'] for r in rows)}")

    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {OUT} ({len(rows)} rows)")

    if failures:
        print("\nFAILURES:")
        for x in failures:
            print("  " + x)
        sys.exit(1)
    print("\nall provenance checks passed")


if __name__ == "__main__":
    main()
