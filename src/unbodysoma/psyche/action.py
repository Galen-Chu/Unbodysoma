"""Action selection: competing actions, chosen probabilistically.

See docs/adr/0007-probabilistic-action-selection.md.
"""

from __future__ import annotations

import math
import random

from ..core import BusPort, Module, ParamSpec, SignalSpec, relax
from .policy import softmax, switch

IDLE, FLEE, EAT, EXPLORE = "idle", "flee", "eat", "explore"
DRINK, SEEK_WATER, SEEK_SHELTER, SLEEP = "drink", "seek_water", "seek_shelter", "sleep"
ACTIONS = (IDLE, FLEE, EAT, EXPLORE, DRINK, SEEK_WATER, SEEK_SHELTER, SLEEP)
MOVING = (EXPLORE, SEEK_WATER, SEEK_SHELTER)


class ActionSelection(Module):
    """Actions compete on utilities derived from drives and appraisal; one is sampled each decision.

    Utilities (an action is only available when its precondition holds):

    - ``idle``: 0 (the reference)
    - ``flee``: ``k_flee · (threat − flee_threshold)``
    - ``eat`` (food within reach): ``k_eat · (hunger − eat_threshold)``
    - ``explore`` (no food within reach): ``k_explore · (hunger − explore_threshold)`` — searching for food
    - ``drink`` (water within reach): ``k_drink · (thirst − drink_threshold)``
    - ``seek_water`` (no water within reach): ``k_seek_water · (thirst − seek_water_threshold)``
    - ``seek_shelter`` (a shelter is known and the organism is not in it): the larger of
      ``k_shelter · (thermal discomfort − shelter_threshold)`` and ``k_home · (sleepiness − home_onset)``
      — going home when cold, hot or getting sleepy
    - ``sleep``: awake ``k_sleep · (sleepiness − sleep_onset)``, minus ``outside_penalty`` when a
      shelter is known but the organism is not in it; asleep ``min(sleep_cap, sleep_depth ·
      sleepiness)``, so sleep lasts until sleepiness turns negative (pressure below the wake
      threshold); the cap keeps it below what a strong threat is worth, so danger can always
      wake the organism. After a *premature* awakening (sleep left while sleepiness was above
      ``unfinished_sleep``), the asleep utility applies again for ``resume_window``, so a
      disturbed sleeper drops back to sleep. A natural awakening never allows resumption.

    The current action gets a ``stickiness`` bonus (plus ``eat_commitment`` /
    ``drink_commitment`` while eating / drinking), which produces hysteresis
    without hard thresholds. Switching is a continuous-time process
    (``policy.switch``): the agent leaves its action for ``b`` at rate
    ``reconsideration_rate · exp(Δu / 2T)``, so behaviour does not depend on how
    often decisions are evaluated, and the long-run time budget follows
    ``softmax(utilities, temperature)``. ``temperature = 0`` always picks the best
    action (mode collapse, docs/VARIABILITY.md); higher values make behaviour more variable.
    """

    name = "psyche.action"
    rate_hz = 2.0  # decisions per second
    reads = (
        "psyche.appraisal.threat",
        "psyche.drive.hunger",
        "psyche.drive.thirst",
        "psyche.drive.thermal_discomfort",
        "psyche.drive.sleepiness",
        "extero.food",
        "extero.water",
        "extero.in_shelter",
        "extero.shelter_known",
    )
    signal_specs = (
        SignalSpec("motor.exertion", "normalized", 0.0, 1.0, "Physical effort being exerted"),
        SignalSpec("motor.eating", "normalized", 0.0, 1.0, "Eating behaviour (1 = eating)"),
        SignalSpec("motor.drinking", "normalized", 0.0, 1.0, "Drinking behaviour (1 = drinking)"),
        SignalSpec("motor.sleeping", "indicator", 0.0, 1.0, "1 while asleep"),
        *(SignalSpec(f"psyche.action.p_{a}", "probability", 0.0, 1.0, f"Probability of choosing {a}") for a in ACTIONS),
        *(SignalSpec(f"psyche.action.selected_{a}", "indicator", 0.0, 1.0, f"1 while {a} is chosen") for a in ACTIONS),
    )
    writes = tuple(s.key for s in signal_specs)
    params = (
        ParamSpec(
            "temperature", 0.015, "", 0.0, 5.0, "Choice temperature: 0 = always the best action, higher = more random"
        ),
        ParamSpec("stickiness", 0.1, "", 0.0, 2.0, "Utility bonus for continuing the current action"),
        ParamSpec(
            "reconsideration_rate", 1 / 60, "1/s", 0.0, 10.0, "Rate of switching between two equally good actions"
        ),
        ParamSpec("k_flee", 2.5, "", 0.0, 20.0, "Utility gain of fleeing per unit threat above threshold"),
        ParamSpec("flee_threshold", 0.4, "normalized", 0.0, 1.0, "Appraised threat at which fleeing breaks even"),
        ParamSpec("k_eat", 2.0, "", 0.0, 20.0, "Utility gain of eating per unit hunger above threshold"),
        ParamSpec("eat_threshold", 0.35, "normalized", 0.0, 1.0, "Hunger at which starting to eat breaks even"),
        ParamSpec("eat_commitment", 0.4, "", 0.0, 2.0, "Extra bonus for continuing a meal (sets how sated it ends)"),
        ParamSpec("k_explore", 1.5, "", 0.0, 20.0, "Utility gain of searching for food per unit hunger"),
        ParamSpec("explore_threshold", 0.4, "normalized", 0.0, 1.0, "Hunger at which searching for food breaks even"),
        ParamSpec("k_drink", 2.0, "", 0.0, 20.0, "Utility gain of drinking per unit thirst above threshold"),
        ParamSpec("drink_threshold", 0.3, "normalized", 0.0, 1.0, "Thirst at which starting to drink breaks even"),
        ParamSpec(
            "drink_commitment", 0.4, "", 0.0, 2.0, "Extra bonus for continuing to drink (sets how sated it ends)"
        ),
        ParamSpec("k_seek_water", 1.5, "", 0.0, 20.0, "Utility gain of searching for water per unit thirst"),
        ParamSpec(
            "seek_water_threshold", 0.35, "normalized", 0.0, 1.0, "Thirst at which searching for water breaks even"
        ),
        ParamSpec("k_shelter", 1.5, "", 0.0, 20.0, "Utility gain of going to shelter per unit thermal discomfort"),
        ParamSpec(
            "shelter_threshold", 0.3, "normalized", 0.0, 1.0, "Thermal discomfort at which sheltering breaks even"
        ),
        ParamSpec("k_home", 4.0, "", 0.0, 50.0, "Utility gain of going home to sleep per unit sleepiness"),
        ParamSpec("home_onset", 0.8, "normalized", 0.0, 1.0, "Sleepiness at which going home to sleep breaks even"),
        ParamSpec("outside_penalty", 0.5, "", 0.0, 5.0, "Utility lost by falling asleep outside a known shelter"),
        ParamSpec("k_sleep", 8.0, "", 0.0, 50.0, "How sharply sleep wins once sleepiness passes sleep_onset"),
        ParamSpec("sleep_onset", 0.95, "normalized", 0.0, 1.0, "Sleepiness at which falling asleep breaks even"),
        ParamSpec("sleep_depth", 5.0, "", 0.0, 50.0, "Utility of staying asleep per unit sleepiness"),
        ParamSpec("sleep_cap", 1.0, "", 0.0, 10.0, "Maximum utility of staying asleep (below a full threat's)"),
        ParamSpec("resume_window", 1800.0, "s", 0.0, 14400.0, "How long after waking unfinished sleep can resume"),
        ParamSpec("unfinished_sleep", 0.05, "normalized", 0.0, 1.0, "Sleepiness above which an awakening is premature"),
        ParamSpec("food_seen", 0.5, "normalized", 0.0, 1.0, "Sensed food level that counts as food within reach"),
        ParamSpec("water_seen", 0.5, "normalized", 0.0, 1.0, "Sensed water level that counts as water within reach"),
        ParamSpec(
            "shelter_seen", 0.5, "normalized", 0.0, 1.0, "Sensed level that counts as inside / knowing a shelter"
        ),
        ParamSpec("flee_exertion", 0.8, "normalized", 0.0, 1.0, "Exertion while fleeing"),
        ParamSpec("explore_exertion", 0.3, "normalized", 0.0, 1.0, "Exertion while searching or travelling"),
        ParamSpec("tau", 1.0, "s", 0.01, 60.0, "Time constant of exertion changes"),
        ParamSpec("seed", 4, "", 0, math.inf, "Random seed of the choices", source="run setting"),
    )
    state_fields = ("action", "exertion", "awake_for", "interrupted", "_rng")

    def __init__(
        self,
        temperature: float = 0.015,
        stickiness: float = 0.1,
        reconsideration_rate: float = 1 / 60,
        k_flee: float = 2.5,
        flee_threshold: float = 0.4,
        k_eat: float = 2.0,
        eat_threshold: float = 0.35,
        eat_commitment: float = 0.4,
        k_explore: float = 1.5,
        explore_threshold: float = 0.4,
        k_drink: float = 2.0,
        drink_threshold: float = 0.3,
        drink_commitment: float = 0.4,
        k_seek_water: float = 1.5,
        seek_water_threshold: float = 0.35,
        k_shelter: float = 1.5,
        shelter_threshold: float = 0.3,
        k_home: float = 4.0,
        home_onset: float = 0.8,
        outside_penalty: float = 0.5,
        k_sleep: float = 8.0,
        sleep_onset: float = 0.95,
        sleep_depth: float = 5.0,
        sleep_cap: float = 1.0,
        resume_window: float = 1800.0,
        unfinished_sleep: float = 0.05,
        food_seen: float = 0.5,
        water_seen: float = 0.5,
        shelter_seen: float = 0.5,
        flee_exertion: float = 0.8,
        explore_exertion: float = 0.3,
        tau: float = 1.0,
        seed: int = 4,
    ) -> None:
        self.temperature = temperature
        self.stickiness = stickiness
        self.reconsideration_rate = reconsideration_rate
        self.k_flee = k_flee
        self.flee_threshold = flee_threshold
        self.k_eat = k_eat
        self.eat_threshold = eat_threshold
        self.eat_commitment = eat_commitment
        self.k_explore = k_explore
        self.explore_threshold = explore_threshold
        self.k_drink = k_drink
        self.drink_threshold = drink_threshold
        self.drink_commitment = drink_commitment
        self.k_seek_water = k_seek_water
        self.seek_water_threshold = seek_water_threshold
        self.k_shelter = k_shelter
        self.shelter_threshold = shelter_threshold
        self.k_home = k_home
        self.home_onset = home_onset
        self.outside_penalty = outside_penalty
        self.k_sleep = k_sleep
        self.sleep_onset = sleep_onset
        self.sleep_depth = sleep_depth
        self.sleep_cap = sleep_cap
        self.resume_window = resume_window
        self.unfinished_sleep = unfinished_sleep
        self.food_seen = food_seen
        self.water_seen = water_seen
        self.shelter_seen = shelter_seen
        self.flee_exertion = flee_exertion
        self.explore_exertion = explore_exertion
        self.tau = tau
        self.seed = seed
        self._rng = random.Random(seed)
        self.action = IDLE
        self.exertion = 0.0
        self.awake_for = math.inf  # seconds since sleep last ended
        self.interrupted = False  # did that sleep end prematurely?

    def utilities(
        self,
        threat: float,
        hunger: float,
        sleepiness: float,
        food_near: bool,
        thirst: float = 0.0,
        discomfort: float = 0.0,
        water_near: bool = False,
        in_shelter: bool = False,
        shelter_known: bool = False,
    ) -> dict[str, float]:
        """Utility of every currently available action, including the bonus for the current one."""
        u = {IDLE: 0.0, FLEE: self.k_flee * (threat - self.flee_threshold)}
        if food_near:
            u[EAT] = self.k_eat * (hunger - self.eat_threshold)
        else:
            u[EXPLORE] = self.k_explore * (hunger - self.explore_threshold)
        if water_near:
            u[DRINK] = self.k_drink * (thirst - self.drink_threshold)
        else:
            u[SEEK_WATER] = self.k_seek_water * (thirst - self.seek_water_threshold)
        homeless = shelter_known and not in_shelter
        if homeless:
            u[SEEK_SHELTER] = max(
                self.k_shelter * (discomfort - self.shelter_threshold),
                self.k_home * (sleepiness - self.home_onset),
            )
        resuming = self.interrupted and self.awake_for < self.resume_window and sleepiness > 0.0
        if self.action == SLEEP or resuming:
            u[SLEEP] = min(self.sleep_cap, self.sleep_depth * sleepiness)  # staying asleep; no extra stickiness
        else:
            u[SLEEP] = self.k_sleep * (sleepiness - self.sleep_onset) - (self.outside_penalty if homeless else 0.0)
        if self.action in u and self.action != SLEEP:
            commitment = {EAT: self.eat_commitment, DRINK: self.drink_commitment}.get(self.action, 0.0)
            u[self.action] += self.stickiness + commitment
        return u

    def setup(self, port: BusPort) -> None:
        self._publish(port, {IDLE: 1.0})

    def step(self, dt: float, port: BusPort) -> None:
        utilities = self.utilities(
            threat=port.read("psyche.appraisal.threat"),
            hunger=port.read("psyche.drive.hunger"),
            sleepiness=port.read("psyche.drive.sleepiness"),
            food_near=port.read("extero.food") > self.food_seen,
            thirst=port.read("psyche.drive.thirst"),
            discomfort=port.read("psyche.drive.thermal_discomfort"),
            water_near=port.read("extero.water") > self.water_seen,
            in_shelter=port.read("extero.in_shelter") > self.shelter_seen,
            shelter_known=port.read("extero.shelter_known") > self.shelter_seen,
        )
        probabilities = softmax(utilities, self.temperature)
        previous = self.action
        self.action = switch(self.action, utilities, self.temperature, self.reconsideration_rate, dt, self._rng)
        if previous == SLEEP and self.action != SLEEP:
            self.interrupted = port.read("psyche.drive.sleepiness") > self.unfinished_sleep
        self.awake_for = 0.0 if self.action == SLEEP else self.awake_for + dt
        target = self.flee_exertion if self.action == FLEE else self.explore_exertion if self.action in MOVING else 0.0
        self.exertion = relax(self.exertion, target, dt, self.tau)
        self._publish(port, probabilities)

    def _publish(self, port: BusPort, probabilities: dict[str, float]) -> None:
        port.write("motor.exertion", self.exertion)
        port.write("motor.eating", 1.0 if self.action == EAT else 0.0)
        port.write("motor.drinking", 1.0 if self.action == DRINK else 0.0)
        port.write("motor.sleeping", 1.0 if self.action == SLEEP else 0.0)
        for a in ACTIONS:
            port.write(f"psyche.action.p_{a}", probabilities.get(a, 0.0))
            port.write(f"psyche.action.selected_{a}", 1.0 if self.action == a else 0.0)
