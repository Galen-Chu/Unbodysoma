"""Feeding: a hungry organism finds food, is interrupted by a threat, and eats until sated.

Timeline: food appears at t = 120 s; a threat appears during the meal (400-430 s).

Run:  python examples/feeding.py [--runs runs/feeding]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from unbodysoma import build_minimal_human
from unbodysoma.observe import HealthMonitor, Recorder, RunWriter
from unbodysoma.world import Event

EVENTS = [
    Event(120.0, 1e9, "world.food_available", 1.0),
    Event(400.0, 430.0, "world.threat", 0.9),
]
SIGNALS = {
    "world.food_available": "food",
    "world.threat": "threat",
    "psyche.drive.hunger": "hunger",
    "motor.eating": "eating",
    "motor.exertion": "exertion",
    "soma.metabolism.energy_reserve": "reserve",
    "psyche.affect.valence": "valence",
}
SHOW_AT = (0, 60, 120, 180, 300, 390, 410, 425, 450, 600, 900, 1200, 1300, 1500, 1800)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=Path, help="also write a run record to this directory")
    args = parser.parse_args()

    engine = build_minimal_human(EVENTS, overrides={"soma.metabolism": {"initial_reserve": 0.4}})
    recorder = Recorder(SIGNALS, every=1.0)
    engine.observe(recorder)
    monitor = HealthMonitor().attach(engine)
    writer = RunWriter(args.runs, config={"scenario": "feeding"}).attach(engine) if args.runs else None
    engine.run(1800.0)
    if writer:
        writer.close()

    recorder.rows = [row for row in recorder.rows if round(row[0]) in SHOW_AT]
    print(recorder.table(headers=SIGNALS.values()))
    print(f"\nhealth alerts: {sum(a.raised for a in monitor.alerts)}")


if __name__ == "__main__":
    main()
