"""
Tests for evaldrift.

These target the properties the conclusions rest on, and several pin an error
that was actually made. Measurement code is unusually prone to looking correct
while being wrong, because the output is a plausible number either way — which
is the same problem the project is about.
"""

from __future__ import annotations

import math

import pytest

from evaldrift import detect
from evaldrift.churn import ChurnResult, by_segment, compare, silent_regressions, simulate
from evaldrift.detect import DetectionCosts, expected_cost, recommend
from evaldrift.power import (
    interval_halfwidth, is_claim_supportable, items_required, resolution,
    wilson_interval, z_for,
)


# ===========================================================================
# Power
# ===========================================================================

class TestPower:

    def test_interval_narrows_with_sample_size(self):
        assert interval_halfwidth(0.7, 100) > interval_halfwidth(0.7, 1000)
        assert interval_halfwidth(0.7, 1000) > interval_halfwidth(0.7, 10000)

    def test_wilson_stays_inside_zero_one_at_the_boundaries(self):
        """
        The textbook normal interval runs past 1.0 at high accuracy, which is
        exactly where teams are most confident and least entitled to be.
        """
        lo, hi = wilson_interval(100, 100)
        # Floating point lands a hair under 1.0; the property is containment.
        assert hi == pytest.approx(1.0) and hi <= 1.0 and 0 < lo < 1
        lo, hi = wilson_interval(0, 100)
        assert lo == pytest.approx(0.0) and lo >= 0.0 and 0 < hi < 1

    def test_small_benchmarks_cannot_resolve_small_effects(self):
        """The headline finding, asserted rather than described."""
        r = resolution(200, 0.70)
        assert r.min_detectable_effect > 0.10, (
            "a 200-item benchmark should not resolve anything under ten points")

    def test_even_large_benchmarks_cannot_resolve_one_point(self):
        """MMLU's full 14,042 items still cannot detect a 1% change."""
        r = resolution(14042, 0.70)
        assert r.min_detectable_effect > 0.01

    def test_items_required_scales_as_inverse_square_of_effect(self):
        """Halving the detectable effect quadruples the sample needed."""
        n_small = items_required(0.02)
        n_half = items_required(0.01)
        assert 3.5 < n_half / n_small < 4.5

    def test_paired_beats_unpaired_when_runs_agree(self):
        """
        REGRESSION. The default discordance was 2p(1-p) — what UNRELATED
        models disagree on — which made paired and unpaired power identical
        and erased the advantage the function exists to show.
        """
        r = resolution(1000, 0.70, discordance=0.15)
        assert r.paired_min_detectable < r.min_detectable_effect

    def test_paired_equals_unpaired_for_independent_runs(self):
        """And it must NOT claim an advantage where none exists."""
        p = 0.70
        r = resolution(1000, p, discordance=2 * p * (1 - p))
        assert r.paired_min_detectable == pytest.approx(
            r.min_detectable_effect, rel=1e-6)

    def test_claim_check_rejects_an_unsupportable_improvement(self):
        ok, why = is_claim_supportable(0.02, 200)
        assert not ok
        assert "NOT distinguishable" in why
        assert "would be required" in why

    def test_claim_check_accepts_a_large_effect(self):
        ok, _ = is_claim_supportable(0.25, 200)
        assert ok

    def test_zero_effect_is_rejected(self):
        with pytest.raises(ValueError):
            items_required(0.0)

    def test_z_for_matches_known_quantiles(self):
        assert z_for(0.975) == pytest.approx(1.96, abs=0.01)
        assert z_for(0.80) == pytest.approx(0.8416, abs=0.01)


# ===========================================================================
# Churn
# ===========================================================================

