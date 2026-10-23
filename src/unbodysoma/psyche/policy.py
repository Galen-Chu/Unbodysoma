"""Probabilistic choice between competing actions. See docs/adr/0007-probabilistic-action-selection.md."""

from __future__ import annotations

import math
import random
from collections.abc import Mapping


def softmax(utilities: Mapping[str, float], temperature: float) -> dict[str, float]:
    """Choice probabilities ``p_i ∝ exp(u_i / T)``.

    ``T = 0`` is the deterministic limit (all mass on the best action, first
    one wins ties): the "mode collapse" case of docs/VARIABILITY.md.
    """
    if not utilities:
        raise ValueError("no actions to choose from")
    if temperature <= 0.0:
        best = max(utilities, key=lambda k: utilities[k])
        return {k: 1.0 if k == best else 0.0 for k in utilities}
    top = max(utilities.values())
    weights = {k: math.exp((u - top) / temperature) for k, u in utilities.items()}
    total = sum(weights.values())
    return {k: w / total for k, w in weights.items()}


def sample(probabilities: Mapping[str, float], rng: random.Random) -> str:
    """Draw one action; iteration order is the mapping's order, so draws are reproducible."""
    r = rng.random()
    cumulative = 0.0
    last = ""
    for action, p in probabilities.items():
        cumulative += p
        last = action
        if r < cumulative:
            return action
    return last  # guards against rounding when the probabilities sum to just under 1


_MAX_EXPONENT = 50.0  # exp(50) is already "immediate"; avoids overflow at tiny temperatures


def switch(
    current: str,
    utilities: Mapping[str, float],
    temperature: float,
    rate: float,
    dt: float,
    rng: random.Random,
) -> str:
    """Continuous-time action switching: leave ``current`` for ``b`` at rate ``rate · exp((u_b − u_current) / 2T)``.

    Because switching is a rate, the chance of abandoning an action over an
    hour is the same whether decisions are taken every 0.5 s or every 5 s.
    Urgent alternatives (large utility gaps) still win almost at once, and the
    long-run share of time spent on each action is exactly ``softmax(utilities, T)``
    (detailed balance: the ratio of opposite rates is ``exp(Δu / T)``). Each
    step allows at most one switch, which is accurate while ``rate · dt`` is
    small; large rates only occur for urgent switches, which happen at once
    anyway. If ``current`` is no longer available, a fresh choice is sampled
    from the softmax.
    """
    if current not in utilities:
        return sample(softmax(utilities, temperature), rng)
    if temperature <= 0.0:
        best = max(utilities, key=lambda k: utilities[k])
        return best if utilities[best] > utilities[current] else current
    base = utilities[current]
    rates = {
        b: rate * math.exp(min(_MAX_EXPONENT, (u - base) / (2.0 * temperature)))
        for b, u in utilities.items()
        if b != current
    }
    total = sum(rates.values())
    if total <= 0.0 or rng.random() >= 1.0 - math.exp(-total * dt):
        return current
    return sample({b: r / total for b, r in rates.items()}, rng)
