"""Energy metabolism — L1 glucose-insulin core with an integrated energy store (docs/SOMA.md §2.3).

Structure follows the minimal model of Bergman, Ider, Bowden & Cobelli (1979)
with a two-compartment oral input from the Dalla Man, Rizza & Cobelli (2006)
meal-model family (including its incretin idea: eating itself turns insulin
secretion on within minutes, before glucose appears). Acceptance bounds for
the oral-glucose response follow ADA (2021) normal ranges
(tests/test_metabolism_l1.py).

Since 2026-11-18 the energy reserve is the *net glucose balance* rather than
a directly-filled tank: eating only delivers oral glucose to the gut; the
insulin-mediated share of glucose disposal (X · G) is stored in the reserve
(glycogen), and the reserve pays the metabolic drain that defends fasting
glucose. Interoception reads the result the other way round — satiety from
insulin, acute hunger from a glucose dip (see interface/interoception.py).
"""

from __future__ import annotations

from ..core import BusPort, Module, ParamSpec, SignalSpec, clamp

_SECONDS_PER_HOUR = 3600.0


class Metabolism(Module):
    """A minimal-model glucose-insulin core (L1) with an integrated store (L1-lite).

    Store: no direct fill from food. Storage = a share of the insulin-mediated
    glucose disposal (X · G, in mass units); drain = the Phase 1 metabolic
    cost (basal, scaled by exertion, shivering and sleep) — the net cost of
    defending fasting glucose. Starved of reserve, the defended fasting level
    collapses (health rule ``glucose_abnormal``), as before.

    Glucose-insulin: eating delivers oral glucose to a two-compartment gut
    and turns on insulin secretion (incretin phase); appearance in plasma
    drives glucose, insulin secretion above a threshold builds insulin,
    insulin acts on glucose disposal through the delayed action variable X,
    and adrenaline adds hepatic output (glycogenolysis).
    """

    name = "soma.metabolism"
    rate_hz = 1.0
    reads = (
        "motor.exertion",
        "motor.sleeping",
        "world.food_intake",
        "soma.endocrine.adrenaline",
        "soma.thermo.shivering",
    )
    signal_specs = (
        SignalSpec("soma.metabolism.energy_reserve", "fraction", 0.0, 1.0, "Net glucose balance (1 = full store)"),
        SignalSpec("soma.metabolism.glucose", "mg/dL", 0.0, 600.0, "Blood glucose"),
        SignalSpec("soma.metabolism.insulin", "μU/mL", 0.0, 400.0, "Plasma insulin"),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec("initial_reserve", 0.8, "fraction", 0.0, 1.0, "Energy reserve at t = 0"),
        ParamSpec(
            "hours_to_empty_at_rest",
            48.0,
            "h",
            1.0,
            500.0,
            "Time for a full reserve to drain at rest",
            source="calibrated: about three meals a day",
        ),
        ParamSpec("exertion_cost", 4.0, "", 0.0, 20.0, "Extra drain per unit exertion, relative to basal"),
        ParamSpec("shiver_cost", 3.0, "", 0.0, 20.0, "Extra drain per unit shivering, relative to basal"),
        ParamSpec("sleep_metabolic_factor", 0.9, "", 0.5, 1.0, "Basal drain during sleep, relative to awake rest"),
        ParamSpec(
            "storage_share",
            1.5,
            "",
            0.0,
            3.0,
            "Share of the positive net glucose flux stored in the reserve",
            source="calibrated: one typical meal refills about what it did in Phase 1",
        ),
        ParamSpec(
            "incretin_gain",
            6700.0,
            "μU/mL per fraction",
            0.0,
            50000.0,
            "Insulin secreted per unit of food intake while eating (the incretin/cephalic phase)",
            source="calibrated: insulin rises ≈ 2 μU/mL per minute of eating, satiating within ~10 min",
        ),
        ParamSpec(
            "glucose_setpoint",
            90.0,
            "mg/dL",
            60.0,
            130.0,
            "Defended fasting glucose",
            source="ADA (2021): normal fasting 70–99 mg/dL; 90 mid-range",
        ),
        ParamSpec(
            "glucose_effectiveness",
            0.026,
            "1/min",
            0.002,
            0.1,
            "Insulin-independent glucose disposal per unit glucose (S_G)",
            source="Bergman et al. (1979): typical value",
        ),
        ParamSpec(
            "insulin_action_rate",
            0.05,
            "1/min",
            0.005,
            0.5,
            "Rate of insulin-action dynamics (p2)",
            source="Bergman et al. (1979): typical value",
        ),
        ParamSpec(
            "insulin_action_gain",
            5e-5,
            "1/min per μU/mL",
            1e-6,
            1e-3,
            "Insulin action gained per unit plasma insulin above basal (p3)",
            source="calibrated: post-meal X ≈ 0.04 1/min at ΔI ≈ 40 μU/mL",
        ),
        ParamSpec(
            "insulin_basal",
            8.0,
            "μU/mL",
            0.0,
            60.0,
            "Fasting plasma insulin",
            source="typical fasting 5–15 μU/mL",
        ),
        ParamSpec(
            "insulin_secretion_gain",
            0.13,
            "μU/mL/min per mg/dL",
            0.0,
            2.0,
            "Insulin secreted per mg/dL of glucose above the threshold",
            source="calibrated: post-meal insulin peaks 50–80 μU/mL",
        ),
        ParamSpec(
            "insulin_threshold",
            100.0,
            "mg/dL",
            60.0,
            180.0,
            "Glucose above which insulin secretion turns on",
            source="calibrated: fasting + 10 mg/dL",
        ),
        ParamSpec(
            "insulin_tau",
            420.0,
            "s",
            60.0,
            3600.0,
            "Time constant of insulin clearance",
            source="insulin half-life ≈ 5 min (τ = 7 min)",
        ),
        ParamSpec(
            "glucose_volume",
            112.0,
            "dL",
            20.0,
            400.0,
            "Glucose distribution volume",
            source="1.6 dL/kg × 70 kg reference body",
        ),
        ParamSpec(
            "gut_glucose_per_reserve",
            2.3e5,
            "mg",
            1e4,
            3e6,
            "Oral glucose mass per unit of reserve refilled",
            source="calibrated: a full meal's refill ≈ 55–60 g carbohydrate",
        ),
        ParamSpec(
            "gut_tau",
            2100.0,
            "s",
            60.0,
            14400.0,
            "Time constant of each gut compartment (two in series)",
            source="Dalla Man et al. (2006) family: appearance peaks ≈ 40 min",
        ),
        ParamSpec(
            "adrenaline_glucose_production",
            2.5,
            "mg/dL/min",
            0.0,
            20.0,
            "Hepatic glucose output per unit adrenaline (glycogenolysis)",
            source="calibrated: ≈ +30 mg/dL sustained, as in the L0 model",
        ),
        ParamSpec(
            "glucose_defense_reserve",
            0.1,
            "fraction",
            0.01,
            1.0,
            "Reserve below which glucose can no longer be defended",
        ),
    )
    state_fields = ("reserve", "glucose", "insulin", "x_action", "gut1", "gut2")

    def __init__(
        self,
        initial_reserve: float = 0.8,
        hours_to_empty_at_rest: float = 48.0,
        exertion_cost: float = 4.0,
        shiver_cost: float = 3.0,
        sleep_metabolic_factor: float = 0.9,
        storage_share: float = 1.5,
        incretin_gain: float = 6700.0,
        glucose_setpoint: float = 90.0,
        glucose_effectiveness: float = 0.026,
        insulin_action_rate: float = 0.05,
        insulin_action_gain: float = 5e-5,
        insulin_basal: float = 8.0,
        insulin_secretion_gain: float = 0.13,
        insulin_threshold: float = 100.0,
        insulin_tau: float = 420.0,
        glucose_volume: float = 112.0,
        gut_glucose_per_reserve: float = 2.3e5,
        gut_tau: float = 2100.0,
        adrenaline_glucose_production: float = 2.5,
        glucose_defense_reserve: float = 0.1,
    ) -> None:
        self.initial_reserve = initial_reserve
        self.hours_to_empty_at_rest = hours_to_empty_at_rest
        self.exertion_cost = exertion_cost
        self.shiver_cost = shiver_cost
        self.sleep_metabolic_factor = sleep_metabolic_factor
        self.storage_share = storage_share
        self.incretin_gain = incretin_gain
        self.glucose_setpoint = glucose_setpoint
        self.glucose_effectiveness = glucose_effectiveness
        self.insulin_action_rate = insulin_action_rate
        self.insulin_action_gain = insulin_action_gain
        self.insulin_basal = insulin_basal
        self.insulin_secretion_gain = insulin_secretion_gain
        self.insulin_threshold = insulin_threshold
        self.insulin_tau = insulin_tau
        self.glucose_volume = glucose_volume
        self.gut_glucose_per_reserve = gut_glucose_per_reserve
        self.gut_tau = gut_tau
        self.adrenaline_glucose_production = adrenaline_glucose_production
        self.glucose_defense_reserve = glucose_defense_reserve
        self.reserve = initial_reserve
        self.glucose = glucose_setpoint
        self.insulin = insulin_basal
        self.x_action = 0.0
        self.gut1 = 0.0
        self.gut2 = 0.0

    def setup(self, port: BusPort) -> None:
        port.write("soma.metabolism.energy_reserve", self.reserve)
        port.write("soma.metabolism.glucose", self.glucose)
        port.write("soma.metabolism.insulin", self.insulin)

    def step(self, dt: float, port: BusPort) -> None:
        basal_drain = 1.0 / (self.hours_to_empty_at_rest * _SECONDS_PER_HOUR)
        if port.read("motor.sleeping") > 0.5:
            basal_drain *= self.sleep_metabolic_factor
        drain = basal_drain * (
            1.0
            + self.exertion_cost * port.read("motor.exertion")
            + self.shiver_cost * port.read("soma.thermo.shivering")
        )
        food = port.read("world.food_intake")

        # Oral input: eating deposits glucose mass in the first gut compartment;
        # two compartments in series give the meal-like appearance curve.
        self.gut1 += food * self.gut_glucose_per_reserve * dt
        flow1 = self.gut1 / self.gut_tau
        self.gut1 -= flow1 * dt
        self.gut2 += flow1 * dt
        flow2 = self.gut2 / self.gut_tau
        self.gut2 -= flow2 * dt
        appearance = flow2 / self.glucose_volume * 60.0  # mg/dL per min into plasma

        adrenaline = port.read("soma.endocrine.adrenaline")
        m = dt / 60.0  # minimal-model rates are per minute
        # Incretin/cephalic phase: eating itself drives insulin within minutes,
        # ahead of gut absorption (Dalla Man et al. 2006 family).
        secretion = (
            self.insulin_secretion_gain * max(0.0, self.glucose - self.insulin_threshold) + self.incretin_gain * food
        )
        self.insulin = max(
            0.0, self.insulin + (secretion - (self.insulin - self.insulin_basal) * 60.0 / self.insulin_tau) * m
        )
        self.x_action = max(
            0.0,
            self.x_action
            + (
                -self.insulin_action_rate * self.x_action
                + self.insulin_action_gain * (self.insulin - self.insulin_basal)
            )
            * m,
        )
        defended = self.glucose_setpoint * min(1.0, self.reserve / self.glucose_defense_reserve)
        disposal = self.glucose_effectiveness + self.x_action
        production = self.glucose_effectiveness * defended + self.adrenaline_glucose_production * adrenaline
        d_glucose = (-disposal * self.glucose + production + appearance) * m
        self.glucose = clamp(self.glucose + d_glucose, 0.0, 600.0)

        # The reserve is the net glucose balance: whatever total disposal
        # exceeds total production (mg/dL per min, in mass units) flows into
        # the store; the metabolic drain and adrenaline's hepatic output
        # (glycogenolysis) are its costs.
        net_flux = max(0.0, disposal * self.glucose - production)
        storage = self.storage_share * net_flux * self.glucose_volume / 60.0
        adrenaline_cost = self.adrenaline_glucose_production * adrenaline * self.glucose_volume / 60.0
        self.reserve = clamp(self.reserve + ((storage - adrenaline_cost) / self.gut_glucose_per_reserve - drain) * dt)

        port.write("soma.metabolism.energy_reserve", self.reserve)
        port.write("soma.metabolism.glucose", self.glucose)
        port.write("soma.metabolism.insulin", self.insulin)
