"""
The noise floor, as published.

`harness.html` measures self-disagreement by running one model twice. That was
built because no published floor was known. One exists, it is better sourced
than anything this project could produce, and it comes from the benchmark
authors themselves.

The MMLU-Pro authors evaluated models under **24 different but reasonable
prompts** and reported the resulting spread in scores. That is a noise floor in
the strict sense: the model did not change, the items did not change, only the
wording of the request did. Every point of spread is measurement error.

    MMLU        4-5% typical, peaks at 10.98%
    MMLU-Pro    ~2% typical, maximum 3.74%

Set against what the same literature reports for the gaps being measured:
frontier models cluster within 2-4% of each other on MMLU.

**The measurement error is as large as the differences being measured, and on
the original MMLU it is larger.** That is not an inference from a power
calculation. It is two published numbers placed side by side.

Why this supersedes measuring it here
-------------------------------------
A floor measured on one model, one benchmark and one temperature would not
transfer, and this project says so in `detect.recommend`. The published figures
come from the benchmark's own authors, across 24 prompts and multiple models,
and are the number a team should reach for before running anything.

The harness remains useful for one thing the published figures cannot give: a
team's OWN floor, on its own items and its own decoding settings. But the
question "is the floor large enough to matter" is already answered, and it was
answered in the paper that introduced MMLU-Pro.

The one component averaging actually fixes
------------------------------------------
Messing (2026) measures replicate noise directly — repeated API calls with
identical inputs, which is precisely what `harness.html` was built to measure.
It is 21% of per-observation variance in their safety demonstration.

Their framing of that number is the part that matters, and it cuts against the
harness rather than for it. Replicate noise is large per observation but
contributes **under 0.5% of the variance of the mean** at 8 replications,
because it divides by every other factor count. It is the one component that
more sampling genuinely fixes.

Prompt and judge variance do not divide away, which is why they dominate the
corrected interval. So the harness measures the least consequential source of
error, and the sources that matter are the ones it cannot see. That is worth
stating plainly here rather than leaving the harness looking more useful than
it is.

A note on sourcing
------------------
Only primary sources are recorded below — figures reported by the authors of
the benchmark or of the study that produced them. A widely repeated claim of
"13 percentage points of reproducibility variance for GPT-4o on MMLU-Pro"
appears in secondary commentary without a traceable primary citation, and is
therefore excluded. It would have strengthened the argument, which is exactly
why it needed checking.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NoiseFloor:
    """A published measure of variance with the model held constant."""

    benchmark: str
    source_of_variance: str
    typical: float
    maximum: float | None
    method: str
    citation: str

    def exceeds(self, claimed_improvement: float) -> bool:
        return self.typical >= claimed_improvement


PUBLISHED_FLOORS: list[NoiseFloor] = [
    NoiseFloor(
        benchmark="AILuminate (safety)",
        source_of_variance="replicate — repeated calls, identical inputs",
        typical=0.21,
        maximum=None,
        method="8 replications per cell across 50,760 calls; variance "
               "decomposition via REML",
        citation="Messing 2026, 'Hidden Measurement Error in LLM Pipelines', "
                 "section 4.1 and SI section C.5",
    ),
    NoiseFloor(
        benchmark="MMLU",
        source_of_variance="prompt wording",
        typical=0.045,
        maximum=0.1098,
        method="24 different but reasonable prompts, same model, same items",
        citation="Wang et al. 2024, 'MMLU-Pro: A More Robust and Challenging "
                 "Multi-Task Language Understanding Benchmark', section 6.3",
    ),
    NoiseFloor(
        benchmark="MMLU-Pro",
        source_of_variance="prompt wording",
        typical=0.02,
        maximum=0.0374,
        method="24 different but reasonable prompts, same model, same items",
        citation="Wang et al. 2024, section 6.3",
    ),
]


# What the same literature reports for the gaps these benchmarks are used to
# measure. The comparison is the finding.
COMPETITIVE_SPREAD = {
    "description": "State-of-the-art models cluster within this range on MMLU",
    "low": 0.02,
    "high": 0.04,
    "citation": "Wang et al. 2024, on benchmark saturation and low "
                "discriminativity",
}


def signal_to_noise(benchmark: str = "MMLU") -> dict:
    """
    Compare a benchmark's published noise floor against the differences it is
    used to detect.

    A ratio at or below one means the instrument cannot resolve what it is
    being asked to resolve, whatever the sample size. No amount of extra items
    fixes variance that comes from prompt wording rather than from sampling.
    """
    floor = next((f for f in PUBLISHED_FLOORS if f.benchmark == benchmark), None)
    if floor is None:
        raise ValueError(f"no published floor recorded for {benchmark}")

    lo, hi = COMPETITIVE_SPREAD["low"], COMPETITIVE_SPREAD["high"]
    mid = (lo + hi) / 2

    return {
        "benchmark": benchmark,
        "noise_floor_typical": floor.typical,
        "noise_floor_max": floor.maximum,
        "competitive_spread": [lo, hi],
        "signal_to_noise_typical": mid / floor.typical,
        "signal_to_noise_worst": (mid / floor.maximum) if floor.maximum else None,
        "resolvable": mid > floor.typical,
        "method": floor.method,
        "citation": floor.citation,
        "note": (
            "This variance does not shrink with more items. Sampling error "
            "falls as 1/sqrt(n); prompt sensitivity does not fall at all, "
            "because it is not sampling error. A benchmark whose prompt "
            "variance exceeds the differences being reported cannot resolve "
            "them at any size."
        ),
    }


def summary() -> str:
    """One paragraph a reader can quote."""
    mmlu = signal_to_noise("MMLU")
    pro = signal_to_noise("MMLU-Pro")
    return (
        f"The authors of MMLU-Pro measured score spread across 24 reasonable "
        f"prompts with the model and items held fixed: "
        f"{mmlu['noise_floor_typical']:.1%} typically on MMLU, peaking at "
        f"{mmlu['noise_floor_max']:.2%}, against {pro['noise_floor_typical']:.1%} "
        f"on MMLU-Pro. The same literature reports frontier models clustering "
        f"within {COMPETITIVE_SPREAD['low']:.0%}-{COMPETITIVE_SPREAD['high']:.0%} "
        f"of each other on MMLU. Measurement error is therefore as large as the "
        f"differences being measured, and on the original MMLU it is larger. "
        f"Crucially this variance does not shrink with more items: sampling "
        f"error falls as one over root n, prompt sensitivity does not fall at "
        f"all. A bigger benchmark does not fix it."
    )
