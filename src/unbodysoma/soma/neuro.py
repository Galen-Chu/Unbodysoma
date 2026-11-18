"""Neuromodulation: the three-amine axes — dopamine, serotonin, norepinephrine.

The minimal Phase 3 substrate on which the Phase 4 learner will act. Each axis
maps onto an existing loop rather than adding a new one:

- **dopamine** — phasic burst when the total felt homeostatic error falls
  faster than its own slow baseline: reward as *relief*, sized by how much
  error was actually removed (a hungry meal is a burst; food when sated barely
  moves the error and barely fires). This is the "homeostatic error reduction"
  reward of BACKLOG §5, made a signal; Schultz et al. (1997) frame the phasic
  response as a reward-prediction error, which the Phase 4 model will compute
  explicitly (negative dips included).
- **serotonin** — a slow tone dragged down by sustained pain and sustained
  deficit: chronic bad states read as low mood (Dayan & Huys, 2009).
- **norepinephrine** — fast vigilance from threat, pain and cardiac arousal
  (Aston-Jones & Cohen, 2005); appraisal reads it as the amplifier of
  perceived threat, so an already-urgent organism over-reads mild cues
  (hyper-vigilance), and a hurt one jumps at shadows.

Equations and anchors: docs/SOMA.md §2.10; acceptance: tests/test_neuro.py.
"""

from __future__ import annotations

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp, relax


