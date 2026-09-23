"""
The README must agree with what the code computes.

A figure quoted in prose drifts from the figure the code produces. On a
previous project it did: the document carried a number one run out of date
while the evidence file had moved on, and nobody reads the evidence file.

The document people read is where a stale number does its damage, so the
agreement is asserted rather than trusted — which is the same argument this
project makes about evaluation dashboards, applied to itself.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from evaldrift.benchmarks import REGISTRY, resolution_table
from evaldrift.detect import DetectionCosts
from evaldrift.power import items_required

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


def _readme() -> str:
    if not README.exists():
        pytest.skip("no README")
    return README.read_text()


class TestReadmeMatchesCode:

    def test_every_benchmark_row_is_current(self):
        """
        Each benchmark's item count and minimum detectable effect as printed
        must be what the code produces now.
        """
        text = _readme()
        for row in resolution_table(0.02):
            name = row["benchmark"]
            if name not in text:
                continue
            assert f"{row['items']:,}" in text, (
                f"{name}: item count {row['items']:,} not in README")
            assert f"{row['min_detectable_effect']:.1%}" in text, (
                f"{name}: MDE {row['min_detectable_effect']:.1%} not in README")

    def test_the_headline_count_is_current(self):
        """'Six of nine' must be what the table actually shows."""
        rows = resolution_table(0.02)
        fails = sum(1 for r in rows if not r["claim_supportable"])
        words = {4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight",
                 9: "nine", 10: "ten"}
        text = _readme().lower()

        # Accept digits or words on either side, since prose mixes them.
        num = {str(fails), words.get(fails, str(fails))}
        den = {str(len(rows)), words.get(len(rows), str(len(rows)))}
        forms = {f"{a} of {b}" for a in num for b in den}
        assert any(f in text for f in forms), (
            f"README headline does not state {fails} of {len(rows)}; "
            f"looked for any of {sorted(forms)}")

    def test_paired_item_counts_are_current(self):
        text = _readme()
        for d in (0.42, 0.15, 0.08):
            n = items_required(0.01, paired=True, discordance=d)
            assert f"{n:,}" in text, f"paired count {n:,} for d={d} not in README"

    def test_asymmetry_table_is_current(self):
        text = _readme()
        for h in (0.0002, 0.002, 0.02, 0.2):
            ratio = DetectionCosts(harm_per_degraded_request=h).asymmetry(0.02)
            assert f"{ratio:,.0f}x" in text, (
                f"asymmetry {ratio:,.0f}x for harm={h} not in README")

    def test_icc_figures_are_current(self):
        """The measured ICC and its consequences must match the code."""
        from evaldrift.icc import verdict
        v = verdict("MMLU")
        text = _readme()
        assert f"{v['estimated_icc']:.3f}" in text
        assert f"{v['effective_n']:.0f}" in text

    def test_published_floor_figures_are_current(self):
        from evaldrift.floors import PUBLISHED_FLOORS, signal_to_noise
        text = _readme()
        for f in PUBLISHED_FLOORS:
            # Prose writes 21% where the formatter gives 21.0%. Both forms
            # are accepted: the test exists to catch a stale NUMBER, not a
            # trailing zero.
            forms = {f"{f.typical:.1%}", f"{f.typical:.0%}"}
            assert any(v in text for v in forms), (
                f"{f.benchmark} floor {forms} not in README")
        assert f"{signal_to_noise('MMLU')['signal_to_noise_typical']:.2f}" in text

    def test_the_case_against_is_not_stale(self):
        """
        against.md conceded two objections that have since been addressed.
        A document that argues against a version of the project that no
        longer exists is the drift this repository is about, one level up.
        """
        against = (ROOT / "docs" / "against.md")
        if not against.exists():
            pytest.skip("no against.md")
        text = against.read_text()
        assert "since addressed" in text or "since sourced" in text
        assert "has not been measured\n\nThe harness exists" not in text

    def test_no_orphan_benchmark_named(self):
        """A benchmark discussed in prose but absent from the registry."""
        text = _readme()
        named = re.findall(r"\|\s*([A-Z][A-Za-z0-9\- ]+?)\s*\|\s*[\d,]+\s*\|", text)
        known = {b.name for b in REGISTRY}
        stray = {n.strip() for n in named} - known - {"Benchmark", "Items"}
        # Only complain about rows that look like benchmark rows.
        stray = {s for s in stray if s and s[0].isupper() and len(s) > 3}
        assert not stray, f"README names benchmarks absent from the registry: {stray}"
