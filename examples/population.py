"""A population of twelve individuals meets the same 10-minute protocol.

Usage:
    python examples/population.py [--runs runs/population]

Individual i is drawn from the Phase 2 population spec (docs/VARIABILITY.md
§4) with engine seed base + i — same draws, same trajectories, every time.
The summary shows population mean ± SD per statistic: the spread is the
point, not the average.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from unbodysoma.observe.run import RunWriter
from unbodysoma.population import population_summary, run_population, sample_individual
from unbodysoma.presets import build_minimal_human
from unbodysoma.world import Event

SECONDS = 600.0
PROTOCOL = [Event(120.0, 150.0, "world.threat", 0.9), Event(0.0, 1e9, "world.food_available", 1.0)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--runs", type=Path, default=None, help="write each individual's run record under this directory"
    )
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    if args.runs:
        for i in range(args.count):
            engine = build_minimal_human(PROTOCOL, seed=args.seed + i, overrides=sample_individual(args.seed, i))
            with RunWriter(args.runs / f"ind_{i:02d}", every=1.0).attach(engine):
                engine.run(SECONDS)

    results = run_population(
        args.count, base_seed=args.seed, seconds=SECONDS, builder=build_minimal_human, events=PROTOCOL
    )
    print(population_summary(results))


if __name__ == "__main__":
    main()