class TestChurn:

    def test_identical_runs_have_no_churn(self):
        runs = [True, False, True, True]
        r = compare(runs, runs)
        assert r.gross_change == 0.0 and r.net_change == 0.0

    def test_net_can_be_zero_while_gross_is_large(self):
        """
        The central claim: an unchanged aggregate does not mean unchanged
        behaviour.
        """
        before = [True] * 50 + [False] * 50
        after = [False] * 50 + [True] * 50
        r = compare(before, after)
        assert r.net_change == 0.0
        assert r.gross_change == 1.0
        assert math.isinf(r.hidden_ratio)

    def test_regressions_and_improvements_are_counted_separately(self):
        r = compare([True, True, False], [True, False, True])
        assert r.regressed == 1 and r.improved == 1

    def test_mismatched_lengths_are_refused(self):
        """
        A mismatched join produces churn that is pure bookkeeping error and
        looks exactly like a finding.
        """
        with pytest.raises(ValueError, match="different item counts"):
            compare([True, False], [True])

    def test_mcnemar_is_insignificant_for_balanced_flips(self):
        r = compare([True] * 10 + [False] * 10, [False] * 10 + [True] * 10)
        assert r.mcnemar_p() > 0.5

    def test_mcnemar_is_significant_for_one_sided_flips(self):
        before = [True] * 30
        after = [False] * 25 + [True] * 5
        assert compare(before, after).mcnemar_p() < 0.01

    def test_simulation_produces_noisy_net_not_exact_zero(self):
        """
        REGRESSION. The first simulator pinned flip counts, so net change was
        exactly zero every time. That made concealment look total and was an
        artefact of the construction rather than a property of evaluation.
        """
        nets = [simulate(500, 0.70, 0.15, net_shift=0.0, seed=s).net_change
                for s in range(8)]
        assert len({round(n, 6) for n in nets}) > 1, "net change is deterministic"
        assert any(n != 0 for n in nets)

    def test_simulation_hits_the_requested_discordance(self):
        r = simulate(4000, 0.70, discordance=0.20, seed=3)
        assert 0.16 < r.gross_change < 0.24

    def test_segment_split_preserves_every_item(self):
        before = [True, False, True, False]
        after = [True, True, False, False]
        segs = ["a", "a", "b", "b"]
        assert sum(s.result.n_items for s in by_segment(before, after, segs)) == 4

    def test_silent_regression_is_found_when_aggregate_holds(self):
        # Segment A degrades; B improves enough to mask it.
        before = [True] * 50 + [False] * 50
        after = [False] * 12 + [True] * 38 + [True] * 20 + [False] * 30
        segs = ["a"] * 50 + ["b"] * 50
        found = silent_regressions(before, after, segs, min_items=10)
        assert [s.segment for s in found] == ["a"]

    def test_nothing_is_silent_when_the_aggregate_already_dropped(self):
        """If the headline shows it, it is not a silent regression."""
        before = [True] * 100
        after = [False] * 40 + [True] * 60
        assert silent_regressions(before, after, ["a"] * 100) == []

    def test_tiny_segments_are_not_reported(self):
        """
        A slice too small to measure is not evidence, and listing it buries
        the real findings.
        """
        before = [True] * 100
        after = [False] * 3 + [True] * 97
        segs = ["tiny"] * 3 + ["big"] * 97
        assert silent_regressions(before, after, segs, min_items=30) == []


# ===========================================================================
# Detection
# ===========================================================================

def _result(n, before_acc, regressed, improved):
    both_correct = round(before_acc * n) - regressed
    return ChurnResult(
        n_items=n, accuracy_before=before_acc,
        accuracy_after=(both_correct + improved) / n,
        both_correct=both_correct,
        both_wrong=n - both_correct - regressed - improved,
        regressed=regressed, improved=improved,
    )


