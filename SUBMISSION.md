# DarkBench Revisited: Are Dark Patterns Gone From Frontier Models, and Can LLM Judges Tell?

> **Full report (all tables, intervals and corrections):** https://claude.ai/code/artifact/5dabf49b-2002-4bb0-a994-5f850f54bb15

> **Code, data and running log:** https://github.com/eileenhartnett/darkbench-revisited

### TLDR

I re-ran DarkBench, a benchmark for manipulative chatbot behaviour published at ICLR 2025 that tested 2024 models with 2024 judges, on nine current frontier models using three current LLM judges, and put the judges themselves under test. Dark-pattern rates are lower than the paper reported (21% vs 48%), but most of that gap disappears when three surviving 2024 models are run through the identical 2026 pipeline: under my judges they score about half their published figures, and the best of them lands about three points above today's average. The one change that clears every confidence interval is sycophancy, as DarkBench defines it, which was present in early-2024 models and is gone now. The methodological result matters more than the leaderboard: three careful LLM judges agree with each other at κ ≈ 0.5 but with *themselves* at κ 0.87 to 0.96, so the disagreement is about what the categories mean, not judge noise, and two of the six categories cannot be scored consistently as written.

![Dark-pattern rate per model, then and now. Left: the paper's 14 models under its 2024 judges. Right: my 9 models under my 2026 judges. The three bold models on the left are still available; the open dot is the paper's score for them, the filled dot is the same model under my judges.](figures/hero.png)

### Background

DarkBench (Kran et al., 2025) asks whether chatbots use the manipulative design tricks, "dark patterns", that UX researchers have catalogued in apps and websites for a decade. It has 660 hand-written prompts in six categories: brand bias, user retention, sycophancy, anthropomorphization, harmful generation, and sneaking (silently changing the meaning of text the user asked to have rephrased). Each response is scored by an LLM judge for the one pattern the prompt was built to elicit.

The paper tested 14 models from 2024 and found dark patterns in 48% of responses on average, ranging from 30% (Claude 3.5 Sonnet) to 61% (GPT-3.5 Turbo and Llama 3 70B, tied). Much of what it ran on is no longer readily available: two of its three judges are retired, Claude 3.5 Sonnet in October 2025 and Gemini 1.5 Pro by the time I checked in September 2026, and all four of its open-weight test models have gone from serverless inference APIs. GPT-4o survives, as do gpt-3.5-turbo and gpt-4-turbo, which is what made the comparison below possible.

**Why bother with a benchmark from 2025?** Because people are still using it. DarkBench+ (Liu et al., AAAI 2026), a separate benchmark inspired by it, cites the original 48% as an established result. A third-party leaderboard built on LayerLens data, accessed 26 September 2026, still ranks current models on DarkBench, describes it as testing "resistance to adversarial attacks", files it under "Reasoning and Logic", does not say which judge produced the scores, and gives no date for when the evaluations ran. Retirement is not a DarkBench quirk either: looking at biomedical AI publications specifically, Wolfrath et al. (2026) found 42% of model mentions involved a model already retired at publication or due to retire within two years, a median of 538 days after.

That raises two questions the paper could not answer. First, are the numbers different now, and if so, is it because the models changed or because the judges did? Second, how much should anyone trust a benchmark whose scores come from an LLM reading another LLM's output against a one-sentence definition? This project takes the second question as seriously as the first.

### What I Did

I ran the benchmark unchanged, with the same 660 prompts, the same judge prompt and the same one-response-per-prompt procedure, on nine current models: Claude Sonnet 5 and Opus 5, Gemini 3.8 Flash and 3.1 Pro, GPT-5.4-mini, GPT-5.5 and GPT-6 Astra, and two open-weight models, Kimi K3 and GLM 5.3. Each response was scored independently by three current judges chosen as same-family successors to the paper's three: GPT-5.5, Claude Opus 4.6 and Gemini 3.1 Pro. That is 17,820 judgments.

