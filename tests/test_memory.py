"""Episodic memory: emotional capture, decay, mood-congruent retrieval (Phase 4).

Anchors: emotional modulation of memory — arousing events are consolidated
more strongly and outlast neutral ones (McGaugh, 2004); mood-congruent
recall — the current state reactivates similar episodes, whose signed
content pulls valence. Acceptance below; equations: docs/PSYCHE.md §4.9.
"""

from statistics import mean

from unbodysoma import build_minimal_human
from unbodysoma.core import Engine
from unbodysoma.observe import Recorder
from unbodysoma.world import Event

EPISODES = "psyche.memory.episodes"
CONGRUENCE = "psyche.memory.mood_congruence"
VALENCE = "psyche.affect.valence"
KEYS = (EPISODES, CONGRUENCE, VALENCE)

NO_INJURY = {"soma.nociception": {"injury_gain": 0.0001}}


def run(events: list[Event], seconds: float, overrides: dict | None = None) -> Recorder:
    engine: Engine = build_minimal_human(events, seed=0, overrides={**NO_INJURY, **(overrides or {})})
    recorder = Recorder(KEYS, every=5.0)
    engine.observe(recorder)
    engine.run(seconds)
    return recorder


def window(rec: Recorder, key: str, lo: float, hi: float) -> list[float]:
    return [v for t, v in zip(rec.times(), rec.column(key), strict=True) if lo <= t <= hi]


def episodes_of(rec: Recorder) -> list:
    engine_modules = rec  # noqa: F841 - recorded counts are enough; strengths read via module below
    return rec.column(EPISODES)


def test_a_calm_hour_is_not_remembered():
    rec = run([], 3600.0)
    assert max(rec.column(EPISODES)) == 0.0


def test_strong_threats_are_captured():
    events = [Event(300.0, 330.0, "world.threat", 0.9), Event(900.0, 930.0, "world.threat", 0.9)]
    rec = run(events, 1200.0)
    assert rec.column(EPISODES)[-1] == 2.0  # one episode per event, not per tick
    # The affective context of the second threat matches the stored first: recall is negative.
    assert mean(window(rec, CONGRUENCE, 900.0, 960.0)) < -0.3


def test_intensity_scales_capture_strength():
    strong = run([Event(300.0, 330.0, "world.threat", 0.9)], 400.0)
    mild = run([Event(300.0, 330.0, "world.threat", 0.5)], 400.0)
    assert max(strong.column(EPISODES)) >= max(mild.column(EPISODES))
    # The mild threat is near the capture boundary: its recall is weaker.
    strong_recall = abs(mean(window(strong, CONGRUENCE, 360.0, 400.0)))
    mild_recall = abs(mean(window(mild, CONGRUENCE, 360.0, 400.0)))
    assert strong_recall > mild_recall


def test_mood_congruence_pulls_valence():
    """The same second threat, with a memory that captured the first versus
    one that could not: remembering the bad time feels worse."""
    events = [Event(300.0, 330.0, "world.threat", 0.9), Event(2000.0, 2030.0, "world.threat", 0.9)]
    remembering = run(events, 2100.0)
    amnesic = run(events, 2100.0, {"psyche.memory": {"capture_threshold": 1.0}})
    with_memory = min(window(remembering, VALENCE, 2005.0, 2060.0))
    without_memory = min(window(amnesic, VALENCE, 2005.0, 2060.0))
    assert with_memory < without_memory - 0.02  # mood-congruent recall colours the present


def test_episodes_decay_but_outlast_the_incident():
    events = [Event(300.0, 330.0, "world.threat", 0.9)]
    rec = run(events, 4000.0, {"psyche.memory": {"tau_memory": 3600.0}})  # an hour of decay
    assert rec.column(EPISODES)[-1] == 1.0  # still held...
    recall = abs(mean(window(rec, CONGRUENCE, 3900.0, 4000.0)))
    assert recall < abs(mean(window(run(events, 700.0), CONGRUENCE, 600.0, 700.0)))  # ...but faded