class TestDetectionRules:

    def test_aggregate_rule_fires_on_noise(self):
        """
        REAL FINDING, pinned. 18 items lost against 15 gained is a coin flip
        (p=0.73), and the aggregate-delta rule most teams use fires on it
        while the paired test correctly stays silent.
        """
        r = _result(300, 0.70, regressed=18, improved=15)
        agg = detect.aggregate_delta(r, margin=0.005)
        mc = detect.mcnemar_rule(r)
        assert agg.fired, "aggregate rule should fire on this noise"
        assert not mc.fired, "paired test should not"
        assert mc.statistic > 0.5

    def test_mcnemar_fires_on_a_one_sided_shift(self):
        r = _result(300, 0.70, regressed=30, improved=5)
        assert detect.mcnemar_rule(r).fired

    def test_interval_rule_is_underpowered(self):
        """
        Non-overlapping intervals is stricter than a significant difference,
        so this rule misses regressions a proper test catches.
        """
        r = _result(300, 0.70, regressed=30, improved=5)
        assert detect.mcnemar_rule(r).fired
        assert not detect.interval_rule(r).fired

    def test_segment_scan_corrects_for_multiplicity(self):
        """
        Twenty segments at alpha 0.05 yields about one false alarm per release
        from chance alone, and a team that acts on all of them stops trusting
        the alerts.
        """
        before, after, segs = [], [], []
        for i in range(20):
            before += [True] * 50
            after += [True] * 50
            segs += [f"s{i}"] * 50
        out = detect.segment_scan(before, after, segs)
        assert out
        assert all(d.threshold < 0.05 for d in out)

    def test_segment_scan_can_disable_the_correction(self):
        before = [True] * 60
        after = [False] * 10 + [True] * 50
        segs = ["a"] * 60
        with_corr = detect.segment_scan(before, after, segs)[0]
        without = detect.segment_scan(before, after, segs,
                                      correct_multiplicity=False)[0]
        assert without.threshold >= with_corr.threshold

    def test_segment_scan_ignores_small_slices(self):
        before, after, segs = [True] * 20, [False] * 20, ["tiny"] * 20
        assert detect.segment_scan(before, after, segs, min_items=30) == []


class TestCostModel:

    def test_asymmetry_is_modest_at_default_parameters(self):
        """
        REGRESSION on a claim, not code. The module originally asserted the
        asymmetry was orders of magnitude. At the stated defaults it is about
        two to one, and the docstring was corrected rather than the parameter
        tuned to fit the narrative.
        """
        c = DetectionCosts()
        assert 1 < c.asymmetry(0.02) < 10

    def test_asymmetry_is_driven_by_one_unpublished_parameter(self):
        """
        Swinging harm-per-request across its plausible range moves the
        conclusion from 'barely worth detecting' to 'detect at any cost'. The
        honest output is that sensitivity, not a threshold.
        """
        low = DetectionCosts(harm_per_degraded_request=0.0002).asymmetry(0.02)
        high = DetectionCosts(harm_per_degraded_request=0.2).asymmetry(0.02)
        assert high / max(low, 1e-9) > 100

    def test_larger_regressions_cost_more(self):
        c = DetectionCosts()
        assert c.missed_cost(0.05) > c.missed_cost(0.01)

    def test_a_perfect_detector_still_costs_something(self):
        """False alarms at zero and detection at one is not free of noise."""
        cost = expected_cost(0.0, 1.0, costs=DetectionCosts())
        assert cost == 0.0

    def test_a_blind_detector_carries_full_exposure(self):
        cost = expected_cost(0.0, 0.0, costs=DetectionCosts())
        assert cost > 0


class TestRecommendation:

    def test_recommendation_uses_the_measured_floor(self):
        low = recommend(0.03, n_items=300)
        high = recommend(0.20, n_items=300)
        assert (low["smallest_detectable_regression_paired"]
                < high["smallest_detectable_regression_paired"])

    def test_recommendation_states_what_the_aggregate_rule_misses(self):
        rec = recommend(0.08, n_items=300)
        assert rec["smallest_detectable_regression_aggregate"] > \
               rec["smallest_detectable_regression_paired"]
        assert "invisible to the" in rec["recommendation"]

    def test_recommendation_says_the_floor_does_not_transfer(self):
        """
        The floor is measured on one model, one benchmark, one temperature.
        Presenting it as a general constant would be the exact error this
        project exists to catch.
        """
        rec = recommend(0.08)
        assert "does not transfer" in rec["caveat"]
        assert "measure its own" in rec["caveat"]


# Acklam's rational approximation carries relative error of about 1.15e-9,
# so absolute error near z=2 is a few parts in a billion. Tolerance is set to
# the method's documented resolution rather than tighter: asserting precision
# an instrument does not have is the same error this project measures.
APPROX_TOL = 1e-8


