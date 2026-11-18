"""Nociception: dual-phase pain, sensitization and avoidance (Phase 3).

Anchors: the fast first pain / slow second pain separation of the dual pain
response and primary hyperalgesia (Julius & Basbaum 2001), and C-fibre
wind-up under repeated stimulation (Mendell 1966). Bounds are coarse, as
everywhere in this project: we check the *shape* of the phenomena (what is
fast, what is slow, what outlasts the stimulus, what grows with repetition),
not precise curves. See docs/SOMA.md §2.9.
"""

from collections.abc import Callable

import pytest

from unbodysoma import build_grid_human, build_minimal_human
from unbodysoma.core import BusPort, Engine, SignalBus
from unbodysoma.observe import Recorder
from unbodysoma.soma import Nociception
from unbodysoma.world import Event, FoodPatch, Hazard, Shelter, WaterSource

PAIN = "soma.nociception.pain"
SHARP = "soma.nociception.sharp"
BURNING = "soma.nociception.burning"
INJURY = "soma.nociception.injury"
VALENCE = "psyche.affect.valence"
AROUSAL = "psyche.affect.arousal"
FLEE_P = "psyche.action.p_flee"
KEYS = (PAIN, SHARP, BURNING, INJURY, VALENCE, AROUSAL, FLEE_P)

ONSET = 300.0
END = 305.0  # a five-second maximal noxious stimulus


def run_pulse(damage: float = 1.0, seconds: float = 500.0, overrides: dict | None = None) -> Recorder:
    events = [Event(ONSET, END, "world.damage", damage)]
    engine: Engine = build_minimal_human(events, seed=0, overrides=overrides)
    recorder = Recorder(KEYS, every=0.5)
    engine.observe(recorder)
    engine.run(seconds)
    return recorder


def value_at(rec: Recorder, key: str, t: float) -> float:
    best, best_dt = 0.0, math_inf
    for time, v in zip(rec.times(), rec.column(key), strict=True):
        if abs(time - t) < best_dt:
            best, best_dt = v, abs(time - t)
    return best


def first_crossing(rec: Recorder, key: str, threshold: float, after: float) -> float:
    for time, v in zip(rec.times(), rec.column(key), strict=True):
        if time >= after and v >= threshold:
            return time
    return math_inf


def max_between(rec: Recorder, key: str, lo: float, hi: float) -> float:
    return max(v for t, v in zip(rec.times(), rec.column(key), strict=True) if lo <= t <= hi)


math_inf = float("inf")


@pytest.fixture(scope="module")
def pulse() -> Recorder:
    return run_pulse()


# -- dual-phase separation -------------------------------------------------


def test_first_pain_is_immediate(pulse: Recorder):
    rec = pulse
    assert value_at(rec, SHARP, ONSET) < 0.05  # nothing before the stimulus
    # first pain rises at once (the recorder samples every 0.5 s; the second
    # phase needs seconds — see the next test)
    assert first_crossing(rec, SHARP, 0.05, ONSET) - ONSET < 0.8


def test_second_pain_is_delayed_and_persists(pulse: Recorder):
    rec = pulse
    # Second pain arrives seconds after the first, not with it...
    assert value_at(rec, BURNING, ONSET + 1.0) < 0.05
    assert first_crossing(rec, BURNING, 0.05, ONSET) - ONSET < 8.0
    # ...and outlasts it by an order of magnitude.
    after = END + 10.0
    assert value_at(rec, BURNING, after) > 5.0 * value_at(rec, SHARP, after)
    assert value_at(rec, BURNING, after) > 0.05


def test_tissue_injury_accumulates_and_felt_pain_is_bounded(pulse: Recorder):
    rec = pulse
    assert 0.02 < max_between(rec, INJURY, ONSET, END + 60.0) <= 1.0
    assert 0.0 <= max_between(rec, PAIN, ONSET, END) <= 1.0
    assert value_at(rec, PAIN, ONSET) < 0.05  # calm before the stimulus


def test_pain_feels_bad_and_arousing(pulse: Recorder):
    rec = pulse
    baseline = max_between(rec, VALENCE, 0.0, ONSET - 30.0)
    worst = min(v for t, v in zip(rec.times(), rec.column(VALENCE), strict=True) if ONSET + 1.0 <= t <= END)
    assert worst < baseline - 0.4  # pain pulls valence strongly down
    arousal = max_between(rec, AROUSAL, ONSET + 1.0, END)
    assert arousal > max_between(rec, AROUSAL, 0.0, ONSET - 30.0) + 0.1  # and arouses


def test_pain_primes_escape(pulse: Recorder):
    rec = pulse
    control = run_pulse(damage=0.0)
    with_pain = max_between(rec, FLEE_P, ONSET + 0.5, END)
    without = max_between(control, FLEE_P, ONSET + 0.5, END)
    assert with_pain > 10.0 * without  # hurt organisms are primed to escape


