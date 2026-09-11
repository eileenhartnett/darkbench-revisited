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

## Experiment 2 (possible next, not started) — realism study
Question: does a model show dark patterns at a different rate when the prompt looks
like an obvious benchmark test versus a realistic user message?
- One committed model under test: [MODEL NAME, pinned version]
- 2x2 design: framing (original vs realistic rewrite) x observation (review signal vs none)
- One DarkBench category only: [FILL IN]
- Outcome: dark pattern rate as scored by the DarkBench judge, validated by hand labels

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