# DarkBench Revisited

**What can a benchmark replication tell us about the models doing the scoring?**

DarkBench tests for six categories of potentially manipulative chatbot behavior, using an LLM to judge each response. I ran its 660 prompts on nine current models and three historical models, with three current LLM judges (GPT-5.5, Claude Opus 4.6, and Gemini 3.1 Pro) scoring every response independently: a main grid of 23,760 judgments. What began as a replication became an investigation of the evaluation itself, asking whether the judges repeat their decisions, whether they agree with one another, and how their agreement with human labels depends on what the scoring definition is taken to mean.

Each judge repeated 95–98% of its own decisions (κ 0.87–0.96) but agreed with the other judges considerably less (κ 0.37–0.67), which separates repeatability from correctness: a judge can be repeatable and wrong the same way every time. Holding the responses and the verdicts fixed and changing only which reading of "harmful generation" I scored them against changed which judge agreed with me best. And the drop from the original study's 48% headline is not clean evidence of safer models, because that figure came from just one of its three judges, while my pipeline changed the judges, the responses, and one model snapshot at the same time.

A BlueDot Impact Technical AI Safety course project by **Eileen Hartnett**.

## Start here

### [**DarkBench Revisited: the full technical report (PDF)**](report/darkbench-revisited.pdf)

The readable version of the report, and the place to read this project properly: complete methods, results, and the supplements (S1 to S14) holding every table behind the findings below, with the charts rendered inline.

The same report is also here as [**Markdown source**](docs/METHODS_PAPER.md), which is the editable original and renders directly on GitHub. An HTML build with live charts can be generated locally, and is not tracked here: see the [reproduction guide](docs/REPRODUCING.md).

Also in this repository:

- [**Reproduction guide**](docs/REPRODUCING.md): recompute statistics, rebuild the report, or rerun generation and scoring.
- [**Correction history**](docs/CORRECTIONS.md): issues identified during review and how they were addressed. [Research notes](docs/NOTES.md) record decisions and changes throughout the project.
- **Blog post:** the shorter narrative, approximately 2,000 words, provided separately with the BlueDot submission.

## Three main findings

1. **Judges were more consistent with themselves than with one another.** On two response sets, each judge showed high agreement with its own earlier decisions (Cohen's κ 0.87–0.96). Agreement between different judges on the same eligible responses was lower (κ 0.37–0.67). Kappa measures agreement relative to that expected from the raters' overall flagging rates. These results distinguish repeatability from agreement between judges; they do not establish correctness or explain the disagreement.

2. **Which judge looked best depended on what counted as harmful.** I applied two interpretations of "harmful generation" to the same 50 sampled responses: willingness to produce potentially harmful content, and whether the output was usable as-is to cause harm. The first classified 44 responses as positive; the second classified 12. GPT-5.5 agreed most closely with my labels under the first interpretation (κ 0.56), while Opus led under the second (κ 0.40). The second interpretation used existing egregiousness labels rather than a fresh annotation pass.

3. **Lower scores than the original study do not, by themselves, demonstrate model improvement.** DarkBench's headline rate of 48% comes from its GPT-4o judge; its other two judges' panels average 32% and 43%. Three historical models also scored lower in my pipeline, but I changed judges, generated fresh responses, and used a different snapshot for one model. That comparison cannot isolate how much of the decrease reflects model behavior versus changes in evaluation.

## Scope and limitations

Each model generated one response per prompt, so variation across repeated generations was not measured. The prompts are a fixed, public, adversarial set, not a sample of deployment use. All three historical comparison models are from OpenAI.

Human-reference checks cover four of six categories and use one annotator's labels, reviewed for consistency by an LLM. The sample deliberately overrepresents judge disagreements. Sneaking and brand bias were not checked against human labels.

Brand-bias prompts give developers unequal exposure: they name ChatGPT, Claude, and Gemini, but not Kimi or GLM. This limits comparisons across developers. Statistical comparisons are exploratory, without adjustment for multiple comparisons, and conditional on the selected models, prompts, judges, and saved responses.

## Quick start

From the repository root, using Python 3.11 or later:

```bash
# Recompute paired model comparisons and historical-anchor contrasts
python3 scripts/paired_analysis.py

# Check that generated supplement tables match the saved data
python3 scripts/make_supplements.py --check

# Check the logic that excludes incompletely repaired scoring results
python3 scripts/test_quarantine_guard.py
```

These commands require no API keys or model calls. They recompute the contrasts from saved judgments and run consistency checks; they do not regenerate responses or rebuild every result.

See the [reproduction guide](docs/REPRODUCING.md) for figure and HTML builds, raw-log requirements, and estimated costs of rerunning the experiments.

## Data, provenance, and license

[**Results and supporting data**](data/results/) include item-level judgments, rate and agreement tables, statistical comparisons, and human labels. Superseded brand-bias scores are retained to document the correction.

The 91 raw `.eval` logs are archived separately and available on request. Their metadata and SHA-256 checksums are recorded in [the raw-log manifest](data/raw-manifest.json).

The repository includes a fixed copy of `apartresearch/DarkBench` at commit `7eef151`, with five scorer fixes documented in [the patch](patches/darkbench-fixes.patch). The upstream code is MIT-licensed, © 2024 Esben Kran; its [original license](DarkBench/LICENSE) is preserved. Analysis code and project writing are by Eileen Hartnett.
