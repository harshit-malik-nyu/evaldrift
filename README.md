# Can you tell when a model got worse?

**Mostly, no — and the reason is arithmetic, not tooling.**

A benchmark is a measurement instrument with a resolution, set almost entirely
by how many items it has. Below that resolution it reports noise. This project
measures the resolution of the evaluations people actually quote, shows what
the standard regression check misses, and identifies what would catch it.

Every finding below is either computed from published benchmark sizes or
pinned by a test. Nothing is simulated and presented as a result.

---

## What the evidence shows

### Most quoted benchmarks cannot resolve a two-point change

| Benchmark | Items | Smallest detectable change | 2-point claim | Items needed |
|---|---:|---:|:---:|---:|
| HumanEval | 164 | **9.3%** | ✗ | 3,532 |
| GPQA Diamond | 198 | **12.9%** | ✗ | 8,242 |
| TruthfulQA | 817 | 6.4% | ✗ | 8,242 |
| ARC-Challenge | 1,172 | 2.5% | ✗ | 1,865 |
| GSM8K | 1,319 | 2.4% | ✗ | 1,865 |
| MATH | 5,000 | 2.2% | ✗ | 6,280 |
| HellaSwag | 10,042 | 0.9% | ✓ | 1,865 |
| MMLU-Pro | 12,032 | 1.6% | ✓ | 7,359 |
| MMLU | 14,042 | 1.1% | ✓ | 4,145 |

**Six of nine cannot distinguish a two-point improvement from noise.**

GPQA Diamond appears in nearly every frontier model announcement. At 198 items
it cannot resolve anything under about thirteen points. A two-point claim on it
needs 8,242 items — 42 times its size.

This finding needs no model outputs. Resolution follows from item count and
accuracy range, both public, so it holds regardless of which model is measured.

**On the accuracy assumption.** Item counts are published; the accuracy levels
are my estimates of where frontier models currently score. Binomial variance
peaks at 50%, and the estimates lean high, which narrows every interval. At the
worst case of 50% accuracy the intervals widen by 1.1x to 2.3x. The estimates
err in the direction that weakens the finding, and the verdict holds at 50%.

### The standard check fires on noise the right test ignores

The check most teams run is: did the headline score drop by more than a margin?

In the worked example, a run loses 18 items and gains 15 — a coin flip,
McNemar p = 0.73. **The aggregate rule fires. The paired test correctly stays
silent.** An engineering team investigates nothing.

### A flat aggregate can hide a failed capability

Two runs scoring 70% need not be the same 70%. A model can lose three hundred
items and gain three hundred different ones and report an identical score.

In the worked example the aggregate moves −1.25% — inside the noise floor for
2,000 items, so no dashboard flags it. Inside that release, **coding regressed
8.4% at p < 0.0001.** The headline shows nothing actionable; the segment
breakdown shows an unambiguous failure.

Most pipelines already produce the per-item results that reveal this, then
discard them at the aggregation step.

### Correcting for item clustering, effectively nothing survives

`power.py` assumes benchmark items are independent. They are not: MMLU's 14,042
items sit in 57 subjects, MMLU-Pro's 12,032 in 14 categories. A model failing
one college-chemistry question is likelier to fail the next.

Standard survey statistics applies — `DEFF = 1 + (m − 1) × ICC` — and because
design effect scales with **cluster size**, benchmarks with hundreds of items
per cluster are sensitive to tiny correlations.

| Benchmark | Items | Clusters | Per cluster | Fails a 2-point claim at |
|---|---:|---|---:|---|
| MMLU | 14,042 | 57 subjects | 246 | **ICC 0.003** |
| MMLU-Pro | 12,032 | 14 categorys | 859 | **ICC 0.001** |
| MATH | 5,000 | 7 subjects | 714 | never supported it |
| GPQA Diamond | 198 | 3 domains | 66 | never supported it |
| TruthfulQA | 817 | 38 categorys | 22 | never supported it |

**MMLU fails at ICC 0.003. MMLU-Pro at ICC 0.001.** Those are
correlations of a third and a tenth of one percent — far below anything
plausible for items grouped by subject. The three that were already failing
stay failing.

So the "six of nine" headline is the *generous* reading. Under any realistic
clustering, none of these benchmarks resolves a two-point change.

