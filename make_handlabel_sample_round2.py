"""Build a second blind hand-labelling sample: sneaking + brand-bias.

Round 2 of the hand-label validation (see NOTES.md 2026-09-15) — round 1 covered
harmful-generation, anthropomorphization, sycophancy, user-retention and found
those categories rested only on inter-judge agreement, not human validation.
This does the same for the two categories left unchecked.

Usage (from DarkBench/): .venv/bin/python ../make_handlabel_sample_round2.py

Writes to data/results/handlabel/:
  sneaking_brandbias_auditing.csv  - blind: key, category, definition, prompt, response, empty label columns
  sneaking_brandbias_auditing.md   - the same items, readable, grouped by category
  sneaking_brandbias_auditing_key.csv     - NOT blind: key -> model, each judge's verdict, vote pattern.
                        Don't open until labelling is done.
Hand labels belong in data/labels/ (Eileen's directory); this script never writes there.
Does not touch round 1's sample.csv / sample.md / key.csv.
"""

import csv
import glob
import os
import random
import sys

from inspect_ai.log import read_eval_log

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze import LOG_DIR, is_flagged, is_invalid, short_model  # noqa: E402
from darkbench.dark_patterns import DARK_PATTERNS  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(LOG_DIR), "..", "results", "handlabel")
SEED = 20260915  # different from round 1 (20260911) so this draws a fresh sample
JUDGES = ["gpt55", "opus46", "gemini31pro"]

# category -> quota by number of judges that flagged: {0:n, 1:n, 2:n, 3:n}
# 50 per category, same over-sample-the-splits shape as round 1.
PLAN = {
    "sneaking": {0: 12, 1: 15, 2: 15, 3: 8},
    "brand-bias": {0: 12, 1: 15, 2: 15, 3: 8},
}


def load():
    """Return {(model, sample_id): {"category", "prompt", "response", "votes": {judge: value}}}."""
    items = {}
    for path in sorted(glob.glob(os.path.join(LOG_DIR, "*-scored-*.eval"))):
        judge = path.rsplit("-scored-", 1)[1].replace(".eval", "")
        if judge not in JUDGES:
            continue
        log = read_eval_log(path)
        if len(log.samples) != 660:
            continue
        model = short_model(log.eval.model)
        for s in log.samples:
            score = (s.scores or {}).get("overseer")
            if score is None:
                continue
            it = items.setdefault((model, s.id), {
                "category": s.target,
                "prompt": s.input if isinstance(s.input, str) else s.input_text,
                "response": s.output.completion,
                "votes": {},
            })
            it["votes"][judge] = score.value
    return {k: v for k, v in items.items() if len(v["votes"]) == 3 and v["response"].strip()}


def main():
    rng = random.Random(SEED)
    items = load()
    pools = {}
    for (model, sid), it in items.items():
        if it["category"] not in PLAN:
            continue
        votes = it["votes"].values()
        if any(is_invalid(v) for v in votes):
            continue
        n_flag = sum(is_flagged(v) for v in votes)
        pools.setdefault((it["category"], n_flag), []).append((model, sid))

    chosen = []
    for cat, quota in PLAN.items():
        for n_flag, k in quota.items():
            pool = pools.get((cat, n_flag), [])
            rng.shuffle(pool)
            chosen.extend(pool[:k])
            if len(pool) < k:
                print(f"note: only {len(pool)} items for {cat} with {n_flag} judges flagging (wanted {k})")

    rng.shuffle(chosen)
    chosen.sort(key=lambda ms: list(PLAN).index(items[ms]["category"]))

    os.makedirs(OUT_DIR, exist_ok=True)
    blind_path = os.path.join(OUT_DIR, "sneaking_brandbias_auditing.csv")
    key_path = os.path.join(OUT_DIR, "sneaking_brandbias_auditing_key.csv")
    md_path = os.path.join(OUT_DIR, "sneaking_brandbias_auditing.md")
    with open(blind_path, "w", newline="") as f_blind, \
         open(key_path, "w", newline="") as f_key, \
         open(md_path, "w") as f_md:
        blind = csv.writer(f_blind)
        blind.writerow(["key", "category", "definition", "prompt", "response",
                        "label_present_0_or_1", "egregious_0_or_1", "notes"])
        key = csv.writer(f_key)
        key.writerow(["key", "model", "sample_id", "category"] + JUDGES + ["n_judges_flagged"])

        current_cat = None
        for i, (model, sid) in enumerate(chosen, 1):
            it = items[(model, sid)]
            cat = it["category"]
            definition = DARK_PATTERNS[cat.replace("-", "_")].description
            k = f"HL2-{i:03d}"
            blind.writerow([k, cat, definition, it["prompt"], it["response"], "", "", ""])
            votes = it["votes"]
            key.writerow([k, model, sid, cat] + [votes[j] for j in JUDGES]
                         + [sum(is_flagged(votes[j]) for j in JUDGES)])
            if cat != current_cat:
                current_cat = cat
                f_md.write(f"\n\n# {cat}\n\n**Definition used by the judges:** {definition}\n\n"
                           f"Label 1 if the response shows the pattern, 0 if not. "
                           f"Mark egregious=1 only for clear, strong cases.\n")
            f_md.write(f"\n---\n\n## {k}\n\n**Prompt:**\n\n{it['prompt']}\n\n**Response:**\n\n"
                       f"{it['response']}\n\n**Label (0/1):** ___   **Egregious (0/1):** ___   **Notes:**\n")

    from collections import Counter
    by_cat = Counter(items[ms]["category"] for ms in chosen)
    by_model = Counter(ms[0] for ms in chosen)
    print(f"wrote {len(chosen)} items to {os.path.abspath(OUT_DIR)}")
    print(f"  blind sample: {blind_path}")
    print(f"  key (do not open until done): {key_path}")
    print("by category:", dict(by_cat))
    print("by model:", dict(sorted(by_model.items())))


if __name__ == "__main__":
    main()
