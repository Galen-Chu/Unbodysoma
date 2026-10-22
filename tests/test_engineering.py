"""Acceptance tests for engineering guarantees: read-only observers, packaging, Recorder output."""

import csv
import tomllib
from pathlib import Path

import pytest

import unbodysoma
from unbodysoma import build_minimal_human
from unbodysoma.core import BusReader
from unbodysoma.observe import Recorder

ROOT = Path(__file__).resolve().parents[1]


def test_observers_receive_a_read_only_view():
    engine = build_minimal_human()
    seen: list[object] = []
    engine.observe(lambda t, bus: seen.append(bus))
    engine.step()
    view = seen[-1]
    assert isinstance(view, BusReader)
    assert not hasattr(view, "write")
    with pytest.raises(AttributeError):
        view.write("soma.cardio.heart_rate", 0.0)  # type: ignore[attr-defined]
    assert view.read("soma.cardio.heart_rate") == engine.bus.read("soma.cardio.heart_rate")
    assert "soma.cardio.heart_rate" in view


def test_breakpoints_receive_a_read_only_view():
    engine = build_minimal_human()
    seen: list[object] = []
    engine.run(0.05, until=lambda bus: seen.append(bus) or False)
    assert all(isinstance(v, BusReader) for v in seen) and len(seen) == 5


def test_version_has_a_single_source():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "version" not in pyproject["project"]
    assert "version" in pyproject["project"]["dynamic"]
    assert pyproject["tool"]["setuptools"]["dynamic"]["version"] == {"attr": "unbodysoma.__version__"}
    assert unbodysoma.__version__.count(".") == 2


def test_package_ships_type_information():
    assert (ROOT / "src" / "unbodysoma" / "py.typed").exists()


def test_recorder_columns_csv_and_table(tmp_path):
    engine = build_minimal_human()
    recorder = Recorder(["soma.cardio.heart_rate", "psyche.affect.valence"], every=1.0)
    engine.observe(recorder)
    engine.run(3.0)

    assert recorder.times() == pytest.approx([0.0, 1.0, 2.0, 3.0])
    assert recorder.column("soma.cardio.heart_rate")[0] == 65.0

    recorder.to_csv(tmp_path / "out.csv")
    with open(tmp_path / "out.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["time", "soma.cardio.heart_rate", "psyche.affect.valence"]
    assert len(rows) == 5
    assert float(rows[1][1]) == 65.0

    lines = recorder.table(headers=["HR", "valence"]).splitlines()
    assert lines[0].split() == ["t", "HR", "valence"]
    assert lines[1].split() == ["0.00", "65.00", "0.10"]
    assert len(lines) == 5
