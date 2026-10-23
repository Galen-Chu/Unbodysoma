"""Generate the signal and parameter catalogs in docs/ from module specs.

python -m unbodysoma.catalog            # rewrite docs/SIGNALS.md table and docs/PARAMETERS.md
python -m unbodysoma.catalog --check    # exit 1 if the docs are out of date (used by tests / CI)
"""

from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Sequence
from pathlib import Path

from .core import Engine, Module, SignalSpec
from .presets import build_grid_human, build_minimal_human

BEGIN = "<!-- BEGIN GENERATED: python -m unbodysoma.catalog -->"
END = "<!-- END GENERATED -->"


def _bound(x: float) -> str:
    return "−∞" if x == -math.inf else "∞" if x == math.inf else f"{x:g}"


def _range(lo: float, hi: float) -> str:
    if math.isinf(lo) and math.isinf(hi):
        return "—"
    return f"[{_bound(lo)}, {_bound(hi)}]"


def _value(x: object) -> str:
    return f"{x:g}" if isinstance(x, float) else str(x)


def presets() -> list[Engine]:
    """Every shipped assembly; the catalogs describe their union."""
    return [build_minimal_human(), build_grid_human()]


def signal_table(engines: Sequence[Engine]) -> str:
    specs: dict[str, SignalSpec] = {}
    writers: dict[str, set[str]] = {}
    readers: dict[str, set[str]] = {}
    for engine in engines:
        specs.update(engine.signal_specs())
        for key in engine.signals():
            writers.setdefault(key, set()).add(str(engine.writer_of(key)))
        for module in engine.modules:
            for key in module.reads:
                readers.setdefault(key, set()).add(module.name)
    lines = ["| 訊號 | 單位 | 範圍 | 寫入者 | 讀取者 | 說明 |", "|---|---|---|---|---|---|"]
    for key in sorted(writers):
        spec = specs.get(key)
        unit = spec.unit if spec else "—"
        rng = _range(spec.lo, spec.hi) if spec else "—"
        desc = spec.description if spec else "（未描述）"
        who_writes = ", ".join(f"`{w}`" for w in sorted(writers[key]))
        who_reads = ", ".join(f"`{r}`" for r in sorted(readers.get(key, set()))) or "—（預留）"
        lines.append(f"| `{key}` | {unit} | {rng} | {who_writes} | {who_reads} | {desc} |")
    return "\n".join(lines)


def _unique_modules(engines: Sequence[Engine]) -> list[Module]:
    seen: dict[str, Module] = {}
    for engine in engines:
        for module in engine.modules:
            seen.setdefault(module.name, module)
    return list(seen.values())


def parameter_catalog(engines: Sequence[Engine]) -> str:
    parts = [
        "# 參數 Parameters",
        "",
        "> 本文件由 `python -m unbodysoma.catalog` 從模組的 `ParamSpec` 自動產生，**請勿手動編輯**。",
        "> 預設值目前都是 L0 玩具值；個體差異與族群分布的規劃見 [VARIABILITY.md](VARIABILITY.md)。",
        "",
    ]
    for module in _unique_modules(engines):
        if not module.params:
            continue
        cls = type(module)
        parts += [
            f"## `{module.name}`",
            "",
            f"`{cls.__module__}.{cls.__qualname__}`",
            "",
            "| 參數 | 預設值 | 單位 | 有效範圍 | 說明 | 來源 |",
            "|---|---|---|---|---|---|",
        ]
        for p in module.params:
            unit = p.unit or "—"
            parts.append(
                f"| `{p.name}` | {_value(p.default)} | {unit} | {_range(p.lo, p.hi)} | {p.description} | {p.source} |"
            )
        parts.append("")
    return "\n".join(parts)


_LAYERS = {"world": "World 環境層", "interface": "Interface 介面層", "soma": "Soma 身體層", "psyche": "Psyche 心智層"}


def dependency_graph(engine: Engine) -> str:
    """Mermaid flowchart: one node per module, one edge per writer -> reader pair, labelled with the signals."""
    node = {m.name: m.name.replace(".", "_") for m in engine.modules}
    lines = ["flowchart LR"]
    for layer, title in _LAYERS.items():
        members = [m for m in engine.modules if m.name.split(".")[0] == layer]
        if members:
            lines.append(f'    subgraph {layer}["{title}"]')
            lines += [f'        {node[m.name]}["{m.name}"]' for m in members]
            lines.append("    end")
    edges: dict[tuple[str, str], list[str]] = {}
    for module in engine.modules:
        for key in module.reads:
            writer = engine.writer_of(key)
            if writer is not None and writer != module.name:
                edges.setdefault((writer, module.name), []).append(key.split(".", 1)[1])
    for (writer, reader), keys in sorted(edges.items()):
        label = ", ".join(sorted(keys)[:2]) + (f" +{len(keys) - 2}" if len(keys) > 2 else "")
        lines.append(f'    {node[writer]} -->|"{label}"| {node[reader]}')
    return "\n".join(lines)


def graph_document(engines: Sequence[Engine]) -> str:
    names = {"world.scripted": "minimal：腳本化世界", "world.grid": "grid：網格世界"}
    parts = [
        "# 訊號依賴圖 Signal graph",
        "",
        "> 本文件由 `python -m unbodysoma.catalog` 從模組的 `reads` / `writes` 宣告自動產生，**請勿手動編輯**。",
        "> 每條邊代表「寫入者 → 讀取者」，標籤是經過的訊號（省略最外層的命名空間，"
        "例如 `soma.cardio.heart_rate` 寫成 `cardio.heart_rate`）；訊號的意義見 [SIGNALS.md](SIGNALS.md)。",
        "",
    ]
    for engine in engines:
        title = next((names[m.name] for m in engine.modules if m.name in names), "preset")
        parts += [f"## {title}", "", "```mermaid", dependency_graph(engine), "```", ""]
    return "\n".join(parts)


def render(docs: Path) -> dict[Path, str]:
    """Expected content of every generated file."""
    engines = presets()
    signals_path = docs / "SIGNALS.md"
    current = signals_path.read_text(encoding="utf-8")
    head, _, rest = current.partition(BEGIN)
    _, _, tail = rest.partition(END)
    return {
        signals_path: f"{head}{BEGIN}\n{signal_table(engines)}\n{END}{tail}",
        docs / "PARAMETERS.md": parameter_catalog(engines),
        docs / "SIGNAL_GRAPH.md": graph_document(engines),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--docs", type=Path, default=Path("docs"))
    parser.add_argument("--check", action="store_true", help="only report whether the docs are up to date")
    args = parser.parse_args(argv)

    stale = []
    for path, content in render(args.docs).items():
        old = path.read_text(encoding="utf-8") if path.exists() else None
        if old == content:
            continue
        stale.append(path)
        if not args.check:
            path.write_text(content, encoding="utf-8", newline="\n")
    for path in stale:
        print(f"{'out of date' if args.check else 'updated'}: {path}")
    return 1 if args.check and stale else 0


if __name__ == "__main__":
    sys.exit(main())
