"""
Command line interface.

Three questions, each answerable without running a model:

    resolution   what can a benchmark of this size detect?
    check        is a claimed improvement supportable on this benchmark?
    table        the resolution of every benchmark people quote
"""

from __future__ import annotations

import argparse
import json
import sys

from .benchmarks import resolution_table
from .power import is_claim_supportable, items_required, resolution


def _fmt_pct(x: float) -> str:
    return f"{x:.1%}"


def cmd_resolution(args: argparse.Namespace) -> int:
    r = resolution(args.items, args.accuracy, discordance=args.discordance)
    if args.json:
        print(json.dumps(r.as_dict(), indent=2))
        return 0

    print(f"A benchmark of {args.items:,} items at {args.accuracy:.0%} accuracy:")
    print(f"  interval on one score      ±{_fmt_pct(r.halfwidth)}")
    print(f"  smallest detectable change  {_fmt_pct(r.min_detectable_effect)}")
    print(f"  paired, if runs disagree on {_fmt_pct(r.discordance)}: "
          f"{_fmt_pct(r.paired_min_detectable)}")
    print()
    print("  Sampling bounds only. Prompt formatting, temperature and scoring")
    print("  ambiguity widen these further, so this is a lower bound on")
    print("  uncertainty — the most generous reading.")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    ok, why = is_claim_supportable(args.effect, args.items, args.accuracy)
    if args.json:
        print(json.dumps({"supportable": ok, "explanation": why,
                          "items_needed": items_required(
                              args.effect, args.accuracy)}, indent=2))
        return 0 if ok else 1

    print(("SUPPORTABLE" if ok else "NOT SUPPORTABLE") + f": {why}")
    return 0 if ok else 1


def cmd_table(args: argparse.Namespace) -> int:
    rows = resolution_table(args.effect)
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    fails = sum(1 for r in rows if not r["claim_supportable"])
    print(f"Can a {args.effect:.0%} improvement be distinguished from noise?")
    print()
    print(f"{'benchmark':16s} {'items':>7} {'detectable':>11} "
          f"{'claim':>6} {'needed':>10}")
    for r in rows:
        print(f"{r['benchmark']:16s} {r['items']:>7,} "
              f"{r['min_detectable_effect']:>10.1%} "
              f"{'yes' if r['claim_supportable'] else 'NO':>6} "
              f"{r['items_needed_for_claim']:>10,}")
    print()
    print(f"{fails} of {len(rows)} cannot distinguish a {args.effect:.0%} "
          "change from noise.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="evaldrift",
        description="What benchmark evaluation can and cannot detect.")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("resolution", help="what a benchmark of size N can detect")
    p.add_argument("items", type=int)
    p.add_argument("--accuracy", type=float, default=0.70)
    p.add_argument("--discordance", type=float, default=None,
                   help="share of items two runs disagree on; measure it with "
                        "the noise-floor harness rather than guessing")
    p.set_defaults(func=cmd_resolution)

    p = sub.add_parser("check", help="is a claimed improvement supportable?")
    p.add_argument("effect", type=float, help="claimed change, e.g. 0.02")
    p.add_argument("items", type=int)
    p.add_argument("--accuracy", type=float, default=0.70)
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("table", help="resolution of published benchmarks")
    p.add_argument("--effect", type=float, default=0.02)
    p.set_defaults(func=cmd_table)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
