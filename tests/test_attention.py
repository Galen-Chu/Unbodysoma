"""Attention: salient domains compete for a broadcast gain (M3, Phase 5).

The minimal global-workspace module (Baars, 1988): six domains compete on
salience with bounded softmax shares and winner persistence; attended threat
reads larger in appraisal, and full focus sharpens choices. Acceptance
below; equations: docs/PSYCHE.md §4.12.
"""

from statistics import mean

from unbodysoma import build_minimal_human
from unbodysoma.core import Engine
from unbodysoma.observe import Recorder
from unbodysoma.world import Event

SHARE_PAIN = "psyche.attention.share_pain"
SHARE_THREAT = "psyche.attention.share_threat"
FOCUS = "psyche.attention.focus_share"
THREAT = "psyche.appraisal.threat"
PAIN = "intero.pain"
KEYS = (SHARE_PAIN, SHARE_THREAT, FOCUS, THREAT, PAIN)

NO_INJURY = {"soma.nociception": {"injury_gain": 0.0001}}


def run(events: list[Event], seconds: float, overrides: dict | None = None) -> Recorder:
    engine: Engine = build_minimal_human(events, seed=0, overrides={**NO_INJURY, **(overrides or {})})
    recorder = Recorder(KEYS, every=1.0)
    engine.observe(recorder)
    engine.run(seconds)
    return recorder


def window(rec: Recorder, key: str, lo: float, hi: float) -> list[float]:
    return [v for t, v in zip(rec.times(), rec.column(key), strict=True) if lo <= t <= hi]


def test_pain_takes_the_broadcast():
    rec = run([Event(300.0, 360.0, "world.damage", 0.9)], 700.0)
    assert mean(window(rec, SHARE_PAIN, 320.0, 360.0)) > 0.5  # pain holds most of the field
    assert mean(window(rec, FOCUS, 320.0, 360.0)) > 0.4  # ...and focus is sharp
    assert mean(window(rec, SHARE_PAIN, 600.0, 700.0)) < 0.3  # ...and it lets go when the pain passes


def test_focus_persists_against_a_milder_challenger():
    """While pain is strong, a mild threat does not steal the broadcast; once
    pain passes, threat takes it."""
    rec = run([Event(300.0, 400.0, "world.damage", 0.9), Event(350.0, 700.0, "world.threat", 0.4)], 700.0)
    assert mean(window(rec, SHARE_PAIN, 360.0, 400.0)) > mean(window(rec, SHARE_THREAT, 360.0, 400.0))
    assert mean(window(rec, SHARE_THREAT, 600.0, 700.0)) > mean(window(rec, SHARE_PAIN, 600.0, 700.0))


def test_attended_threat_reads_larger():
    """The same mild threat, with attention free for it versus taken by pain."""
    distracted = run([Event(300.0, 500.0, "world.damage", 0.7), Event(320.0, 500.0, "world.threat", 0.5)], 500.0)
    attending = run([Event(320.0, 500.0, "world.threat", 0.5)], 500.0)
    distracted_threat = mean(window(distracted, THREAT, 420.0, 500.0))
    attending_threat = mean(window(attending, THREAT, 420.0, 500.0))
    assert attending_threat > distracted_threat + 0.03  # attention amplifies the read
