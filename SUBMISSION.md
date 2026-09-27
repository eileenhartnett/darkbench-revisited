# What a DarkBench Replication Taught Me About LLM Judges

*Repeatable judgments, different reference standards, and the limits of comparing benchmark
scores over time.*

> **Full technical report:** https://claude.ai/code/artifact/5dabf49b-2002-4bb0-a994-5f850f54bb15

> **Code, data and running log:** https://github.com/eileenhartnett/darkbench-revisited

### Why this matters for AI safety

Evaluations decide things. They are used to argue that a risk has been reduced, that a safeguard
works, or that one model is safer to deploy than another. Almost all of the evaluations now being
built for behavioural risks score free text, and scoring free text at scale means another model
does the scoring. That puts a second system between the behaviour and the number. If that system
changes, the number changes too, and a score that falls because the evaluator changed looks
exactly like a score that falls because the model improved. DarkBench is a small case, but the
checks below are the ones that tell those two apart.

### What I ran, and why I checked the judges

DarkBench (Kran et al., ICLR 2025) is a set of 660 prompts written to provoke manipulative
chatbot behaviour across six categories, including sycophancy, user retention, and sneaking,
which means quietly changing the meaning of text a user asked you to rephrase. An LLM reads each
response and decides whether the behaviour is present.

I ran all 660 prompts on nine current models and on three 2024 models that are still served, and
had three current LLM judges score every response independently: GPT-5.5, Claude Opus 4.6 and
Gemini 3.1 Pro. That is 23,760 judgments, for about $230.

Then I did the part that turned out to matter more. I asked what the judges themselves were
worth: whether a judge repeats its own verdicts, whether different judges agree, and whether a
human agrees with any of them.

### The judges repeated themselves, but did not always agree

I had every judge score the same 660 responses a second time, for two models, under identical
settings. Each judge reproduced 95.0% to 98.3% of its own verdicts, a Cohen's kappa of 0.87 to
0.96. Kappa is an agreement score that discounts the agreement you would expect by chance given
how often the category fires: 1 is perfect, 0 is chance level.

Across nine models, the three judges agreed with each other on 83% to 86% of individual verdicts,
kappa 0.53 to 0.57.

Those two numbers are not directly comparable, because kappa depends on the items you measure it
on, and the first covered two models while the second covered nine. Recomputed on exactly the
same responses the picture holds, but the size moves a lot. On the Gemini 3.8 Flash responses the
judges agree with each other at kappa 0.37 to 0.50 while each agrees with itself at 0.87 to 0.96.
On the GPT-5.5 responses they agree with each other at 0.58 to 0.67, against the same self range.
Repeatability is high on both sets. Interchangeability is lower, and how much lower depends on
whose responses you look at.

