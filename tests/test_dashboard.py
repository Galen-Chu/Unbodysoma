"""The offline dashboard: structure and determinism (OBSERVABILITY.md §7)."""

from __future__ import annotations

from pathlib import Path

from unbodysoma import build_minimal_human
from unbodysoma.observe.dashboard import render_dashboard, write_dashboard
from unbodysoma.observe.run import RunWriter
from unbodysoma.world import Event


def make_run(tmp_path: Path) -> Path:
    path = tmp_path / "run"
    engine = build_minimal_human([Event(60.0, 90.0, "world.threat", 0.9)], seed=0)
    with RunWriter(path, every=1.0).attach(engine):
        engine.run(120.0)
    return path


def test_dashboard_has_the_expected_sections(tmp_path: Path):
    page = write_dashboard(make_run(tmp_path)).read_text(encoding="utf-8")
    assert page.startswith("<!doctype html>")
    assert "unbodysoma ·" in page  # header names the run
    assert "signals" in page and "sparklines" in page
    assert "affect plane" in page  # valence and arousal were recorded
    assert page.count("<svg") == 1 + len(engine_signals())  # one per signal + the phase plane


def engine_signals() -> list[str]:
    return build_minimal_human().signals()


def test_dashboard_is_deterministic(tmp_path: Path):
    run = make_run(tmp_path / "again")
    from unbodysoma.observe import load_run

    assert render_dashboard(load_run(run)) == render_dashboard(load_run(run))


def test_dashboard_cli_writes_next_to_the_record(tmp_path: Path):
    from unbodysoma.__main__ import main

    run = make_run(tmp_path / "cli")
    assert main(["dashboard", str(run)]) == 0
    assert (run / "dashboard.html").exists()
