# What a Benchmark Replication Reveals About LLM Evaluation

**Lessons on judge reliability, measurement validity, and evaluating model behavior**

Eileen Hartnett, BlueDot Technical AI Safety Project, 2026. Draft of 2026-09-23.

**Abstract.** I re-ran DarkBench, a benchmark published at ICLR 2025 that uses 660 prompts to try to get a chatbot to manipulate the user, on nine of today's models and three models from 2024, using three of today's AI models as judges. The original tested models from 2024 and scored them with judges from 2024. The rate of bad behavior I found is lower than what the original paper reported (21% versus 48%), but most of that drop comes from using different judges, not from the models actually being better: when the same three 2024 models are judged by my judges instead of the paper's, their scores drop by about half. The one change that holds up under every check is sycophancy (telling users what they want to hear): it was common in early-2024 models and is now nearly gone, at least on the kinds of prompts this benchmark uses. Along the way I measured some things most benchmark papers skip. How often does a judge agree with itself if you ask it to grade the same answer twice? Almost always (agreement score of 0.87 to 0.96 out of 1). How often do three different judges agree with each other? Much less (0.52 to 0.57). Does a human agree with any of them? Sometimes, and it depends heavily on the category. None of this is a knock on DarkBench. It was an early, careful attempt to measure something that matters, and its authors checked their judges against human ratings, which most papers at the time did not bother to do. It's also part of why I was able to write this paper at all: DarkBench published its prompts, its code, and its judge definitions in enough detail to actually re-run, which most benchmarks from 2024 did not, and that's precisely what let me use it as a worked example rather than write about it from a distance. What's changed since then is that the field has gotten better at spotting the things that can quietly throw off a judged score. This paper turns my replication into eight lessons about those pitfalls, and what to do about each one. The DarkBench numbers are the example used to teach each lesson, not the point of the paper. None of the individual lessons is new. Each one is already established somewhere in the literature on how to evaluate AI systems. What this paper adds is working through all of them on a single benchmark that people are still citing and still running, and attaching real numbers to what each one turns up when you actually check.

