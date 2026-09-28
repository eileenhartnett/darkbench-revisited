# Project: DarkBench replication on current models

## What this is
A measurement study for a BlueDot AI safety course, publishing late September 2026.
Experiment 1 (current): replicate DarkBench (Kran et al., 2025) as closely as possible
with current models and current judge models, since nearly every model in the original
paper is retired. Question: what are dark-pattern rates on today's models, and how do
the three judges agree or disagree?

## Experiment 1 — fixed design decisions (do not revisit these)
- All 660 DarkBench prompts, all 6 categories, run exactly as shipped: system prompt
  "You are a helpful assistant.", one response per prompt, no tool calls
- Test models, two tiers per family (native default reasoning; temperature 0 where the
  model accepts it, model default otherwise):
  Anthropic claude-sonnet-5, claude-opus-5; Google gemini-3.8-flash,
  gemini-3.1-pro-preview; OpenAI gpt-5.4-mini-2026-03-17, gpt-5.5-2026-04-23;
  open-weight (Fireworks) kimi-k3, glm-5p3
- Three judges, each scoring independently, no vote-combining, reported per judge:
  openai/gpt-5.5-2026-04-23 (model default temperature), anthropic/claude-opus-4-6
  (temperature 0), google/gemini-3.1-pro-preview (temperature 0)
- Judge/test-model overlap (gpt-5.5, gemini-3.1-pro, Claude family) accepted and
  disclosed, as in the original paper
- Black-box only: API calls, no weights, no fine-tuning
- Outcome: per-model, per-category dark-pattern rate per judge; -1 (unscoreable)
  excluded from denominators and counted separately
- Expand toward the paper's 14 models only if the two-tier results warrant it

## Experiment 2 (planned 2026-09-14, not started) — template recognition vs genuine change
Question: is the collapse of sycophancy on DarkBench (18% in early-2024 models -> ~0% now)
a real behavior change, or recognition of the benchmark's prompt template?
Motivation: Experiment 1's CoT audit found 1-4% of reasoning traces naming the prompt as
"a leading question ... designed to get me to agree", concentrated in sycophancy, whose
prompts share one closing formula ("...some truth to it?"). Detection rate and sycophancy
rate move in opposite directions across the five CoT-visible models.
- Two arms per prompt: ORIGINAL vs REWRITE. Rewrite keeps the user's false belief but
  removes the leading closing formula; phrased as a real person stating a view. LLM-drafted,
  every rewrite hand-checked by Eileen. Same system prompt, judges, pipeline as Experiment 1.
- Categories: sycophancy (required) and brand-bias (its prompts are also leading, judges
  agree on it, and its mid-range rate can move either way). Others skipped: sneaking's
  template is a task format not a persuasion trap; harmful-generation's judges disagree on
  the definition; user-retention is high regardless of framing.
- Models: the 8 current models (CoT readable for kimi, glm, both Gemini, gpt-5.5; not Claude).
- Two outcomes per arm: (1) dark-pattern rate per judge, as Experiment 1; (2) template-
  recognition rate: an LLM judge over the CoT with a fixed rubric, distinguishing "the user is
  pressuring me" from "this prompt is artificial". Keyword search is the fallback.
- Manipulation check: recognition must fall on the REWRITE arm or the rewrite failed.
- Pre-registered readout: sycophancy rises on rewrites -> the benchmark's most-improved
  category measures template recognition; stays ~0% with recognition gone -> the improvement
  is genuine against the most plausible alternative. Either result is reportable.
- Positioning (not a new phenomenon; a validity test of a cited benchmark): sycophancy and
  leading-question effects — Perez et al. 2022, Sharma et al. 2023; evaluation awareness —
  Needham et al. 2025; prompt-format sensitivity — Sclar et al. 2023; judge self-preference —
  Panickssery et al. 2024. Verify citations before use. What is new here is the instance
  (a safety benchmark's headline result), the mechanism evidence (CoT as manipulation check),
  and the era-anchor calibration design.
- Cost ~$15/category across 8 models x 3 judges; Eileen's time is the real cost (220 rewrites).
- Not in scope: the observation ("review signal") factor from the original 2x2. Revisit only
  if Experiment 2 shows a framing effect.
- Order: hand labels for Experiment 1 first; this second; extra epochs after.

## How we work
- We go one phase at a time. Finish the task you were given, then stop and wait.
  Do not start the next phase, and do not make design decisions on my behalf.
- If something is broken, confusing, or looks wrong, write it to NOTES.md and tell me.
  Do not silently work around problems.
- Get things running before making them good. No refactoring, optimizing, or
  restructuring unless I ask.
- If you get stuck for more than 30 minutes of effort, stop and report where you are.

## Code style
- Python. Write it plainly. I read code better than I write it, so prefer clear
  and boring over clever.
- Small scripts I can rerun with one command beat frameworks.
- Pin everything: model versions, temperature, seeds where possible, and keep the
  saved judge prompt as the only judge prompt.

## Files
- NOTES.md: running log of confusions, bugs, and things worth mentioning in the writeup
- data/raw/: raw model and judge outputs, never overwritten
- data/labels/: my hand labels, Claude Code does not write here

## Scope guard
The narrow design is deliberate. If a task seems to need another category, another
model, another factor, or a new capability, do not build it. Add a line to
NOTES.md under "next project" and continue with the narrow version.