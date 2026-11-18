"""Habituation: a repeated innocuous stimulus loses its orienting value.

Anchors are the behavioral criteria of Rankin et al. (2009) as instantiated in
the nematode tap-withdrawal literature (Ardel & Rankin 2010): repeated
presentation decrement, spontaneous recovery after rest, and faster
habituation with shorter inter-stimulus intervals. Single stimulus channel, so
stimulus specificity and dishabituation wait for Phase 4's cue identities.
See docs/PSYCHE.md §4.6.
"""

from statistics import mean

import pytest

from unbodysoma import build_minimal_human
from unbodysoma.core import Engine
from unbodysoma.observe import Recorder
from unbodysoma.world import Event

NOVELTY = "psyche.habituation.novelty"
AROUSAL = "psyche.affect.arousal"
KEYS = (NOVELTY, AROUSAL)

ONSET = 300.0
DURATION = 2.0  # each presentation lasts two seconds


def pulses(count: int, isi: float, start: float = ONSET) -> list[Event]:
    return [Event(start + isi * i, start + isi * i + DURATION, "world.stimulus", 1.0) for i in range(count)]


def run_protocol(events: list[Event], seconds: float) -> Recorder:
    engine: Engine = build_minimal_human(events, seed=0)
    recorder = Recorder(KEYS, every=0.25)
    engine.observe(recorder)
    engine.run(seconds)
    return recorder


def peak(rec: Recorder, key: str, lo: float, hi: float) -> float:
    return max((v for t, v in zip(rec.times(), rec.column(key), strict=True) if lo <= t <= hi), default=0.0)


@pytest.fixture(scope="module")
def slow_protocol() -> Recorder:
    """Ten presentations a minute apart, then a long rest and a probe pulse."""
    events = pulses(10, 60.0)
    events.append(Event(ONSET + 60.0 * 10 + 1200.0, ONSET + 60.0 * 10 + 1200.0 + DURATION, "world.stimulus", 1.0))
    return run_protocol(events, ONSET + 60.0 * 10 + 1200.0 + 10.0)


def test_first_presentation_is_novel(slow_protocol: Recorder):
    assert peak(slow_protocol, NOVELTY, ONSET, ONSET + 5.0) > 0.9


def test_repeated_presentations_lose_novelty(slow_protocol: Recorder):
    first = peak(slow_protocol, NOVELTY, ONSET, ONSET + 5.0)
    tenth = peak(slow_protocol, NOVELTY, ONSET + 60.0 * 9, ONSET + 60.0 * 9 + 5.0)
    assert tenth < 0.6 * first  # response decrement across repetitions (Rankin et al. 2009)


def test_orienting_arousal_shrinks_with_novelty(slow_protocol: Recorder):
    def bump(index: int) -> float:
        t0 = ONSET + 60.0 * index
        rec = slow_protocol
        base = mean(v for t, v in zip(rec.times(), rec.column(AROUSAL), strict=True) if t0 - 20.0 <= t <= t0 - 5.0)
        peak_value = peak(rec, AROUSAL, t0, t0 + 4.0)
        return peak_value - base

    assert bump(0) > bump(7) + 0.03  # the eighth tap startles less than the first


def test_spontaneous_recovery_after_rest(slow_protocol: Recorder):
    rec = slow_protocol
    last = peak(rec, NOVELTY, ONSET + 60.0 * 9, ONSET + 60.0 * 9 + 5.0)
    probe = peak(rec, NOVELTY, ONSET + 60.0 * 10 + 1200.0 - 5.0, ONSET + 60.0 * 10 + 1200.0 + 10.0)
    assert probe > 1.6 * last  # twenty minutes of rest brings most of it back


def test_higher_frequency_habituates_deeper():
    slow = run_protocol(pulses(8, 60.0), ONSET + 60.0 * 8)
    fast = run_protocol(pulses(8, 15.0), ONSET + 15.0 * 8)
    sixth_slow = peak(slow, NOVELTY, ONSET + 60.0 * 5, ONSET + 60.0 * 5 + 5.0)
    sixth_fast = peak(fast, NOVELTY, ONSET + 15.0 * 5, ONSET + 15.0 * 5 + 5.0)
    assert sixth_fast < 0.5 * sixth_slow  # shorter intervals, faster habituation
