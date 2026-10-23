"""Acceptance tests for TOML scenario files and the command line (ADR-0008)."""

from pathlib import Path

import pytest

from unbodysoma import build_grid_human, build_minimal_human
from unbodysoma.__main__ import main
from unbodysoma.config import ScenarioError, load_scenario, parse_scenario
from unbodysoma.observe import load_run
from unbodysoma.world import Event, FoodPatch, Hazard

SCENARIOS = sorted((Path(__file__).resolve().parents[1] / "scenarios").glob("*.toml"))

FEAR = """
[scenario]
name = "fear"
duration_s = 120
seed = 3

[organism]
preset = "minimal"

[organism.overrides."soma.cardio"]
resting_bpm = 70

[[events]]
start = 30
end = 60
key = "world.threat"
value = 0.9

[[interventions]]
type = "clamp"
key = "psyche.affect.arousal"
value = 0.2
start = 40
end = 50
"""


@pytest.mark.parametrize("path", SCENARIOS, ids=lambda p: p.name)
def test_every_shipped_scenario_is_valid(path):
    scenario = load_scenario(path)
    assert scenario.duration_s > 0
    assert scenario.build().unspecified_signals() == []


def test_a_scenario_file_is_exactly_the_python_experiment():
    from_file = parse_scenario(FEAR).build()
    from_file.run(120.0)

    by_hand = build_minimal_human(
        [Event(30.0, 60.0, "world.threat", 0.9)], seed=3, overrides={"soma.cardio": {"resting_bpm": 70}}
    )
    by_hand.clamp("psyche.affect.arousal", 0.2, 40.0, 50.0)
    by_hand.run(120.0)

    assert from_file.bus.snapshot() == by_hand.bus.snapshot()


def test_a_grid_scenario_builds_the_described_world():
    text = """
    [scenario]
    duration_h = 1
    [organism]
    preset = "grid"
    [world]
    width = 12
    height = 8
    start = [2, 3]
    [[world.food]]
    x = 5
    y = 5
    regrow_per_hour = 0.1
    [[world.hazards]]
    x = 9
    y = 2
    radius = 1.5
    end = 600
    """
    engine = parse_scenario(text).build()
    reference = build_grid_human(
        food=[FoodPatch(5.0, 5.0, regrow_per_hour=0.1)],
        hazards=[Hazard(9.0, 2.0, radius=1.5, end=600.0)],
        width=12.0,
        height=8.0,
        start=(2.0, 3.0),
    )
    engine.run(300.0)
    reference.run(300.0)
    assert engine.bus.snapshot() == reference.bus.snapshot()


def test_running_a_scenario_records_its_source(tmp_path):
    result = parse_scenario(FEAR).run(out=tmp_path / "run")
    meta = load_run(tmp_path / "run").meta
    assert meta["config"]["source"] == FEAR
    assert len(meta["config"]["source_sha256"]) == 64
    assert result.stopped is None and result.monitor is not None


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("[scenario]\nduration_s = 1\n", "missing required key(s) ['organism']"),
        ("[scenario]\nduration_s = 1\n[organism]\npreset = 'minimal'\n[extra]\n", "unknown key(s) ['extra']"),
        ("[scenario]\n[organism]\npreset = 'minimal'\n", "exactly one of duration_s or duration_h"),
        ("[scenario]\nduration_s = 1\n[organism]\npreset = 'android'\n", "'android' is not one of"),
        (
            "[scenario]\nduration_s = 1\n[organism]\npreset = 'minimal'\n"
            "[[events]]\nstrt = 1\nend = 2\nkey = 'world.threat'\nvalue = 1\n",
            "events[0]: unknown key(s) ['strt']",
        ),
        (
            "[scenario]\nduration_s = 1\n[organism]\npreset = 'grid'\n"
            "[[events]]\nstart = 1\nend = 2\nkey = 'world.threat'\nvalue = 1\n",
            "only available with preset = 'minimal'",
        ),
        (
            "[scenario]\nduration_s = 1\n[organism]\npreset = 'minimal'\n"
            "[organism.overrides.'soma.cardio']\nresting_bmp = 60\n",
            "resting_bmp",
        ),
        (
            "[scenario]\nduration_s = 1\n[organism]\npreset = 'minimal'\n"
            "[organism.overrides.'soma.cardio']\nresting_bpm = 500\n",
            "outside",
        ),
        (
            "[scenario]\nduration_s = 1\n[organism]\npreset = 'minimal'\n[[interventions]]\ntype = 'zap'\n",
            "expected 'clamp' or 'lesion'",
        ),
        (
            "[scenario]\nduration_s = 1\n[organism]\npreset = 'minimal'\n"
            "[[interventions]]\ntype = 'clamp'\nkey = 'soma.liver'\nvalue = 1\n",
            "unknown signal",
        ),
        ("[scenario]\nduration_s = 'long'\n[organism]\npreset = 'minimal'\n", "expected a number"),
        ("[scenario]\nduration_s = 1\n[organism]\npreset = 'minimal'\n[observe]\nhalt_on = 'panic'\n", "halt_on"),
        ("not = [valid", "not valid TOML"),
    ],
)
def test_mistakes_are_reported_with_their_location(text, message):
    with pytest.raises(ScenarioError) as error:
        parse_scenario(text)
    assert message in str(error.value)


def test_command_line_validate_and_run(tmp_path, capsys):
    assert main(["validate", *map(str, SCENARIOS)]) == 0
    assert "ok" in capsys.readouterr().out

    path = tmp_path / "fear.toml"
    path.write_text(FEAR, encoding="utf-8")
    assert main(["run", str(path), "--hours", "0.01", "--seed", "7", "--out", str(tmp_path / "run")]) == 0
    out = capsys.readouterr().out
    assert "seed 7" in out and "36.0 s" in out
    assert load_run(tmp_path / "run").meta["config"]["seed"] == 7


def test_command_line_reports_errors_without_a_traceback(tmp_path, capsys):
    path = tmp_path / "broken.toml"
    path.write_text("[scenario]\nduration_s = 1\n", encoding="utf-8")
    assert main(["run", str(path)]) == 2
    assert "error:" in capsys.readouterr().err
