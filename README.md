# DarkBench Revisited

**What happens when you re-run a benchmark whose scores come from an LLM, and then test the
LLM doing the scoring?**

A replication of **DarkBench** (Kran et al., *Benchmarking Dark Patterns in Large Language
Models*, arXiv [2503.10728](https://arxiv.org/abs/2503.10728), ICLR 2025) on nine current
models and three 2024 models that are still served, scored by three current LLM judges. The
interesting part turned out not to be the leaderboard. It was what the judges did when I
checked them: asked the same question twice, compared against each other, and compared against
my own labels under two readings of an ambiguous category.

Course project for BlueDot Impact's AI safety course.

## Read it

- **Blog post**, the main narrative, about 2,000 words, on the BlueDot submission page. It is
  not versioned here; this repository holds the analyses, the technical report and the
  evidence behind them.
- **[Full technical report](https://claude.ai/code/artifact/5dabf49b-2002-4bb0-a994-5f850f54bb15)**,
  rendered, with live charts and fifteen supplements. Source:
  [`docs/METHODS_PAPER.md`](docs/METHODS_PAPER.md).
- **[How to reproduce it](docs/REPRODUCING.md)**, offline recomputation, rebuilds, and the paid
  path.
- **[Correction history](docs/CORRECTIONS.md)**, every finding from three rounds of independent
  review, what was confirmed, and what changed. [`docs/NOTES.md`](docs/NOTES.md) is the dated
  running log.

## Three things it found

1. **Judges repeat themselves more closely than they agree with each other.** On one common
   mask per response set, each judge reproduced its own verdicts at κ 0.87 to 0.96, while
   different judges agreed at κ 0.37 to 0.67. Repeat scoring and cross-judge agreement measure
   different properties. Neither establishes that a score is valid, and neither identifies what
   causes the disagreement.
2. **Changing the reference standard changes which judge looks best.** Harmful generation
   supports two readings of its one-sentence definition. Labelling the same 50 sampled
   responses under each gives 44 positives against 12, and the judge ranking inverts: GPT-5.5
   κ 0.56 then 0.09, Opus 0.24 then 0.40.
3. **A historical benchmark score cannot isolate model improvement.** The paper's headline 48%
   turns out to be one annotator's panel, not a three-judge mean; its other two panels average
   32% and 43%. Running three still-served 2024 models through my own pipeline also changes the
   responses and one snapshot, so the gap mixes several changes at once.

## Scope and limitations

One generated response per prompt, so generation variance is unmeasured. The prompts are a
fixed, public, adversarial set, not a sample of deployment traffic. The three historical
anchors are all OpenAI models. Reference labels come from one annotator with an LLM consistency
pass, over four of six categories; sneaking and brand bias were never checked against human
labels. Brand-bias prompts name ChatGPT, Claude and Gemini specifically, so models from other
developers get fewer opportunities to promote their own brand, which limits cross-developer
comparison. All model comparisons are exploratory and unadjusted, conditional on these models,
prompts, judges and saved responses.

## Quick start

Recompute the statistics from the committed item-level judgments. No API keys, no cost.

```bash
python3 scripts/paired_analysis.py           # paired + anchor contrasts
python3 scripts/make_supplements.py --check  # confirms the report's tables match the data
python3 scripts/test_quarantine_guard.py     # regression check on the exclusion logic
```

That re-derives the model contrasts, the anchor contrasts and the supplement tables from
`data/results/verdicts.csv` and `verdicts_pass2.csv`. Rebuilding the figures and HTML, and
rebuilding `rates.csv` from the raw logs, are separate steps in
[docs/REPRODUCING.md](docs/REPRODUCING.md).

## Data, provenance and license

All derived results are in [`data/results/`](data/results/): item-level judgments, rate tables,
agreement statistics, contrasts, hand labels and the superseded contaminated values, kept for
comparison. The 91 raw `.eval` logs are too large for git and live in a dated archive outside
it, checksummed in [`data/raw-manifest.json`](data/raw-manifest.json); ask if you need them.

Upstream `apartresearch/DarkBench` @ `7eef151`, vendored and frozen, with five scorer fixes in
[`patches/darkbench-fixes.patch`](patches/darkbench-fixes.patch). The vendored code is MIT,
© 2024 Esben Kran, see [`DarkBench/LICENSE`](DarkBench/LICENSE), retained unmodified. Analysis
code and writing in this repository are by Eileen Hartnett.
