"""Episodic memory: emotionally intense moments are kept, and color the present.

The minimal symbolic-hybrid representation of BACKLOG §5: an episode is a
timestamped snapshot of core affect and pain. Capture is gated by emotional
intensity (strong moments are remembered, dull ones are not) and throttled;
each episode's strength decays over days; the weakest are forgotten when the
store is full. Retrieval is mood-congruent: the current affective context
reactivates similar episodes, and their signed content pulls valence —
remembering bad times feels bad, which is also how low mood sustains itself
(McGaugh, 2004, for the emotional-modulation anchor).

Vector embeddings, replay-based consolidation and prospective use (Phase 5's
allostasis) are deferred until a consumer needs them. Acceptance:
tests/test_memory.py; equations: docs/PSYCHE.md §4.9.
"""

from __future__ import annotations

import math

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp

_SIMILARITY_SPAN = 0.5  # mean channel difference at which similarity reaches zero


class EpisodicMemory(Module):
    """Keeps emotionally intense affect snapshots; reactivation is mood-congruent."""

    name = "psyche.memory"
    rate_hz = 10.0
    reads = (
        "psyche.affect.valence",
        "psyche.affect.arousal",
        "intero.pain",
    )
    signal_specs = (
        SignalSpec("psyche.memory.episodes", "count", 0.0, 64.0, "Episodes currently held"),
        SignalSpec(
            "psyche.memory.mood_congruence",
            "normalized",
            -1.0,
            1.0,
            "Signed reactivation of stored episodes by the current context (negative memories pull down)",
        ),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec(
            "capture_threshold",
            0.55,
            "normalized",
            0.0,
            1.0,
            "Emotional intensity above which a moment is captured as an episode",
            source="calibrated: a real threat or meal is kept, an unremarkable minute is not",
        ),
        ParamSpec(
            "min_gap",
            300.0,
            "s",
            1.0,
            3600.0,
            "Minimum spacing between captured episodes",
            source="calibrated: one episode per emotional event, not per tick",
        ),
        ParamSpec(
            "tau_memory",
            172800.0,
            "s",
            600.0,
            2.6e6,
            "Time constant of episode decay",
            source="days-scale forgetting; emotionally intense episodes outlast the incident",
        ),
        ParamSpec("max_episodes", 64, "episodes", 4, 1024, "Store capacity; the weakest is forgotten when full"),
    )
    state_fields = ("episodes", "last_capture")

    def __init__(
        self,
        capture_threshold: float = 0.55,
        min_gap: float = 300.0,
        tau_memory: float = 172800.0,
        max_episodes: int = 64,
    ) -> None:
        self.capture_threshold = capture_threshold
        self.min_gap = min_gap
        self.tau_memory = tau_memory
        self.max_episodes = max_episodes
        # Each episode: (t, valence, arousal, pain, strength)
        self.episodes: list[tuple[float, float, float, float, float]] = []
        self.last_capture = -math.inf

    def setup(self, port: BusPort) -> None:
        self._publish(port, 0.0)

    @staticmethod
    def _intensity(valence: float, arousal: float, pain: float) -> float:
        return max(abs(valence), pain, 0.5 * arousal)

    def step(self, dt: float, port: BusPort) -> None:
        valence = port.read("psyche.affect.valence")
        arousal = port.read("psyche.affect.arousal")
        pain = port.read("intero.pain")
        t = port.time

        # Decay and forget.
        kept: list[tuple[float, float, float, float, float]] = []
        for t_e, v_e, a_e, p_e, s_e in self.episodes:
            s_e -= s_e * dt / self.tau_memory
            if s_e > 0.02:
                kept.append((t_e, v_e, a_e, p_e, s_e))
        self.episodes = kept

        # Capture (throttled, intensity-gated; strength tracks the intensity).
        intensity = self._intensity(valence, arousal, pain)
        if intensity > self.capture_threshold and t - self.last_capture >= self.min_gap:
            self.episodes.append((t, valence, arousal, pain, clamp(intensity)))
            self.last_capture = t
            if len(self.episodes) > self.max_episodes:
                weakest = min(range(len(self.episodes)), key=lambda i: self.episodes[i][4])
                del self.episodes[weakest]

        # Mood-congruent retrieval: how similar the present is to each stored
        # moment, signed by that moment's valence.
        congruence = 0.0
        for _t_e, v_e, a_e, p_e, s_e in self.episodes:
            error = (abs(valence - v_e) + abs(arousal - a_e) + abs(pain - p_e)) / 3.0
            similarity = clamp(1.0 - error / _SIMILARITY_SPAN)
            congruence += s_e * similarity * (1.0 if v_e >= 0.0 else -1.0)
        self._publish(port, clamp(congruence, -1.0, 1.0))

    def _publish(self, port: BusPort, congruence: float) -> None:
        port.write("psyche.memory.episodes", float(len(self.episodes)))
        port.write("psyche.memory.mood_congruence", congruence)
