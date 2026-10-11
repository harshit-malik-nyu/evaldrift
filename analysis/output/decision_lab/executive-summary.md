# Allocate evaluation spend to decisions that need more paired evidence

Use a prespecified paired evaluation plan matched to the smallest meaningful release effect. Budget labeling and decision review separately; never reinterpret planning power as a significance test.

**Observed evidence:** The paired example with eight wins and zero losses has exact two-sided p=.0078125. Planning MDE alone cannot invalidate an observed paired result.

**Decision owner:** Model release owner (proposed role, not a client).

**Base planning case:** Prespecified paired evaluation plan. This is conditional on the assumptions, not deployment approval.

| Alternative | Economic cost | Cash outlay | Reviewer hours | Passes risk and capacity |
|---|---:|---:|---:|---|
| Fixed large evaluation for every release | $126,240 | $116,640 | 48.0 | True |
| Prespecified paired evaluation plan | $84,936 | $68,136 | 96.0 | True |
| Release on headline accuracy only | $45,360 | $5,760 | 12.0 | False |

Economic cost includes valued staff capacity and scenario incident losses. Cash outlay excludes salaried capacity and contingent losses. These are not realized savings.

**Sensitivity across 27 equally enumerated scenarios:** Prespecified paired evaluation plan: 9, Fixed large evaluation for every release: 9, NO FEASIBLE OPTION: 9. Grid counts are not probabilities.

**Synthetic product experiment:** HOLD. Primary effect 3.9%; 95% interval [0.1%, 7.7%]. Guardrail effect 1.5%; interval [0.8%, 2.3%]. These numbers test the decision logic, not product performance.

**Priority order:**

1. Record the prespecified effect, paired outcomes and missing-item policy before evaluation.
2. Spend labels where the decision remains unresolved rather than maximizing one universal benchmark size.
3. Require a fixed stopping rule and confirmatory analysis after exploratory comparisons.

**What would reverse the recommendation:** A smaller paired design is not economical when labeling costs fall or its false-release rate breaches the gate; increase evidence or hold the release.

**Remaining uncertainty:** The scenario error rates are not inferred from the eight-win illustration. Required item count depends on pairing and disagreement structure.