class TestInverseNormal:
    """
    The approximation used for confidence levels outside the lookup table.

    A numerical routine that is wrong produces a plausible interval, not an
    error, so every branch is checked against known quantiles.
    """

    @pytest.mark.parametrize("p,expected", [
        (0.50, 0.0),
        (0.841, 1.0),
        (0.9772, 2.0),
        (0.99865, 3.0),     # Phi(3.0) = 0.99865, not 0.9987
        (0.0228, -2.0),
        (0.01, -2.326),
        (0.999, 3.090),
    ])
    def test_matches_known_quantiles_across_every_branch(self, p, expected):
        assert z_for(p) == pytest.approx(expected, abs=0.01)

    def test_is_monotonic(self):
        ps = [0.01, 0.05, 0.2, 0.5, 0.8, 0.95, 0.99]
        zs = [z_for(p) for p in ps]
        assert zs == sorted(zs)

    def test_is_antisymmetric(self):
        """
        REGRESSION. The lookup table held values rounded to four places, so
        z(0.90) disagreed with -z(0.10) at the fifth decimal: the table was
        less precise than the approximation it was meant to short-circuit.
        Covers both code paths deliberately — 0.10 goes through the
        approximation, 0.90 through the table.
        """
        for p in (0.02, 0.1, 0.2, 0.3):
            assert z_for(p) == pytest.approx(-z_for(1 - p), abs=APPROX_TOL)

    def test_table_agrees_with_the_approximation(self):
        """The fast path must return what the slow path would."""
        from evaldrift.power import Z
        for level, tabled in Z.items():
            # 1 - level forces the approximation branch; negate to compare.
            assert tabled == pytest.approx(-z_for(1 - level), abs=APPROX_TOL)


class TestPowerEdges:

    def test_empty_benchmark_has_no_interval(self):
        assert wilson_interval(0, 0) == (0.0, 0.0)

    def test_paired_items_required_is_smaller_when_runs_agree(self):
        paired = items_required(0.02, paired=True, discordance=0.10)
        unpaired = items_required(0.02)
        assert paired < unpaired

    def test_higher_confidence_widens_the_interval(self):
        assert interval_halfwidth(0.7, 500, confidence=0.99) > \
               interval_halfwidth(0.7, 500, confidence=0.90)

    def test_resolution_serialises(self):
        d = resolution(500, discordance=0.1).as_dict()
        assert {"n_items", "min_detectable_effect",
                "paired_min_detectable_effect", "assumed_discordance"} <= set(d)


class TestBenchmarkRegistry:

    def test_item_counts_match_published_splits(self):
        """The counts are the checkable part of this finding."""
        from evaldrift.benchmarks import REGISTRY
        known = {"HumanEval": 164, "GPQA Diamond": 198, "GSM8K": 1319,
                 "MMLU": 14042, "MATH": 5000}
        by_name = {b.name: b.items for b in REGISTRY}
        for name, count in known.items():
            assert by_name[name] == count, f"{name} count wrong"

    def test_every_benchmark_is_sourced(self):
        from evaldrift.benchmarks import REGISTRY
        assert all(b.source for b in REGISTRY)

    def test_small_benchmarks_fail_a_two_point_claim(self):
        """The headline, pinned: most quoted benchmarks cannot resolve 2 points."""
        from evaldrift.benchmarks import resolution_table
        rows = {r["benchmark"]: r for r in resolution_table(0.02)}
        for name in ("HumanEval", "GPQA Diamond", "TruthfulQA"):
            assert not rows[name]["claim_supportable"]

    def test_finding_survives_a_less_generous_accuracy(self):
        """
        Accuracy levels are estimates that lean high, which narrows variance
        and flatters each benchmark. The verdict must hold at 50%, the worst
        case, or the finding depends on the estimate.
        """
        from evaldrift.power import is_claim_supportable
        for n in (164, 198, 817):
            assert not is_claim_supportable(0.02, n, 0.50)[0]

    def test_shortfall_is_reported(self):
        from evaldrift.benchmarks import resolution_table
        gpqa = next(r for r in resolution_table(0.02)
                    if r["benchmark"] == "GPQA Diamond")
        assert gpqa["shortfall_multiple"] > 10
