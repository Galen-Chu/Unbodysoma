"""Generate the signal and parameter catalogs in docs/ from module specs.

python -m unbodysoma.catalog            # rewrite docs/SIGNALS.md table and docs/PARAMETERS.md
python -m unbodysoma.catalog --check    # exit 1 if the docs are out of date (used by tests / CI)
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from .core import Engine
from .presets import build_minimal_human

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


def signal_table(engine: Engine) -> str:
    specs = engine.signal_specs()
    readers: dict[str, list[str]] = {}
    for module in engine.modules:
        for key in module.reads:
            readers.setdefault(key, []).append(module.name)
    lines = ["| 訊號 | 單位 | 範圍 | 寫入者 | 讀取者 | 說明 |", "|---|---|---|---|---|---|"]
    for key in engine.signals():
        spec = specs.get(key)
        unit = spec.unit if spec else "—"
        rng = _range(spec.lo, spec.hi) if spec else "—"
        desc = spec.description if spec else "（未描述）"
        who_reads = ", ".join(f"`{r}`" for r in sorted(readers.get(key, []))) or "—（預留）"
        lines.append(f"| `{key}` | {unit} | {rng} | `{engine.writer_of(key)}` | {who_reads} | {desc} |")
    return "\n".join(lines)


def parameter_catalog(engine: Engine) -> str:
    parts = [
        "# 參數 Parameters",
        "",
        "> 本文件由 `python -m unbodysoma.catalog` 從模組的 `ParamSpec` 自動產生，**請勿手動編輯**。",
        "> 預設值目前都是 L0 玩具值；個體差異與族群分布的規劃見 [VARIABILITY.md](VARIABILITY.md)。",
        "",
    ]
    for module in engine.modules:
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


def render(docs: Path) -> dict[Path, str]:
    """Expected content of every generated file."""
    engine = build_minimal_human()
    signals_path = docs / "SIGNALS.md"
    current = signals_path.read_text(encoding="utf-8")
    head, _, rest = current.partition(BEGIN)
    _, _, tail = rest.partition(END)
    return {
        signals_path: f"{head}{BEGIN}\n{signal_table(engine)}\n{END}{tail}",
        docs / "PARAMETERS.md": parameter_catalog(engine),
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
