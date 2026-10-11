# Decision assurance: evaldrift

Use a prespecified paired evaluation plan matched to the smallest meaningful release effect. Budget labeling and decision review separately; never reinterpret planning power as a significance test.

**Evidence:** The paired example with eight wins and zero losses has exact two-sided p=.0078125. Planning MDE alone cannot invalidate an observed paired result.

**Uncertainty:** The scenario error rates are not inferred from the eight-win illustration. Required item count depends on pairing and disagreement structure.

## Robustness of the assumed business case

| Alternative | Feasible grid cases / 27 | Worst regret when feasible | Maximum volume at fixed review capacity |
|---|---:|---:|---:|
| Fixed large evaluation for every release | 18 | $156,312.00 | 250 |
| Prespecified paired evaluation plan | 9 | $0.00 | 125 |
| Release on headline accuracy only | 0 | No feasible case | 1000 |

**Robust minimax choice:** None. No option is feasible across the entire stress grid.

Finite assumed grid, not a probability distribution or protection outside the grid. Conditional regret never overrides feasibility. Null robust option means no unconditional recommendation. Cost regret is relative to the cheapest feasible option in that same scenario. Failure counts can overlap.

## Missing-outcome sensitivity

| Outcomes masked per arm | Primary effect bounds | Incident effect bounds | Every completion clears margins? |
|---|---:|---:|---|
| 0% | [3.9%, 3.9%] | [1.5%, 1.5%] | False |
| 5% | [-0.7%, 9.3%] | [-3.6%, 6.4%] | False |
| 10% | [-5.6%, 14.4%] | [-8.8%, 11.2%] | False |
| 20% | [-15.5%, 24.5%] | [-18.8%, 21.2%] | False |

These are identification bounds on deliberately masked synthetic outcomes, not confidence intervals or measured missingness. Failures and non-starters remain in the assigned denominator. Passing this sensitivity check would still require statistical and domain-quality gates.

## Domain measurement contract

**Decision:** Decide whether a candidate model improves the release-critical task under paired evaluation.

**Primary outcome:** Paired task-success difference on the prespecified eligible item set, accompanied by wins, losses, ties and an uncertainty interval.

**Denominator:** All assigned eligible items evaluated under both versions; report missing pairs and failures explicitly.

**Independent unit:** Independent item or shared-source cluster when multiple questions derive from one document.

**Quality guardrail:** Critical failure slices and latency/cost constraints; pair integrity and fixed stopping policy.

**Minimum required data:** Item/source IDs, both version IDs, paired outcomes, missingness cause, run seed and cost/latency records.

**Missingness and failure handling:** Never drop one-sided failures silently. Specify failure-as-outcome or unknown-outcome treatment in advance and show missing-pair sensitivity.

**Release rule:** Use a prespecified paired inferential method and meaningful improvement threshold plus guardrails; planning MDE is not an observed significance test.

**Reversal trigger:** Effect disappears under valid pairing, critical failures worsen, or dependence invalidates the independent-item calculation.

## Interview defense

**Does low planning power invalidate eight wins and no losses?**

No. That paired example has exact two-sided p=.0078125. Planning power and the observed test answer different questions.

**What is the business value?**

Avoid paying for a larger evaluation or a model release without enough decision-relevant evidence, while preserving critical failure checks.

## Implementation handoff

1. Freeze the eligible population, denominator, outcome horizon and proposed decision owner before comparison.
2. Reconcile assignment and outcome records at the independence unit; classify missingness without deleting cases.
3. Estimate the domain outcome and its uncertainty separately from activation. Apply risk and capacity vetoes before comparing costs.
4. Record approve, hold, or reverse with the evidence version and violated gate. An unmeasured required domain gate means HOLD.

The supplied cluster-budget grid is a planning sensitivity check with assumed ICC. It is not an estimate from real clusters and does not guarantee joint power. No stakeholder approval or real experiment is asserted.
