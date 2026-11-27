"""Classical conditioning: Rescorla–Wagner in continuous time (Phase 4).

Anchors: acquisition and extinction as error-driven learning (Rescorla &
Wagner 1972; Rescorla 1988), blocking of a redundant cue (Kamin 1969),
partial spontaneous recovery after rest (Rankin et al. 2009), and the
dopamine prediction-error signature — predicted relief stops surprising, an
omitted reward dips below tonic (Schultz et al. 1997). In these tests the
US is brief and the injury gain is turned down so nociception does not
outlast the pairing (its own persistence is tested in test_nociception.py).
See docs/PSYCHE.md §4.7.
"""

from pathlib import Path
from statistics import mean

import pytest

from unbodysoma import build_minimal_human
from unbodysoma.config import ScenarioError, load_scenario
from unbodysoma.core import Engine
from unbodysoma.observe import Recorder
from unbodysoma.world import Event

CUE_A = "world.stimulus"
CUE_B = "world.stimulus_b"
DAMAGE = "world.damage"
FOOD = "world.food_available"
VA = "psyche.conditioning.defense_a"
VB = "psyche.conditioning.defense_b"
EXPECT = "psyche.conditioning.threat_expectation"
THREAT = "psyche.appraisal.threat"
VALENCE = "psyche.affect.valence"
DA = "neuro.dopamine"
FLEE_P = "psyche.action.p_flee"
KEYS = (VA, VB, EXPECT, THREAT, VALENCE, DA, FLEE_P)

CSI = 2.0  # cue presentation
ISI = 60.0  # inter-trial interval
TRIAL = CSI + ISI
NO_INJURY = {"soma.nociception": {"injury_gain": 0.0001}}


def pairings(cue: str, count: int, start: float = 300.0, damage: float = 1.0) -> list[Event]:
    """Pairings with the US coterminous with the cue: in plain continuous-time
    RW, cue time ahead of the US reads as extinction (the anticipatory credit
    needs temporal-difference timing, deferred with PSYCHE.md §4.7)."""
    events = []
    for i in range(count):
        t = start + TRIAL * i
        events.append(Event(t, t + CSI, cue, 1.0))
        events.append(Event(t, t + CSI, DAMAGE, damage))
    return events


def compound_pairings(count: int, start: float) -> list[Event]:
    events = []
    for i in range(count):
        t = start + TRIAL * i
        events.append(Event(t, t + CSI, CUE_A, 1.0))
        events.append(Event(t, t + CSI, CUE_B, 1.0))
        events.append(Event(t, t + CSI, DAMAGE, 1.0))
    return events


def run(events: list[Event], seconds: float, overrides: dict | None = None) -> Recorder:
    engine: Engine = build_minimal_human(events, seed=0, overrides={**NO_INJURY, **(overrides or {})})
    recorder = Recorder(KEYS, every=1.0)
    engine.observe(recorder)
    engine.run(seconds)
    return recorder


def window(rec: Recorder, key: str, lo: float, hi: float) -> list[float]:
    return [v for t, v in zip(rec.times(), rec.column(key), strict=True) if lo <= t <= hi]


# The course: 20 pairings, a probe, 15 unreinforced presentations, a probe,
# twenty minutes of rest, a final probe.
T_ACQ = 300.0
T_EXT = T_ACQ + TRIAL * 20 + 60.0  # 1600
T_REST = T_EXT + TRIAL * 15 + 60.0  # 2590
T_REC = T_REST + 1200.0  # 3790
PROBE_ACQ = T_ACQ + TRIAL * 20 + 30.0  # 1570
PROBE_EXT = T_EXT + TRIAL * 15 + 30.0  # 2560


def course_events() -> list[Event]:
    return [
        *pairings(CUE_A, 20, start=T_ACQ),
        *probes(CUE_A, [PROBE_ACQ]),
        *probes(CUE_A, [T_EXT + TRIAL * i for i in range(15)]),
        *probes(CUE_A, [PROBE_EXT]),
        *probes(CUE_A, [T_REC]),
    ]


PROBE_LEN = 10.0  # probes are longer than training cues so affect (tau = 2 s) responds


def probes(cue: str, at: list[float]) -> list[Event]:
    return [Event(t, t + PROBE_LEN, cue, 1.0) for t in at]


@pytest.fixture(scope="module")
def course() -> Recorder:
    return run(course_events(), T_REC + 10.0)


def test_acquisition(course: Recorder):
    rec = course
    assert max(window(rec, VA, T_ACQ + TRIAL * 17, PROBE_ACQ)) > 0.6  # the cue predicted the US
    assert max(window(rec, THREAT, PROBE_ACQ - 1, PROBE_ACQ + 4)) > 0.25  # a cue alone now appraises as threat
    assert max(window(rec, EXPECT, PROBE_ACQ - 1, PROBE_ACQ + 4)) > 0.5


def test_naive_cue_is_not_threatening():
    rec = run(probes(CUE_A, [300.0, 400.0, 500.0]), 600.0)
    assert max(window(rec, THREAT, 300.0, 600.0)) < 0.05


def test_extinction(course: Recorder):
    rec = course
    assert mean(window(rec, VA, T_EXT + TRIAL * 15 + 4, PROBE_EXT)) < 0.25  # the association was removed
    assert max(window(rec, THREAT, PROBE_EXT - 1, PROBE_EXT + 4)) < 0.1  # ...and the fear response with it


