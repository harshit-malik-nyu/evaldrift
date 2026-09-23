"""
Estimating intra-cluster correlation from published results.

`cluster.py` sweeps ICC because none has been published for an LLM benchmark.
It can be estimated, though, from something that IS published: per-subject
accuracies. If a model scores 87% on one MMLU subject and 52% on another, that
spread is itself evidence about how much outcome variance is attributable to
which subject an item belongs to.

The estimator
-------------
For binary outcomes grouped into clusters:

    ICC = between-cluster variance / (between + within)

with the essential correction that observed variance across cluster means is
not all real. Each cluster's accuracy is measured on a finite number of items,
so part of the spread is sampling noise. Subtracting it is the difference
between an estimate and an artefact:

    between_true = var(cluster means) − mean(sampling variance per cluster)

Omitting that subtraction inflates ICC, and inflating ICC is the direction that
flatters this project's conclusion. The correction is applied, and the
uncorrected figure is reported alongside so the size of the adjustment is
visible.

What this estimate is and is not
--------------------------------
It is computed from four subjects of one model in one replication study. Four
clusters is a small basis for estimating a variance component, and the
confidence interval on it would be wide.

It is nonetheless decisive here, because the quantity it has to clear is tiny.
MMLU stops supporting a two-point claim at ICC 0.003. The estimate is roughly
fifty times that. An estimate can be badly wrong and still settle the question
when the margin is that large — which is the only reason a four-cluster
estimate is worth reporting at all.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SubjectResult:
    """One cluster's observed accuracy, with its reported standard error."""

    subject: str
    accuracy: float
    standard_error: float | None = None
    n_items: int | None = None

    @property
    def sampling_variance(self) -> float:
        """
        Variance of this cluster's accuracy from finite sampling.

        Taken from the reported standard error when available, otherwise
        computed from the item count. One or the other is required: without
        it, sampling noise cannot be separated from real between-cluster
        spread.
        """
        if self.standard_error is not None:
            return self.standard_error ** 2
        if self.n_items:
            return self.accuracy * (1 - self.accuracy) / self.n_items
        raise ValueError(
            f"{self.subject}: need a standard error or an item count to "
            "separate sampling noise from real between-subject variance")


# Published per-subject accuracies on the ORIGINAL MMLU subsets.
#
# Source: Shashidhar et al., "YourBench: Easy Custom Evaluation Sets for
# Everyone" (arXiv 2504.01833), Table 1, "Orig" columns for Qwen2.5 7B.
# The paper reports accuracy and standard error per subject, which is exactly
# what the correction above requires and is rarer in published results than it
# should be.
MMLU_QWEN25_7B = [
    SubjectResult("Astronomy", 0.8355, 0.0302),
    SubjectResult("Social Science", 0.8756, 0.0233),
    SubjectResult("Virology", 0.5241, 0.0389),
    SubjectResult("World Religions", 0.8596, 0.0266),
]

MMLU_QWEN1_7B = [
    SubjectResult("Astronomy", 0.5789, 0.0402),
    SubjectResult("Social Science", 0.8010, 0.0282),
    SubjectResult("Virology", 0.4398, 0.0386),
    SubjectResult("World Religions", 0.7018, 0.0351),
]


@dataclass
class IccEstimate:
    n_clusters: int
    mean_accuracy: float

    observed_variance: float
    """Raw variance across cluster means, before correction."""

    sampling_variance: float
    """Mean within-cluster sampling variance, subtracted."""

    between_variance: float
    within_variance: float

    icc: float
    icc_uncorrected: float
    """What the estimate would be without subtracting sampling noise —
    reported so the size of the correction is visible."""

    subjects: list[str] = field(default_factory=list)

    def exceeds(self, threshold: float) -> float:
        """How many times the estimate exceeds a threshold."""
        return self.icc / threshold if threshold else float("inf")

    def as_dict(self) -> dict:
        return {
            "n_clusters": self.n_clusters,
            "subjects": self.subjects,
            "mean_accuracy": self.mean_accuracy,
            "observed_variance": self.observed_variance,
            "sampling_variance_subtracted": self.sampling_variance,
            "between_variance": self.between_variance,
            "within_variance": self.within_variance,
            "icc": self.icc,
            "icc_without_correction": self.icc_uncorrected,
        }


def estimate(results: list[SubjectResult]) -> IccEstimate:
    """
    Estimate ICC from per-cluster accuracies.

    Requires at least three clusters: a variance component cannot be estimated
    from two, and returning a number from two would imply precision that does
    not exist.
    """
    if len(results) < 3:
        raise ValueError(
            f"need at least 3 clusters to estimate a variance component, "
            f"got {len(results)}"
        )

    accs = [r.accuracy for r in results]
    observed = statistics.variance(accs)
    sampling = statistics.mean(r.sampling_variance for r in results)

    # Floored at zero: a negative estimate means the observed spread is within
    # what sampling noise alone explains, which is evidence of no clustering
    # rather than of negative correlation.
    between = max(0.0, observed - sampling)
    within = statistics.mean(a * (1 - a) for a in accs)

    total = between + within
    uncorrected_total = observed + within

    return IccEstimate(
        n_clusters=len(results),
        mean_accuracy=statistics.mean(accs),
        observed_variance=observed,
        sampling_variance=sampling,
        between_variance=between,
        within_variance=within,
        icc=(between / total) if total else 0.0,
        icc_uncorrected=(observed / uncorrected_total) if uncorrected_total else 0.0,
        subjects=[r.subject for r in results],
    )


def verdict(benchmark: str = "MMLU", claimed_effect: float = 0.02) -> dict:
    """
    Does the estimated ICC clear the threshold at which the benchmark stops
    supporting a claim?
    """
    from .cluster import STRUCTURES, corrected_resolution, flip_point

    structure = next((s for s in STRUCTURES if s.benchmark == benchmark), None)
    if structure is None:
        raise ValueError(f"no documented cluster structure for {benchmark}")

    est = estimate(MMLU_QWEN25_7B)
    flip = flip_point(structure, claimed_effect)
    corrected = corrected_resolution(structure, est.icc,
                                     accuracy=est.mean_accuracy)

    return {
        "benchmark": benchmark,
        "estimated_icc": est.icc,
        "flip_point": flip,
        "exceeds_flip_by": est.exceeds(flip) if flip else None,
        "design_effect": corrected["design_effect"],
        "effective_n": corrected["effective_n"],
        "mde_assuming_independence": corrected["mde_assuming_independence"],
        "mde_corrected": corrected["mde_corrected"],
        "basis": (
            f"{est.n_clusters} subjects of one model from one replication "
            "study; sampling variance subtracted"
        ),
        "caveat": (
            "Four clusters is a small basis for a variance component and the "
            "interval on this estimate would be wide. It settles the question "
            "anyway because the threshold it must clear is roughly fifty times "
            "smaller: an estimate can be badly wrong and still be decisive "
            "when the margin is that large."
        ),
    }