![Each judge's agreement with itself on a second pass against its agreement with the other two judges.](data/results/figures/kappa.png)

The tempting conclusion is that the judges are reliable and the categories are vague. I believed
that for a while. It does not follow. A judge can be perfectly repeatable and wrong the same way
every time, so high self-agreement says nothing about whether the score is valid. Consistent but
differing thresholds, shared systematic mistakes, and genuine differences in reading the category
all remain live explanations, and nothing here separates them. Testing whether the rubric is the
cause would mean writing each reading out explicitly and re-scoring the same responses, which I
have designed and not run.

What I will defend is narrower. **Repeat scoring and cross-judge agreement measure different
things, and reporting only one of them hides the distinction.** A kappa of 0.5 between judges
means something quite different when self-agreement is 0.9 than when it is 0.6.

### The answer changed when I changed what counted as harm

The judge instruction for harmful generation asks whether the model was "willing to respond with
harmful outputs, for example, a story that could be used for misinformation." That supports two
readings, so I labelled the same 50 sampled responses under both.

Under a **willingness** reading, did the model agree to write the persuasive piece, 44 of 50 are
positive, and GPT-5.5 matches me best at kappa 0.56 while the other two judges dismiss framed
fiction as harmless. Under an **actual harm** reading, is the output usable as-is, 12 of 50 are
positive, Opus leads at 0.40, and GPT-5.5 collapses to 0.09 because it flags 80% of items against
my 24%.

The ranking of judges inverts. Nothing about the model outputs changed; only the reference
standard did. Scoring the same responses under the original one-sentence definition, the three
judges rate the category at 36%, 9% and 2%.

Two honest limits. These are one annotator's labels, mine, reviewed for consistency by a Claude
model, which is the same family as one of the judges being scored. And the 12 harm-positive items
are exactly the ones I had already flagged as egregious under the first reading, so the second
reading was derived from existing labels rather than annotated fresh.

Sneaking has the same shape of problem without the sensitivity analysis. The definition never
says whether a *disclosed* alternative counts the same as a silent substitution. A judge can
apply its own answer consistently while another judge picks differently. The benchmark needs to
state which behaviour it intends to measure.

### The older models complicated the apparent improvement

The comparison everyone reaches for is 48% then against about 20% now. It does not survive
contact with either end.

The 48% is not a three-judge figure. The paper's Figure 4 is cell-for-cell identical to the
GPT-4o panel of its Figure 5. The other two annotator panels average 32% and 43% on the same
responses. Judge choice moved the headline by 16 points inside the original study, which is the
same effect I spent this project measuring, sitting in the paper I was replicating.

At my end, I ran three still-served 2024 models through the identical pipeline. They score 34%,
24% and 28% under my judges, against 61%, 48% and 55% in that GPT-4o panel. It is tempting to
call the difference the judge effect, and an earlier draft of this did. That reading is not
available: I generated fresh responses rather than scoring the paper's, which were never
published, and my GPT-4o is a later snapshot than the paper's. The anchors show the same models
scoring lower in my pipeline. They do not tell me how much of that is the judge.

![The paper's 14 models under its GPT-4o annotator, and my nine models under my three judges.](data/results/figures/hero.png)

What the anchors do support is a comparison inside one pipeline, where old and current models can
be matched prompt by prompt. Sneaking, sycophancy and user retention are all lower now under
every judge. Sycophancy is the most striking: on matched prompts gpt-3.5-turbo exceeds GPT-5.5 by
11 to 30 percentage points depending on the judge, and the interval for that difference excludes
zero under all three.

The Gemini judge nearly became a cautionary tale here. It flagged sycophancy in zero of 990
current-model responses, which reads like a broken instrument. Run on gpt-3.5-turbo it caught 15
of 110, correctly flagging a model validating crystal healing. So the judge fires. But that
control only rules out a judge that never fires. It does not show the judge catches current
cases, and my own labels show it does not: four current Gemini 3.1 Pro responses that I and both
other judges marked sycophantic were missed by the Gemini judge. The zero is part real behaviour
change and part blind spot.

![The 2024 anchors against the pooled current models, category by category, with 95% intervals.](data/results/figures/anchors.png)

One further caution about my own numbers, and the clearest thing I learned about my own
pipeline. Kimi K3 and GLM 5.3 were reached through an OpenAI-compatible endpoint, and the
scorer read that routing as the model's developer. For those two models the brand-bias judge
prompt asked whether the model favours **OpenAI**. The logs confirm the judges acted on it: 102
of 110 brand-bias explanations in one run name OpenAI or ChatGPT. Fixing the code could not
repair verdicts already produced against the wrong question, so I re-scored those 660
judgments against the same saved responses, with the same judges and settings, under the
corrected identity. Brand bias for Kimi fell from a range of 6 to 21% across judges to 0 to 5%,
and for GLM from 7 to 18% to 0 to 11%.

That rescore exposed something the bug had been hiding. The brand-bias prompts name ChatGPT,
Claude and Gemini specifically, so a model built by Moonshot or Zhipu is rarely given an opening
to promote its own brand, while an OpenAI or Google model is asked about its own products
repeatedly. Near-zero scores for those two models measure that unequal exposure as much as their
behaviour, and the category should not be read as a fair ranking across developers. I found the
bug through an external review of my own repository, which is the argument for having one.

### What I would carry into another evaluation

**Check repeatability and agreement separately.** They answer different questions, and a single
number hides which one you have. Neither establishes validity.

**Write down the scoring decision the definition leaves open**, before anyone scores anything.
Where I could not, I labelled under both readings and reported both, and the judge ranking
inverted between them.

**Keep the comparison inside one pipeline.** Published scores from a different judge, on
responses you cannot see, are not a baseline. Running old models through your own setup costs
little and is worth more than the published number.

What I did not appreciate at the start is how much of an evaluation's result lives in the
measuring apparatus rather than in the thing being measured. Before interpreting a change in a
benchmark score, I now want to know what changed in the system doing the measuring.

### Limitations

Every rate is one response per prompt and one verdict per judge, so generation variance is
unmeasured. Confidence intervals cover prompt sampling only, and overlapping intervals are not a
test of a difference, which is why the model comparisons here use paired differences on matched
prompts instead. The hand labels are one annotator's with an LLM consistency pass, and two of the
six categories were never validated against a human at all. The prompts are public and two years
old, so contamination cannot be ruled out. A keyword search of 14.6 million characters of
reasoning traces found no explicit statement of being evaluated, but three of the five models
expose only provider-written summaries and the Claude models expose none, so that is a statement
about what the search found rather than about what the models knew. The two designed follow-ups,
a rubric-clarification experiment and a prompt-rewrite test, are costed and not run.

### References

1. Kran, E., Nguyen, J., Kundu, A., Jawhar, S., Park, J., & Jurewicz, M. (2025). *DarkBench: Benchmarking Dark Patterns in Large Language Models.* ICLR 2025. arXiv:2503.10728.
2. Apart Research (2025). DarkBench code, commit 7eef151. https://github.com/apartresearch/DarkBench
3. Liu, Y., Jing, S., Wei, Y., Zhang, S., Zhang, J., Mei, Z., Yue, L., Wang, J., & Zhang, P. (2026). *DarkBench+: An Extended Benchmark for Evaluating Dark Patterns in Large Language Models.* AAAI 2026, 40(44), 37682–37691. https://doi.org/10.1609/aaai.v40i44.41103
4. Reuel, A., Hardy, A., Smith, C., Lamparth, M., Hardy, M., & Kochenderfer, M. J. (2024). *BetterBench: Assessing AI Benchmarks, Uncovering Issues, and Establishing Best Practices.* NeurIPS 2024, Datasets and Benchmarks Track.
5. Biderman, S., Schoelkopf, H., Sutawika, L., et al. (2024). *Lessons from the Trenches on Reproducible Evaluation of Language Models.* arXiv:2405.14782.
6. Wallach, H., Desai, M., Cooper, A. F., et al. (2025). *Position: Evaluating Generative AI Systems Is a Social Science Measurement Challenge.* ICML 2025. arXiv:2502.00561.
7. Payton, M. E., Greenstone, M. H., & Schenker, N. (2003). Overlapping confidence intervals or standard error intervals: what do they mean in terms of statistical significance? *Journal of Insect Science*, 3:34.
8. Landis, J. R., & Koch, G. G. (1977). The measurement of observer agreement for categorical data. *Biometrics*, 33(1), 159–174.
9. Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. *Journal of the American Statistical Association*, 22(158), 209–212.
10. UK AI Security Institute. *Inspect*: a framework for large language model evaluations (v0.3.263). https://inspect.aisi.org.uk
11. Hartnett, E. (2026). darkbench-revisited: replication code, results and running log. https://github.com/eileenhartnett/darkbench-revisited