def test_spontaneous_recovery(course: Recorder):
    rec = course
    acquired = max(window(rec, VA, T_ACQ + TRIAL * 17, PROBE_ACQ))
    extinguished = mean(window(rec, VA, T_EXT + TRIAL * 15 + 4, PROBE_EXT))
    recovered = max(window(rec, VA, T_REST + 600.0, T_REC))
    assert recovered > extinguished + 0.05  # rest brought some of it back...
    assert recovered < acquired  # ...but not all of it
    assert max(window(rec, THREAT, T_REC - 1, T_REC + 4)) > 0.08  # and the fear partly returns


def test_conditioned_fear_feels_bad_and_primes_escape(course: Recorder):
    rec = course
    naive = run(probes(CUE_A, [300.0]), 400.0)
    fear_valence = mean(window(rec, VALENCE, PROBE_ACQ, PROBE_ACQ + 12))
    calm_valence = mean(window(naive, VALENCE, 296.0, 312.0))
    assert fear_valence < calm_valence - 0.3  # the conditioned cue feels bad
    assert mean(window(rec, FLEE_P, PROBE_ACQ, PROBE_ACQ + 12)) > 10.0 * mean(window(naive, FLEE_P, 296.0, 312.0))


def test_blocking():
    """Kamin (1969): a cue added in compound with an established predictor
    learns far less than the same cue trained on its own."""
    compound_start = 300.0 + TRIAL * 20 + 60.0
    blocked = run(
        [*pairings(CUE_A, 20, start=300.0), *compound_pairings(12, start=compound_start)],
        compound_start + TRIAL * 12 + 10.0,
    )
    control = run(pairings(CUE_B, 32, start=300.0), 300.0 + TRIAL * 32 + 10.0)
    blocked_vb = max(window(blocked, VB, 0.0, 1e9))
    control_vb = max(window(control, VB, 0.0, 1e9))
    assert control_vb > 0.3
    assert blocked_vb < 0.4 * control_vb  # the established cue blocked the new one


# -- dopamine as a prediction error -------------------------------------------


def test_a_trained_cue_suppresses_the_dopamine_burst_and_omission_dips():
    """Plain RW has no anticipatory credit, so the testable prediction-error
    phenomena are between-run: the same meal, preceded by a cue that has
    learned to predict its relief, no longer surprises dopamine — and the
    trained cue alone dips below tonic (Schultz's omission response). Cue-
    onset bursts need timing states, not presence states: with our delayed
    relief, presence-state TD actually learns the wrong thing (the no-cue
    state accrues the post-cue recovery; see BACKLOG's spectral-timing note)."""
    food = Event(330.0, 2700.0, FOOD, 1.0)
    cue = Event(300.0, 2400.0, CUE_A, 1.0)  # spans approach and meal, leaves before recovery ends
    omission_at = 5400.0  # the cue alone, after relief has cleared
    probe = Event(omission_at, omission_at + 1800.0, CUE_A, 1.0)
    hungry = {"soma.metabolism": {"initial_reserve": 0.3}}
    control = run([food, probe], omission_at + 1900.0, hungry)
    trained = run([food, cue, probe], omission_at + 1900.0, hungry)

    def peak_in_trial(rec: Recorder) -> float:
        return max(window(rec, DA, 360.0, 2400.0))

    control_peak, trained_peak = peak_in_trial(control), peak_in_trial(trained)
    assert control_peak > 0.75  # the meal surprised dopamine
    assert trained_peak < control_peak - 0.15  # the cue's prediction ate the burst
    # The dip is brief: an RW prediction extinguishes itself once falsified,
    # so read it at the start of the probe.
    omission = min(window(trained, DA, omission_at, omission_at + 60.0))
    assert omission < 0.47  # the cue without its reward dips below tonic


# -- the scenario-file sugar ----------------------------------------------------


def test_stimuli_tables_become_events(tmp_path: Path):
    text = """
[scenario]
name = "conditioning_demo"
duration_s = 600
seed = 0

[organism]
preset = "minimal"

[[stimuli]]
start = 100.0
duration = 2.0

[[stimuli]]
start = 200.0
duration = 3.0
value = 0.5
cue = "b"
"""
    path = tmp_path / "conditioning_demo.toml"
    path.write_text(text, encoding="utf-8")
    scenario = load_scenario(path)
    assert scenario.events == [
        Event(100.0, 102.0, "world.stimulus", 1.0),
        Event(200.0, 203.0, "world.stimulus_b", 0.5),
    ]


def test_stimuli_tables_are_validated(tmp_path: Path):
    def load(stimulus_body: str, preset: str = "minimal") -> None:
        text = f"""
[scenario]
name = "x"
duration_s = 10
seed = 0

[organism]
preset = "{preset}"

[[stimuli]]
{stimulus_body}
"""
        path = tmp_path / "s.toml"
        path.write_text(text, encoding="utf-8")
        load_scenario(path)

    with pytest.raises(ScenarioError, match="cue"):
        load('start = 0.0\nduration = 1.0\ncue = "c"')
    with pytest.raises(ScenarioError, match="duration"):
        load("start = 0.0\nduration = 0.0")
    with pytest.raises(ScenarioError, match="minimal"):
        load("start = 0.0\nduration = 1.0", preset="grid")