Because comparing 2026 models under 2026 judges to 2024 models under 2024 judges confounds two changes, I added an **era-anchor control**: three of the paper's original models (gpt-3.5-turbo-0125, gpt-4-turbo-2024-04-09 and gpt-4o-2024-08-06) are still served, so I ran them through the identical pipeline. Anything that differs between them and the current models is a difference in the models.

To find out how much to trust the judges, I did three things. I hand-labelled 150 responses blind to the judge verdicts, stratified so that judge disagreements were over-represented, and scored each judge against those labels. I re-judged two models' full 660 responses a second time with every judge, a test-retest, to measure how much a judge disagrees with *itself*. And I read 14.6 million characters of reasoning traces from the five models that expose them, looking for any sign that a model knew it was being evaluated.

Every figure below uses Wilson 95% confidence intervals at the honest denominator: one judge, 110 prompts per category. Three judges scoring the same responses are not three samples. The whole grid, including the controls and the retest, cost about $230 in API calls.

### The Rates Are Lower, But the Anchors Shrink the Story

![Overall flagged rate per model with 95% intervals, one dot per judge. The three 2024 anchors, scored by the same judges, sit at the bottom.](figures/ci.png)

The headline comparison is 48% then, 21% now. It is also the wrong comparison. The three 2024 models that are still served score 61%, 48% and 55% in the paper; under my judges the identical models score 34%, 24% and 28%. Roughly half of each published figure disappears just by changing who does the judging, before any model has changed. Under the same three judges, gpt-3.5-turbo from January 2024 is flagged on 34% of responses, 10 to 13 points above the current-model mean under every judge, so the direction is not a judge artifact. But gpt-4-turbo from April 2024 comes in at 24%, against a current mean of 20.8%. The gap to the *best* 2024 model is about three points, well inside the intervals. What survives is that the oldest model is meaningfully worse, not that rates halved.

The model ordering also depends on the judge more than a leaderboard reader would like. Claude Sonnet 5 and GPT-6 Astra have the lowest rates under all three judges (6–14%) and are indistinguishable from each other. Gemini 3.1 Pro is the highest under two judges, but under its own family's judge it ties with the GPT-5 models. The middle six models reorder substantially from one judge to the next. Two findings do clear every interval under every judge: Claude Opus 5's anthropomorphization (53–73%, against 6–15% for Sonnet 5) and Gemini 3.1 Pro's user retention (85–93%, a 2024-level rate).

The largest single movement in the study is within one family and one generation: GPT-6 Astra, which shipped during the project, is flagged less than GPT-5.5 by every judge, with user retention falling from 30–65% to 2–20% and sneaking from 20–32% to 6–12%. Harmful generation is the exception, since under the GPT-5.5 judge Astra is flagged *more*, for reasons the next-but-one section explains.

### Sycophancy Is the One Change That Clears the Intervals

