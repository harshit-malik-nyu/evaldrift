# The case against this analysis

The strongest argument I can make that this work should not change how anyone
evaluates models. Several objections are supported by the project's own
numbers, and where one is decisive it says so.

---

## 1. Benchmarks are not used the way this assumes

This treats a benchmark score as an estimate of a population parameter, and
asks whether two estimates differ. That is the statistically correct frame and
it may not be the operating one.

In practice a benchmark is often used as a **regression tripwire on a fixed
item set**, not as a sample from a distribution of possible questions. If the
164 HumanEval problems *are* the thing you care about — not a sample of coding
ability, but the specific suite your product must pass — then sampling
uncertainty is not the relevant uncertainty, and the headline finding does not
apply.

**This is the most serious objection here.** The defence is narrow: teams do
generalise from these numbers, constantly, and every announcement claiming a
model is "better at reasoning" on the strength of a 198-item score is making
exactly the inferential leap this analysis measures. But a team that never
generalises is not making an error this project can catch.

## 2. The accuracy estimates are mine

Item counts are published. The accuracy levels — where frontier models sit —
are my estimates, and resolution depends on them because binomial variance
peaks at 50%.

The direction is favourable: the estimates lean high, which narrows intervals
and flatters each benchmark, and the verdicts are tested at 50% as well. But
"my estimate, in the conservative direction" is weaker than "published", and
the table reads as though every number in it were equally solid.

## 3. The independence assumption — since addressed, and the fix has its own problems

This originally read: every interval treats items as independent Bernoulli
trials, they are not, and the true intervals are wider than reported.

That is now modelled rather than conceded. `cluster.py` computes design effects
from documented groupings and `icc.py` estimates the correlation from published
per-subject accuracies: ICC ≈ 0.15, against a flip point of
0.003. MMLU's effective sample size comes out at
373 rather than 14,042.

**The correction introduces its own weaknesses**, which now need stating:

- The ICC estimate rests on **four subjects of one model** from one replication
  study. Its confidence interval would be wide. The defence is that the
  threshold it must clear is fifty times smaller — decisive, but not precise.
- The design-effect formula assumes **equal cluster sizes**. MMLU subjects vary
  substantially in item count, which biases DEFF upward.
- Applying one ICC across all 57 subjects assumes homogeneous correlation.
  Almost certainly false.

So the corrected numbers are better than the uncorrected ones and should still
not be quoted to two decimal places.

## 4. The cost model is barely a model

Two of its inputs are estimates, one of which — harm per degraded request —
swings the conclusion across three orders of magnitude. The project reports
that sensitivity honestly and then still ships a cost section, which arguably
lends more credibility to the framework than the inputs deserve.

A reader could reasonably say: delete the cost model, keep the measurement.

## 5. The noise floor — since sourced, from someone else

This originally read: the harness has not been run, so every paired-test figure
is conditional on an assumed discordance.

A published floor was then found — the MMLU-Pro authors' 24-prompt experiment,
giving 4.5% typical variance on MMLU against
frontier models clustering within 2–4%.

**That closes the argument and not the measurement.** Prompt variance and
run-to-run self-disagreement are different quantities. The published figure
says the floor is large enough to matter; it does not give a team the number it
needs for its own items and decoding settings. The harness remains unrun, and
the project now leans on someone else's experiment for its most important
constraint.

A reader could fairly say that finding a better source is not the same as doing
the work.

## 6. Nobody in the field is actually confused about this

Statistical power is not a discovery. Any eval team with a statistician knows
that 198 items carries a wide interval, and several have said so publicly. The
contribution here is making it concrete and checkable for specific named
benchmarks — which is useful, and is not the same as new knowledge.

If the practice persists despite being understood, the binding constraint is
incentives, not information, and a better instrument does not fix it.

## 7. The recommendation is cheap to say and awkward to adopt

"Use paired tests on per-item results" is correct and costs almost nothing
computationally. It also requires storing per-item outputs, joining them
correctly across runs, and changing what the dashboard shows — organisational
work this project attaches no cost to, which is precisely the criticism it
makes of others.

---

## What survives

- **The resolution table is arithmetic on published numbers.** It does not
  depend on any model, run, or estimate of mine beyond accuracy, and it holds
  in the conservative direction at 50%.
- **The aggregate rule firing on noise is demonstrable** and pinned by a test.
  18 lost against 15 gained is a coin flip, and the standard check fires on it.
- **Net-versus-gross is a real distinction** that most reporting collapses, and
  the per-item data needed to see it is usually already collected.
- **The noise-floor construction is sound** — the model does not change between
  passes, so ground truth is free. That it has not been run at scale is a gap,
  not a flaw in the design.

## What does not

The specific cost figures, and any threshold derived from them. They rest on a
parameter nobody has published, and the analysis says so, but they should not
be quoted.

## The objection I cannot answer

Argument 1. If a benchmark is a fixed tripwire rather than a sample, sampling
uncertainty is the wrong lens and the headline is a category error.

Settling it requires knowing how teams actually reason from these numbers,
which is not observable from outside. The honest position is that the finding
applies exactly insofar as people generalise from benchmark scores — and the
public evidence that they do is abundant, but it is inference rather than
measurement.
