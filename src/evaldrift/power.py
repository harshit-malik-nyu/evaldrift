"""
What a benchmark can actually detect.

An evaluation is a measurement instrument, and like any instrument it has a
resolution below which it reports noise. That resolution is set almost entirely
by the number of items, and it is routinely ignored: a 200-item benchmark
cannot distinguish a model that is two points better from one that is two
points worse, yet two-point movements are announced constantly.

This module computes the resolution.

Two quantities matter and they are different:

    CONFIDENCE INTERVAL      How precisely one score is known. A single run of
                             200 items at 70% accuracy carries roughly a six
                             point half-width. Any claim finer than that is
                             about the sample, not the model.

    MINIMUM DETECTABLE       How large a real change has to be before two runs
    EFFECT                   can be told apart. Always larger than the
                             interval on one score, because both runs carry
                             error. This is the number an eval team needs and
                             almost never has.

A note on what this does not model
-----------------------------------
These are sampling bounds: the uncertainty from having asked 200 questions
rather than every possible question. Real evaluation carries further variance
from prompt formatting, decoding temperature, and scoring ambiguity, all of
which widen the interval further. Everything here is therefore a LOWER bound on
uncertainty — the most generous possible reading of a benchmark's resolution.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Standard normal quantiles, at full precision.
#
# These were originally rounded to four places, which made the lookup table
# LESS precise than the rational approximation it exists to short-circuit: z at
# 0.90 returned 1.2816 from the table while z at 0.10 returned -1.2815516 from
# the approximation, so two code paths disagreed on mirror-image inputs. A test
# asserting antisymmetry caught it. Kept explicit rather than imported from
# scipy so the arithmetic is inspectable and the package has no dependencies.
Z = {
    0.80: 0.8416212335729143,
    0.90: 1.2815515655446004,
    0.95: 1.6448536269514722,
    0.975: 1.959963984540054,
    0.99: 2.3263478740408408,
}


def z_for(level: float) -> float:
    if level in Z:
        return Z[level]
    # Acklam's rational approximation to the inverse normal CDF, adequate well
    # past the precision this analysis needs.
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    p_low, p_high = 0.02425, 1 - 0.02425
    p = level
    if p < p_low:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > p_high:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def wilson_interval(successes: int, n: int, confidence: float = 0.95
                    ) -> tuple[float, float]:
    """
    Wilson score interval for an accuracy.

    Used rather than the textbook normal approximation because benchmark
    accuracies often sit near 0 or 1 — a model at 95% on an easy suite — where
    the normal interval extends past 1.0 and understates uncertainty exactly
    where teams are most confident.
    """
    if n == 0:
        return (0.0, 0.0)
    z = z_for(0.5 + confidence / 2)
    p = successes / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def interval_halfwidth(accuracy: float, n: int, confidence: float = 0.95
                       ) -> float:
    """Half-width of the interval around a single reported score."""
    lo, hi = wilson_interval(round(accuracy * n), n, confidence)
    return (hi - lo) / 2


@dataclass
class Resolution:
    """What a benchmark of this size can distinguish."""

    n_items: int
    baseline_accuracy: float
    confidence: float
    power: float

    halfwidth: float
    """Half-width of the interval on one score."""

    min_detectable_effect: float
    """Smallest true change two runs can reliably distinguish."""

    paired_min_detectable: float
    """
    The same, when both runs score the SAME items and the comparison uses
    which items flipped rather than the two totals.

    Sensitivity here depends entirely on `discordance`. Against an unrelated
    model there is no advantage; against a successive version of the same
    model, which disagrees on far fewer items, the advantage is large. Most
    pipelines already run the identical set twice and then discard this by
    comparing only the aggregate numbers.
    """

    discordance: float = 0.0
    """Share of items the two runs disagree on, as assumed or measured."""

    def as_dict(self) -> dict:
        return {
            "n_items": self.n_items,
            "baseline_accuracy": self.baseline_accuracy,
            "confidence": self.confidence,
            "power": self.power,
            "interval_halfwidth": self.halfwidth,
            "min_detectable_effect": self.min_detectable_effect,
            "paired_min_detectable_effect": self.paired_min_detectable,
            "assumed_discordance": self.discordance,
        }


def resolution(n_items: int, baseline_accuracy: float = 0.70,
               confidence: float = 0.95, power: float = 0.80,
               discordance: float | None = None) -> Resolution:
    """
    The smallest change a benchmark of this size can detect.

    `discordance` is the share of items on which two runs disagree, and it is
    the parameter that decides whether paired evaluation helps at all.

    The default of 2p(1-p) is what two INDEPENDENT models at the same accuracy
    would disagree on — 42% at p=0.70. At that value paired and unpaired power
    are identical by construction, which is the correct answer for unrelated
    models and the wrong one for the case that matters.

    Successive versions of the same model are not independent. They share
    training data, architecture and most behaviour, and typically disagree on
    something closer to 10-20% of items. That is where paired evaluation earns
    its keep: the comparison runs over the discordant items only, so halving
    discordance cuts the required sample by half.

    The default is deliberately the pessimistic one. A team that measures its
    own discordance will find paired testing more sensitive than this reports,
    never less.
    """
    z_alpha = z_for(0.5 + confidence / 2)
    z_beta = z_for(power)
    p = baseline_accuracy

    half = interval_halfwidth(p, n_items, confidence)

    # Two independent proportions, equal n.
    unpaired = (z_alpha + z_beta) * math.sqrt(2 * p * (1 - p) / n_items)

    # Paired: McNemar. Only discordant pairs carry information, so the
    # sensitivity gain is exactly the reduction in discordance relative to two
    # independent runs.
    if discordance is None:
        discordance = 2 * p * (1 - p)
    discordance = max(discordance, 1e-9)
    paired = (z_alpha + z_beta) * math.sqrt(discordance / n_items)

    return Resolution(
        n_items=n_items, baseline_accuracy=p, confidence=confidence,
        power=power, halfwidth=half,
        min_detectable_effect=min(unpaired, 1.0),
        paired_min_detectable=min(paired, 1.0),
        discordance=discordance,
    )


def items_required(effect: float, baseline_accuracy: float = 0.70,
                   confidence: float = 0.95, power: float = 0.80,
                   paired: bool = False,
                   discordance: float | None = None) -> int:
    """
    How many items are needed to detect a change of a given size.

    The inverse question, and the one worth asking before building a benchmark
    rather than after reporting from it.
    """
    if effect <= 0:
        raise ValueError("effect must be positive")

    z_alpha = z_for(0.5 + confidence / 2)
    z_beta = z_for(power)
    p = baseline_accuracy

    if paired:
        d = discordance if discordance is not None else 2 * p * (1 - p)
        n = ((z_alpha + z_beta) ** 2) * d / (effect ** 2)
    else:
        n = ((z_alpha + z_beta) ** 2) * 2 * p * (1 - p) / (effect ** 2)

    return int(math.ceil(n))


def is_claim_supportable(claimed_effect: float, n_items: int,
                         baseline_accuracy: float = 0.70,
                         confidence: float = 0.95,
                         power: float = 0.80) -> tuple[bool, str]:
    """
    Whether a reported improvement is distinguishable from noise at this size.

    Returns (supportable, explanation). The explanation is written to be
    quotable, because the point of this module is to make a specific claim
    about a specific number rather than a general caution about statistics.
    """
    res = resolution(n_items, baseline_accuracy, confidence, power)
    mde = res.min_detectable_effect

    if claimed_effect >= mde:
        return True, (
            f"a {claimed_effect:.1%} change is detectable on {n_items:,} items "
            f"(minimum detectable effect {mde:.1%})"
        )

    needed = items_required(claimed_effect, baseline_accuracy, confidence, power)
    return False, (
        f"a {claimed_effect:.1%} change is NOT distinguishable from noise on "
        f"{n_items:,} items. The minimum detectable effect is {mde:.1%}, and "
        f"{needed:,} items would be required — {needed / n_items:.1f}x the "
        f"benchmark size."
    )
