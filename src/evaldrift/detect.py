"""
Deciding whether a model regressed.

Everything upstream measures. This decides, and the decision depends on what
each error costs.

    FALSE ALARM        An engineering team investigates noise. Costly,
                       bounded, and self-correcting — the investigation ends
                       when nothing is found.

    MISSED REGRESSION  A degraded model ships. Cost scales with traffic and
                       with how long it survives before something else
                       surfaces it.

A finding worth stating plainly, because it contradicts the intuition this
module was built on: at the default parameters the asymmetry is about TWO to
one, not the orders of magnitude the framing assumes. A false alarm costs
roughly $4,500 in engineering time; a missed two-point regression costs
roughly $8,400.

That is close enough that the optimal threshold is far less conservative than
"never miss a regression" reasoning suggests, and it inverts the usual
recommendation. The result is driven almost entirely by
`harm_per_degraded_request`, which is an estimate nobody has published — so
the honest output is the sensitivity to it rather than the point value. Raise
it tenfold and the asymmetry becomes twenty to one; the conclusion moves with
it.

The original draft of this docstring asserted the asymmetry was large. The
numbers said otherwise and the claim was wrong, so it is recorded here rather
than quietly corrected.

Four rules are implemented because they behave differently and teams typically
use only the first — which, in the worked example, fires on noise that the
paired test correctly ignores.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .churn import ChurnResult, by_segment
from .power import resolution


class Rule(str, Enum):
    AGGREGATE_DELTA = "aggregate_delta"
    """Fire when the headline score drops by more than a fixed margin.

    What almost everyone does, and the weakest of the four: it ignores which
    items moved, so it cannot distinguish a real shift from resampling noise
    and cannot see a regression cancelled by an unrelated gain."""

    CONFIDENCE_INTERVAL = "confidence_interval"
    """Fire when the two score intervals do not overlap.

    Statistically respectable and badly underpowered. Non-overlapping
    intervals is a stricter condition than a significant difference, so this
    rule misses real regressions that a proper test would catch."""

    MCNEMAR = "mcnemar"
    """Fire when the paired test on discordant items is significant.

    The correct test for this data shape. Conditions on the items that
    actually moved instead of diluting them across the whole set, which is
    where its extra power comes from."""

    SEGMENT_SCAN = "segment_scan"
    """Fire when any segment regresses significantly, whatever the aggregate.

    The only rule that catches a silent regression — a capability lost inside
    a release whose headline looks flat or positive. It also multiplies the
    opportunities to be wrong, so it needs a multiplicity correction to be
    usable rather than merely sensitive."""


@dataclass
class Detection:
    rule: Rule
    fired: bool
    statistic: float
    threshold: float
    detail: str
    segment: str | None = None

    def as_dict(self) -> dict:
        return {
            "rule": self.rule.value, "fired": self.fired,
            "statistic": self.statistic, "threshold": self.threshold,
            "detail": self.detail, "segment": self.segment,
        }


def aggregate_delta(result: ChurnResult, margin: float = 0.01) -> Detection:
    drop = -result.net_change
    return Detection(
        rule=Rule.AGGREGATE_DELTA,
        fired=drop > margin,
        statistic=drop, threshold=margin,
        detail=(f"score moved {result.net_change:+.2%}; rule fires below "
                f"{-margin:.2%}"),
    )


def interval_rule(result: ChurnResult, confidence: float = 0.95) -> Detection:
    from .power import wilson_interval

    n = result.n_items
    lo_b, hi_b = wilson_interval(round(result.accuracy_before * n), n, confidence)
    lo_a, hi_a = wilson_interval(round(result.accuracy_after * n), n, confidence)
    separated = hi_a < lo_b
    return Detection(
        rule=Rule.CONFIDENCE_INTERVAL,
        fired=separated,
        statistic=lo_b - hi_a, threshold=0.0,
        detail=(f"before [{lo_b:.1%}, {hi_b:.1%}], after [{lo_a:.1%}, "
                f"{hi_a:.1%}]; intervals "
                f"{'do not overlap' if separated else 'overlap'}"),
    )


def mcnemar_rule(result: ChurnResult, alpha: float = 0.05) -> Detection:
    p = result.mcnemar_p()
    # One-sided in effect: only a net loss counts as a regression.
    regressed = result.regressed > result.improved
    return Detection(
        rule=Rule.MCNEMAR,
        fired=bool(regressed and p < alpha),
        statistic=p, threshold=alpha,
        detail=(f"{result.regressed} lost vs {result.improved} gained, "
                f"p={p:.4f}"),
    )


def segment_scan(before: list[bool], after: list[bool], segments: list[str],
                 alpha: float = 0.05, min_items: int = 30,
                 correct_multiplicity: bool = True) -> list[Detection]:
    """
    Test every segment, with a correction for testing many of them.

    Scanning twenty segments at alpha 0.05 produces roughly one false alarm
    per release from chance alone. A team that acts on every such alert stops
    trusting the alerts, which costs more than the scan gains — so Bonferroni
    is applied by default.

    The correction is conservative and will miss real regressions in small
    segments. That is the intended trade: this rule exists to catch a
    capability loss worth investigating, not to flag every wobble.
    """
    segs = [s for s in by_segment(before, after, segments)
            if s.result.n_items >= min_items]
    if not segs:
        return []

    adjusted = alpha / len(segs) if correct_multiplicity else alpha
    out = []
    for s in segs:
        p = s.result.mcnemar_p()
        regressed = s.result.regressed > s.result.improved
        out.append(Detection(
            rule=Rule.SEGMENT_SCAN,
            fired=bool(regressed and p < adjusted),
            statistic=p, threshold=adjusted,
            segment=s.segment,
            detail=(f"{s.segment}: {s.result.net_change:+.2%}, "
                    f"{s.result.regressed} lost, p={p:.4f} "
                    f"(threshold {adjusted:.4f} after correcting for "
                    f"{len(segs)} segments)"),
        ))
    return out


# ---------------------------------------------------------------------------
# Cost
# ---------------------------------------------------------------------------

@dataclass
class DetectionCosts:
    """
    What each error costs.

    Both are ESTIMATES and both are meant to be replaced. The point of stating
    them explicitly is that the operating point follows from them, so a reader
    who disagrees can substitute their own and re-derive rather than reject
    the analysis.
    """

    investigation_hours: float = 30.0
    """Engineering time burned chasing a false alarm."""

    engineer_cost_per_hour: float = 150.0

    daily_requests: float = 10_000_000.0
    """Traffic exposed to an undetected regression."""

    days_to_independent_discovery: float = 21.0
    """
    How long a missed regression survives before something else surfaces it —
    a support trend, a customer escalation, a later eval.

    The weakest number here, and unknowable without incident data. Swept
    rather than defended.
    """

    harm_per_degraded_request: float = 0.002
    """
    Cost of one request answered worse than it would have been.

    Deliberately small and deliberately crude. Most degraded responses cost
    nothing measurable; a few cost a customer. This is an average standing in
    for a distribution nobody has published.
    """

    @property
    def false_alarm_cost(self) -> float:
        return self.investigation_hours * self.engineer_cost_per_hour

    def missed_cost(self, regression_size: float) -> float:
        """Cost of shipping a regression of this size, undetected."""
        degraded = (self.daily_requests * self.days_to_independent_discovery
                    * regression_size)
        return degraded * self.harm_per_degraded_request

    def asymmetry(self, regression_size: float = 0.02) -> float:
        """How many false alarms one missed regression is worth."""
        fa = self.false_alarm_cost
        return self.missed_cost(regression_size) / fa if fa else math.inf


@dataclass
class OperatingPoint:
    """A detection rule and threshold, costed."""

    rule: Rule
    threshold: float
    false_alarm_rate: float
    """MEASURED, by running the identical model twice."""
    detection_rate: float
    expected_annual_cost: float
    releases_per_year: float

    def as_dict(self) -> dict:
        return {
            "rule": self.rule.value, "threshold": self.threshold,
            "false_alarm_rate": self.false_alarm_rate,
            "detection_rate": self.detection_rate,
            "expected_annual_cost_usd": self.expected_annual_cost,
            "releases_per_year": self.releases_per_year,
        }


def expected_cost(false_alarm_rate: float, detection_rate: float,
                  *, costs: DetectionCosts, regression_size: float = 0.02,
                  releases_per_year: float = 24.0,
                  regression_prevalence: float = 0.15) -> float:
    """
    Annual cost of operating a detector at a given performance point.

    `regression_prevalence` — the share of releases that actually carry a
    regression worth catching — matters as much as the detector and is
    likewise an estimate. A detector looks excellent against a population with
    no regressions in it, because it never has the chance to miss one.
    """
    clean_releases = releases_per_year * (1 - regression_prevalence)
    bad_releases = releases_per_year * regression_prevalence

    false_alarms = clean_releases * false_alarm_rate
    missed = bad_releases * (1 - detection_rate)

    return (false_alarms * costs.false_alarm_cost
            + missed * costs.missed_cost(regression_size))


def recommend(measured_floor: float, *, costs: DetectionCosts | None = None,
              n_items: int = 300, baseline_accuracy: float = 0.70) -> dict:
    """
    What to do, given a measured noise floor.

    `measured_floor` is the self-disagreement rate from running the identical
    model twice — the single most important input, and the one almost nobody
    has. Everything else follows from it.
    """
    costs = costs or DetectionCosts()
    res = resolution(n_items, baseline_accuracy, discordance=measured_floor)

    detectable = res.paired_min_detectable
    aggregate_detectable = res.min_detectable_effect

    return {
        "measured_noise_floor": measured_floor,
        "n_items": n_items,
        "smallest_detectable_regression_paired": detectable,
        "smallest_detectable_regression_aggregate": aggregate_detectable,
        "aggregate_rule_is_blind_below": aggregate_detectable,
        "asymmetry_ratio": costs.asymmetry(),
        "recommendation": (
            f"On {n_items:,} items with a measured self-disagreement rate of "
            f"{measured_floor:.1%}, a paired test resolves regressions down to "
            f"{detectable:.1%}. The aggregate-delta rule most teams use cannot "
            f"resolve anything below {aggregate_detectable:.1%} — so a "
            f"regression between those two figures is invisible to the "
            f"standard dashboard and visible to a paired test on the same "
            f"data already collected."
        ),
        "caveat": (
            "The noise floor is measured on one model, one benchmark and one "
            "temperature. It does not transfer: a team must measure its own, "
            "which costs two evaluation runs and is the cheapest useful thing "
            "in this repository."
        ),
    }
