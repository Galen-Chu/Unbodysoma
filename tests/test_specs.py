"""Acceptance tests for ADR-0006: declarative parameter and signal specs."""

import inspect
from pathlib import Path

import pytest

from unbodysoma import build_grid_human, build_minimal_human, catalog
from unbodysoma.core import BusPort, Engine, Module, ParamSpec, SignalSpec
from unbodysoma.observe import HealthMonitor, RunWriter, load_run
from unbodysoma.soma import Cardio
from unbodysoma.world import DEFAULT_WORLD_SIGNALS, Event

DOCS = Path(__file__).resolve().parents[1] / "docs"


def preset_modules() -> list[Module]:
    grid_only = [m for m in build_grid_human().modules if m.name not in {x.name for x in build_minimal_human().modules}]
    return build_minimal_human().modules + grid_only


def test_every_signal_in_the_presets_has_a_spec():
    assert build_minimal_human().unspecified_signals() == []
    assert build_grid_human().unspecified_signals() == []


@pytest.mark.parametrize("module", preset_modules(), ids=lambda m: m.name)
def test_param_specs_match_the_constructor(module):
    """Guards against a ParamSpec drifting from the __init__ argument it describes."""
    signature = inspect.signature(type(module).__init__)
    arguments = {n: p.default for n, p in signature.parameters.items() if n != "self" and n not in module.config_args}
    assert {p.name: p.default for p in module.params} == arguments
    recorded = module.get_params()
    assert {k: recorded[k] for k in arguments} == arguments  # stored under the same attribute names
    assert set(module.config_args) <= set(recorded)  # structural configuration is recorded too


@pytest.mark.parametrize("module", preset_modules(), ids=lambda m: m.name)
def test_defaults_lie_within_their_valid_range(module):
    for p in module.params:
        p.check(p.default, module.name)


def test_out_of_range_parameter_is_rejected_when_assembling():
    with pytest.raises(ValueError, match="resting_bpm"):
        Engine().add(Cardio(resting_bpm=500.0))
    with pytest.raises(TypeError, match="must be a number"):
        Engine().add(Cardio(tau="fast"))  # type: ignore[arg-type]


def test_rejected_module_leaves_the_engine_untouched():
    engine = Engine()
    with pytest.raises(ValueError):
        engine.add(Cardio(resting_bpm=500.0))
    engine.add(Cardio())  # its signals were not half-registered by the failed attempt


def test_spec_for_an_unwritten_signal_is_rejected():
    class Liar(Module):
        name = "test.liar"
        writes = ("test.a",)
        signal_specs = (SignalSpec("test.b", "unit"),)

        def step(self, dt: float, port: BusPort) -> None:
            port.write("test.a", 0.0)

    with pytest.raises(ValueError, match="does not write"):
        Engine().add(Liar())


def test_param_spec_check_rejects_nan():
    with pytest.raises(ValueError):
        ParamSpec("x", 0.0, lo=0.0, hi=1.0).check(float("nan"), "test")


def test_run_record_stores_parameters_specs_and_scenario(tmp_path):
    engine = Engine()
    for module in build_minimal_human([Event(1.0, 2.0, "world.threat", 0.5)]).modules:
        if module.name == "soma.cardio":
            module = Cardio(resting_bpm=72.0)
        engine.add(module)
    with RunWriter(tmp_path / "run").attach(engine):
        engine.run(1.0)

    meta = load_run(tmp_path / "run").meta
    modules = {m["name"]: m for m in meta["modules"]}
    assert modules["soma.cardio"]["params"]["resting_bpm"] == 72.0
    assert modules["world.scripted"]["params"]["events"] == [
        {"start": 1.0, "end": 2.0, "key": "world.threat", "value": 0.5}
    ]
    assert modules["world.scripted"]["params"]["signals"] == list(DEFAULT_WORLD_SIGNALS)
    assert modules["world.scripted"]["params"]["baselines"] == {"world.ambient_temperature": 22.0}
    assert meta["signals"]["soma.cardio.heart_rate"]["unit"] == "bpm"
    assert meta["signals"]["world.threat"]["hi"] == 1.0


def test_health_monitor_enforces_signal_specs():
    engine = build_minimal_human()
    engine.clamp("psyche.affect.valence", 2.0, start=5.0)  # outside the declared [-1, 1]
    monitor = HealthMonitor(halt_on="critical").attach(engine)
    reason = engine.run(30.0)
    assert reason is not None and "psyche.affect.valence" in reason
    assert [a.rule for a in monitor.alerts] == ["spec:psyche.affect.valence"]


def test_spec_checks_can_be_turned_off():
    engine = build_minimal_human()
    engine.clamp("psyche.affect.valence", 2.0)
    monitor = HealthMonitor(check_specs=False).attach(engine)
    engine.run(1.0)
    assert monitor.alerts == []


def test_generated_catalogs_are_up_to_date():
    for path, expected in catalog.render(DOCS).items():
        assert path.read_text(encoding="utf-8") == expected, f"{path.name} is stale: run python -m unbodysoma.catalog"


def test_signal_graph_shows_the_known_causal_links():
    graph = catalog.dependency_graph(build_grid_human())
    assert '    soma_cardio -->|"cardio.heart_rate"| interface_interoception' in graph.splitlines()
    assert any(
        line.startswith("    psyche_action -->") and line.endswith("psyche_navigation") for line in graph.splitlines()
    )
    assert any(
        line.startswith("    psyche_navigation -->") and line.endswith("world_grid") for line in graph.splitlines()
    )
    for module in build_grid_human().modules:
        assert f'["{module.name}"]' in graph  # every module is a node
