# Reproducing DarkBench Revisited

Everything needed to re-derive the results, rebuild the report, or rerun the experiment from
scratch. The short version lives in the [README](../README.md); this is the detail.

Two things are worth separating before you start, because they cost very different amounts and
prove very different things:

- **Rebuilding the figures and HTML** renders the saved numbers. It is free and offline, and it
  confirms the published report matches the committed data. It does not re-derive anything.
- **Independently recomputing the statistics** runs the analysis over the item-level judgments.
  Also free and offline. This is the one that actually checks the numbers.
- **Regenerating the model outputs** re-runs generation and scoring against live APIs. This
  costs money and will not reproduce the saved verdicts exactly, since models drift.

---

## Offline: recompute the statistics

No API keys, no cost, nothing downloaded. Needs Python 3.11+ only.

```bash
python3 scripts/paired_analysis.py    # verdicts.csv -> paired_contrasts.csv,
                                      #    judge_agreement_matched.csv, anchor_contrasts.csv
python3 scripts/make_supplements.py   # CSVs -> regenerates S1-S5 and S7 in the report
python3 scripts/test_quarantine_guard.py     # regression check on the exclusion logic
python3 scripts/make_supplements.py --check  # fails if any generated table is stale
```

`data/results/verdicts.csv` holds all 23,760 first-pass judgments and
`data/results/verdicts_pass2.csv` the 3,960 retest judgments, each with sample id, model, judge,
category, verdict, validity and quarantine flag. Those two files are enough to reproduce the
paired model contrasts, the anchor contrasts and the common-mask reliability table without the
raw archive.

**What still needs the raw logs.** Rebuilding `rates.csv` from the source verdicts
(`scripts/analyze.py`), the common-mask reliability computation itself
(`scripts/reliability_matched.py`, which reads the retest logs), and the provenance verification
(`scripts/verify_rescore_provenance.py`, which reads the saved judge requests). Ask for the zip
named in `data/raw-manifest.json`.

## Offline: rebuild the figures and HTML

Run in this order. Each step consumes the previous step's output, and skipping `make_chart.py`
leaves a stale category figure embedded in the HTML.

```bash
python3 scripts/make_chart.py         # rates.csv -> data/results/rates.svg
python3 scripts/make_supplements.py   # refresh the generated supplement tables
python3 scripts/make_artifact.py      # report + CSVs -> artifact.html, prints three spot checks
python3 scripts/make_figures.py       # artifact chart code -> data/results/figures/*.png
python3 scripts/make_standalone.py    # artifact.html -> darkbench-revisited.html
```

`make_figures.py` shells out to headless Chrome at a hardcoded macOS path
(`/Applications/Google Chrome.app/...`). Edit `CHROME` at the top of that file on another
platform.

## Regenerating model outputs (paid)

```bash
cd DarkBench
uv venv && uv pip install -r ../requirements-frozen.txt   # inspect_ai 0.3.263
export ANTHROPIC_API_KEY=... OPENAI_API_KEY=... GOOGLE_API_KEY=...
```

Generate one model, then score once per judge:

```bash
.venv/bin/inspect eval darkbench/darkbench --model anthropic/claude-sonnet-5 \
  --no-score --no-fail-on-error --max-connections 4 --timeout 300 --max-retries 3 \
  --log-dir ../data/raw/inspect-logs

.venv/bin/inspect score <log>.eval --scorer darkbench/overseer \
  -S model=anthropic/claude-opus-4-6 --output-file <log>-scored-opus46.eval
```

Then rebuild the results:

```bash
.venv/bin/python ../scripts/analyze.py   # -> rates.csv (216 rows), judge_agreement.csv,
                                         #    verdicts.csv, quarantine.csv, majority_rates.csv
```

### Provider notes

- **Fireworks-hosted models** route through the OpenAI provider:
  `OPENAI_API_KEY=$FIREWORKS_API_KEY --model openai/accounts/fireworks/models/kimi-k3
  --model-base-url https://api.fireworks.ai/inference/v1`. Note the scorer resolves a model's
  *developer* from its identifier; fix 5 in the patch exists because that routing was once read
  as the developer being OpenAI.
- **Gemini** needs `--batch` for generation and `-S batch=true` for judging. Its interactive
  tier is capped at 250 requests per day.
- **GPT-5.5** rejects an explicit `temperature`; the scorer's default path handles this.
- Rate limits, batch quirks, resuming a partial run with `eval-retry`, and the fact that every
  provider halted the run at least once on billing are all recorded in [NOTES.md](NOTES.md).

### Cost

Roughly **$232 total**, useful for planning a rerun rather than as an accounting record:

| stage | approximate |
|---|---|
| generation | $100 |
| judging | $105 |
| judge test-retest | $25 |
| brand-bias re-score | $2 |

**These are estimates, not verified billing.** `inspect score` does not record judge token usage
in the log, so the judging and re-score figures are reconstructed from rendered prompts and
stored completions at list prices. Reconstruction can miss billable usage the log never shows,
including reasoning tokens and retried calls, so the true figure could be higher. No provider
invoice was checked.

## Raw logs

The 91 `.eval` logs are **not in git**. They are archived as a zip outside the repository, dated
2026-09-27, with SHA-256 checksums and per-log metadata (model, date, status, sample count,
inspect version, role) in [`data/raw-manifest.json`](../data/raw-manifest.json). There is one
canonical 660-sample, zero-error generation log per model; partial and smoke-test logs are kept
and labelled as such. The six brand-bias re-score logs from 2026-09-27 are included and labelled
`rescored-brandbias`.

## Changes to the benchmark code

Vendored at upstream commit `7eef151`, deliberately frozen and not rebased during the study.
Five fixes, all in `darkbench/scorer.py`, captured in
[`patches/darkbench-fixes.patch`](../patches/darkbench-fixes.patch):

1. **Category lookup crashed on hyphenated names.** The dataset uses `brand-bias`; the code's
   IDs use `brand_bias`. Three of six categories were unscoreable as shipped, independently
   reported in an open upstream PR.
2. **The judge prompt was `.format()`-ed twice**, so braces a model wrote (LaTeX like `10^{24}`)
   crashed scoring. Fixed by escaping; the judge sees identical text otherwise.
3. **`batch` parameter** threaded through, so judging can use a provider Batch API.
4. **Batch per-request failures retried** instead of aborting a whole 660-sample pass.
5. **Developer resolved instead of API provider.** Models reached through an OpenAI-compatible
   endpoint were resolved as built by OpenAI, and that name was interpolated into the brand-bias
   judge prompt. Applied 2026-09-27; it does not repair scores already produced, so the affected
   judgments were re-scored. See [CORRECTIONS.md](CORRECTIONS.md).

Two discrepancies between the paper and the released code are documented in
`DarkBench/background.md`: the code applies an undisclosed system prompt, and the default judge
is a single `gpt-4o-mini` rather than the paper's three-model ensemble.

## Provenance and license

Upstream `apartresearch/DarkBench` @ `7eef151` (2025-03-29), itself a fork of `sjawhar/DarkBench`,
rooted at `esbenkc/DarkGPT`. The paper's own Reproducibility Statement cites an anonymized review
mirror that now returns HTTP 401.

The vendored code is **MIT**, © 2024 Esben Kran, see [`DarkBench/LICENSE`](../DarkBench/LICENSE),
retained unmodified. Analysis code and writing in this repository are by Eileen Hartnett.
