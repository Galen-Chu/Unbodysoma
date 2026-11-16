"""Offline dashboard: render a run record as one self-contained HTML file.

CLI-first and deterministic: no server, no external assets, no timestamps —
the same run record always renders to the same bytes. The page has a header
(scenario, duration, signals, events), a per-signal statistics table, a
sparkline grid of every recorded signal, and — when affect was recorded — a
phase-plane plot of the valence / arousal circumplex. See
docs/OBSERVABILITY.md §7.
"""

from __future__ import annotations

import html
from math import isfinite
from pathlib import Path
from statistics import mean
from typing import Any

from .run import Run, load_run

_STYLE = """
body{font-family:ui-monospace,Consolas,monospace;background:#101418;color:#d8dee6;margin:2rem}
h1{font-size:1.2rem}h2{font-size:1rem;margin-top:2rem;color:#9fb3c8}
table{border-collapse:collapse;font-size:.85rem}
td,th{border:1px solid #2a3440;padding:.15rem .6rem;text-align:right}
th:first-child,td:first-child{text-align:left}
.grid{display:flex;flex-wrap:wrap;gap:1rem}
.card{background:#161c22;border:1px solid #2a3440;border-radius:6px;padding:.5rem}
.card div{font-size:.75rem;color:#9fb3c8}
svg{display:block}
"""


def _polyline(values: list[float | None], width: int, height: int) -> str:
    """A normalized polyline of the series; gaps (None) break the line."""
    points = [v for v in values if v is not None]
    if len(points) < 2:
        return ""
    lo, hi = min(points), max(points)
    span = (hi - lo) or 1.0
    parts, pen = [], False
    for i, v in enumerate(values):
        if v is None:
            pen = False
            continue
        x = i / (len(values) - 1) * (width - 2) + 1
        y = height - 2 - (v - lo) / span * (height - 4)
        parts.append(f"{x:.1f},{y:.1f}" if pen else f"M{x:.1f},{y:.1f}")
        pen = True
    return '<path d="' + " L".join(parts) + '" fill="none" stroke="#7ec8e3" stroke-width="1"/>'


def _sparkline(key: str, values: list[float | None]) -> str:
    points = [v for v in values if v is not None]
    lo, hi = (min(points), max(points)) if points else (0.0, 0.0)
    label = html.escape(key)
    return (
        f'<div class="card"><div>{label}</div>'
        f'<svg width="260" height="64" role="img" aria-label="{label}">{_polyline(values, 260, 64)}</svg>'
        f"<div>{lo:.3g} … {hi:.3g}</div></div>"
    )


def _phase_plane(run: Run) -> str:
    valence, arousal = run.columns.get("psyche.affect.valence"), run.columns.get("psyche.affect.arousal")
    if not valence or not arousal:
        return ""
    points = [
        (v, a)
        for v, a in zip(valence, arousal, strict=True)
        if v is not None and a is not None and isfinite(v) and isfinite(a)
    ]
    if len(points) < 2:
        return ""
    w, h = 300, 300
    path = " L".join(f"{(v + 1) / 2 * (w - 8) + 4:.1f},{h - 4 - a * (h - 8):.1f}" for v, a in points)
    return (
        "<h2>affect plane (valence × arousal)</h2>"
        f'<svg width="{w}" height="{h}" role="img" aria-label="affect phase plane">'
        f'<rect width="{w}" height="{h}" fill="#161c22"/>'
        f'<line x1="{w / 2}" y1="0" x2="{w / 2}" y2="{h}" stroke="#2a3440"/>'
        f'<line x1="0" y1="{h / 2}" x2="{w}" y2="{h / 2}" stroke="#2a3440"/>'
        f'<path d="M{path}" fill="none" stroke="#e3a67e" stroke-width="1"/></svg>'
    )


def render_dashboard(run: Run) -> str:
    """Render a loaded run record as a self-contained HTML page."""
    config: dict[str, Any] = run.meta.get("config", {})
    duration = run.times[-1] - run.times[0] if run.times else 0.0
    rows = []
    for key, values in run.columns.items():
        points = [v for v in values if v is not None]
        if not points:
            continue
        rows.append(
            f"<tr><td>{html.escape(key)}</td><td>{min(points):.4g}</td><td>{mean(points):.4g}</td>"
            f"<td>{max(points):.4g}</td><td>{points[-1]:.4g}</td></tr>"
        )
    kinds: dict[str, int] = {}
    for event in run.events:
        kinds[event.get("kind", "?")] = kinds.get(event.get("kind", "?"), 0) + 1
    event_line = ", ".join(f"{html.escape(str(k))} ×{n}" for k, n in sorted(kinds.items())) or "none"
    name = html.escape(str(config.get("scenario", {}).get("name", "run")))
    description = html.escape(str(config.get("scenario", {}).get("description", "")))
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f"<title>unbodysoma · {name}</title><style>{_STYLE}</style></head><body>"
        f"<h1>unbodysoma · {name}</h1><p>{description}</p>"
        f"<p>duration {duration / 3600:.2f} h · {len(run.columns)} signals"
        f" · {len(run.times)} samples · events: {event_line}</p>"
        "<h2>signals</h2><table><tr><th>signal</th><th>min</th><th>mean</th><th>max</th><th>last</th></tr>"
        + "".join(rows)
        + "</table>"
        + _phase_plane(run)
        + '<h2>sparklines</h2><div class="grid">'
        + "".join(_sparkline(key, values) for key, values in run.columns.items())
        + "</div></body></html>\n"
    )


def write_dashboard(path: str | Path, out: str | Path | None = None) -> Path:
    """Load a run record and write its dashboard next to it (or to ``out``)."""
    run = load_run(path)
    target = Path(out) if out is not None else Path(path) / "dashboard.html"
    target.write_text(render_dashboard(run), encoding="utf-8", newline="\n")
    return target


__all__ = ["Run", "load_run", "render_dashboard", "write_dashboard"]