class Neuromodulation(Module):
    """Reward (dopamine), mood tone (serotonin) and vigilance (norepinephrine)."""

    name = "soma.neuro"
    rate_hz = 10.0
    reads = (
        "intero.energy_deficit",
        "intero.water_deficit",
        "intero.thermal",
        "intero.sleep_pressure",
        "intero.pain",
        "intero.cardiac_arousal",
        "psyche.appraisal.threat",
    )
    signal_specs = (
        SignalSpec("neuro.dopamine", "normalized", 0.0, 1.0, "Dopamine: phasic reward from homeostatic relief"),
        SignalSpec("neuro.serotonin", "normalized", 0.0, 1.0, "Serotonin: slow mood tone"),
        SignalSpec("neuro.norepinephrine", "normalized", 0.0, 1.0, "Norepinephrine: vigilance"),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec("w_energy", 0.4, "", 0.0, 1.0, "Weight of felt energy deficit in the total homeostatic error"),
        ParamSpec("w_water", 0.3, "", 0.0, 1.0, "Weight of felt water deficit in the total homeostatic error"),
        ParamSpec("w_thermal", 0.15, "", 0.0, 1.0, "Weight of felt thermal discomfort (cold or hot) in the error"),
        ParamSpec("w_sleep", 0.15, "", 0.0, 1.0, "Weight of felt sleep pressure in the error"),
        ParamSpec(
            "tau_error_fast",
            10.0,
            "s",
            0.5,
            120.0,
            "Low-pass of the error for the relief estimate",
            source="calibrated: seconds-scale, so felt noise does not read as relief",
        ),
        ParamSpec(
            "tau_error_slow",
            300.0,
            "s",
            30.0,
            3600.0,
            "Baseline the relief is measured against (the slow trailing average)",
            source="calibrated: relief during a meal outlasts the bites but not the afternoon",
        ),
        ParamSpec(
            "dopamine_baseline",
            0.5,
            "normalized",
            0.0,
            1.0,
            "Tonic dopamine with no relief and no loss",
        ),
        ParamSpec(
            "dopamine_gain",
            10.0,
            "",
            0.0,
            50.0,
            "Dopamine rise per unit relief (error recently removed)",
            source="calibrated: a hungry meal peaks the axis, a sated one barely lifts it",
        ),
        ParamSpec("tau_dopamine", 1.5, "s", 0.05, 60.0, "Time constant of the phasic dopamine response"),
        ParamSpec("serotonin_baseline", 0.5, "normalized", 0.0, 1.0, "Serotonin tone with no pain and no deficit"),
        ParamSpec("w_pain_serotonin", 0.8, "", 0.0, 2.0, "Serotonin lost per unit sustained felt pain"),
        ParamSpec("w_deficit_serotonin", 0.4, "", 0.0, 2.0, "Serotonin lost per unit sustained homeostatic error"),
        ParamSpec(
            "tau_serotonin",
            600.0,
            "s",
            10.0,
            86400.0,
            "Time constant of the serotonergic tone",
            source="calibrated: minutes-to-hours mood dynamics, slower than any single need",
        ),
        ParamSpec(
            "w_cardiac_norepinephrine",
            0.6,
            "",
            0.0,
            1.0,
            "Share of felt cardiac arousal that counts as vigilance",
        ),
        ParamSpec("tau_norepinephrine", 3.0, "s", 0.1, 120.0, "Time constant of the vigilance response"),
    )
    state_fields = ("error_fast", "error_slow", "dopamine", "serotonin", "norepinephrine", "warmed")

    def __init__(
        self,
        w_energy: float = 0.4,
        w_water: float = 0.3,
        w_thermal: float = 0.15,
        w_sleep: float = 0.15,
        tau_error_fast: float = 10.0,
        tau_error_slow: float = 300.0,
        dopamine_baseline: float = 0.5,
        dopamine_gain: float = 10.0,
        tau_dopamine: float = 1.5,
        serotonin_baseline: float = 0.5,
        w_pain_serotonin: float = 0.8,
        w_deficit_serotonin: float = 0.4,
        tau_serotonin: float = 600.0,
        w_cardiac_norepinephrine: float = 0.6,
        tau_norepinephrine: float = 3.0,
    ) -> None:
        self.w_energy = w_energy
        self.w_water = w_water
        self.w_thermal = w_thermal
        self.w_sleep = w_sleep
        self.tau_error_fast = tau_error_fast
        self.tau_error_slow = tau_error_slow
        self.dopamine_baseline = dopamine_baseline
        self.dopamine_gain = dopamine_gain
        self.tau_dopamine = tau_dopamine
        self.serotonin_baseline = serotonin_baseline
        self.w_pain_serotonin = w_pain_serotonin
        self.w_deficit_serotonin = w_deficit_serotonin
        self.tau_serotonin = tau_serotonin
        self.w_cardiac_norepinephrine = w_cardiac_norepinephrine
        self.tau_norepinephrine = tau_norepinephrine
        self.error_fast = 0.0
        self.error_slow = 0.0
        self.warmed = False  # until the first step, the error filters hold the current error
        self.dopamine = dopamine_baseline
        self.serotonin = serotonin_baseline
        self.norepinephrine = 0.0

    def setup(self, port: BusPort) -> None:
        self._publish(port)

    def step(self, dt: float, port: BusPort) -> None:
        error = (
            self.w_energy * port.read("intero.energy_deficit")
            + self.w_water * port.read("intero.water_deficit")
            + self.w_thermal * abs(port.read("intero.thermal"))
            + self.w_sleep * port.read("intero.sleep_pressure")
        )
        if not self.warmed:
            # First step: seed both filters at the current error, so no startup
            # transient reads as relief (or as sudden deficit).
            self.error_fast = error
            self.error_slow = error
            self.warmed = True
        else:
            self.error_fast = relax(self.error_fast, error, dt, self.tau_error_fast)
            self.error_slow = relax(self.error_slow, error, dt, self.tau_error_slow)
        # Relief: the error is now below where it has been settling — i.e. the
        # organism is actively recovering, not just briefly un-noisy.
        relief = clamp(self.error_slow - self.error_fast)
        self.dopamine = relax(
            self.dopamine, clamp(self.dopamine_baseline + self.dopamine_gain * relief), dt, self.tau_dopamine
        )
        tone_target = clamp(
            self.serotonin_baseline
            - self.w_pain_serotonin * port.read("intero.pain")
            - self.w_deficit_serotonin * self.error_slow
        )
        self.serotonin = relax(self.serotonin, tone_target, dt, self.tau_serotonin)
        vigilance = max(
            port.read("psyche.appraisal.threat"),
            port.read("intero.pain"),
            self.w_cardiac_norepinephrine * port.read("intero.cardiac_arousal"),
        )
        self.norepinephrine = relax(self.norepinephrine, clamp(vigilance), dt, self.tau_norepinephrine)
        self._publish(port)

    def _publish(self, port: BusPort) -> None:
        port.write("neuro.dopamine", self.dopamine)
        port.write("neuro.serotonin", self.serotonin)
        port.write("neuro.norepinephrine", self.norepinephrine)
