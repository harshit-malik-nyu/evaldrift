# Related work, and what this project adds after finding it

Partway through building this, I found concurrent work that does much of what
it does, more rigorously.

**Solomon Messing, "Hidden Measurement Error in LLM Pipelines Distorts
Annotation, Evaluation, and Benchmarking"** (arXiv 2604.11581, May 2026) builds
a full variance-decomposition framework — Total Evaluation Error — over LLM
pipelines: a linear mixed model with item, prompt, temperature, judge and
replication facets, REML estimation, D-study projections for budget allocation,
and Monte Carlo validation under five misspecification scenarios.

That is a more complete treatment of the same problem, and it should be read
first.

## What it establishes that this project also argues

| Claim here | Their result |
|---|---|
| Benchmarks cannot resolve the differences they report | Naive standard errors are **40–60% smaller** than TEE-corrected ones |
| Prompt variance does not shrink with more items | Naive 95% CI coverage **falls as n grows**, from nominal at n=100 to **79% at n=2,000** |
| Items are clustered, and it matters | Within-category item heterogeneity is **35.0%** of Var(θ̂) on MMLU |
| The standard check is the weakest one | Of 13 surveyed benchmarks, **most report no uncertainty at all**; the four with CIs capture only item sampling |

Independent confirmation of a conclusion is worth more than another derivation
of it, and their derivation is better.

## What it answers that was open here

The noise floor. This project built a harness to measure run-to-run
self-disagreement and never ran it at scale.

Their decomposition measures it directly. **Replicate noise — repeated API
calls with identical inputs — is 21% of per-observation variance** in their
safety demonstration, from a design of 8 replications per cell across 50,760
calls.

That is the quantity the harness was for, measured properly, by someone who ran
it.

Their framing of it is the part worth carrying: replicate noise is large per
observation but contributes **under 0.5% of the variance of the mean** at R=8,
because it divides by every other factor count. It is noise that *averaging
fixes*. Prompt and judge variance are not, which is why those dominate the
corrected interval.

**That sharpens this project's conclusion rather than confirming it.** The
harness measures the one variance component that more replication actually
solves. The components that matter are the ones it does not measure.

## What this project still adds

Narrower, and worth being precise about.

**Per-benchmark resolution against published sizes.** Their framework tells a
team how to decompose its own pipeline. It does not answer "can GPQA Diamond,
at 198 items, support the two-point claim in this announcement?" That question
needs only published split sizes, and `evaldrift check 0.02 198` answers it
with an exit code.

**Design effects from documented cluster structure.** They estimate item
heterogeneity as a variance component. This project takes the further step of
converting documented groupings — MMLU's 57 subjects, MMLU-Pro's 14 categories
— into an **effective sample size** and a **flip point**: the correlation at
which a specific benchmark stops supporting a specific claim. MMLU's 14,042
items behave like roughly 373 independent ones at the estimated ICC.

I have not found that calculation published for LLM benchmarks, including in
their paper.

**A gate rather than a framework.** Their contribution is a method and an R
package for teams willing to run a 540-call pilot. This is a check that runs in
CI with no model calls at all.

## The honest summary

If a team can run the pilot, they should use TEE. It is the better instrument
and it answers more questions.

This project is useful in the narrower case where someone is reading a claim
rather than producing one, and wants to know whether the benchmark behind it
could have supported it. That is a smaller contribution than it looked like
before I found this paper, and saying so is more useful than not having looked.

## Other work this paper surfaced

Each of these is a stronger single fact than anything measured here:

- **Sclar et al. 2024**: formatting choices alone produce up to **76 accuracy
  points** of spread on identical models
- **Alzahrani et al. 2024**: minor reorderings of answer choices shift MMLU
  leaderboard rankings by up to **8 positions**
- **Yuan et al. 2025**: infrastructure nondeterminism shifts results by up to
  **9 percentage points even at temperature zero**
- **Huang et al. 2026**: dropping **0.003%** of Chatbot Arena human preferences
  flips the top-ranked model
- **Singh et al. 2025**: Meta ran 27 private Llama-4 variants on Chatbot Arena
  and published only the top scorer; best-of-K=27 inflates Elo by **56 points**
- **Li et al. 2024**: only **22.6%** of MT-Bench model pairs have
  non-overlapping confidence intervals
