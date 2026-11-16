"""Population sampling and batch runs — the Phase 2 population layer.

Draws individuals from the parameter distributions of docs/VARIABILITY.md §4
(the individual-difference candidates of that table) and runs them through
the same protocol, collecting per-individual summary statistics. The same
``(base_seed, index)`` always draws the same individual and produces the
same trajectory — populations are exactly as reproducible as single runs.

Distributions are clipped-normal with the ranges taken from the parameter
specs themselves, so a draw can never leave a module's declared bounds.
The SDs are calibrated plausibility, flagged for literature refinement as
VARIABILITY.md §4 demands — they are a starting grid, not a claim.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from statistics import mean, pstdev
from typing import Any

from .core import Engine
from .observe import Recorder
from .observe.metrics import (
    distribution,
    entropy_ratio,
    mode_amplification_ratio,
    rmssd_ms,
    rr_intervals,
)
from .presets import build_minimal_human
from .psyche.action import ACTIONS

# (module, parameter, mean, sd) — see docs/VARIABILITY.md §4 for the rationale
# of each individual-difference candidate.
POPULATION_SPEC: tuple[tuple[str, str, float, float], ...] = (
    ("soma.cardio", "age_years", 42.0, 15.0),
    ("soma.cardio", "resting_bpm", 66.0, 9.0),
    ("soma.endocrine", "cortisol_baseline", 0.2, 0.04),
    ("soma.endocrine", "car_amplitude", 0.5, 0.15),
    ("soma.endocrine", "acth_gain", 0.45, 0.12),
    ("psyche.affect", "baseline_valence", 0.1, 0.08),
    ("psyche.affect", "w_threat_valence", 0.9, 0.2),
    ("psyche.appraisal", "arousal_bias", 0.5, 0.2),
)

_STATS_KEYS = (
    "soma.cardio.heart_rate",
    "psyche.affect.valence",
    "psyche.affect.arousal",
    "soma.metabolism.glucose",
)
_SELECTED_KEYS = tuple(f"psyche.action.selected_{a}" for a in ACTIONS)


def _spec_ranges() -> dict[tuple[str, str], tuple[float, float]]:
    """Declared (lo, hi) of every population parameter, from a reference engine."""
    ranges: dict[tuple[str, str], tuple[float, float]] = {}
    for module in build_minimal_human().modules:
        for spec in module.params:
            if (module.name, spec.name) in {(m, p) for m, p, _, _ in POPULATION_SPEC}:
                ranges[(module.name, spec.name)] = (spec.lo, spec.hi)
    missing = {(m, p) for m, p, _, _ in POPULATION_SPEC} - set(ranges)
    if missing:
        raise ValueError(f"population parameters not found in any module: {sorted(missing)}")
    return ranges


def sample_individual(base_seed: int, index: int) -> dict[str, dict[str, float]]:
    """Draw one individual's parameter overrides (clipped to the spec ranges)."""
    rng = random.Random(f"{base_seed}:{index}")
    ranges = _spec_ranges()
    overrides: dict[str, dict[str, float]] = {}
    for module_name, param, mu, sd in POPULATION_SPEC:
        lo, hi = ranges[(module_name, param)]
        value = min(max(rng.gauss(mu, sd), lo), hi)
        overrides.setdefault(module_name, {})[param] = value
    return overrides


@dataclass(frozen=True)
class IndividualResult:
    index: int
    seed: int
    overrides: Mapping[str, Mapping[str, float]] = field(default_factory=dict)
    stats: Mapping[str, tuple[float, float, float]] = field(default_factory=dict)  # key -> (min, mean, max)
    action_shares: Mapping[str, float] = field(default_factory=dict)  # action -> share of samples
    rmssd_ms: float = 0.0


def run_population(
    n: int,
    base_seed: int = 0,
    seconds: float = 300.0,
    builder: Callable[..., Engine] = build_minimal_human,
    **builder_kwargs: object,
) -> list[IndividualResult]:
    """Run ``n`` sampled individuals through the same protocol.

    Individual ``i`` uses engine seed ``base_seed + i`` and the parameter
    draws of ``sample_individual(base_seed, i)`` — same inputs, same outputs.
    """
    results = []
    for i in range(n):
        engine = builder(seed=base_seed + i, overrides=sample_individual(base_seed, i), **builder_kwargs)
        recorder = Recorder(_STATS_KEYS + _SELECTED_KEYS, every=1.0)
        engine.observe(recorder)
        engine.run(seconds)
        stats = {}
        for key in _STATS_KEYS:
            column = recorder.column(key)
            stats[key] = (min(column), mean(column), max(column))
        shares = {action: mean(recorder.column(key)) for action, key in zip(ACTIONS, _SELECTED_KEYS, strict=True)}
        rr = rr_intervals(recorder.times(), recorder.column("soma.cardio.heart_rate"))
        results.append(
            IndividualResult(
                index=i,
                seed=base_seed + i,
                overrides=sample_individual(base_seed, i),
                stats=stats,
                action_shares=shares,
                rmssd_ms=rmssd_ms(rr) if len(rr) > 3 else 0.0,
            )
        )
    return results


def population_action_metrics(results: list[IndividualResult]) -> dict[str, Any]:
    """Distribution-level acceptance metrics over the population's choices.

    The pooled action distribution is the reference; each individual is
    compared to it (VARIABILITY.md §6): mean entropy ratio ≈ 1 means
    individuals are as diverse as the population, and the mode amplification
    ratio ≈ 1 means no single mode swallows the population.
    """
    pooled_counts = {a: sum(r.action_shares.get(a, 0.0) for r in results) for a in ACTIONS}
    pooled = distribution({a: v for a, v in pooled_counts.items() if v > 0})
    ratios = [entropy_ratio(r.action_shares, pooled) for r in results if sum(r.action_shares.values()) > 0]
    amplifications = [
        mode_amplification_ratio(r.action_shares, pooled) for r in results if sum(r.action_shares.values()) > 0
    ]
    return {
        "pooled": pooled,
        "mean_entropy_ratio": mean(ratios) if ratios else 0.0,
        "mode_amplification_ratio": mean(amplifications) if amplifications else 0.0,
    }


def population_summary(results: list[IndividualResult]) -> str:
    """A readable table: per-statistic population mean ± SD across individuals."""
    lines = [f"population: {len(results)} individuals"]
    for key in _STATS_KEYS:
        maxes = [r.stats[key][2] for r in results]
        means = [r.stats[key][1] for r in results]
        lines.append(
            f"  {key}: max {mean(maxes):7.2f} ± {pstdev(maxes) if len(results) > 1 else 0.0:5.2f}"
            f" | mean {mean(means):7.3f} ± {pstdev(means) if len(results) > 1 else 0.0:5.3f}"
        )
    rmssd = [r.rmssd_ms for r in results]
    lines.append(f"  RMSSD: {mean(rmssd):6.1f} ± {pstdev(rmssd) if len(results) > 1 else 0.0:5.1f} ms")
    return "\n".join(lines)
