"""Acceptance tests for the Rerun live-view adapter.

Most tests use a recording fake of the rerun module, so they run without the
optional dependency; the last one uses the real rerun-sdk when it is installed.
"""

import pytest

from unbodysoma import build_grid_human, build_minimal_human
from unbodysoma.observe.rerun import RerunSink
from unbodysoma.world import Event


class FakeRerun:
    """Stands in for ``import rerun``: archetypes become tuples, every call is recorded."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        outer = self

        class Stream:
            def __init__(self, application_id: str) -> None:
                outer.calls.append(("init", application_id))

            def spawn(self) -> None:
                outer.calls.append(("spawn",))

            def save(self, path: str) -> None:
                outer.calls.append(("save", path))

            def memory_recording(self) -> str:
                return "memory"

            def set_time(self, timeline: str, *, duration: float) -> None:
                outer.calls.append(("time", timeline, duration))

            def log(self, path: str, entity: tuple, static: bool = False) -> None:
                outer.calls.append(("log", path, entity, static))

            def flush(self) -> None:
                outer.calls.append(("flush",))

        self.RecordingStream = Stream

    @staticmethod
    def Scalars(value: float) -> tuple:  # noqa: N802 - mirrors the rerun API
        return ("Scalars", value)

    @staticmethod
    def TextLog(text: str, level: str) -> tuple:  # noqa: N802
        return ("TextLog", text, level)

    @staticmethod
    def Points2D(positions, radii=None, colors=None) -> tuple:  # noqa: N802
        return ("Points2D", positions, radii)

    def logs(self, path: str) -> list[tuple]:
        return [c for c in self.calls if c[0] == "log" and c[1] == path]


def test_signals_are_logged_as_time_series_on_the_simulation_clock():
    fake = FakeRerun()
    engine = build_minimal_human()
    sink = RerunSink(keys=["soma.cardio.heart_rate"], every=1.0, module=fake).attach(engine)
    engine.run(3.0)
    times = [c[2] for c in fake.calls if c[0] == "time"]
    assert times == pytest.approx([0.0, 1.0, 2.0, 3.0])
    beats = fake.logs("signals/soma/cardio/heart_rate")
    assert len(beats) == 4 and beats[0][2] == ("Scalars", 65.0)
    assert sink.memory == "memory"  # neither spawn nor save: recorded in memory


def test_events_become_a_text_log_with_severity_levels():
    fake = FakeRerun()
    engine = build_minimal_human()
    engine.lesion("soma.cardio", start=5.0)
    from unbodysoma.observe import HealthMonitor

    HealthMonitor(every=1.0).attach(engine)
    RerunSink(keys=[], module=fake).attach(engine)
    engine.run(10.0)
    texts = [c[2] for c in fake.logs("events")]
    assert any(t[1].startswith("intervention.scheduled") for t in texts)  # logged although it predates attach
    assert any(t[2] == "ERROR" and "heart_rate_survivable" in t[1] for t in texts)


def test_the_grid_world_map_is_logged():
    fake = FakeRerun()
    engine = build_grid_human()
    RerunSink(keys=[], every=5.0, module=fake).attach(engine)
    engine.run(10.0)
    assert fake.logs("world/shelters")[0][3] is True  # static layout
    assert fake.logs("world/hazards") and fake.logs("world/water")
    assert len(fake.logs("world/organism")) == 3
    food = fake.logs("world/food")[-1][2]
    assert len(food[1]) == 4 and all(0.1 <= r <= 0.5 for r in food[2])


def test_streaming_to_rerun_does_not_change_the_simulation():
    bare = build_grid_human(seed=4)
    bare.run(120.0)
    watched = build_grid_human(seed=4)
    RerunSink(every=0.05, module=FakeRerun()).attach(watched)
    watched.run(120.0)
    assert watched.bus.snapshot() == bare.bus.snapshot()


def test_spawn_and_save_destinations():
    fake = FakeRerun()
    RerunSink(spawn=True, save="out.rrd", module=fake).attach(build_minimal_human([Event(0, 1, "world.threat", 1)]))
    assert ("spawn",) in fake.calls and ("save", "out.rrd") in fake.calls


def test_a_missing_installation_explains_how_to_install(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def no_rerun(name, *args, **kwargs):
        if name == "rerun":
            raise ImportError("No module named 'rerun'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_rerun)
    monkeypatch.delitem(__import__("sys").modules, "rerun", raising=False)
    with pytest.raises(ImportError, match=r"unbodysoma\[viz\]"):
        RerunSink().attach(build_minimal_human())


def test_with_the_real_rerun_sdk_a_recording_file_is_written(tmp_path):
    pytest.importorskip("rerun")
    engine = build_grid_human()
    sink = RerunSink(every=1.0, save=tmp_path / "run.rrd").attach(engine)
    engine.run(30.0)
    sink.flush()
    assert (tmp_path / "run.rrd").stat().st_size > 1000
