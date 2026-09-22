"""
Net change versus gross change.

A dashboard shows one number per run. When that number does not move, the
conclusion drawn is "nothing changed". That inference is wrong, and the way it
is wrong is the reason silent regressions survive to production.

Two runs scoring 70% need not be the same 70%. A model can lose three hundred
items and gain three hundred different ones, report an identical aggregate, and
have become materially worse for everyone who depended on the lost set. The
aggregate reports the NET change. A user experiences the GROSS change.

    net    = accuracy_after − accuracy_before
    gross  = share of items whose outcome flipped in either direction
    churn  = gross, decomposed into regressions and improvements

Why this is the harder problem
------------------------------
A visible regression gets fixed, because someone sees the number drop. A
regression cancelled out by an unrelated improvement does not, because nothing
in the reporting surfaces it. The failure mode is not a missed alarm — it is an
alarm that was never capable of ringing.

Detecting it requires per-item results from both runs. Most eval pipelines
already produce exactly that and then discard it at the aggregation step.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass
class ChurnResult:
    """Item-level comparison of two evaluation runs."""

    n_items: int

    accuracy_before: float
    accuracy_after: float

    both_correct: int
    both_wrong: int
    regressed: int
    """Correct before, wrong after. The items a user lost."""
    improved: int
    """Wrong before, correct after."""

    @property
    def net_change(self) -> float:
        return self.accuracy_after - self.accuracy_before

    @property
    def gross_change(self) -> float:
        """Share of items whose outcome flipped, in either direction."""
        return (self.regressed + self.improved) / self.n_items if self.n_items else 0.0

    @property
    def regression_rate(self) -> float:
        """Share of all items that got worse, regardless of the aggregate."""
        return self.regressed / self.n_items if self.n_items else 0.0

    @property
    def hidden_ratio(self) -> float:
        """
        How much behaviour change the aggregate conceals.

        Gross divided by the absolute net. A value of 1 means every flip
        showed up in the headline number. A value of 20 means the aggregate
        surfaced one twentieth of what actually moved.

        Returns infinity when the net is exactly zero, which is the worst
        case rather than a degenerate one: total behavioural change,
        completely invisible.
        """
        net = abs(self.net_change)
        if net == 0:
            return math.inf
        return self.gross_change / net

    def mcnemar_p(self) -> float:
        """
        Exact binomial test on the discordant pairs.

        The correct test for paired binary outcomes, and far more sensitive
        than comparing the two aggregate scores — it conditions on the items
        that actually moved rather than diluting them across the whole set.
        """
        n_disc = self.regressed + self.improved
        if n_disc == 0:
            return 1.0

        k = min(self.regressed, self.improved)
        # Two-sided exact binomial at p=0.5.
        total = 0.0
        for i in range(k + 1):
            total += math.comb(n_disc, i) * (0.5 ** n_disc)
        return min(1.0, 2 * total)

    def as_dict(self) -> dict:
        return {
            "n_items": self.n_items,
            "accuracy_before": self.accuracy_before,
            "accuracy_after": self.accuracy_after,
            "net_change": self.net_change,
            "gross_change": self.gross_change,
            "regressed": self.regressed,
            "improved": self.improved,
            "both_correct": self.both_correct,
            "both_wrong": self.both_wrong,
            "regression_rate": self.regression_rate,
            "hidden_ratio": (None if math.isinf(self.hidden_ratio)
                             else self.hidden_ratio),
            "mcnemar_p": self.mcnemar_p(),
        }


def compare(before: list[bool], after: list[bool]) -> ChurnResult:
    """
    Compare two runs over the same items, in the same order.

    Order matters and is the caller's responsibility: item i in `before` must
    be item i in `after`. A mismatched join silently produces churn that is
    pure bookkeeping error, and it would look exactly like a real finding.
    """
    if len(before) != len(after):
        raise ValueError(
            f"runs cover different item counts ({len(before)} vs {len(after)}). "
            "Paired comparison requires the same items in the same order."
        )

    n = len(before)
    both_correct = sum(1 for b, a in zip(before, after) if b and a)
    both_wrong = sum(1 for b, a in zip(before, after) if not b and not a)
    regressed = sum(1 for b, a in zip(before, after) if b and not a)
    improved = sum(1 for b, a in zip(before, after) if not b and a)

    return ChurnResult(
        n_items=n,
        accuracy_before=sum(before) / n if n else 0.0,
        accuracy_after=sum(after) / n if n else 0.0,
        both_correct=both_correct, both_wrong=both_wrong,
        regressed=regressed, improved=improved,
    )


def simulate(n_items: int, accuracy: float, discordance: float,
             net_shift: float = 0.0, seed: int = 0) -> ChurnResult:
    """
    Construct a pair of runs with known churn, for testing the detector.

    This exists to characterise the instrument, not to stand in for data. It
    answers "if a change of this shape occurred, would the detector see it",
    which is a question about the detector. Every number reported as a FINDING
    comes from `compare` on real run outputs.
    """
    rng = random.Random(seed)
    before = [rng.random() < accuracy for _ in range(n_items)]

    # Flips are drawn per item rather than fixed by count. A construction that
    # pins the totals produces a net change of exactly zero every time, which
    # makes the concealment look total and is an artefact of the simulator
    # rather than a property of evaluation. Real runs carry sampling noise in
    # both directions.
    p_regress = max(0.0, (discordance - net_shift) / 2)
    p_improve = max(0.0, (discordance + net_shift) / 2)

    n_correct = sum(before)
    n_wrong = n_items - n_correct
    rate_regress = (p_regress * n_items / n_correct) if n_correct else 0.0
    rate_improve = (p_improve * n_items / n_wrong) if n_wrong else 0.0

    after = [
        (False if (b and rng.random() < rate_regress)
         else True if (not b and rng.random() < rate_improve)
         else b)
        for b in before
    ]
    return compare(before, after)


@dataclass
class SegmentChurn:
    """Churn within one slice of the benchmark."""

    segment: str
    result: ChurnResult

    @property
    def is_silent_regression(self) -> bool:
        """
        Degraded here while the aggregate held steady or improved.

        The specific failure this project exists to surface: a capability that
        got worse inside a release that looked flat or positive.
        """
        return self.result.net_change < 0


def by_segment(before: list[bool], after: list[bool],
               segments: list[str]) -> list[SegmentChurn]:
    """
    Churn per slice, which is where silent regressions actually live.

    A model that improves broadly while degrading on one domain shows a
    healthy aggregate. Whether that matters depends on who was using that
    domain, and the aggregate cannot tell you.
    """
    if not (len(before) == len(after) == len(segments)):
        raise ValueError("before, after and segments must align item for item")

    buckets: dict[str, tuple[list[bool], list[bool]]] = {}
    for b, a, s in zip(before, after, segments):
        buckets.setdefault(s, ([], []))
        buckets[s][0].append(b)
        buckets[s][1].append(a)

    return [SegmentChurn(segment=s, result=compare(bs, as_))
            for s, (bs, as_) in sorted(buckets.items())]


def silent_regressions(before: list[bool], after: list[bool],
                       segments: list[str],
                       min_items: int = 30) -> list[SegmentChurn]:
    """
    Segments that got worse inside a release whose aggregate did not.

    `min_items` guards against reporting a two-item segment as a regression.
    A slice too small to measure is not evidence of anything, and listing it
    would bury the real findings in noise — the same discipline that applies
    to the benchmark as a whole.
    """
    overall = compare(before, after)
    if overall.net_change < 0:
        return []          # not silent; the aggregate already shows it

    return [s for s in by_segment(before, after, segments)
            if s.is_silent_regression and s.result.n_items >= min_items]
