# DarkBench Revisited

A replication of **DarkBench** (Kran et al., *Benchmarking Dark Patterns in Large Language
Models*, arXiv [2503.10728](https://arxiv.org/abs/2503.10728), ICLR 2025) on current models,
with a three-judge ensemble and an era-matched control.

Course project for BlueDot Impact's AI safety course. **Status: draft, analysis in progress.**
Numbers below are provisional; see [Limitations](#limitations) before citing anything.

---

## What was run

All **660** original DarkBench prompts (110 in each of six dark-pattern categories) against
**11 models**, each response scored independently by **3 judges** — 33 model×judge passes,
21,780 judgments.

| | models |
|---|---|
| **Current (2026)** | `claude-sonnet-5`, `claude-opus-5`, `gemini-3.8-flash`, `gemini-3.1-pro-preview`, `gpt-5.4-mini-2026-03-17`, `gpt-5.5-2026-04-23`, `kimi-k3`, `glm-5p3` |
| **2024 control** | `gpt-3.5-turbo-0125`, `gpt-4-turbo-2024-04-09`, `gpt-4o-2024-08-06` |
| **Judges** | `gpt-5.5-2026-04-23`, `claude-opus-4-6`, `gemini-3.1-pro-preview` |

The 2024 models are three of the paper's original fourteen that are still served. They make the
comparison internal: same prompts, same judges, same pipeline, only the model generation
differs — so we never have to compare our judges against the paper's retired ones.

## Headline findings

1. **Judge choice moves the result more than model choice does.** Pairwise agreement between
   judges is 76–92% (Cohen's κ 0.52–0.57). On harmful generation the three judges scored the
   *same* responses at 2%, 10% and 37% (κ 0.24) — they disagree about whether clearly-framed
   fiction counts. Any single-judge benchmark number should be read with that in mind.
2. **Sycophancy has genuinely collapsed.** 2024 models flag at 11–30%; every current model
   except one sits at ~0%. Confirmed three ways: all judges agree, the 2024 control shows the
   behaviour was present, and the confidence intervals don't overlap.
3. **The "models got better" story does not otherwise survive.** Against the *best* 2024 model
   the current average is ~2 points lower — inside noise. Only the oldest model (gpt-3.5-turbo)
   is clearly worse than today's.
4. **Two model-specific results are robust:** Claude Opus 5 shows anthropomorphization at
   53–73% (vs 6–15% for Sonnet 5), and Gemini 3.1 Pro shows user retention at 85–93% — both
   under all three judges, both well outside sampling noise.
5. **The benchmark has partly saturated.** Its sycophancy prompts no longer discriminate
   between current models.

Full analysis, per-cell tables and a claim-by-claim uncertainty audit: **[`WRITEUP.md`](WRITEUP.md)**.

![Flagged rate by category, model and judge](data/results/rates.svg)

## Limitations

- **No judge is validated.** Hand-labelling is in progress (`data/results/handlabel/`); until
  then we know the judges disagree, not which is correct.
- **One response per prompt.** Confidence intervals are ±6–9 points per category cell, so two
  models need ~15 points of difference to separate. `WRITEUP.md` §3b marks every claim as
  survives / partial / fails against this.
- Those intervals are optimistic: they omit generation and judging variance entirely (a verdict
  has already flipped on an identical re-run at temperature 0).
- Current models reason before answering; the paper's did not. Reasoning is excluded from what
  the judge sees, but it is a behavioural difference from the original setup.
- The prompts are public and two years old; contamination cannot be ruled out.

## Repository layout

```
DarkBench/               vendored upstream benchmark, frozen at apartresearch 7eef151
  darkbench/             task, scorer, dark-pattern definitions, the 660 prompts
  background.md          how the benchmark works; paper-vs-code discrepancies
  judge_prompt_original.txt
darkbench-fixes.patch    the four scorer fixes applied to the vendored copy
analyze.py               scored logs -> data/results/rates.csv + tables + judge agreement
make_chart.py            rates.csv -> data/results/rates.svg
make_handlabel_sample.py blind stratified hand-labelling sample
data/results/            rates.csv, rates.svg, handlabel/
data/raw-manifest.json   SHA-256s + metadata for the raw logs (archived outside git)
data/labels/             hand labels (ground truth) — created during labelling
NOTES.md                 dated running log: every bug, decision, correction and retraction
WRITEUP.md               the draft paper
claude-code-project-file.md   project charter
requirements-frozen.txt  exact environment that produced every result
```

## Reproducing

```bash
cd DarkBench
uv venv && uv pip install -r ../requirements-frozen.txt   # inspect_ai 0.3.263
export ANTHROPIC_API_KEY=... OPENAI_API_KEY=... GOOGLE_API_KEY=...
```

Generate (one model), then score once per judge:

```bash
.venv/bin/inspect eval darkbench/darkbench --model anthropic/claude-sonnet-5 \
  --no-score --no-fail-on-error --max-connections 4 --timeout 300 --max-retries 3 \
  --log-dir ../data/raw/inspect-logs

.venv/bin/inspect score <log>.eval --scorer darkbench/overseer \
  -S model=anthropic/claude-opus-4-6 --output-file <log>-scored-opus46.eval
```

Fireworks models route through the OpenAI provider
(`OPENAI_API_KEY=$FIREWORKS_API_KEY --model openai/accounts/fireworks/models/kimi-k3
--model-base-url https://api.fireworks.ai/inference/v1`). Gemini needs `--batch` for generation
and `-S batch=true` for judging — its interactive tier is capped at 250 requests/day.

Then rebuild the results:

```bash
.venv/bin/python ../analyze.py      # -> data/results/rates.csv (198 rows)
python3 ../make_chart.py            # -> data/results/rates.svg
```

Cost for the full grid was ≈ $250. Practical notes — rate limits, batch quirks, resuming a
partial run with `eval-retry`, and the fact that every provider halted the run at least once on
billing — are in `NOTES.md`.

## Raw logs

The 75 `.eval` logs (~270 MB) are **not in git**. They are archived as a zip outside the repo,
with SHA-256 checksums and per-log metadata (model, date, status, sample count, inspect version,
role) recorded in [`data/raw-manifest.json`](data/raw-manifest.json). One canonical 660-sample,
zero-error generation log per model; partial and smoke-test logs are kept and labelled as such.

## Changes to the benchmark code

Vendored at upstream commit `7eef151`, deliberately frozen — not rebased during the study. Four
fixes, all in `darkbench/scorer.py`, captured in `darkbench-fixes.patch`:

1. **Category lookup crashed on hyphenated names.** The dataset uses `brand-bias`; the code's
   IDs use `brand_bias`. Three of six categories were unscoreable as shipped — independently
   reported in an open upstream PR.
2. **The judge prompt was `.format()`-ed twice**, so braces a model wrote (LaTeX like `10^{24}`)
   crashed scoring. Fixed by escaping; the judge sees identical text otherwise.
3. **`batch` parameter** threaded through, so judging can use a provider Batch API.
4. **Batch per-request failures retried** instead of aborting a whole 660-sample pass.

Two discrepancies between the paper and the released code are documented in
`DarkBench/background.md` (the code applies an undisclosed system prompt; the default judge is a
single `gpt-4o-mini`, not the paper's three-model ensemble).

## Provenance and license

Upstream `apartresearch/DarkBench` @ `7eef151` (2025-03-29) — itself a fork of
`sjawhar/DarkBench`, rooted at `esbenkc/DarkGPT`. The paper's own Reproducibility Statement
cites an anonymized review mirror that now returns HTTP 401.

The vendored code is **MIT**, © 2024 Esben Kran — see [`DarkBench/LICENSE`](DarkBench/LICENSE),
retained unmodified. Analysis code and writeup in this repository are by Eileen Hartnett.
