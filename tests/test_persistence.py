"""Acceptance tests for snapshot files and replaying run records."""

import json
import math
import random

import pytest

from unbodysoma import build_grid_human
from unbodysoma.__main__ import main
from unbodysoma.config import ScenarioError, parse_scenario, replay
from unbodysoma.core import load_snapshot, save_snapshot
from unbodysoma.core.persist import decode, encode
from unbodysoma.observe import RunWriter

SCENARIO = """
[scenario]
name = "replay_me"
duration_s = 600
seed = 2

[organism]
preset = "minimal"

[[events]]
start = 100
end = 130
key = "world.threat"
value = 0.9

[[interventions]]
type = "clamp"
key = "psyche.affect.arousal"
value = 0.3
start = 300
end = 400
"""


# -- encoding -------------------------------------------------------------------


def test_state_values_round_trip_through_strict_json():
    rng = random.Random(42)
    rng.random()
    value = {"rng": rng, "nested": {"t": (1, (2.5, "x")), "inf": math.inf, "list": [1, -math.inf]}, "none": None}
    text = json.dumps(encode(value), allow_nan=False)  # strict JSON: no Infinity / NaN literals
    back = decode(json.loads(text))
    assert back["rng"].getstate() == rng.getstate()
    assert back["nested"] == {"t": (1, (2.5, "x")), "inf": math.inf, "list": [1, -math.inf]}
    assert back["none"] is None


def test_unsupported_or_ambiguous_state_is_refused():
    with pytest.raises(TypeError):
        encode({"thing": object()})
    with pytest.raises(ValueError, match="reserved"):
        encode({"__tuple__": [1]})


# -- snapshot files -------------------------------------------------------------


def test_a_saved_snapshot_resumes_exactly_in_a_new_process(tmp_path):
    """Everything — body, mind, world, every random stream — survives a round trip to disk."""
    original = build_grid_human(seed=3, overrides={"soma.metabolism": {"initial_reserve": 0.5}})
    original.run(1800.0)
    save_snapshot(original.snapshot(), tmp_path / "snap.json")
    original.run(1800.0)

    resumed = build_grid_human(seed=3, overrides={"soma.metabolism": {"initial_reserve": 0.5}})
    resumed.restore(load_snapshot(tmp_path / "snap.json"))
    resumed.run(1800.0)

    assert resumed.tick == original.tick
    assert resumed.bus.snapshot() == original.bus.snapshot()


def test_snapshot_files_are_strict_json(tmp_path):
    engine = build_grid_human()
    engine.run(10.0)
    save_snapshot(engine.snapshot(), tmp_path / "snap.json")

    def refuse(constant: str) -> None:
        raise AssertionError(f"non-standard JSON constant {constant}")

    data = json.loads((tmp_path / "snap.json").read_text(encoding="utf-8"), parse_constant=refuse)
    assert data["format"] == "unbodysoma.snapshot/1"


def test_loading_something_else_fails_clearly(tmp_path):
    (tmp_path / "other.json").write_text('{"hello": 1}', encoding="utf-8")
    with pytest.raises(ValueError, match="not a snapshot file"):
        load_snapshot(tmp_path / "other.json")


# -- replay -----------------------------------------------------------------------


def recorded(tmp_path, text: str = SCENARIO):
    out = tmp_path / "run"
    parse_scenario(text).run(out=out)
    return out


def test_a_recorded_scenario_replays_bit_for_bit(tmp_path):
    outcome = replay(recorded(tmp_path))
    assert outcome.identical, outcome.detail
    assert "ticks reproduced bit for bit" in outcome.detail


def test_replay_detects_a_record_that_does_not_reproduce(tmp_path):
    out = recorded(tmp_path)
    lines = (out / "signals.csv").read_text(encoding="utf-8").splitlines()
    cells = lines[200].split(",")
    cells[3] = repr(float(cells[3]) + 1e-9)  # the smallest of edits
    lines[200] = ",".join(cells)
    (out / "signals.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    outcome = replay(out)
    assert not outcome.identical
    assert "signals.csv line 201" in outcome.detail


def test_replay_refuses_a_tampered_scenario_source(tmp_path):
    out = recorded(tmp_path)
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    meta["config"]["source"] = meta["config"]["source"].replace("value = 0.9", "value = 0.5")
    (out / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(ScenarioError, match="checksum"):
        replay(out)


def test_only_scenario_runs_can_be_replayed(tmp_path):
    engine = build_grid_human()
    with RunWriter(tmp_path / "plain").attach(engine):
        engine.run(1.0)
    with pytest.raises(ScenarioError, match="not produced from a scenario file"):
        replay(tmp_path / "plain")
    with pytest.raises(ScenarioError, match="not a run record"):
        replay(tmp_path / "nowhere")


def test_replay_uses_the_seed_and_duration_actually_run(tmp_path, capsys):
    path = tmp_path / "s.toml"
    path.write_text(SCENARIO, encoding="utf-8")
    assert main(["run", str(path), "--seed", "9", "--hours", "0.05", "--out", str(tmp_path / "run")]) == 0
    assert main(["replay", str(tmp_path / "run")]) == 0
    assert "identical: 18000 ticks" in capsys.readouterr().out


def test_scripted_events_still_reproduce_with_a_different_record_interval(tmp_path):
    """Sanity check that replay compares like with like: the record interval is part of the scenario."""
    text = SCENARIO.replace('name = "replay_me"', 'name = "coarse"') + "\n[observe]\nrecord_every = 7.0\n"
    assert replay(recorded(tmp_path, text)).identical
