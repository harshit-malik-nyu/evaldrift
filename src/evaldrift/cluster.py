"""
Item clustering, and why it makes every interval wider.

Everything in `power.py` treats benchmark items as independent Bernoulli
trials. They are not, and the violation is not subtle.

MMLU's 14,042 items are organised into 57 subjects. A model that fails one
college-chemistry question is more likely to fail the next, because the two
share a topic, a knowledge requirement and often a solution pattern. The same
holds for MATH's subject-and-difficulty grid, MMLU-Pro's categories, and
GPQA's three scientific domains.

The consequence is standard survey statistics and it is large.

    design effect  DEFF = 1 + (m − 1) × ICC
    effective n    n_eff = n / DEFF

where `m` is the average cluster size and `ICC` the intra-cluster correlation —
the share of outcome variance attributable to which cluster an item is in.

With large clusters, DEFF grows fast. MMLU averages 246 items per subject, so
even a modest ICC of 0.05 gives DEFF ≈ 13, cutting the effective sample from
14,042 to roughly 1,060. Every interval widens by the square root of that.

Why this matters for the headline
---------------------------------
`power.py` reports the most generous possible reading: independent items, no
prompt variance, no scoring ambiguity. The benchmarks that pass a two-point
claim there pass by narrow margins. Under any realistic clustering they stop
passing, which means the uncorrected table understates the problem rather than
overstating it.

When this correction applies, and when it does not
--------------------------------------------------
This matters and it is easy to overclaim, so it is stated precisely.

The design effect applies when generalising BEYOND the sampled clusters. If
the claim is "this model is better at graduate-level science", MMLU's 57
subjects stand in for a wider universe of subjects, the subjects are a sample,
and clustering inflates the uncertainty exactly as computed here.

It does NOT apply when the clusters are the entire target. If the claim is
"this model scores higher on these 57 specific subjects", nothing is being
generalised, the items are a census rather than a sample, and sampling
uncertainty of this kind is not the relevant uncertainty at all.

Both claims get made from the same number. The first is what nearly every
model announcement asserts — capability claims about reasoning, science, code
— and it is the one this correction governs. The second is a narrower claim
than anyone actually makes in public.

So the flip points below bound the generalising claim. A team using a benchmark
purely as a fixed regression tripwire on a frozen item set is making the second
kind of claim, and should ignore this module.

On the ICC itself
-----------------
Nobody has published an intra-cluster correlation for an LLM benchmark. Getting
one requires per-item results grouped by cluster, which is exactly the data that
sits behind gated corpora. So this module does not assert a value — it sweeps a
plausible range and reports where each benchmark's verdict flips.

That is the honest output. A single corrected number would imply a measurement
that has not been made.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ClusterStructure:
    """Documented grouping for a benchmark."""

    benchmark: str
    n_items: int
    n_clusters: int
    cluster_unit: str
    source: str

    @property
    def mean_cluster_size(self) -> float:
        return self.n_items / self.n_clusters if self.n_clusters else 1.0


# Cluster counts as published by each benchmark's authors. Only benchmarks with
# an explicit, documented grouping are listed: inventing a cluster structure
# would manufacture the very effect this module measures.
STRUCTURES: list[ClusterStructure] = [
    ClusterStructure("MMLU", 14042, 57, "subject",
                     "Hendrycks et al. 2020: 57 tasks spanning STEM, humanities, "
                     "social sciences and other"),
    ClusterStructure("MMLU-Pro", 12032, 14, "category",
                     "Wang et al. 2024: 14 subject categories"),
    ClusterStructure("MATH", 5000, 7, "subject",
                     "Hendrycks et al. 2021: 7 subjects, each with 5 difficulty "
                     "levels"),
    ClusterStructure("GPQA Diamond", 198, 3, "domain",
                     "Rein et al. 2023: biology, physics, chemistry"),
    ClusterStructure("TruthfulQA", 817, 38, "category",
                     "Lin et al. 2021: 38 categories including health, law, "
                     "finance and politics"),
]


def design_effect(mean_cluster_size: float, icc: float) -> float:
    """
    Variance inflation from clustering.

    DEFF = 1 + (m − 1) × ICC. At ICC = 0 it is 1 and nothing changes, which is
    the assumption `power.py` makes implicitly.
    """
    if icc < 0 or icc > 1:
        raise ValueError("ICC must lie in [0, 1]")
    return 1.0 + (mean_cluster_size - 1.0) * icc


def effective_n(n_items: int, mean_cluster_size: float, icc: float) -> float:
    """Sample size after correcting for clustering."""
    return n_items / design_effect(mean_cluster_size, icc)


def corrected_resolution(structure: ClusterStructure, icc: float,
                         accuracy: float = 0.70, confidence: float = 0.95,
                         power: float = 0.80) -> dict:
    """
    What a clustered benchmark can actually detect.

    The correction is applied by reducing the sample size rather than by
    adjusting the interval directly, which is equivalent and keeps the
    arithmetic inspectable.
    """
    from .power import resolution

    deff = design_effect(structure.mean_cluster_size, icc)
    n_eff = effective_n(structure.n_items, structure.mean_cluster_size, icc)

    naive = resolution(structure.n_items, accuracy, confidence, power)
    # n_eff can fall below 1 at extreme ICC; floor it so the arithmetic stays
    # defined and the result reads as "hopeless" rather than erroring.
    corrected = resolution(max(2, int(round(n_eff))), accuracy,
                           confidence, power)

    return {
        "benchmark": structure.benchmark,
        "n_items": structure.n_items,
        "n_clusters": structure.n_clusters,
        "cluster_unit": structure.cluster_unit,
        "mean_cluster_size": structure.mean_cluster_size,
        "icc": icc,
        "design_effect": deff,
        "effective_n": n_eff,
        "mde_assuming_independence": naive.min_detectable_effect,
        "mde_corrected": corrected.min_detectable_effect,
        "inflation": (corrected.min_detectable_effect
                      / naive.min_detectable_effect),
    }


def flip_point(structure: ClusterStructure, claimed_effect: float = 0.02,
               accuracy: float = 0.70, max_icc: float = 0.30,
               step: float = 0.001) -> float | None:
    """
    The ICC at which this benchmark stops being able to support a claim.

    Returns None when the benchmark cannot support the claim even under
    independence — it never had the resolution, so there is nothing for
    clustering to take away.

    Reporting a flip point rather than a corrected number is the point of this
    module. It converts "the intervals are wrong" into "here is exactly how
    much correlation it takes for this specific benchmark to fail", which a
    reader can weigh against their own sense of how correlated benchmark items
    are.
    """
    from .power import resolution

    naive = resolution(structure.n_items, accuracy).min_detectable_effect
    if naive > claimed_effect:
        return None

    icc = 0.0
    while icc <= max_icc:
        r = corrected_resolution(structure, icc, accuracy)
        if r["mde_corrected"] > claimed_effect:
            return icc
        icc += step
    return None


def sweep(claimed_effect: float = 0.02,
          iccs: list[float] | None = None,
          accuracy: float = 0.70) -> list[dict]:
    """Every documented benchmark, across a range of plausible ICC."""
    iccs = iccs or [0.0, 0.01, 0.02, 0.05, 0.10, 0.20]
    out = []
    for s in STRUCTURES:
        row: dict = {
            "benchmark": s.benchmark,
            "n_items": s.n_items,
            "clusters": s.n_clusters,
            "mean_cluster_size": round(s.mean_cluster_size, 1),
            "flip_icc": flip_point(s, claimed_effect, accuracy),
            "by_icc": {},
        }
        for icc in iccs:
            r = corrected_resolution(s, icc, accuracy)
            row["by_icc"][icc] = {
                "effective_n": round(r["effective_n"], 1),
                "mde": r["mde_corrected"],
                "supports_claim": r["mde_corrected"] <= claimed_effect,
            }
        out.append(row)
    return out


def summary(claimed_effect: float = 0.02, accuracy: float = 0.70) -> str:
    """One paragraph a reader can quote."""
    rows = sweep(claimed_effect, accuracy=accuracy)
    flips = [(r["benchmark"], r["flip_icc"]) for r in rows
             if r["flip_icc"] is not None]
    never = [r["benchmark"] for r in rows if r["flip_icc"] is None]

    parts = []
    if flips:
        detail = "; ".join(f"{b} at ICC {icc:.3f}" for b, icc in flips)
        parts.append(
            f"Correcting for documented item clustering, the benchmarks that "
            f"support a {claimed_effect:.0%} claim under an independence "
            f"assumption stop supporting it at modest correlation: {detail}."
        )
    if never:
        parts.append(
            f"{', '.join(never)} cannot support the claim even assuming "
            f"independence, so clustering changes nothing for them."
        )
    parts.append(
        "No intra-cluster correlation has been published for any LLM "
        "benchmark, so no corrected figure is asserted here. The flip points "
        "are the finding: they say how much correlation it would take, and a "
        "reader can judge whether benchmark items are that correlated."
    )
    return " ".join(parts)
