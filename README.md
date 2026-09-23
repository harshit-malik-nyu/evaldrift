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

**No measured floor is reported here yet.** Quoting one before it has been run
would be precisely the error this project documents.

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
