"""Fear response: a threat appears for 30 s, the organism appraises, flees and recovers.

Run:  python examples/fear_response.py [--csv out.csv]
"""

from __future__ import annotations

import argparse

from unbodysoma import build_minimal_human
from unbodysoma.observe import Recorder
from unbodysoma.world import Event

SIGNALS = {
    "world.threat": "stimulus",
    "psyche.appraisal.threat": "threat",
    "soma.endocrine.adrenaline": "adrenal",
    "soma.cardio.heart_rate": "HR(bpm)",
    "motor.exertion": "exertion",
    "psyche.affect.arousal": "arousal",
    "psyche.affect.valence": "valence",
    "soma.metabolism.glucose": "glucose",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", help="write the full 1 Hz recording to this CSV file")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    engine = build_minimal_human(events=[Event(60.0, 90.0, "world.threat", 0.9)], seed=args.seed)
    recorder = Recorder(SIGNALS, every=1.0)
    engine.observe(recorder)
    engine.run(300.0)

    print(Recorder.table(_every(recorder, 10), headers=SIGNALS.values()))
    if args.csv:
        recorder.to_csv(args.csv)
        print(f"\nwrote {len(recorder.rows)} rows to {args.csv}")


def _every(recorder: Recorder, n: int) -> Recorder:
    """A view of ``recorder`` keeping every n-th row, for a compact printout."""
    view = Recorder(recorder.keys, recorder.every * n)
    view.rows = recorder.rows[::n]
    return view


if __name__ == "__main__":
    main()
