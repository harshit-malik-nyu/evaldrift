"""
The benchmarks people actually quote, and how large they are.

Sizes are the evaluation splits as published by each benchmark's authors. They
are the most checkable numbers in this repository: each is stated in the
source paper or dataset card, and GSM8K's was verified directly by downloading
the split (1,319 items).

Why sizes are enough
--------------------
The resolution of a benchmark depends on its item count and the accuracy range
it is used in, both of which are public. No model outputs are needed to show
that a benchmark cannot distinguish a two-point change, because that follows
from its size alone. This makes the headline finding here unusually robust: it
does not depend on any model, any run, or any estimate.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Benchmark:
    name: str
    items: int
    typical_accuracy: float
    """
    Where frontier models currently score — an ESTIMATE, unlike the item
    counts, which are published.

    It matters because binomial variance peaks at 50% and falls toward the
    extremes, so resolution is worst mid-range and best near ceiling. The
    estimates here lean HIGH for most benchmarks, which shrinks the variance
    and makes each benchmark look more capable than it would at a lower
    accuracy. Every "cannot resolve" verdict below therefore survives a less
    generous assumption; the error in these estimates runs in the direction
    that weakens the finding, not the one that inflates it.
    """
    split: str
    source: str


REGISTRY: list[Benchmark] = [
    Benchmark("HumanEval", 164, 0.90, "test",
              "Chen et al. 2021, 'Evaluating Large Language Models Trained on Code'"),
    Benchmark("GPQA Diamond", 198, 0.70, "diamond",
              "Rein et al. 2023, 'GPQA: A Graduate-Level Google-Proof Q&A Benchmark'"),
    Benchmark("TruthfulQA", 817, 0.70, "validation",
              "Lin et al. 2021, 'TruthfulQA: Measuring How Models Mimic Human Falsehoods'"),
    Benchmark("ARC-Challenge", 1172, 0.95, "test",
              "Clark et al. 2018, 'Think you have Solved Question Answering?'"),
    Benchmark("GSM8K", 1319, 0.95, "test",
              "Cobbe et al. 2021; size verified directly from openai/grade-school-math"),
    Benchmark("MATH", 5000, 0.80, "test",
              "Hendrycks et al. 2021, 'Measuring Mathematical Problem Solving'"),
    Benchmark("HellaSwag", 10042, 0.95, "validation",
              "Zellers et al. 2019, 'HellaSwag: Can a Machine Really Finish Your Sentence?'"),
    Benchmark("MMLU-Pro", 12032, 0.75, "test",
              "Wang et al. 2024, 'MMLU-Pro: A More Robust and Challenging Multi-Task "
              "Language Understanding Benchmark'"),
    Benchmark("MMLU", 14042, 0.88, "test",
              "Hendrycks et al. 2020, 'Measuring Massive Multitask Language Understanding'"),
]


def resolution_table(claimed_effect: float = 0.02, confidence: float = 0.95,
                     power: float = 0.80) -> list[dict]:
    """
    For every registered benchmark: what it can resolve, and whether a
    typical claimed improvement of `claimed_effect` is distinguishable from
    noise on it.
    """
    from .power import is_claim_supportable, items_required, resolution

    rows = []
    for b in REGISTRY:
        r = resolution(b.items, b.typical_accuracy, confidence, power)
        ok, _ = is_claim_supportable(claimed_effect, b.items,
                                     b.typical_accuracy, confidence, power)
        need = items_required(claimed_effect, b.typical_accuracy,
                              confidence, power)
        rows.append({
            "benchmark": b.name,
            "items": b.items,
            "typical_accuracy": b.typical_accuracy,
            "interval_halfwidth": r.halfwidth,
            "min_detectable_effect": r.min_detectable_effect,
            "claim": claimed_effect,
            "claim_supportable": ok,
            "items_needed_for_claim": need,
            "shortfall_multiple": need / b.items,
            "source": b.source,
        })
    return rows