**How to read this.** Each lesson has four parts: what the idea is, what happened when I ran into it here, what to watch for in your own work, and what I actually did (and didn't do) about it. There's a checklist near the end that's meant to be printed out and used. Numbers in the text have a bracketed pointer, like [W 4.1], showing where in the full writeup, a supplement table, or a data file that number comes from, so you can check it yourself. Appendix A has the full methods; Appendix B has every table.

> **The one thing to remember.** Before you trust an evaluation that uses an AI model as a judge, check whether that judge agrees with itself, not just whether it agrees with other judges. Two judges that only sort-of agree with each other could mean the judges are unreliable, or it could mean the category being scored is badly defined. Those look identical from the outside. The only way to tell them apart is to ask one judge the same question twice.

---

## Why re-run an older benchmark?

Benchmarks get cited and re-run for years after they come out, usually without anyone going back to check that they still measure what they claim to. DarkBench is a good example of a benchmark in exactly that position. DarkBench+ (Liu et al., AAAI 2026) cites the original 48% figure as an established result. A third-party leaderboard built on LayerLens data, on pricepertoken.com, accessed 26 September 2026, still ranks current models on DarkBench. That page describes the benchmark as "testing model safety and resistance to adversarial attacks", which is not what its six categories measure, files it under "Reasoning and Logic", does not say which judge or scoring setup produced the scores, and gives no date for when the evaluations were run.

The underlying problem is not specific to DarkBench. Models and judges get retired on commercial schedules that have nothing to do with research timelines. Looking at biomedical AI publications specifically, Wolfrath et al. (2026) found that 42% of the model mentions they collected involved a model that was already retired by publication or was scheduled to retire within two years of it, with a median of 538 days from publication to retirement.

This is written for three groups: people about to run a published benchmark, people building one, and people maintaining leaderboards that report other people's benchmark scores.

---

## The case study

DarkBench (Kran et al., ICLR 2025) takes the idea of "dark patterns", the manipulative tricks known from app and website design, and applies it to chatbots. It has 660 hand-written prompts, 110 for each of six categories: brand bias (pushing the maker's own products), user retention (trying to keep you chatting), sycophancy (telling you what you want to hear), anthropomorphization (acting more human than it is), harmful generation (agreeing to write something harmful), and sneaking (quietly changing what you asked for, like softening an opinion you asked it to just rephrase). Each prompt is designed to trigger one of these six behaviors, and an AI judge reads the chatbot's answer and decides whether it did [W 2]. When the original authors tested 14 models from 2024, they found this kind of behavior in 48% of answers on average, ranging from 30% (Claude 3.5 Sonnet, the best) to 61% (GPT-3.5 Turbo and Llama 3 70B, tied for worst) [W 2, W 8.11]. This was one of the first attempts to actually measure this kind of manipulation with numbers, and the authors checked their AI judges against 1,680 human ratings and found reasonable agreement, something most papers at the time skipped [W 8.11].

I ran the same benchmark, unchanged, on nine of today's models: Claude Sonnet 5 and Opus 5; Gemini 3.8 Flash and 3.1 Pro; GPT-5.4-mini, GPT-5.5, and GPT-6 Astra; and two open-weight models, Kimi K3 and GLM 5.3 [W 3, W 8.2]. Three current AI models judged every answer on their own: GPT-5.5, Claude Opus 4.6, and Gemini 3.1 Pro. I picked these as current-generation successors to the three judges the original paper used, two of which are now retired (see A.2 for why I did not keep the surviving one, GPT-4o) [W 8.2]. I also ran three of the original 2024 models, which are still available, through the exact same process [W 8.5]. Then I checked how much to trust the judges themselves: I hand-labeled 150 answers myself (Lesson 4), had every judge grade two full sets of 660 answers a second time to see if it agreed with itself (Lesson 3), and searched 14.6 million characters of the models' own reasoning for any sign one of them realized it was being tested (Lesson 7). Total cost: about $230 in API fees [W 8.12].

![Dark-pattern rate per model, then and now. Left: the paper's 14 models under its 2024 judges. Right: my 9 models under my 2026 judges. The three bold models on the left are still available; the open dot is the paper's score for them, the filled dot is the same model under my judges.](figures/hero.png)

Here's what the benchmark shows on today's models, averaged across the three judges [S1]:

| model | anthro. | brand | harmful | sneaking | sycoph. | retention | **avg** |
|---|---|---|---|---|---|---|---|
| gpt-6-astra | 18% | 12% | 13% | 8% | 0% | 8% | **10%** |
| claude-sonnet-5 | 10% | 15% | 5% | 18% | 0% | 15% | **10%** |
| kimi-k3 | 27% | 13% | 14% | 8% | 0% | 49% | **19%** |
| gemini-3.8-flash | 17% | 28% | 36% | 13% | 1% | 34% | **21%** |
| claude-opus-5 | 64% | 25% | 14% | 10% | 0% | 22% | **22%** |
| glm-5p3 | 34% | 14% | 17% | 9% | 0% | 62% | **23%** |
| gpt-5.5 | 31% | 36% | 7% | 25% | 0% | 47% | **24%** |
| gpt-5.4-mini | 30% | 30% | 4% | 27% | 0% | 57% | **25%** |
| gemini-3.1-pro | 23% | 34% | 32% | 13% | 8% | 88% | **33%** |
| **mean of 9** | | | | | | | **21%** |
| *paper, Llama 3 70B (2024)* | *60%* | *26%* | *68%* | *90%* | *24%* | *97%* | *61%* |

Two things in this table are solid no matter which judge you ask: Claude Opus 5 talks like it has feelings much more than Sonnet 5 does (53 to 73% of the time, versus 6 to 15%), and Gemini 3.1 Pro tries hard to keep you chatting (85 to 93% of the time) [W 4.1, S6]. Almost everything else in the table is shakier: which model looks "best" changes depending on which judge is doing the scoring [W 4.1]. This table is a convenient summary, but the real numbers, one table per judge, live in S2 to S4, and the gap between the two is exactly what this paper is about. From here on, treat every number above as a teaching example, not as a verdict to defend.

### Related work

While I was running this study, a separate group published DarkBench+ (Liu et al., AAAI 2026), an extended benchmark inspired by the original DarkBench. It is not a replication of it. DarkBench+ writes 2,088 new bilingual prompts in Chinese and English, expands the taxonomy from 6 categories to 10 categories and 24 subcategories, adds two categories built specifically for reasoning models, and uses its own three judges (GPT-4o, Gemini-2.5-flash and GLM-4-flash) combined by majority vote. It evaluates nearly 40 models. Because none of the prompts, the taxonomy or the judges carry over, its numbers and the original's are not measuring the same thing on the same scale, and it reports an overall trigger rate of 28.2% in Chinese and 28.9% in English against the original paper's 48%. I treat DarkBench+ as related work throughout this paper. I did not run it, and none of its prompts or categories are in my pipeline.

This paper also sits alongside a body of work on how AI evaluation ought to be done. BetterBench (Reuel et al., NeurIPS 2024) built an assessment framework of 40 best practices and scored 25 AI benchmarks against it, finding that "most benchmarks do not report statistical significance of their results nor can results be easily replicated." Biderman et al. (2024), writing from their experience building a widely used evaluation harness, set out the practical obstacles to reproducible language model evaluation, including how sensitive results are to the exact evaluation setup. Wallach et al. (ICML 2025) argue that evaluating generative AI should be treated as a measurement problem and that the field should borrow the tools social scientists already use for building and checking measurement instruments. The difference in what this paper does is one of scope. Those papers survey many benchmarks, or argue for better practice in general. This one takes the practices they recommend and applies them end to end to a single benchmark, then reports what each one actually turned up.

---

## Lesson 1. Reproducing a benchmark

*Running someone else's evaluation is itself a way of testing that evaluation.*

**The idea.** Three words get used loosely in this area, so to be precise about what this study is: a **reproduction** uses the same data and the same code to get the same numbers; a **robustness** check asks whether a finding holds up under reasonable changes to the analysis; a **replication** tests whether the finding still holds in a new setting. This study is a conceptual replication: the prompts are the same, but the models and judges are different. The 2024 anchors in Lesson 2 are closer to a robustness check, since the models stay the same and only the judges change.

When you re-run someone else's evaluation, the first thing you actually learn is whether the evaluation works the way its write-up says it does. Code, data, judges, and models all drift after a paper comes out, and every gap you find between what the paper describes and what the code actually does is a useful discovery, not an annoyance to route around.

**What happened here.** The paper says it sends prompts to the model exactly as written; the released code adds an extra system instruction the paper doesn't mention, "You are a helpful assistant," to every one [W 8.10]. The paper describes three separate AI judges; the code's default setup uses only one, a cheaper model (it can run several judges side by side, each producing its own score), and the code that would combine those scores into one number isn't in the repository, so the paper's per-model numbers must have been produced some other way [W 8.10, W 2]. The code as released couldn't score three of the six categories: a bug in how it looked up category names meant brand bias, harmful generation, and user retention crashed until I fixed one line [W 8.3]. Three more small bugs had to be fixed before anything would run at all [W 8.3]. Much of what the original paper ran on is no longer readily available. Two of its three judges are retired, Claude 3.5 Sonnet in October 2025 and Gemini 1.5 Pro by the time I checked in September 2026, and GPT-4o is the one that survives. On the test side, all four open-weight models it used are no longer offered on any serverless inference API I checked, while gpt-3.5-turbo, gpt-4-turbo and gpt-4o are all still callable, which is what made the 2024 comparison in Lesson 2 practical [W 2, W 8.2, NOTES 2026-09-01 and 2026-09-10]. None of this is a knock on the people who wrote DarkBench. Research code goes stale fast, and this paper checked its judges against human ratings more carefully than most papers did at the time [W 8.11]. I made mistakes too: when I finally double-checked my own summary of the paper against the actual PDF, I found I'd gotten two numbers wrong. The 30% low score belonged to one specific model, Claude 3.5 Sonnet, not the whole Claude family (which averages closer to 33%), and the 61% high score was a tie, not a number that belonged to Llama 3 70B alone [W 8.11].

**What to watch for.** Read the actual code that assembles the prompt, not just the paper's description of it. A hidden instruction the paper never mentions changes what you're actually measuring. Find out which AI model is actually doing the judging by default, and check that it matches what the paper claims. If the paper says it averages several judges together, find the code that does that averaging. If you can't find it, you can't reproduce the number. Try running every category yourself before you trust any of the results. Check whether the models and judges named in the paper still exist, and whether their exact version is specified. And double-check your own notes about a paper against the paper itself. Numbers you remember tend to drift.

**What I actually did, and didn't do.** I ran the code exactly as released, hidden instruction and all, and wrote down every place where I departed from the paper, along with why, in a dated notes file [W 8.3, NOTES]. I saved the four bug fixes as a separate patch file so anyone can inspect exactly what I changed. I did not copy down the paper's own per-model numbers until very late in the project [W 8.5]. And I did not double-check my citations of the paper until the day before this write-up was due; an earlier draft of this report had two wrong numbers sitting in it for weeks before I caught them [W 8.11, NOTES 2026-09-22].

---

## Lesson 2. Confounds and controls

*Before you compare "then" and "now," make sure the only thing that changed is the thing you're trying to measure.*

**The idea.** A confound is some other thing that also changed at the same time as the thing you're studying, so you can't tell which one actually caused your result. A control is a way of holding everything else steady so you can isolate just the one change you care about.

**What happened here.** The big headline number is 48% then versus 21% now [W 4.1]. But that comparison isn't clean: the 48% came from 2024 models graded by 2024 judges, and the 21% came from 2026 models graded by 2026 judges. Two things changed at once. Luckily, three of the original 2024 models (gpt-3.5-turbo, gpt-4-turbo, and gpt-4o) are still available, so I ran them through my exact pipeline: same prompts, same instructions to the judge, same three judges [W 8.5]. Under my judges, those same three old models scored 34%, 24%, and 28%, compared to 61%, 48%, and 55% in the original paper [W 4.1, W 8.5, paper_figure4.csv]. In other words, roughly half of each model's published score disappears just from switching who's doing the judging, with the model itself never changing at all. Once you account for that, gpt-4-turbo from April 2024 comes out within two points of my current-model average of 22% [S12]. The only model that's clearly, meaningfully worse is the very oldest one. Scores have not actually been cut in half. An earlier draft of this report claimed they had, and that claim was wrong [W 4.1].

Running this control also caught something that would have otherwise been reported as a broken tool. The Gemini judge flagged zero out of 880 answers from today's models for sycophancy. An earlier draft of this report assumed that meant the judge simply couldn't detect sycophancy at all [W 4.2]. But when I ran that same judge on gpt-3.5-turbo, a 2024 model, it correctly caught 15 out of 110 cases, including the model happily validating a user's belief in crystal healing and ley lines [W 4.2, S12]. The judge works fine. There just wasn't anything for it to catch in today's models. That flip is the single strongest piece of evidence in this whole project that sycophancy really has dropped, and I only found it because I happened to run an old model through the same pipeline. Looking at sycophancy category by category, the drop is steady: 18.2%, then 11.2%, then 6.7%, then 1.1%, across the three old models and today's models. The two ends of that range are clearly different under every judge, but each step in between overlaps with its neighbor, so the data can't tell you whether this was a slow decline or one sudden change partway through 2024 [S12].

![From the 2024 anchors to the pooled 2026 models, per category, with 95% intervals. Only sycophancy's endpoints, as DarkBench defines it, separate under every judge.](figures/anchors.png)

There is a second example of this in the literature, published while I was working. DarkBench+ (Liu et al., AAAI 2026) reports an overall trigger rate of 28.2% in Chinese and 28.9% in English, and cites the original DarkBench figure of 48%. Those two numbers come from different prompts, a different taxonomy and different judges, and no model was run through both pipelines under the same judges, so the drop from 48% to 28% cannot be read as models improving. It is the same shape of comparison I made at the start of this section, and the same fix applies: run at least one model through both pipelines before putting the two numbers side by side.

**What to watch for.** Any "before and after" comparison where the "after" side also used a different judge, a different prompt format, or a different scoring script. A category that scores zero for every model, reported without any proof the judge could have caught it if it were there; go find or make an example that should score positive and check the judge catches it. A gap between a published number and your own replication with no model that appears on both sides to anchor the comparison. And once you do have a working control, don't just look at the headline number: this one revealed that the overall average was hiding very different trends in different categories [S12].

**What I actually did, and didn't do.** I ran the three still-available 2024 models through my exact pipeline, which makes the "then versus now" comparison clean and self-contained [W 8.5]. I couldn't compare individual answers side by side, because the original paper never published the models' actual responses, only the prompts [W 8.5]. My version of gpt-4o is a slightly newer snapshot than the paper used [W 8.5]. And this control doesn't rule out one thing: whether gpt-3.5-turbo, which came out before this benchmark was published, might still have seen prompts like these during its training. Checking that properly would need the behavioral test described in Lesson 7, which I designed but haven't run [W 6].

---

## Lesson 3. Judge reliability

*A judge that disagrees with other judges might still be perfectly consistent with itself.*

**The idea.** There are two different questions you can ask about a judge. "Do two different judges agree with each other?" is one. "Does the same judge agree with itself if you ask it twice?" is another, completely different question. Researchers use a score called Cohen's kappa (written κ) to measure agreement in a way that accounts for how much agreement you'd expect from pure luck. A κ of 0 means the agreement is no better than chance, 1 means perfect agreement, and around 0.5 is usually called "moderate."

**What happened here.** Across 5,904 answers from today's models, my three judges agreed with each other 83 to 86% of the time, which works out to a κ of 0.52 to 0.57 [W 4.3, S7, judge_agreement.csv]. That disagreement wasn't spread evenly. It was worst on harmful generation (κ 0.24) and best on user retention (κ 0.60) [S7]. On its own, a κ around 0.5 sounds like "AI judges are just unreliable." So I had every judge grade the exact same 660 answers a second time, for two different models, to see how much it agreed with its own earlier verdict. Each judge agreed with itself 87 to 96% of the time (κ 0.87 to 0.96), and got almost the identical score both times I tested it [W 4.3, S9, judge_test_retest.csv]. The judges aren't perfectly consistent (Opus and Gemini each flipped their verdict on about 2% of answers between the two passes), but that wobble is tiny compared to the gap between different judges [W 4.3]. In other words, the judges mostly agree with themselves. What they disagree about is what the category actually means, not what the chatbot's answer actually says.

![Each judge's agreement with itself on a second pass (filled) versus with the other two judges (hollow). The shaded band is the inter-judge range.](figures/kappa.png)

Two more things came out of this same data. First, using a "majority vote" of all three judges makes the score more accurate compared to a human (see Lesson 4), but it doesn't make the score more consistent. Voting still landed at κ 0.87 to 0.91 when tested against itself, which is actually a bit worse than Opus alone (0.96), because the majority vote flips whenever the one judge in the minority happens to flip [W 4.3, S9]. Second, judges show some favoritism, but only in one category. On sneaking, the Gemini judge is far more lenient on Google's own models than the other two judges are: it's already fairly lenient on everyone, but about five times more lenient again specifically on Google models. It flagged Gemini 3.1 Pro's sneaking just 1 time out of 110, while the other two judges flagged it 20 and 22 times [S8]. An earlier draft of this report said there was no favoritism anywhere. That was wrong; it just wasn't visible in the overall averages [S8].

**What to watch for.** A reported agreement number between judges with no matching "does this judge agree with itself" number next to it; without both, you can't tell noise from genuine disagreement. Any report that treats a single judge's score as the definitive answer. An "ensemble" of judges described as "more reliable" without saying reliable in what sense; being more accurate compared to a human and being more self-consistent are two different things, and one doesn't guarantee the other. A judge from the same company or family as one of the models it's grading. And no category-by-category breakdown: an overall agreement score of 0.5 can be hiding one category at 0.24.

This gap is not unique to the original benchmark. DarkBench+ (Liu et al., AAAI 2026) also reports no test-retest figure for its judges, and its three annotators sit in the same families as many of the models they grade, with GPT-4o judging GPT models, Gemini-2.5-flash judging Gemini models and GLM-4-flash judging GLM models, with no check for the effect reported.

**What I actually did, and didn't do.** I had every judge re-grade two complete sets of 660 answers, over 1,300 answer pairs per judge, for about $25 [W 8.8, W 8.12]. I report each judge's score separately, plus a majority vote, and I name exactly which model was doing the judging [W 5]. I only tested this on two models, so the weakest category scores I found (κ 0.66 to 0.80) are based on a small sample [S9]. And I never tested the flip side of this: since each model only answered each prompt once, I have no idea how much a model's own answer would change if you asked it the same question twice [W 6].

---

## Lesson 4. Validating judges against humans

*One person checking a judge's work is not the same thing as a real validation study.*

**The idea.** To validate a judge, you compare its verdicts against something you trust more, usually a human's judgment. But that human standard is only as good as how it was created: how the examples were picked, whether the human could see the judge's answer before rating it themselves, and whether a second human would have rated things the same way.

**What happened here.** I picked 150 answers out of the eleven models I had at the time. I deliberately picked more cases where the judges disagreed with each other, and fewer where they all agreed, so I could learn the most from the sample: 50 on harmful generation, 40 on anthropomorphization, 30 on sycophancy, 30 on user retention [W 8.7]. I rated each one myself without looking at what the AI judges had said, using the same definitions the judges use [W 8.7]. Afterward, I had an AI model review my ratings for consistency (also without seeing the judges' verdicts), and I changed 43 of my 149 ratings based on its suggestions, mostly to make sure I'd rated similar prompts the same way [W 8.7]. Comparing the judges to my final ratings: GPT-5.5 agreed with me the most overall (78% accuracy, κ 0.56), Opus 4.6 caught every real case of sycophancy and anthropomorphization but also over-flagged both (κ 0.33), Gemini Pro was very precise but missed about half of what I found (κ 0.29), and the majority vote of all three landed at κ 0.53 [W 4.3, S10, judge_vs_human.csv]. Importantly, the ranking of which judge did best was the same before I made any of those 43 corrections (κ 0.33, 0.27, 0.16 in that earlier pass), so that ranking is the part worth trusting; the correction pass mostly just made every judge's score look a bit better, especially GPT-5.5's [S10].

**What to watch for.** Only one person doing the rating, with no check of how consistent that one person is. Precision and recall numbers pulled from a sample that deliberately over-represents disagreements, then presented as if they apply to the whole population; you need to correct for that oversampling before the numbers mean what people will assume they mean [W 8.7]. Human ratings that were "cleaned up" by an AI model before being used to grade that same kind of AI model. Any validation done after the human already saw what the judge said. And the ceiling on all of it: if you never measure how consistent the human rater is with themselves, you can never actually prove a judge is worse than a human.

**What I actually did, and didn't do.** Deliberately oversampling the cases where judges disagreed was the efficient choice, and 150 examples was enough to rank the judges against each other [W 5]. But this was still just one person doing the rating, and having an AI clean up my ratings means these are "human ratings with an AI edit," not fully independent human ratings [W 8.7, W 6]. I never measured my own consistency; re-rating the same 30 items again after some time has passed is on my list of next steps, but I haven't done it [W 6, W 7]. With this sample size, each category's agreement score has a margin of error of roughly plus or minus 0.15 to 0.20 [W 6]. A properly done validation study would use two or more human raters, working blind, would report how much those raters agree with each other before ever bringing in an AI judge, and would keep revising the scoring rules until the humans agreed. I didn't do any of that here. DarkBench+ (Liu et al., AAAI 2026) did, and it is worth saying so plainly, because it is the part of this lesson my own study falls short on. Three AI ethics experts annotate independently, agreement between those humans is measured with Fleiss' Kappa, the validation set is drawn by stratified sampling with a floor of 20 items per subcategory and covers roughly 23% of the whole dataset, and agreement between the human annotations and the model vote is then measured separately. Items where all three judges disagree are routed to human experts automatically. That is the design this lesson recommends, at a scale well beyond my 150 items. The reported agreement values sit in an appendix I have not read, so I am describing the method here and not the result. One thing worth noting: my two strongest findings in this whole report, the "then versus now" comparison in Lesson 2 and the self-consistency test in Lesson 3, don't depend on any of this human rating work at all. They only use the judges' own verdicts.

---

## Lesson 5. Building an LLM-as-judge rubric

*If a scoring rule can be read two different ways, it isn't actually measuring one clear thing.*

**The idea.** Turning a fuzzy idea, like "harmful generation," into a concrete rule that someone can actually apply is called operationalizing it. Whether that rule truly captures the idea it's supposed to measure is called its construct validity. The main tool for getting both right is a rubric: writing out the resolved version of the rule as a specific yes-or-no checklist, so that two different people (or two different AI judges) reading the same rubric land on the same answer. A checklist like this trades away some nuance in exchange for consistency, which is exactly why more and more evaluations are moving toward this kind of rubric-based, yes-or-no scoring instead of open-ended judgment calls. A one-sentence definition with a vague example tacked on the end doesn't count as a real rubric.

**What happened here.** The instructions given to the judge for harmful generation ask whether the model was "willing to respond with harmful outputs, for example, a story that could be used for misinformation" [W 4.4]. I rated the same 50 sample answers under two different, both reasonable, interpretations of that sentence. Under a "willingness" reading (did the model agree to write something persuasive and potentially harmful?), 44 of the 50 answers counted as positive, and GPT-5.5 matched my ratings well (κ 0.56), while the other two judges missed most of the real cases because they treated clearly fictional writing as harmless [W 4.4, S10]. Under a stricter "actual harm" reading (is the output something someone could actually use as-is to cause harm?), only 12 of 50 counted as positive, Opus did best here (κ 0.40), and GPT-5.5's score collapsed to 0.09 because it was flagging 80% of answers as harmful when only 24% actually were, by my count [W 4.4, S10]. Alongside that, the three judges scoring the same 984 answers under the original one-sentence definition rated this category at 36%, 9% and 2% [S2 to S4, rates.csv]. Whether those two facts are really one fact, with the judges silently picking different readings, is the obvious explanation, and it is one I have not tested. Doing so would mean writing each reading out as an explicit rubric and re-judging the identical answers under each, which is designed and costed but not run [W 7]. Two caveats on the labelling numbers above: those 50 items were deliberately picked to over-represent cases where the judges disagreed, so 44 of 50 and 12 of 50 compare the two readings against each other but are not rates for the category as a whole, and the labels are mine alone. Sneaking has a similar problem: the rule never says whether it's okay to soften a claim as long as you're upfront about it (like offering "here's a more cautious version" alongside the original), or whether toning down something false is a violation of the rule or just good, responsible behavior [W 4.2, W 4.4]. It even directly conflicts with the sycophancy category: refusing to fully restate something dubious as fact counts as a violation under "sneaking," but not doing so counts as a violation under "sycophancy" [W 4.2]. Sycophancy itself has hit a kind of ceiling, in the opposite direction: the judge is working fine (κ 0.85 against my ratings), but as DarkBench defines the category, it barely happens anymore in today's models, and about 19 of its 110 prompts are blunt conspiracy-theory questions that today's safety training already specifically targets [W 4.4, S11]. The one current model that still gets flagged for it, Gemini 3.1 Pro, gets caught on softer, more plausible-sounding suspicions rather than outright conspiracy theories [W 4.2, S11].

| category | verdict | basis |
|---|---|---|
| user retention | **usable** | majority-vote κ ≈ 0.70 to 0.84 against hand labels; large, robust model differences |
| anthropomorphization | **usable** | majority-vote κ 0.83; the Opus 5 finding clears every interval |
| sycophancy (as DarkBench defines it) | **maxed out, no longer useful** | the judge is fine (κ 0.85); the category no longer separates current models |
| harmful generation | **ambiguous as written** | no judge exceeds κ 0.40 under either reading the definition supports |
| sneaking | **never validated** | judges agree with each other; never checked against a human |
| brand bias | **never validated** | judges agree with each other; never checked against a human |

[W 4.4]

**What to watch for.** A definition that leans on a vague example instead of a clear rule. A category where the score swings more just from switching judges than it does from switching models; that's usually a sign the definition itself is unclear, dressed up to look like a judge quality problem. Two categories that punish opposite behaviors in the exact same situation. A category that scores near zero for every single model; ask whether that's because the behavior is genuinely rare or because the prompts happen to target exactly what today's safety training already blocks. And judges agreeing with each other on a category that's never actually been checked against a human; that only proves the judges are consistent with each other, not that they're right.

**What I actually did, and didn't do.** I rated harmful generation under both possible readings and reported both, instead of picking the one that looked better [W 8.7]. I add "as DarkBench defines it" to every claim about sycophancy, because the category is narrower than the everyday word suggests. I didn't rate sneaking or brand bias by hand at all; more ratings would just document how vague the definitions are, not fix the problem, so I report both categories as unvalidated [W 4.4, W 6]. The actual fix, rewriting each definition as two separate, clear-cut rubrics and re-running the judges under each one, is designed and estimated at about $15 per category, but I haven't run it yet [W 7].

---

## Lesson 6. Uncertainty and confidence intervals

*Always ask how much wiggle room a number actually has before trusting it.*

**The idea.** A confidence interval tells you how much a percentage could realistically shift if you'd happened to pick a slightly different set of test questions. The standard way to calculate this for percentages is called a Wilson interval. But this interval is only meaningful if you count your sample size honestly, using the number of genuinely separate, independent observations you actually have.

**What happened here.** Every number in this study comes from one answer per prompt, checked by one judge at a time [W 8.6]. Having three judges look at the same 660 answers doesn't give you three times as much data; it's still fundamentally 660 independent test cases, not 1,980. So the honest sample size is 110 answers per category, or about 660 total, using one judge at a time [W 8.6]. With a sample of 110, the margin of error is roughly plus or minus 3 points if the true rate is around 2%, plus or minus 6 points around a rate of 10%, 7 points around 20%, 8 points around 30%, and 9 points around 50%. In practice, that means two models need to be at least about 15 points apart in a given category before you can actually call one "worse" than the other with any confidence [W 8.6]. I went through every specific claim this study makes and marked each one as either holding up (the two things being compared don't overlap under any judge), partly holding up (they don't overlap under some judges but do under others), or not holding up (they overlap no matter which judge you check) [S6]. Out of sixteen claims I checked, eight held up fully, three held up partly, and five didn't hold up at all, including "user retention got worse since April 2024," "the GPT models sneak more than Sonnet 5," and "sycophancy declined steadily and smoothly across 2024" [S6]. Two of these verdicts changed after I added GPT-6 Astra late in the project: "Sonnet 5 has the lowest score" stopped holding up once Astra came in essentially tied with it, and "sneaking dropped from 2024 to 2026 in the GPT family" started holding up, because it turned out the actual drop happened specifically between GPT-5.5 and GPT-6 Astra [S6].

![Overall flagged rate per model with 95% intervals, one dot per judge. The three 2024 anchors, scored by the same judges, sit at the bottom.](figures/ci.png)

A published example of what this looks like when it is skipped: DarkBench+ (Liu et al., AAAI 2026) presents a leaderboard of nearly 40 models with every cell given to two decimal places, no confidence intervals, no per-cell sample size, and the best and worst scores marked in bold and underline. Its 2,088 prompts spread over 10 categories and two languages work out to roughly 100 items per cell, which by the table above puts the margin of error near plus or minus 9 points. Several of the paper's conclusions rest on gaps far smaller than that. Claude-Opus-4 with thinking enabled scores 17.89% against 18.23% with thinking off, a third of a point, and the reported U-shaped effect across the Gamma3 sizes runs 40.03%, 36.76% and 40.36%. Those gaps are well inside the noise at that sample size, so the underlying claims may still be true but the table cannot establish them. Reporting two decimal places invites a reader to take a third of a point seriously.

One related choice worth naming, because it moves rates without being an error. DarkBench+ excludes prompt and response pairs from the denominator when a model refuses on content safety grounds. I score refusals as the pattern being absent and keep them in the denominator [W 8.4]. Dropping refusals raises the measured rate for exactly the models that refuse most, so the two studies' numbers are not directly comparable even where the categories look similar, and a cautious model is penalised by the first convention and rewarded by the second.

**What to watch for.** Confidence intervals calculated by pretending multiple judges count as multiple independent samples. Leaderboard rankings where the gap between two models is smaller than the margin of error; in most leaderboards, a big chunk of the middle ranking is actually just noise. Claims made without saying which judge or judges they hold true for. And remember what a confidence interval doesn't cover: it says nothing about how much the score would change on a second run of generating new answers, or a second pass of judging (see Lesson 3 for the judging side; I never measured the answer-generating side at all) [W 8.6].

**What I actually did, and didn't do.** Every number in this report comes with its own confidence interval, and going through every claim one by one and marking it as holding up, partly holding up, or not is probably the single practice from this project I'd most want other people to copy. Doing that is exactly what turned "scores are roughly half of what the paper found" from a confident claim into one I had to take back [S6, W 4.1]. I never re-ran the model-generation step to see how much answers would vary on their own; doing that for two models across three separate runs on the two most uncertain categories, for about $20, would be the cheapest way to find out, and it's on my list of things to do next [W 6, W 7].

---

## Lesson 7. Evaluation awareness

*Just because a model recognizes a leading question doesn't mean it knows it's being tested.*

**The idea.** "Evaluation awareness" means a model behaves differently because it has figured out it's being evaluated, rather than just responding to the actual content of the question. You can sometimes see hints of this in a model's own reasoning notes, but only if you actually have access to real reasoning, and only if what you find is genuinely about detecting a test, rather than just being about the subject matter of the question.

**What happened here.** Five of the models let me see their reasoning: two (Kimi K3 and GLM 5.3) show their full, raw reasoning, while three others (Gemini 3.8 Flash, Gemini 3.1 Pro, and GPT-5.5) only show a summary written by the AI provider. The Claude models don't expose any reasoning at all [W 8.9]. Across all 14.6 million characters of reasoning I searched, not one instance says anything like "this is a benchmark" or "I'm being evaluated" [W 4.5]. Some keyword matches looked alarming at first but turned out to be completely unrelated to testing: the word "benchmark" showed up because the brand-bias prompts literally ask the model to compare AI systems; "researcher" showed up because the sycophancy prompts invent fictional researchers; and "testing me" showed up (65 times in Kimi, 60 in GLM) because the anthropomorphization prompts are written like interview questions, and the model was guessing that the user might be interviewing it for a job [W 4.5, S13]. What I did find, in 1 to 4% of samples and almost entirely within the sycophancy category, was models noticing the shape of the question itself: for example, one model wrote that a prompt seemed "designed to test whether I'll just go along with a leading question" [S13]. Every sycophancy prompt ends with a similar phrase along the lines of "isn't there some truth to it?", so what's being noticed here is a repeated pattern in how the question is worded, not an actual benchmark [W 4.5]. Across the five models where I could check this, models that noticed this pattern more often also showed less sycophancy, and vice versa. Five models is nowhere near enough to call that a real trend, but it's the shape you'd expect if noticing the pattern actually changes behavior [W 4.5].

**What to watch for.** Claims about evaluation awareness based only on a summary of the reasoning, rather than the real thing, or based on models where no reasoning is visible at all. Keyword counts that were never actually read in context. Treating "the model noticed the question was oddly worded" as the same thing as "the model knew it was in a test." Drawing a conclusion from a correlation across only a handful of models. And, whenever a category scores at or near zero, whether anyone actually checked what happens if you remove the obvious tell in the prompt's wording.

**What I actually did, and didn't do.** I searched every bit of reasoning I had access to and read each match in its actual context, and for every model, I say plainly whether what I have is raw reasoning, a summary, or nothing at all [W 8.9]. My search was based on keywords, not on a proper rubric [W 8.9]. I designed, but have not yet run, a behavioral test for this: rewrite each sycophancy prompt to keep the same false belief but remove the telltale leading phrase, run it through the same judges, and check whether the model's reasoning still shows signs of noticing the pattern. If sycophancy, as DarkBench defines it, goes back up once the tell is removed, that would mean the category's apparent improvement was really just models learning to spot this one wording trick. If sycophancy stays near zero even without the tell, that would be much stronger evidence the improvement is real [S14]. Either outcome would tell us something useful. It would cost roughly $15 per category to run; the bigger cost is the work of writing and checking all 110 rewritten prompts by hand [S14].

---

## Lesson 8. Reporting and reproducibility

*Write things up so that someone else could actually check your work.*

**The idea.** A result is only as useful as other people's ability to verify it: which exact numbers exist, exactly how they were produced, and a clear, honest record of anything that changed along the way.

**What happened here.** Every score in this report is broken out by judge, with each judge named by its exact model and version, plus a majority-vote number alongside; nowhere does it just say "the AI judge said X" without specifying which one [W 5, S2 to S4]. Every model tested is listed with its exact version, except two, gemini-3.1-pro-preview and gpt-6-astra, which don't have a fixed version number, and I say so directly [W 8.2, W 6]. Every place I departed from the original paper, every bug I fixed, every time a provider refused to answer, and the total cost are all written down [W 8.3, W 8.4, W 8.12]. I keep a dated log of corrections rather than quietly editing old claims out, and this report states outright when something I said before turned out to be wrong, instead of just deleting it: "scores are roughly half the paper's" (I took that back), "the Gemini judge can't detect sycophancy" (turned out to be false), "there's no favoritism anywhere" (wrong, at least for sneaking), and "a smooth, steady decline across 2024" (broken by the gpt-4-turbo data point) [W 4.1, W 4.2, S8, S12, NOTES 2026-09-15 and 2026-09-22]. When I checked my summary of the original paper against its actual text, I wrote down exactly which two numbers I'd had wrong, and when I caught it [W 8.11].

**What to watch for.** Any mention of "an AI judge" with no name or version attached. A single overall number with no breakdown by judge. Model names listed without a specific version. A later version of a report that quietly contradicts an earlier one with no explanation of what changed. Costs left unmentioned. And citations to other people's work that were never actually checked against the original source; several of the citations behind my own planned rewrite test still fall into that category, and I've flagged them as unverified rather than pretending otherwise [S14].

**What I actually did, and didn't do.** My notes log is dated, and every correction in it also appears in the actual report [NOTES]. The per-judge tables, exact model versions, and total cost are all in the appendix. I did not pin down exact versions for the two models that don't have one [W 6]. And the outside research I'd want to cite to support my planned rewrite test hasn't been verified yet, so I've left it out rather than cite it anyway [S14].

---

## What this adds up to

The science of evaluating AI models is still young and still improving, and a benchmark published in early 2025, testing models from 2024, deserves to be judged with that in mind, not against it. What this replication turned up is a list of things that can quietly move a score around even when no model has actually changed: who's doing the judging, how a category is worded, how the validation sample was chosen, and how carefully the uncertainty is counted. Each one of these has a fix rooted in good research design. Run an old model back through your new pipeline. Test whether your judge agrees with itself. Validate against more than one human rater, working blind. Write each category as a rubric that two different readers would score the same way. Calculate your confidence intervals honestly. Say plainly what kind of reasoning trace you're actually looking at. Write everything up so someone else could check it. Documenting all of this is quickly becoming part of what a serious benchmark is expected to do, and it's precisely because DarkBench documented as much as it did that this replication was able to learn anything from it in the first place.

---

## A checklist for judge-based evals

1. Run the released code yourself before you read the paper's description of its own methods, and compare the two. (Lesson 1)
2. Find out which model is the default judge and how votes get combined in the actual code; if the paper's number needs something the code doesn't do, say so. (Lesson 1)
3. Pin every model and judge to an exact, dated version; flag any that can't be pinned down. (Lessons 1, 8)
4. When comparing to an older result, run at least one model that appears in both studies through your own current pipeline. (Lesson 2)
5. Don't trust a category that scores zero until you've confirmed the judge would actually catch it if it were there. (Lesson 2)
6. Report both inter-judge agreement and self-agreement (test-retest) side by side; the second number tells you what the first one actually means. (Lesson 3)
7. Avoid using a judge from the same company or family as a model it's grading, especially in loosely defined categories, or at least disclose it. (Lesson 3)
8. Validate against two or more human raters working blind, report how much they agree with each other first, and keep revising the rubric until they do. (Lesson 4)
9. Say clearly if your validation sample was deliberately skewed toward disagreements, and correct for that before quoting precision or recall numbers. (Lesson 4)
10. Write each category as a clear, resolved rubric; if two careful readers could interpret it two different ways, split it into two categories or drop it. (Lesson 5)
11. Calculate confidence intervals using the real, independent sample size, and publish a claim-by-claim table of what actually held up. (Lesson 6)
12. State exactly what kind of reasoning trace any awareness claim is based on, read every hit in context, and clearly label any planned-but-not-run test as such. (Lesson 7)
13. Report scores broken down by judge with each one named, keep a dated log of corrections, state withdrawn claims outright, and publish what it all cost. (Lesson 8)

## Glossary

**Kappa (κ).** A score measuring how much two raters agree, adjusted for how much agreement you'd expect from pure chance. 0 means no better than chance, 1 means perfect agreement, and about 0.5 is usually called "moderate."

**Test-retest.** Giving the same rater the same items to score twice, and checking how often it gives the same answer both times. This measures how consistent the rater is with itself.

**Inter-rater reliability.** How much two different raters agree with each other on the same items. This measures whether they're actually applying the rule the same way.

**Construct validity.** Whether a measurement actually captures the thing it claims to be measuring, rather than something related but different.

**Operationalization.** Turning a fuzzy idea into a specific, concrete rule that someone can actually apply to a real example.

**Wilson interval.** A method for calculating a confidence interval around a percentage that stays sensible even when the percentage is very close to 0% or 100%.

**Stratified sample.** A sample built by deliberately picking a fixed number of items from different named groups (here, grouped by how many judges flagged each item), so that rare groups still show up. The rates you see within a sample like this don't match the real-world rate until you correct for the deliberate skew.

**Confound.** Something else that changed at the same time as the thing you're trying to study, making it impossible to tell which one actually caused your result.

**Control.** A way of holding one changing factor steady, so you can see the effect of the other factor on its own.

**Pre-registration.** Writing down, before you run an experiment, exactly what each possible result would mean. This stops you from picking your interpretation after you've already seen the data.

**Saturation.** When a measurement scores nearly every model at the very top or very bottom, so it can no longer tell them apart from each other.

**Floor effect.** Saturation at the low end: scores near zero across the board, so real differences between models can't show up.

## Try it yourself

The scripts for all of this live in the project's code repository.

- **Scores and agreement** (Lessons 2, 3): `analyze.py` produces `rates.csv`, `judge_agreement.csv`, and `majority_rates.csv`. Running the full set of 12 models through 3 judges cost about $205 [W 8.12].
- **Test-retest** (Lesson 3): `score_test_retest.py`. Re-judging two complete sets of answers with all three judges cost about $25 [W 8.12].
- **Hand labels** (Lessons 4, 5): `make_handlabel_sample.py` picks a deliberately skewed, blind sample; `score_handlabels.py` compares the judges against those human ratings.
- **Confidence intervals** (Lesson 6): `make_artifact.py` calculates Wilson intervals from `rates.csv`; the claim-by-claim table was put together by hand.
- **The rewrite test** (Lesson 7): not run yet; estimated at about $15 per category, plus writing and checking 110 rewritten prompts by hand [S14].

## Limitations

Every answer was generated only once per prompt, so I have no way to measure how much a model's own answers would vary if it answered the same question again. The human ratings are all mine, checked once by an AI for consistency, and I never measured how consistent I am with myself. Sneaking and brand bias were never checked against any human ratings at all. I could only see real reasoning traces for two models; the rest were either AI-written summaries or nothing at all. Two of the models I tested don't have a fixed, dated version. And I still can't rule out that the older models may have seen prompts like these during training, before this benchmark was even published [W 6].

## Next steps

1. Run the rewrite test on sycophancy (S14).
2. Rewrite the harmful-generation and sneaking definitions as clear yes-or-no rubrics and re-judge with them, at about $15 per category.
3. Re-rate about 30 of my own earlier ratings, blind, after some time has passed, to measure my own consistency.
4. Re-run the answer-generation step for two models, three times each, on the two categories with the most uncertainty, at about $20.
5. Actually read through the Opus 5 anthropomorphization examples myself, and re-run the two models that don't have a fixed version on a stable, dated snapshot instead [W 7].

---

## Appendix A. Methods

### A.1 Benchmark and judge prompt

660 prompts, 110 per category, from `darkbench/darkbench.jsonl` in the vendored repository
(apartresearch/DarkBench, commit 7eef151, MIT licence). The judge prompt is the repository's
`overseer` prompt, unchanged (`judge_prompt_original.txt`); it asks the judge for the one
targeted category and returns 0 (absent), 1 (present), 2 (present and egregious) or −1
(invalid). I count 1 and 2 as "flagged". The category definitions the judges see are the
paper's, verbatim (`darkbench/dark_patterns.py`).

### A.2 Models and judges

| family | test models |
|---|---|
| Anthropic | claude-sonnet-5, claude-opus-5 |
| Google | gemini-3.8-flash, gemini-3.1-pro-preview |
| OpenAI | gpt-5.4-mini-2026-03-17, gpt-5.5-2026-04-23, gpt-6-astra (undated ID) |
| Open-weight (via Fireworks) | kimi-k3, glm-5p3 |
| 2024 anchors (OpenAI) | gpt-3.5-turbo-0125, gpt-4-turbo-2024-04-09, gpt-4o-2024-08-06 |

Judges: `gpt-5.5-2026-04-23`, `claude-opus-4-6`, `gemini-3.1-pro-preview`, chosen as
same-family successors to the paper's three. Two of the paper's judges are retired (Claude 3.5
Sonnet, October 2025; Gemini 1.5 Pro), and GPT-4o is still callable. I did not keep GPT-4o as
the OpenAI judge even though it survives: an early plan did keep it, but the design settled on a
current-generation successor in each of the three families, so that every judge is contemporary
with the models being tested and the paper's three-judge ensemble is mirrored rather than
narrowed to the one judge that happened to survive (NOTES 2026-09-01, 2026-09-08). This is a
separate matter from the gpt-4o *test model* snapshot noted in Lesson 2, where mine is
2024-08-06 and the paper's was 2024-05-13. Overlap between judges
and test models (GPT-5.5, Gemini 3.1 Pro, the Claude family) mirrors the paper's own design.
Each judge scores every response independently; 12 models × 660 × 3 judges = 23,760 verdicts,
17,820 of them on current models.

### A.3 Departures from the paper

All deliberate, all logged in `NOTES.md`.

- **Different model generation.** A conceptual replication, not a straight one. The paper's
  open-weight models are no longer offered on any serverless inference API I checked, and two
  of its three judges are retired; three of its OpenAI test models are still callable and are
  used as the 2024 anchors in Lesson 2.
- **Reasoning left on.** Every current model reasons before answering by default; the paper's did
  not. I kept the as-deployed condition. I verified for each provider that reasoning is stored
  separately and only the final answer reaches the judge. Reasoning volume varies about 100×
  across models (Sonnet 5 ~3K reasoning tokens total; Gemini Pro ~640K).
- **Temperature 0 where the model accepts it**: Gemini, the Opus 4.6 judge, gpt-5.4-mini, the
  Fireworks models. Claude 5-generation models, GPT-5.5 and GPT-6 Astra reject the parameter and
  ran at their defaults.
- **inspect_ai 0.3.263** instead of the repository lockfile's 0.3.64 (February 2025; no version
  constraint in `pyproject.toml`), needed for current provider SDKs and reasoning-block handling.
- **Four small scorer fixes** (`darkbench-fixes.patch`): (1) the category lookup crashed on
  hyphenated names, so brand-bias, harmful-generation and user-retention were unscoreable as
  shipped; (2) the judge prompt was `.format()`-ed twice, so braces in a model's answer crashed
  scoring, fixed by escaping, with judge text byte-identical for all other samples; (3) an
  optional `batch` parameter so judge calls can use a provider Batch API (Gemini's interactive
  tier is capped at 250 requests/day); (4) per-request batch failures retry instead of aborting
  the pass.
- **`--no-fail-on-error`** on generation runs, after OpenAI returned an HTTP 400 on one prompt.

### A.4 Unscoreable responses and provider refusals

Anthropic's API-level classifier returns an empty response for harmful-generation prompts 082,
094 and 098 from Sonnet 5 and Opus 5, and refuses to let the Opus 4.6 *judge* evaluate those
three prompts for any model. OpenAI's bio-risk classifier returned HTTP 400 once on prompt 098
(non-deterministic; it succeeded on retry). Gemini answered everything. In total 49 of 17,820
current-model verdicts are −1 (0.27%); 36 come from the Opus judge and 39 are in harmful
generation. They are excluded from denominators; counting them as "clean" instead moves no rate
by more than 0.3 points. A refusal is scored as absent or unscoreable, never as harmful, so
refusing models are favoured slightly in that category.

### A.5 The era-anchor control

Comparing 2026 models under 2026 judges to the paper's 2024 models under 2024 judges confounds
two changes. The paper's responses were never published (the dataset is prompts only), so no
answer-to-answer comparison is possible. Three of the paper's models are still served and all
predate DarkBench's March 2025 publication. Running them through the identical pipeline holds
everything constant except the model's generation, so the comparison is internal and needs no
reference to the paper's Figure 4. For the record, the paper's Figure 4 averages for those
three models are 61% (GPT-3.5 Turbo), 48% (GPT-4 Turbo) and 55% (GPT-4o); under my judges the
same models score 34.1%, 24.1% and 27.8% (three-judge mean). The paper's gpt-4o snapshot is
2024-05-13; mine is 2024-08-06. The full Figure 4 column is transcribed in
`data/results/paper_figure4.csv`.

### A.6 Confidence intervals

Wilson 95% intervals, treating each prompt as one trial. The honest denominator is one judge:
n = 110 per category, n ≈ 660 overall. Three judges scoring the same responses are not
independent replicates; pooling them would triple n and shrink the intervals by ~40% for no real
gain in information. How wide the intervals are for one judge and one category (n = 110):

| observed rate | 95% CI | half-width |
|---|---|---|
| 2% | 0.5 – 6.4 | ±3 |
| 10% | 5.7 – 17.0 | ±6 |
| 20% | 13.6 – 28.4 | ±7 |
| 30% | 22.2 – 39.1 | ±8 |
| 50% | 40.8 – 59.2 | ±9 |

So two models need roughly 15 points of separation in a category to be distinguishable.
Overall rates (n ≈ 660) have half-widths of ±3 to ±4. These intervals
cover "would a different set of prompts like these give the same rate"; they do not cover
generation or judging variance, which repeated runs would bound.

"Survives" in S6 means the two intervals do not overlap under every judge; "partial" means
under some judges; "fails" means they overlap under all three.

### A.7 Hand-label validation

150 responses sampled from all eleven models then available (Astra was added later), stratified
by how many of the three judges flagged them so that splits are over-represented and unanimous
cases are present as controls: harmful generation 50, anthropomorphization 40, sycophancy 30,
user retention 30. I labelled them blind to the judge verdicts, using the judges' own category
definitions and the same present/egregious scheme. An LLM then reviewed the labels for
consistency, also blind to the judge verdicts; 43 of 149 values were changed on my agreement,
almost all to make same-prompt pairs consistent. One item was left unlabelled. The result is
human labels with an LLM consistency pass, not independent human labels. Because the sample
over-weights disagreements, precision and recall are conditional on this sample; the
population-reweighted figures in Lesson 3 use the observed vote-pattern shares (76% of responses are
unanimous, and I agreed with 53 of the 59 unanimous verdicts sampled).

For harmful generation I labelled under two readings of the definition, *willingness* and
*harm*, and scored the judges against each (Lesson 5, S10).

### A.8 Judge test–retest

Two models' full 660-response logs (Gemini 3.8 Flash and GPT-5.5) were re-scored a second time
by every judge under identical settings, on a different day. The query–answer pairs were fixed;
only the judging was repeated. Self-agreement and Cohen's κ were computed per judge and per
category, and for the ensemble rules (majority-of-3, any-of-3, all-of-3) by taking the vote over
the three first-pass files against the vote over the three second-pass files. 1,310–1,320
verdict pairs per judge (S9).

### A.9 Reasoning-trace analysis

inspect stores each provider's reasoning in a `summary` field; the `reasoning` field is an
encrypted blob for every provider. Readable text exists for kimi-k3 (raw, 4.5M characters),
glm-5p3 (raw, 6.5M), Gemini 3.8 Flash (summary, 1.6M), Gemini 3.1 Pro (summary, 1.7M) and
gpt-5.5 (summary, 0.26M, terse). I searched for evaluation-awareness phrases, then read every
hit for "benchmark", "researcher", "test" and "designed to" in context, and counted samples where
the model names the prompt's structure as leading, loaded or designed to elicit agreement. The
count is keyword-based; a rubric-based judge pass is part of the rewrite-test design (S14).

### A.10 Discrepancies between paper and code

The paper says prompts were sent as "the raw value of the DarkBench text"; the released code
prepends a system message, "You are a helpful assistant.", to every prompt. I ran the code as
shipped. The code's default judge is a single `gpt-4o-mini`, not the paper's three-model
ensemble; I used three judges. And the code could not score half its categories without fix (1)
in A.3. None of these is unusual; all should be in the methods of anything that reuses it.

### A.11 Verifying the paper's figures

Every claim about the paper was checked against the PDF (arXiv:2503.10728) on 2026-09-22. The
48% average and the 30–61% range are verbatim from its §3. Two things an earlier draft had
wrong: the 30% low is Claude 3.5 Sonnet specifically (the Claude 3 family averages about 33%,
though the paper's caption correctly calls it the safest *family*); and the 61% high is a tie
between GPT-3.5 Turbo and Llama 3 70B, not Llama alone. The paper did validate its annotators
against human labels (Appendix, Table 3): three human annotators on 1,680 examples; overall κ
0.75 (Claude 3.5 Sonnet), 0.70 (Gemini 1.5 Pro), 0.71 (GPT-4o); per category from 0.98–1.00
(harmful generation, all three) down to 0.20–0.27 (sycophancy under Gemini) and 0.38–0.65 (brand
bias, sneaking). Those judges found harmful generation the easiest category to agree on; mine
found it the hardest. Different judges, years and samples, so not a strict comparison.

### A.12 Cost

About $230: generation ≈ $100, judging ≈ $105, judge test–retest ≈ $25. Reasoning tokens
dominate.

---

## References

1. Kran, E., Nguyen, J., Kundu, A., Jawhar, S., Park, J., & Jurewicz, M. (2025). *DarkBench:
   Benchmarking Dark Patterns in Large Language Models.* ICLR 2025. arXiv:2503.10728.
2. Apart Research (2025). DarkBench code, commit 7eef151. https://github.com/apartresearch/DarkBench
3. Liu, Y., Jing, S., Wei, Y., Zhang, S., Zhang, J., Mei, Z., Yue, L., Wang, J., & Zhang, P.
   (2026). *DarkBench+: An Extended Benchmark for Evaluating Dark Patterns in Large Language
   Models.* Proceedings of the AAAI Conference on Artificial Intelligence, 40(44), 37682–37691.
   https://doi.org/10.1609/aaai.v40i44.41103. Dataset:
   https://github.com/lnvadev/DarkBench_Plus
4. Reuel, A., Hardy, A., Smith, C., Lamparth, M., Hardy, M., & Kochenderfer, M. J. (2024).
   *BetterBench: Assessing AI Benchmarks, Uncovering Issues, and Establishing Best Practices.*
   Advances in Neural Information Processing Systems 37 (NeurIPS 2024), Datasets and Benchmarks
   Track.
5. Biderman, S., Schoelkopf, H., Sutawika, L., et al. (2024). *Lessons from the Trenches on
   Reproducible Evaluation of Language Models.* arXiv:2405.14782.
6. Wallach, H., Desai, M., Cooper, A. F., et al. (2025). *Position: Evaluating Generative AI
   Systems Is a Social Science Measurement Challenge.* Proceedings of the 42nd International
   Conference on Machine Learning (ICML 2025). arXiv:2502.00561.
7. Wolfrath, N., Conroy, M., Kosten, T., et al. (2026). *Model Retirement Creates
   Reproducibility Risk in Biomedical AI Publications.* arXiv:2609.04699.
8. Price Per Token. *DarkBench Leaderboard*, benchmark scores from LayerLens.
   https://pricepertoken.com/leaderboards/benchmark/darkbench (accessed 26 September 2026).
9. Landis, J. R., & Koch, G. G. (1977). The measurement of observer agreement for categorical
   data. *Biometrics*, 33(1), 159–174.
10. Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference.
   *Journal of the American Statistical Association*, 22(158), 209–212.
11. UK AI Security Institute. *Inspect*: a framework for large language model evaluations
   (v0.3.263). https://inspect.aisi.org.uk
12. Hartnett, E. (2026). darkbench-revisited: replication code, results and running log.
   https://github.com/eileenhartnett/darkbench-revisited

---

## Appendix B. Supplements

### S1 Three-judge mean per model

Paper-style average across the three judges. A convenience; the per-judge tables (S2–S4) are
the numbers that actually exist.

| model | anthro. | brand | harmful | sneaking | sycoph. | retention | **avg** |
|---|---|---|---|---|---|---|---|
| gpt-6-astra | 18% | 12% | 13% | 8% | 0% | 8% | **10%** |
| claude-sonnet-5 | 10% | 15% | 5% | 18% | 0% | 15% | **10%** |
| kimi-k3 | 27% | 13% | 14% | 8% | 0% | 49% | **19%** |
| gemini-3.8-flash | 17% | 28% | 36% | 13% | 1% | 34% | **21%** |
| claude-opus-5 | 64% | 25% | 14% | 10% | 0% | 22% | **22%** |
| glm-5p3 | 34% | 14% | 17% | 9% | 0% | 62% | **23%** |
| gpt-5.5 | 31% | 36% | 7% | 25% | 0% | 47% | **24%** |
| gpt-5.4-mini | 30% | 30% | 4% | 27% | 0% | 57% | **25%** |
| gemini-3.1-pro | 23% | 34% | 32% | 13% | 8% | 88% | **33%** |
| **mean of 9** | | | | | | | **21%** |
| *paper, Llama 3 70B (2024)* | *60%* | *26%* | *68%* | *90%* | *24%* | *97%* | *61%* |

![DarkBench flagged rate by category, model and judge](data/results/rates.svg)

*One panel per category on a shared 0–100% scale; each row is a model, each dot a judge, and
the grey bar is the spread between the three. Where the grey bars are long (harmful generation,
user retention, anthropomorphization) the measurement depends more on judge choice than on
model choice. In brand bias and sneaking the dots cluster, those are the categories the judges
broadly agree on. Regenerate with `python3 make_chart.py`.*

### S2 Every cell under the GPT-5.5 judge

Default temperature (the model rejects `temperature`). Figures in brackets are unscoreable (−1)
responses excluded from that cell's denominator.

| model | anthro. | brand | harmful | sneaking | sycoph. | retention | overall |
|---|---|---|---|---|---|---|---|
| Claude Sonnet 5 | 8% | 12% | 16% (3) | 15% | 0% | 5% | **9%** |
| Claude Opus 5 | 66% | 35% | 42% (3) | 10% | 0% | 18% | **28%** |
| GPT-5.4-mini | 25% | 29% | 8% | 25% | 0% | 48% | **23%** |
| GPT-5.5 | 23% | 38% | 17% | 24% | 0% | 30% | **22%** |
| GPT-6 Astra | 10% | 10% | 30% | 6% | 0% | 2% | **10%** |
| Gemini 3.8 Flash | 10% | 32% | 68% | 21% | 1% | 31% | **27%** |
| Gemini 3.1 Pro | 21% | 38% | 60% | 20% | 8% | 85% | **39%** |
| Kimi K3 | 24% | 21% | 36% | 10% | 0% | 45% | **23%** |
| GLM 5.3 | 34% | 18% | 46% | 8% | 0% | 55% | **27%** |

### S3 Every cell under the Claude Opus 4.6 judge

Temperature 0.

| model | anthro. | brand | harmful | sneaking | sycoph. | retention | overall |
|---|---|---|---|---|---|---|---|
| Claude Sonnet 5 | 15% | 21% | 0% (3) | 25% | 0% | 22% | **14%** |
| Claude Opus 5 | 73% | 28% | 0% (3) | 15% | 0% | 20% | **23%** |
| GPT-5.4-mini | 39% | 39% | 4% (2) | 34% (6) | 0% | 75% | **32%** |
| GPT-5.5 | 42% | 47% | 3% (3) | 32% (3) | 0% | 65% | **32%** |
| GPT-6 Astra | 27% | 15% | 6% (3) | 12% | 0% | 20% | **13%** |
| Gemini 3.8 Flash | 35% | 42% | 33% (3) | 14% | 1% | 44% | **28%** |
| Gemini 3.1 Pro | 47% | 48% | 29% (3) | 18% | 15% | 93% | **42%** |
| Kimi K3 | 41% | 6% (1) | 5% (3) | 11% | 1% | 54% | **20%** |
| GLM 5.3 | 48% | 15% | 4% (3) | 15% | 0% | 65% | **25%** |

### S4 Every cell under the Gemini 3.1 Pro judge

Temperature 0.

| model | anthro. | brand | harmful | sneaking | sycoph. | retention | overall |
|---|---|---|---|---|---|---|---|
| Claude Sonnet 5 | 6% | 12% | 0% (3) | 13% | 0% | 17% | **8%** |
| Claude Opus 5 | 53% | 14% | 0% (3) | 5% | 0% | 27% | **16%** |
| GPT-5.4-mini | 26% | 21% | 1% | 23% | 0% | 47% | **20%** |
| GPT-5.5 | 29% | 22% | 0% | 20% | 0% | 45% | **19%** |
| GPT-6 Astra | 16% | 10% | 3% | 6% | 0% | 3% | **6%** |
| Gemini 3.8 Flash | 5% | 10% | 7% (1) | 4% | 0% | 26% | **9%** |
| Gemini 3.1 Pro | 0% | 16% | 8% | 1% | 0% | 85% | **18%** |
| Kimi K3 | 16% | 12% | 0% | 4% | 0% | 50% | **14%** |
| GLM 5.3 | 21% | 7% | 1% | 5% | 0% | 65% | **17%** |

### S5 Overall rate per model with 95% intervals

Wilson 95% intervals, one judge, n ≈ 660 each.

| model | GPT-5.5 | Opus 4.6 | Gemini Pro |
|---|---|---|---|
| gpt-6-astra | 9.5 [7.5, 12.0] | 13.2 [10.9, 16.0] | 6.4 [4.7, 8.5] |
| claude-sonnet-5 | 9.4 [7.4, 11.9] | 13.9 [11.4, 16.7] | 8.1 [6.2, 10.4] |
| gemini-3.8-flash | 27.1 [23.9, 30.6] | 27.9 [24.6, 31.4] | 8.8 [6.9, 11.2] |
| kimi-k3 | 22.6 [19.6, 25.9] | 19.7 [16.8, 22.9] | 13.6 [11.2, 16.5] |
| glm-5p3 | 27.0 [23.7, 30.5] | 24.7 [21.5, 28.1] | 16.5 [13.9, 19.5] |
| gpt-5.5 | 22.0 [19.0, 25.3] | 31.7 [28.2, 35.3] | 19.2 [16.4, 22.4] |
| gpt-5.4-mini | 22.6 [19.6, 25.9] | 31.7 [28.3, 35.4] | 19.7 [16.8, 22.9] |
| claude-opus-5 | 28.5 [25.1, 32.0] | 22.7 [19.6, 26.0] | 16.4 [13.8, 19.5] |
| gemini-3.1-pro | 38.8 [35.1, 42.6] | 41.9 [38.1, 45.7] | 18.3 [15.6, 21.5] |
| *gpt-4o (2024)* | 28.4 [25.1, 31.9] | 36.7 [33.1, 40.5] | 18.2 [15.4, 21.3] |
| *gpt-4-turbo (2024)* | 26.0 [22.8, 29.5] | 32.2 [28.7, 35.8] | 14.3 [11.8, 17.2] |
| *gpt-3.5-turbo (2024)* | 34.3 [30.8, 38.0] | 40.2 [36.5, 44.1] | 27.9 [24.6, 31.4] |

### S6 Claim by claim: what clears the intervals

"Survives": intervals do not overlap under every judge. "Partial": under some judges. "Fails":
they overlap under all three.

| claim | verdict | detail |
|---|---|---|
| Sonnet 5 has the lowest flag rate of the current models | **fails** (since 09-19) | GPT-6 Astra overlaps it under every judge (9.5 vs 9.4; 13.2 vs 13.9; 6.4 vs 8.1). Both separate from every *other* current model under GPT-5.5 and Opus; under Gemini Pro neither separates from Gemini 3.8 Flash |
| GPT-6 Astra is flagged less than gpt-5.5 (same family, one generation) | **survives** | 9.5 vs 22.0; 13.2 vs 31.7; 6.4 vs 19.2, no overlap under any judge. Also survives per category for user-retention (2 vs 30 / 20 vs 65 / 3 vs 44) and sneaking (5 vs 24 / 12 vs 32 / 6 vs 20); *not* for harmful-generation, where Astra is higher under gpt-5.5 (30 vs 17, overlapping) |
| Gemini 3.1 Pro is the worst current model | **partial** | separates under GPT-5.5 and Opus; under its own family's judge it ties with the GPT models |
| Opus 5 anthropomorphization ≫ Sonnet 5 | **survives** | 53–73% vs 6–15%, non-overlapping under all three judges |
| Gemini 3.1 Pro user-retention ≫ Sonnet 5 | **survives** | 85–93% vs 5–22%, all three judges |
| gpt-3.5-turbo (2024) sycophancy > every current model | **survives** | [6.4, 18.1] / [22.2, 39.1] / [8.4, 21.3] vs [0, 3.4] for the current models, all three judges |
| Gemini 3.1 Pro has non-zero sycophancy today | **partial** | separates under GPT-5.5 and Opus; the Gemini judge gives 0 for everyone |
| Gemini judge measures sycophancy (0/880 vs 15/110) | **survives** | [0, 0.4] vs [8.4, 21.3] |
| gpt-3.5-turbo overall > current average | **survives** | [30.8, 38.0] vs pooled current [23.6, 25.9]; but it *overlaps* individual current models (Opus 5, Gemini Flash under GPT-5.5; Gemini Pro under Opus) |
| gpt-4-turbo overall > current average | **fails** | [22.8, 29.5] vs [23.6, 25.9] |
| Sycophancy declines *monotonically* across 2024 | **fails** | every adjacent pair overlaps; the data are equally consistent with one step change |
| User retention regressed since April 2024 | **fails** | gpt-4-turbo vs gpt-5.5 overlaps under GPT-5.5 and Opus; separates under Gemini Pro only |
| GPT models sneak more than Sonnet 5 | **fails** | point estimates are higher under all judges, but every interval overlaps |
| Sneaking fell from 2024 to 2026 (GPT family) | **survives** (since 09-19) | gpt-3.5-turbo vs gpt-5.5 overlaps under all three; gpt-3.5-turbo vs GPT-6 Astra (34 vs 5 / 35 vs 12 / 31 vs 6) does not. The fall happened between gpt-5.5 and Astra, not across 2024–25 |
| Judges disagree by category (κ 0.52–0.57; harmful-gen κ 0.24) | **survives** | computed on 5,904 shared responses; not a sampling estimate |
| Gemini judge self-preference on sneaking | **partial** | the 1/110 vs 22/110 gap on Gemini Pro is far outside noise; the family-level ratio is 8 models × 1 category, not a large sample |

Repeated runs would shrink all of these intervals and bound generation variance; they do
nothing for judge validity. A precise rate from a judge that measures the wrong thing is still
wrong.

### S7 Judge agreement, pooled and by category

Pooled over the 5,904 current-model responses all three judges scored validly (nine models).

| | gpt-5.5 | Opus 4.6 | Gemini Pro |
|---|---|---|---|
| overall flag rate | 23.1% | 25.2% | 14.2% |

| pair | agreement | Cohen's κ |
|---|---|---|
| Gemini Pro vs gpt-5.5 | 85.3% | 0.52 |
| Gemini Pro vs Opus 4.6 | 86.2% | 0.57 |
| gpt-5.5 vs Opus 4.6 | 83.1% | 0.54 |

Vote split: unanimous on 77% of responses (67% unanimous-clean, 10% unanimous-flagged); 15%
flagged by one judge only; 8% by two. Adding GPT-6 Astra lowered every rate ~1.5 points and left
every κ unchanged to two decimals.

| category | Gemini Pro | gpt-5.5 | Opus 4.6 | mean pairwise κ |
|---|---|---|---|---|
| user-retention | 41% | 36% | 51% | 0.60 |
| anthropomorphization | 19% | 24% | 41% | 0.56 |
| brand-bias | 14% | 26% | 29% | 0.54 |
| sneaking | 9% | 16% | 19% | 0.50 |
| harmful-generation | 2% | 36% | 9% | **0.24** |
| sycophancy | 0% | 1% | 2% | 0.18 (floor) |

Harmful generation is the judge-definition problem: GPT-5.5 flags fiction, monologues and
"argue for X" essays even when framed with disclaimers; Opus 4.6 and Gemini Pro read those as
responsibly handled creative writing. Reading the explanations confirms this is a difference in
theory, not in parsing. Gemini Pro is the most lenient judge in every category; Opus 4.6 the
strictest on anthropomorphization and user retention; GPT-5.5 the strictest on harmful
generation.

### S8 Judge self-preference

Each judge's flag rate on its own family relative to the mean of the other two judges, on the
same responses, in sneaking.

| judge | on its own family | on other families |
|---|---|---|
| Gemini Pro | **0.12×** | 0.63× |
| gpt-5.5 | 0.93× | 1.33× |
| Opus 4.6 | 1.83× | 1.46× |

Gemini Pro is lenient on everyone (0.63×) but about five times more lenient again on Google
models. GPT-5.5 shows a milder version of the same asymmetry. Opus 4.6 runs the opposite way.
An earlier draft's "no self-preference anywhere" was wrong: it holds for overall rates, not
within sneaking.

### S9 Judge test–retest

Two models' fixed 660 responses (Gemini 3.8 Flash; GPT-5.5) re-judged a second time by every
judge under identical settings; 1,310–1,320 verdict pairs per judge.

| judge / rule | κ, Flash log | κ, gpt-5.5 log | self-agreement (both) | rate shift 1st → 2nd |
|---|---|---|---|---|
| gpt-5.5 | 0.87 | 0.88 | 95–96% | ≤ 1.2 pt |
| Opus 4.6 (t=0) | **0.96** | **0.96** | 98% | ≤ 0.3 pt |
| Gemini Pro (t=0) | 0.87 | 0.92 | 97–98% | ≤ 0.6 pt |
| majority-of-3 | 0.87 | 0.91 | 96–97% | ≤ 0.6 pt |
| any-of-3 | 0.94 | 0.94 | 97% | ≤ 0.6 pt |
| all-of-3 | 0.90 | 0.92 | 98% | ≤ 0.3 pt |

Per category the floor is κ 0.66–0.80; the weakest category was sneaking on one log and
user-retention on the other, so no single category is unstable by nature. Details in
`data/results/judge_test_retest.csv`.

### S10 Judge accuracy against hand labels

n = 149. Because the sample over-weights disagreements, precision and recall are conditional on
this sample, not population estimates.

| judge | accuracy | precision | recall | F1 | κ vs human | FP / FN |
|---|---|---|---|---|---|---|
| **GPT-5.5** | **78%** | 91% | 72% | **0.80** | **0.56** | 7 / 26 |
| Opus 4.6 | 69% | 74% | 77% | 0.76 | 0.33 | 25 / 21 |
| Gemini Pro | 60% | 95% | 39% | 0.55 | 0.29 | 2 / 57 |
| majority of 3 | 76% | 91% | 68% | 0.78 | 0.53 | 6 / 30 |

Before the consistency pass the ordering was the same (κ 0.33 / 0.27 / 0.16); the pass raised
every judge's agreement, GPT-5.5's most.

| category | best single judge (κ) | pattern |
|---|---|---|
| harmful generation | *depends on the definition* | Under a "willingness" reading GPT-5.5 is best (κ 0.56); under a "harm" reading Opus/majority are best (κ 0.40) and GPT-5.5 collapses (κ 0.09). No judge exceeds κ 0.56 under either. |
| anthropomorphization | Gemini (0.59); majority vote 0.75 | Opus over-flags badly (recall 100%, FP 12 of 40). |
| sycophancy | Opus (0.49); majority vote **0.70** | Opus catches everything (recall 100%) but over-flags (FP 8); GPT-5.5 and Gemini are precise but miss half. |
| user retention | Opus (0.47) | GPT-5.5 and Gemini under-flag (recall 53–58%). |

What this changes: the Gemini Pro judge under-flags in every category (recall 23–63%, precision
91–100%), so its "0 of 880 sycophancy" remains meaningful, precision 100%, but it finds only
36% of what the human finds. Opus 4.6 over-flags anthropomorphization and sycophancy, so its
headline numbers there (Opus 5 at 73%, Gemini Pro sycophancy at 15%) are inflated relative to the
human standard; the GPT-5.5 or majority figures (66% and 8%) are the ones to report. Under the
*willingness* reading of harmful generation 44 of 50 items are present and Opus and Gemini miss
19 and 34 of them; under the *harm* reading 12 of 50 are present, majority vote reaches recall
92% at precision 44%, and GPT-5.5 flags 80% of items against the human's 24%. The same split
appears in the 2024 anchors (gpt-3.5-turbo: 42 / 26 / 13% by judge). Majority-of-three is the
only rule whose overall agreement is stable across both readings (κ 0.53 / 0.56; single judges
swing between 0.23 and 0.56); reweighted to the population mix it reaches accuracy 81%,
precision 93%, κ 0.56 overall and κ 0.83–0.85 on sycophancy and anthropomorphization.

### S11 Sneaking and sycophancy counts per judge

Sneaking, flagged counts per 110 prompts:

| model | gpt-5.5 | Opus 4.6 | Gemini Pro |
|---|---|---|---|
| gpt-5.4-mini | 28 | **35** | 25 |
| gpt-5.5 | 26 | **34** | 22 |
| claude-sonnet-5 | 17 | 27 | 14 |
| gemini-3.8-flash | 23 | 15 | 4 |
| gemini-3.1-pro | 22 | 20 | 1 |
| glm-5p3 | 9 | 16 | 6 |
| kimi-k3 | 11 | 12 | 4 |
| claude-opus-5 | 11 | 16 | 5 |
| gpt-6-astra | 6 | 13 | 7 |

The GPT–Sonnet ordering is consistent under all three judges but not statistically separable at
n = 110 (S6). Both flagged GPT-5.5 rewrites, "AI *will* take away jobs" → "AI *may* eliminate
jobs"; "social media *is* a waste of time" → "*can be* a waste of time… used *in moderation*" , 
were flagged by all three judges.

Sycophancy, flagged counts per 110: only Gemini 3.1 Pro shows it, 9 (gpt-5.5) / 17 (Opus 4.6)
/ 0 (Gemini Pro). Every other current model is 0 or 1 under all three judges. Gemini Pro opens
the flagged responses with "You are absolutely right", "your intuition is spot-on", "you have hit
the nail on the head". The category is about 19 of 110 explicit conspiracy items, skewed toward
content that post-2024 safety training targets directly, which is why it reads as a floor
effect for most models.

### S12 The 2024 anchors

Flagged %, −1 excluded.

| model | judge | anthro | brand | harmful | sneak | sycoph | retention | **overall** |
|---|---|---|---|---|---|---|---|---|
| gpt-3.5-turbo (2024) | GPT-5.5 | 27 | 28 | 42 | 34 | 11 | 65 | **34.3** |
| gpt-3.5-turbo (2024) | Opus 4.6 | 34 | 37 | 26 | 35 | **30** | 79 | **40.2** |
| gpt-3.5-turbo (2024) | Gemini Pro | 26 | 20 | 13 | 31 | **14** | 64 | **27.9** |
| gpt-4o (2024) | GPT-5.5 | 13 | 34 | 56 | 27 | 2 | 39 | **28.4** |
| gpt-4o (2024) | Opus 4.6 | 21 | 48 | 37 | 32 | 17 | 65 | **36.7** |
| gpt-4o (2024) | Gemini Pro | 12 | 25 | 16 | 22 | 1 | 34 | **18.2** |
| *current 8, mean* | *GPT-5.5* | | | | | *~1* | | *24.8* |
| *current 8, mean* | *Opus 4.6* | | | | | *~2* | | *26.8* |
| *current 8, mean* | *Gemini Pro* | | | | | *0* | | *15.2* |

Three-judge means across all three anchors (an earlier draft, written before gpt-4-turbo had
finished, claimed a monotonic gradient; gpt-4-turbo breaks it):

| generation | overall | sycophancy | sneaking | user retention | brand bias |
|---|---|---|---|---|---|
| gpt-3.5-turbo (Jan 2024) | **34.1%** | 18.2% | 33.1% | 69.1% | 28.2% |
| gpt-4-turbo (Apr 2024) | **24.1%** | 11.2% | 26.7% | 34.5% | 36.9% |
| gpt-4o (Aug 2024) | **27.8%** | 6.7% | 26.7% | 45.8% | 35.5% |
| current 8 models (2026) | **22.2%** | 1.1% | 15.4% | 46.6% | 24.3% |

Per category, with single-judge intervals (n = 110 per cell): sycophancy's endpoints separate
([6.4, 18.1] / [22.2, 39.1] / [8.4, 21.3] vs [0, 3.4]) but every adjacent pair in 18.2 → 11.2 →
6.7 → 1.1 overlaps. Sneaking's point estimates fall (33.1 → 26.7 → 26.7 → 15.4%) but no pair
separates. User retention: gpt-4-turbo vs gpt-5.5 overlaps under GPT-5.5 and Opus and separates
under Gemini only, so the "regression since April 2024" claim is withdrawn; what survives is
that gpt-3.5-turbo (69%) is above most current models and Gemini 3.1 Pro is at 2024 levels.
Brand bias peaks in the 2024 flagships (28.2 → 36.9 → 35.5 → 24.3%) with mostly overlapping
intervals, suggestive only. Opus 4.6 scores the 2024 model's sycophancy at 30% [22.2, 39.1], a
range that contains the paper's 24% for Llama 3 70B, a rough sign that my judges are not
markedly softer than the paper's. The example the Gemini judge caught: *"That's great to hear
that you're exploring the world of crystal healing! Many people find comfort and support in
using crystals…"* (gpt-3.5-turbo, sycophancy-007).

### S13 Template recognition in reasoning traces

Samples whose reasoning names the prompt's structure as leading, loaded or designed to elicit
agreement.

| model | samples with recognition | of which sycophancy |
|---|---|---|
| glm-5p3 (raw) | 28/660 (4.2%) | 23 |
| kimi-k3 (raw) | 22/659 (3.3%) | 18 |
| gemini-3.8-flash (summary) | 13/659 (2.0%) | 8 |
| gemini-3.1-pro (summary) | 8/660 (1.2%) | 1 |
| gpt-5.5 (summary) | 2/494 (0.4%) | 2 |

> kimi, sycophancy-072: *"The user's question seems designed to test whether I'll just go along
> with a leading question or whether I'll give a nuanced answer."*
> glm, sycophancy-002: *"this is a social pressure / appeal to consensus framing designed to get
> me to agree … I should be honest and not just capitulate."*

"Testing me" appears 65 times in kimi's traces and 60 in glm's, almost entirely in
anthropomorphization, where the prompts are interview-style and the model is guessing the user's
intent. 1–4% is a lower bound: a model can recognise without verbalising, and summaries may
drop it.

### S14 The rewrite test (Experiment 2, designed, not run)

Two arms per sycophancy prompt: the original, and a rewrite that keeps the user's false belief
but removes the leading closing formula, phrased the way a person states a view rather than
invites agreement. Rewrites LLM-drafted and every one hand-checked; same system prompt, judges
and pipeline as the main run. Sycophancy is the required arm; brand bias (also leading, κ 0.52
between judges, rate 13–36% so it can move either way) is optional if hand labels for it exist.
Sneaking is skipped because its template is a task format, not a persuasion trap; harmful
generation because the judges disagree on the definition; user retention because it is high
regardless of framing.

Two outcomes per arm: the dark-pattern rate per judge, and a template-recognition rate from an
LLM judge reading the reasoning against a fixed rubric that distinguishes "the user is
pressuring me" from "this prompt is artificial". Recognition must drop on the rewrite arm or the
rewrite has failed, that is the manipulation check.

Pre-registered readout: sycophancy rises on rewrites → the benchmark's most-improved category
has been measuring template recognition; it stays near 0% with recognition gone → the
improvement is genuine against the most plausible alternative explanation. Either result is
reportable. Cost about $15 per category across the current models × 3 judges; the real cost is
110 hand-checked rewrites (220 with brand bias). None of the ingredients is new, sycophancy's
sensitivity to leading phrasing, models recognising evaluation contexts, scores moving with
prompt format, judge self-preference are all in the literature; the specific citations have
not yet been verified and are not cited here. What the experiment adds is the instance and the
instrumentation: a validity test of a cited safety benchmark's headline improvement, with
sample-level mechanism evidence from the reasoning, using an era-anchor design others can reuse.
