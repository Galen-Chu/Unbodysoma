"""The multi-need valence composition decision (Phase 2; PSYCHE.md §5).

Behavioral data chose the saturating union over the linear sum for the
default (grid_72h comparison in docs/PSYCHE.md §5). These tests pin the two
properties that decided it: several mild needs must not out-vote a single
strong one, and a single dominant threat must feel just as bad under both
compositions. Drives and threat are set with engine clamps (ADR-0005) —
scenario events may only address world.* signals.
"""

from statistics import mean

from unbodysoma import build_minimal_human
from unbodysoma.core import Engine
from unbodysoma.observe import Recorder

VALENCE = "psyche.affect.valence"


def run_valence(overrides: dict, clamps: dict[str, float]) -> float:
    engine: Engine = build_minimal_human([], seed=0, overrides={"psyche.affect": overrides})
    for key, value in clamps.items():
        engine.clamp(key, value)
    recorder = Recorder((VALENCE,), every=1.0)
    engine.observe(recorder)
    engine.run(120.0)
    return mean(recorder.column(VALENCE)[-60:])


MILD_NEEDS = {
    "psyche.drive.hunger": 0.6,
    "psyche.drive.thirst": 0.6,
    "psyche.drive.thermal_discomfort": 0.6,
}
THREAT = {"psyche.appraisal.threat": 0.9}


def test_several_mild_needs_do_not_outvote_a_single_strong_one():
    linear = run_valence({"need_saturation": 0.0}, MILD_NEEDS)
    saturating = run_valence({"need_saturation": 1.0}, MILD_NEEDS)
    threat = run_valence({"need_saturation": 1.0}, THREAT)
    assert linear < saturating  # the linear sum overreacts to mild needs
    assert saturating > threat  # three mild needs still feel better than real threat


def test_a_dominant_threat_feels_equally_bad_under_both_compositions():
    linear = run_valence({"need_saturation": 0.0}, THREAT)
    saturating = run_valence({"need_saturation": 1.0}, THREAT)
    assert abs(linear - saturating) < 0.05  # a single pull pools to itself


def test_default_is_the_saturating_composition():
    default = run_valence({}, MILD_NEEDS)
    explicit = run_valence({"need_saturation": 1.0}, MILD_NEEDS)
    assert abs(default - explicit) < 1e-9
