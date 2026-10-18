"""Lesion study: how much of "fear" depends on feeling the body?

Runs the same 30 s threat under four conditions and compares the outcome:

  intact         the full organism
  no_intero      interoception silenced: the mind cannot feel its heart
  beta_blocker   heart rate clamped at rest (a crude propranolol analogue)
  no_heart       cardio silenced at t = 30 s: the health monitor halts the run

Run:  python examples/lesion_study.py [--runs runs/lesion_study]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from unbodysoma import build_minimal_human
from unbodysoma.core import Engine
from unbodysoma.observe import HealthMonitor, Recorder, RunWriter
from unbodysoma.world import Event

THREAT = [Event(60.0, 90.0, "world.threat", 0.9)]
KEYS = ("soma.cardio.heart_rate", "psyche.appraisal.threat", "psyche.affect.arousal", "psyche.affect.valence")

CONDITIONS = {
    "intact": lambda e: None,
    "no_intero": lambda e: e.lesion("interface.interoception"),
    "beta_blocker": lambda e: e.clamp("soma.cardio.heart_rate", 65.0),
    "no_heart": lambda e: e.lesion("soma.cardio", start=30.0),
}


def run_condition(name: str, seed: int, runs_dir: Path | None) -> dict[str, object]:
    engine: Engine = build_minimal_human(THREAT, seed=seed)
    CONDITIONS[name](engine)
    recorder = Recorder(KEYS, every=0.1)
    engine.observe(recorder)
    monitor = HealthMonitor(halt_on="critical").attach(engine)

    writer = RunWriter(runs_dir / name, config={"condition": name, "seed": seed}) if runs_dir else None
    if writer:
        writer.attach(engine)
    try:
        stopped = engine.run(300.0)
    finally:
        if writer:
            writer.close()

    return {
        "condition": name,
        "peak HR": max(recorder.column("soma.cardio.heart_rate")),
        "peak threat": max(recorder.column("psyche.appraisal.threat")),
        "peak arousal": max(recorder.column("psyche.affect.arousal")),
        "min valence": min(recorder.column("psyche.affect.valence")),
        "alerts": sum(a.raised for a in monitor.alerts),
        "ended": f"halted at t={engine.time:.1f}s" if stopped else "completed",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=Path, help="write a run record per condition under this directory")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    results = [run_condition(name, args.seed, args.runs) for name in CONDITIONS]
    headers = list(results[0])
    print("  ".join(f"{h:>14}" for h in headers))
    for row in results:
        print("  ".join(f"{v:>14.2f}" if isinstance(v, float) else f"{v!s:>14}" for v in row.values()))
    if args.runs:
        print(f"\nrun records written to {args.runs}/")


if __name__ == "__main__":
    main()