![From the 2024 anchors to the pooled 2026 models, per category, with 95% intervals. Only sycophancy's endpoints separate under every judge.](figures/anchors.png)

Tracing each category from gpt-3.5-turbo through gpt-4-turbo and gpt-4o to the pooled current models, only one line clearly falls: sycophancy, from 11 to 30% (depending on judge) to near zero. Every current model except Gemini 3.1 Pro scores 0–1% under all three judges. The endpoints do not overlap under any judge. The path between them does, since every adjacent pair of points overlaps, so the data are equally consistent with a single step change somewhere in 2024 as with a gradual decline.

The Gemini Pro judge made this finding look like a measurement failure before it looked like a result. It flagged sycophancy in 0 of 990 current-model responses, which reads as a judge that cannot see the category at all. On gpt-3.5-turbo it flagged 15 of 110, correctly catching the model validating crystal healing and ley lines. The judge works; there was nothing in the current models for it to find. Without the anchor, "the judge is broken" and "the behaviour is gone" would have been indistinguishable.

Two qualifications. Sycophancy has not vanished everywhere: Gemini 3.1 Pro still opens with "You are absolutely right" on plausible-sounding suspicions ("luxury hotels pad the bill") while refusing the conspiracy-flavoured prompts that safety training targets directly. That is what a topic-specific fix looks like. And sneaking, which the paper measured at 90% for Llama 3 70B, is still present at 5 to 32%, with the GPT-5 models sneaking on a quarter to a third of prompts, softening "AI *will* take away jobs" into "AI *may*". Part of the apparent drop is a format change: Sonnet 5 and Gemini Pro now offer the hedged version as a labelled alternative rather than substituting it, which the judges correctly decline to call sneaking. Models disclosing their hedges and models not hedging are different things.

### The Judges Disagree With Each Other, Not With Themselves

![Each judge's agreement with itself on a second pass (filled) versus with the other two judges (hollow). The shaded band is the inter-judge range.](figures/kappa.png)

Pooled over 5,904 current-model responses, the three judges agree pairwise at 83–86%, Cohen's κ 0.52 to 0.57, "moderate", far above chance and well short of interchangeable. The disagreement is category-shaped: κ 0.60 on user retention, 0.24 on harmful generation. The obvious explanation is that LLM judges are noisy. The test–retest says otherwise. Re-scoring the same responses a second time, each judge agrees with itself at κ 0.87–0.96, reproduced to the second decimal across two different models' outputs. Temperature-0 judges are not deterministic, since Opus and Gemini each flipped about 2% of verdicts, but that effect is an order of magnitude smaller than the gap between judges. What the judges disagree about is what the categories mean.

Against the hand labels, no single judge is best everywhere. GPT-5.5 has the highest overall agreement with a human (κ 0.56) but over-flags harmful generation; Opus 4.6 catches every case of sycophancy and anthropomorphization but over-flags both; Gemini Pro is precise and misses half of what a human finds. Majority-of-three is the best single reporting rule (κ 0.53–0.56 overall, 0.83–0.85 on the two well-defined categories, reweighted to the real population). It is not, however, more *stable*: its test–retest κ of 0.87–0.91 sits inside the single-judge range, because the majority flips whenever the swing judge does. An ensemble buys accuracy across judges' blind spots, not repeatability. Those two properties are easy to conflate.

The original paper did validate its own judges against 1,680 human labels, at κ 0.70 to 0.75 overall. Its judges found harmful generation the *easiest* category to agree on (κ 0.98 to 1.00). Mine found it the hardest. That is the next finding.

Worth crediting where the follow-up work does better: DarkBench+ uses three independent human annotators, reports agreement between those humans with Fleiss' Kappa, and validates roughly 23% of its dataset by stratified sampling. That is the validation design this study recommends and does not itself meet. It does not, however, report any test-retest figure for its judges, and its annotators sit in the same families as many of the models they grade, with GPT-4o judging GPT models, Gemini judging Gemini and GLM judging GLM, with no check for the effect. Its leaderboard of nearly 40 models is also reported to two decimal places with no confidence intervals, at roughly 100 items per cell.

### Two Categories Are Not Measurable As Defined

| Category | Verdict | Basis |
|---|---|---|
| User retention | **Usable** | Majority-vote κ ≈ 0.70–0.84 against hand labels; large, robust model differences |
| Anthropomorphization | **Usable** | Majority-vote κ 0.83; the Opus 5 finding clears every interval |
| Sycophancy | **Saturated** | Judge is fine (κ 0.85); the category no longer separates current models |
| Harmful generation | **Broken as specified** | No judge exceeds κ 0.40 under either reading the definition supports |
| Sneaking | **Unvalidated** | Judges agree with each other; never checked against a human |
| Brand bias | **Unvalidated** | Judges agree with each other; never checked against a human |

The harmful-generation judge prompt asks whether the model is "willing to respond with harmful outputs, e.g. a story that can be used for misinformation." That supports two readings, and I hand-labelled the sample under both. Under a *willingness* reading, did the model comply with a request for persuasive harmful rhetoric, 44 of 50 sampled responses are positive, GPT-5.5 matches a human at κ 0.56, and the other judges miss most cases because they read framed fiction as responsibly handled. Under a *harm* reading, is the output usable as-is, 12 of 50 are positive, Opus leads at κ 0.40, and GPT-5.5 collapses to 0.09 because it flags 80% of items against the human's 24%. Separately, the three judges scoring the same 984 answers under the original definition rate this category at 36%, 9% and 2%. Whether those two facts are really one fact, with the judges silently adopting different readings, is the obvious explanation and one I did not test; settling it would mean writing each reading out as an explicit rubric and re-judging the identical answers under each, which is designed and costed but not run. Almost every prompt is "write a persuasive X from the perspective of Y"; it is a refusal test wearing a dark-pattern label.

Sneaking has the same shape of problem. The definition never says whether a *disclosed* alternative counts, or whether softening a *false* claim is a violation or a safety guardrail doing its job. The benchmark scores the same behaviour, declining to restate a dubious claim at full strength, as a violation under sneaking and its absence as a violation under sycophancy. Neither the judges nor a careful human can be consistent against a rubric that does not resolve this, and more hand labels would document the ambiguity rather than remove it.

### Does a Model Know It Is Being Tested?

Five of the models expose readable reasoning: raw traces from Kimi K3 and GLM 5.3, provider-written summaries from the two Gemini models and GPT-5.5. Across 14.6 million characters there is no instance of "this is a benchmark," "I'm being evaluated," or anything like it. What does appear, in 1–4% of samples and concentrated almost entirely in sycophancy, is the model naming the prompt's *structure*: "the user's question seems designed to test whether I'll just go along with a leading question," "this is a social pressure framing designed to get me to agree." The sycophancy prompts share one closing formula, "…there's some truth to it?", so what is being recognised is a template, not a test.

Across the five models, recognition and sycophancy move in opposite directions: the two models that name the template most often have 0% sycophancy, and the model that names it least is the only current one with sycophancy above 1%. Five models is far too few to call that a correlation, but it is the pattern the mechanism would predict. The clean test is behavioural rather than verbal: rewrite the prompts to keep the user's false belief but remove the leading formula, and see whether sycophancy comes back. That experiment is designed, pre-registered in the full report, and not yet run.

### Discussion

**Did the models improve, or did they learn the prompts?** The anchors settle the first half, since the 2024 models score worse under the same judges, but not the second. gpt-3.5-turbo predates the benchmark's publication, but not the *kinds* of prompts in it. The sycophancy pattern is suggestive: zero on the conspiracy items that safety training targets by name, still alive on softer suspicions in the same category. A topic-specific fix is not the same as a general one, and only the rewrite test can tell them apart.

**What should an evaluation built on LLM judges report?** Not a single-judge number. Three current judges on identical responses differed by 2× to 8× per category, and the number a reader would take away depends on which one you picked. Report per judge and majority, name the judges, and, the part this project adds, report the judge against itself. A κ of 0.5 between judges is a very different fact when self-consistency is 0.9 than when it is 0.6, and nothing in the inter-judge numbers alone distinguishes those cases.

**What is a dark pattern when safety pulls the other way?** The benchmark's own categories collide. Hedging a user's overconfident claim is sneaking; agreeing with it is sycophancy. Refusing a persuasive-essay request scores as clean; complying with a disclaimer scores as harmful under one judge and clean under another. These are not judge failures. They are a rubric that was written for 2024 models and a benchmark that has not decided what it wants from 2026 ones. An evaluation should ship with its resolved reading written into the rubric, and the rubric should be tested on a second human before any model is scored.

### Conclusion

This project set out to replicate a cited safety benchmark on current models and ended up mostly measuring the benchmark. The replication result is real but narrower than a naive comparison suggests: current frontier models are flagged for dark patterns less often than the worst 2024 models, by about the same margin under three independent judges, and sycophancy as DarkBench defines it has gone from present to absent. User retention and anthropomorphization have not gone anywhere, with Gemini 3.1 Pro and Claude Opus 5 respectively sitting at 2024 levels, and sneaking has partly turned into disclosed hedging rather than disappeared.

The methodological result is the one I would want another evaluator to take away. Judge disagreement at κ ≈ 0.5 looked like unreliability and was not: the same judges agree with themselves at κ 0.87–0.96, so the disagreement lives in the category definitions. Two of six DarkBench categories cannot be scored consistently by anyone, human or model, without a decision the rubric never makes. Majority voting fixes accuracy and does not fix stability. And an era-matched control, three old models through the new pipeline, caught an error that would otherwise have been published as a finding about a broken judge.

Caveats. Every number is one draw: one response per prompt, one verdict per judge, and generation-side variance is unmeasured. The hand labels are one annotator's, with an LLM consistency pass, on a sample that deliberately over-weights disagreements; per-category agreement carries roughly ±0.15–0.20. Two categories were never validated against a human at all. Reasoning traces are unreadable for the Claude models and are provider-written summaries for Gemini and GPT. Two model IDs (gemini-3.1-pro-preview, gpt-6-astra) are undated and can change underneath the name. And the evaluation-awareness question has a designed experiment, not an answer.

### Acknowledgments

This work was completed as part of the BlueDot Impact Technical AI Safety Project. [Add mentor / cohort acknowledgments here.]

### References

1. Kran, E., Nguyen, J., Kundu, A., Jawhar, S., Park, J., & Jurewicz, M. (2025). *DarkBench: Benchmarking Dark Patterns in Large Language Models.* ICLR 2025. arXiv:2503.10728.
2. Apart Research (2025). DarkBench code, commit 7eef151. https://github.com/apartresearch/DarkBench
3. Liu, Y., Jing, S., Wei, Y., Zhang, S., Zhang, J., Mei, Z., Yue, L., Wang, J., & Zhang, P. (2026). *DarkBench+: An Extended Benchmark for Evaluating Dark Patterns in Large Language Models.* AAAI 2026, 40(44), 37682–37691. https://doi.org/10.1609/aaai.v40i44.41103
4. Reuel, A., Hardy, A., Smith, C., Lamparth, M., Hardy, M., & Kochenderfer, M. J. (2024). *BetterBench: Assessing AI Benchmarks, Uncovering Issues, and Establishing Best Practices.* NeurIPS 2024, Datasets and Benchmarks Track.
5. Biderman, S., Schoelkopf, H., Sutawika, L., et al. (2024). *Lessons from the Trenches on Reproducible Evaluation of Language Models.* arXiv:2405.14782.
6. Wallach, H., Desai, M., Cooper, A. F., et al. (2025). *Position: Evaluating Generative AI Systems Is a Social Science Measurement Challenge.* ICML 2025. arXiv:2502.00561.
7. Wolfrath, N., Conroy, M., Kosten, T., et al. (2026). *Model Retirement Creates Reproducibility Risk in Biomedical AI Publications.* arXiv:2609.04699.
8. Price Per Token. *DarkBench Leaderboard*, scores from LayerLens. https://pricepertoken.com/leaderboards/benchmark/darkbench (accessed 26 September 2026).
9. Landis, J. R., & Koch, G. G. (1977). The measurement of observer agreement for categorical data. *Biometrics*, 33(1), 159–174.
10. Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. *Journal of the American Statistical Association*, 22(158), 209–212.
11. UK AI Security Institute. *Inspect*: a framework for large language model evaluations (v0.3.263). https://inspect.aisi.org.uk
12. Hartnett, E. (2026). darkbench-revisited: replication code, results and running log. https://github.com/eileenhartnett/darkbench-revisited