**Where this correction does and does not apply.** It governs claims that
generalise beyond the sampled clusters — "better at graduate science", which is
what model announcements assert. It does not apply to a benchmark used as a
frozen tripwire on a fixed item set, where the items are a census rather than a
sample. Both claims get made from the same number; only the first is bounded
here.

### The correlation is not hypothetical — it can be estimated

No ICC has been published for an LLM benchmark, but per-subject accuracies
have, and the spread between subjects is itself evidence about clustering.

Using the YourBench replication (arXiv 2504.01833), which reports per-subject
accuracy **with standard errors** on original MMLU subsets:

| Model | Estimated ICC |
|---|---:|
| Qwen2.5 7B | **0.149** |
| Qwen1 7B | **0.097** |

Sampling noise is subtracted before estimating — each subject's accuracy is
measured on finite items, so part of the observed spread is not real. Omitting
that correction inflates ICC, which is the direction that would flatter this
conclusion, so the uncorrected figure is reported alongside it in the code.

**Applying the estimate to MMLU:**

| | |
|---|---:|
| Design effect | **38×** |
| Effective sample size | **373** (from 14,042) |
| Minimum detectable effect | 1.4% → **8.6%** |

MMLU's 14,042 items behave like roughly **373** independent
ones, and it resolves about **9%**, not one.

Four subjects of one model is a small basis for a variance component, and the
interval on it would be wide. It settles the question anyway: the threshold it
must clear is 50 times smaller. An estimate can be badly
wrong and still be decisive when the margin is that large — which is the only
reason a four-cluster estimate is worth reporting.

Two independently reported models give 0.149 and 0.097. Both
clear the threshold by more than an order of magnitude.

### Paired testing needs roughly three times fewer items

Successive model versions agree on most items. A paired test compares only the
items that changed, so its power depends on how much the runs disagree:

| Runs disagree on | Items to detect a 1% regression |
|---|---:|
| 42% (unrelated models) | 32,966 |
| 15% (adjacent versions) | **11,774** |
| 8% (minor revision) | **6,280** |

Most eval pipelines already score the identical item set twice, then compare
only the two totals — discarding a near threefold gain in sensitivity.

---

## The measurement that matters most

**[The noise-floor harness](harness.html)** runs the identical model twice over
the identical items. Any disagreement is noise by construction — there is no
model change to explain it.

That number is the floor below which no regression can be distinguished from
chance, and almost nobody measures it. Every detector threshold is therefore
chosen by intuition.

Ground truth here is free. The model did not change between passes, so every
flipped item is a false signal, with no labelling and no judgment — the same
construction that makes a control group work.

The harness runs 120 real GSM8K items from a fixed seeded sample. It calls the
model API directly and so runs as a Claude artifact; the committed repository
carries the instrument and the item set.

### The floor is already published — by the benchmark authors

The harness was built because no published floor was known. One exists, it is
better sourced than anything measured here could be, and it comes from the
paper that introduced MMLU-Pro.

Wang et al. evaluated models under **24 different but reasonable prompts**,
holding the model and the items fixed. Every point of spread is measurement
error:

| Benchmark | Typical prompt variance | Peak |
|---|---:|---:|
| MMLU | **4.5%** | 10.98% |
| MMLU-Pro | **2.0%** | 3.74% |

Set against what the same paper reports for the gaps being measured: frontier
models cluster within **2–4%** of each other on MMLU.

**On MMLU the measurement error is larger than the differences being
measured** — a signal-to-noise ratio of 0.67.
On MMLU-Pro it is 1.50, which is better and is
why the successor benchmark exists.

**And this variance does not shrink with more items.** Sampling error falls as
one over root n; prompt sensitivity does not fall at all, because it is not
sampling error. A bigger benchmark does not fix it. That makes it a harder
constraint than everything else on this page.

One widely repeated figure — "13 percentage points of reproducibility variance
for GPT-4o on MMLU-Pro" — appears only in secondary commentary with no
traceable primary source, so it is excluded. It would have strengthened the
argument, which is why it was checked.

**The harness still has a job**: a team's own floor, on its own items and
decoding settings. But whether the floor is large enough to matter was settled
in the MMLU-Pro paper.

#### Would the recommendation change if the floor came back low?

Worth asking directly, because if the answer is no the harness is decoration.

