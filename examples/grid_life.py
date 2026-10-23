"""Grid life: the Phase 1 completion scenario, summarised day by day.

Runs scenarios/grid_72h.toml (three days in a grid world with slowly regrowing
food and daily predator visits) and prints when the organism slept, ate and fled.

Run:  python examples/grid_life.py [--hours 72] [--seed 0] [--runs runs/grid_life]
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from unbodysoma.config import load_scenario
from unbodysoma.observe import HealthMonitor, Recorder, RunWriter
from unbodysoma.observe.behavior import episodes, time_fraction

SCENARIO = Path(__file__).resolve().parents[1] / "scenarios" / "grid_72h.toml"
KEYS = ("motor.sleeping", "motor.eating", "psyche.action.selected_flee", "world.threat", "soma.circadian.clock_hour")
DAY = 86400.0


def hhmm(hour: float) -> str:
    minutes = round(hour * 60)  # round first, so 11:59.5 becomes 12:00, not 11:00
    return f"{minutes // 60 % 24:02d}:{minutes % 60:02d}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--hours", type=float, default=72.0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--runs", type=Path, help="also write a run record to this directory")
    args = parser.parse_args()

    scenario = replace(load_scenario(SCENARIO), seed=args.seed, duration_s=args.hours * 3600.0)
    engine = scenario.build()
    recorder = Recorder(KEYS, every=1.0)
    engine.observe(recorder)
    monitor = HealthMonitor(every=10.0, halt_on="critical").attach(engine)
    writer = (
        RunWriter(args.runs, every=60.0, config={"scenario": scenario.name, "seed": args.seed}) if args.runs else None
    )
    if writer:
        writer.attach(engine)
    engine.run(scenario.duration_s)
    if writer:
        writer.close()

    t = recorder.times()
    clock = recorder.column("soma.circadian.clock_hour")
    at = lambda s: hhmm(clock[min(int(round(s)), len(clock) - 1)])  # noqa: E731
    found = {
        "sleep": episodes(t, recorder.column("motor.sleeping")),
        "meal": episodes(t, recorder.column("motor.eating")),
        "flight": episodes(t, recorder.column("psyche.action.selected_flee")),
    }
    for day in range(int((scenario.duration_s + DAY - 1) // DAY)):
        print(f"day {day + 1} (08:00 to 08:00)")
        for kind, items in found.items():
            today = [e for e in items if day * DAY <= e.start < (day + 1) * DAY]
            if kind == "sleep":
                text = ", ".join(f"{at(e.start)}-{at(e.end)} ({e.duration / 3600:.1f} h)" for e in today)
            elif kind == "meal":
                text = ", ".join(f"{at(e.start)} ({e.duration / 60:.0f} min)" for e in today)
            else:
                text = ", ".join(at(e.start) for e in today)
            print(f"  {kind + 's':8} {len(today):2d}  {text}")
    danger = 100 * time_fraction(recorder.column("world.threat"), 0.6)
    print(f"\ntime in serious danger (threat > 0.6): {danger:.2f} %   health alerts: {len(monitor.alerts)}")


if __name__ == "__main__":
    main()