def test_analgesia_removes_the_feel_but_not_the_injury(pulse: Recorder):
    """Lesioning nociception output (analgesia): injury still accrues, affect does not care."""
    events = [Event(ONSET, END, "world.damage", 1.0)]
    engine: Engine = build_minimal_human(events, seed=0)
    engine.lesion("soma.nociception", ONSET - 10.0, END + 10.0)
    recorder = Recorder((PAIN, VALENCE), every=0.5)
    engine.observe(recorder)
    engine.run(400.0)
    assert max_between(recorder, PAIN, ONSET, END) == 0.0
    assert max_between(recorder, VALENCE, ONSET, END) > max_between(pulse, VALENCE, ONSET, END)


# -- use-dependent sensitization (wind-up / hyperalgesia) -------------------


class _Bench:
    """Drives a Nociception module directly with a scripted damage input."""

    def __init__(self) -> None:
        self.bus = SignalBus()
        self.noc = Nociception()
        self.module_port = BusPort(self.bus, self.noc.name, self.noc.writes)
        self.stimulus_port = BusPort(self.bus, "bench", ("world.damage",))
        self.bus.commit()

    def run(self, damage: "Callable[[float], float]", seconds: float, dt: float = 0.1) -> list[float]:
        """Step with ``damage(t)``; return the pain samples."""
        pain: list[float] = []
        steps = round(seconds / dt)
        for i in range(steps):
            t = (i + 1) * dt
            self.stimulus_port.write("world.damage", damage(t))
            self.bus.commit()  # publish the stimulus, so the module reads it this step
            self.module_port.time = t
            self.noc.step(dt, self.module_port)
            self.bus.commit()
            pain.append(self.bus.read(PAIN))
        return pain


def test_repeated_damage_sensitizes_and_partially_recovers():
    """Mendell (1966): repeated C-fibre input grows the response; rest recovers it."""
    bench = _Bench()

    def train(t: float) -> float:
        for i in range(5):  # five 1.5 s pulses, 30 s apart
            if 150.0 + 30.0 * i <= t < 151.5 + 30.0 * i:
                return 1.0
        return 0.0

    pain = bench.run(train, 750.0)  # samples of 0.1 s
    sens_after_training = bench.noc.sensitization
    bench.run(lambda t: 0.0, 600.0)  # rest
    after_rest = bench.noc.sensitization
    probe = bench.run(lambda t: 1.0, 0.8)  # the same phase point of a fresh pulse

    # Compare the pulses at the same phase (0.8 s into the pulse), where the
    # pain of the fifth is not yet clipped by the output clamp.
    first, fifth = pain[1507], pain[2707]
    assert fifth > 1.4 * first  # wind-up: the same stimulus hurts more
    assert sens_after_training > 0.3
    assert 0.05 < after_rest < 0.7 * sens_after_training  # 600 s of decay (tau = 900 s) removed most of it
    assert max(probe) > first  # the probe still hurts more than the very first pulse


def test_sensitization_state_decays_exponentially():
    bench = _Bench()
    bench.run(lambda t: 1.0 if t < 10.0 else 0.0, 10.0)
    peak = bench.noc.sensitization
    bench.run(lambda t: 0.0, 900.0)
    decayed = bench.noc.sensitization
    assert decayed == pytest.approx(peak * 2.718281828 ** (-900.0 / 900.0), rel=0.05)


# -- avoidance in the grid world --------------------------------------------


def test_damaged_organism_escapes_the_hazard():
    """Standing in a hazard hurts; the organism takes injury, flees and survives."""
    engine: Engine = build_grid_human(
        food=(FoodPatch(3.0, 3.0),),
        hazards=(Hazard(5.0, 5.0, radius=2.5, strength=0.9),),
        water=(WaterSource(16.0, 16.0),),
        shelters=(Shelter(15.0, 15.0),),
        start=(5.0, 5.0),  # starts inside the hazard
        seed=0,
    )
    recorder = Recorder(("world.damage", PAIN, INJURY, "psyche.action.selected_flee", "world.position_x"), every=0.5)
    engine.observe(recorder)
    engine.run(120.0)
    assert max_between(recorder, "world.damage", 0.0, 120.0) > 0.5  # it really got hurt
    assert max_between(recorder, PAIN, 0.0, 30.0) > 0.3
    assert max_between(recorder, "psyche.action.selected_flee", 0.0, 30.0) > 0.5  # and fled
    x = [v for t, v in zip(recorder.times(), recorder.column("world.position_x"), strict=True) if t >= 60.0]
    assert any(abs(v - 5.0) > 2.5 for v in x)  # well out of the hazard by the end
    assert recorder.column(INJURY)[-1] > 0.0  # the injury is on record (and healing)