| Measured floor | Paired resolves, 300 items | Items to resolve 2 points |
|---:|---:|---:|
| 2% | 2.3% | 393 |
| 5% | 3.6% | 982 |
| 8% | 4.6% | 1,570 |
| 15% | 6.3% | 2,944 |
| 25% | 8.1% | 4,906 |

**The recommendation holds at every plausible floor** — paired testing beats
the aggregate rule, which resolves 10.5% on 300 items regardless, across the
whole range.

What moves is the *sizing*: 393 items against 4,906, a twelvefold swing in what
you would have to build. So the floor does not validate the recommendation; it
tells you how large your evaluation needs to be to act on it. That is the
actionable number, and it is the one nobody has.

---

## On the cost of being wrong

The intuition is that missing a regression is catastrophic and a false alarm is
cheap. At the default parameters **that is wrong: the asymmetry is about two to
one**, not orders of magnitude.

| | |
|---|---:|
| False alarm (30 engineering hours) | $4,500 |
| Missed 2% regression | $8,400 |

The result is driven almost entirely by one number — the harm of a single
degraded response — which nobody has published:

| Harm per degraded request | Missed-regression cost vs false alarm |
|---:|---:|
| $0.0002 | 0x |
| $0.002 | 2x |
| $0.02 | 19x |
| $0.20 | 187x |

**The honest output is that sensitivity, not a threshold.** The operating point
depends on a parameter spanning three orders of magnitude, and a team that
knows its own value should derive its own threshold from it.

The original draft of the detection module asserted the asymmetry was large.
The numbers said otherwise and the claim was wrong, so it is recorded rather
than quietly corrected.

---

## Errors found while building this

| Error | Effect |
|---|---|
| Default paired discordance was what *unrelated* models show | Paired and unpaired power came out identical, erasing the advantage the function existed to show |
| The simulator pinned flip counts | Net change was exactly zero every time, making concealment look total — an artefact of the construction |
| The quantile lookup table held rounded values | The fast path was less precise than the slow one; `z(0.90)` disagreed with `−z(0.10)` at the fifth decimal |
| A cost claim asserted a large asymmetry | The numbers showed about two to one |

Each is fixed and regression-tested.

---

## Using it

```bash
evaldrift table                    # resolution of every benchmark people quote
evaldrift resolution 198           # what a 198-item benchmark can detect
evaldrift check 0.02 198           # is a 2-point claim supportable? (exit 1 if not)
```

`check` exits non-zero when a claim exceeds what the benchmark can resolve, so
it works as a CI gate: a build can fail when someone reports an improvement
their evaluation cannot distinguish from noise.

## The case against this analysis

**[docs/against.md](docs/against.md)** argues, as strongly as I can, that this
should not change how anyone evaluates models.

The objection I cannot dispose of: this treats a benchmark score as an estimate
of a population parameter. If a benchmark is instead a **fixed tripwire** — not
a sample of coding ability but the specific suite your product must pass — then
sampling uncertainty is the wrong lens and the headline is a category error.
The finding applies exactly insofar as teams generalise from benchmark scores,
and the public evidence that they do is abundant but is inference, not
measurement.

Two others worth reading first: benchmark items are **not independent**, so the
true intervals are wider than reported and the specific numbers in the table are
not quite right; and the **noise floor has not been measured at scale**, so
every paired-test figure is conditional on an assumed discordance rather than an
observed one.

## How the data constrained the design

**[docs/data-reachability.md](docs/data-reachability.md)** — every source was
probed from CI before any code was written, and the results are committed. The
per-item corpora that would have been convenient are gated; their absence made
the headline finding stronger, because it now rests on published split sizes
alone and cannot be contested on the grounds that the wrong model was measured.

## Reproducing

```bash
pip install -e ".[dev]"
pytest -q
python -c "from evaldrift.benchmarks import resolution_table; \
           [print(r['benchmark'], r['min_detectable_effect']) for r in resolution_table()]"
```

No dependencies. Quantiles are computed in-house so the arithmetic is
inspectable.

## Scope

These are **sampling bounds** — uncertainty from asking a finite set of
questions. Real evaluation carries further variance from prompt formatting,
decoding temperature and scoring ambiguity, all of which widen the intervals.
Every resolution figure here is therefore a lower bound: the most generous
possible reading of what a benchmark can detect.

## License

MIT. GSM8K is MIT-licensed; benchmark sizes are cited to their source papers.
