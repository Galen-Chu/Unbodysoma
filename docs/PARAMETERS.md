# 參數 Parameters

> 本文件由 `python -m unbodysoma.catalog` 從模組的 `ParamSpec` 自動產生，**請勿手動編輯**。
> 預設值目前都是 L0 玩具值；個體差異與族群分布的規劃見 [VARIABILITY.md](VARIABILITY.md)。

## `world.food`

`unbodysoma.world.food.FoodSource`

| 參數 | 預設值 | 單位 | 有效範圍 | 說明 | 來源 |
|---|---|---|---|---|---|
| `intake_rate` | 0.0003 | fraction/s | [0, 0.01] | Reserve refilled per second of eating (≈ 0.3 per 15 min) | L0 toy value |

## `world.water`

`unbodysoma.world.water.WaterIntake`

| 參數 | 預設值 | 單位 | 有效範圍 | 說明 | 來源 |
|---|---|---|---|---|---|
| `intake_rate` | 0.002 | fraction/s | [0, 0.1] | Hydration restored per second of drinking (≈ 0.24 per 2 min) | L0 toy value |

## `interface.exteroception`

`unbodysoma.interface.exteroception.Exteroception`

| 參數 | 預設值 | 單位 | 有效範圍 | 說明 | 來源 |
|---|---|---|---|---|---|
| `noise` | 0.02 | normalized | [0, 1] | SD of sensory noise | L0 toy value |
| `seed` | 0 | — | [0, ∞] | Random seed of the noise | run setting |

## `interface.interoception`

`unbodysoma.interface.interoception.Interoception`

| 參數 | 預設值 | 單位 | 有效範圍 | 說明 | 來源 |
|---|---|---|---|---|---|
| `resting_bpm` | 60 | bpm | [30, 120] | Heart rate felt as zero activation | L0 toy value |
| `bpm_span` | 100 | bpm | [10, 250] | Heart-rate rise felt as full activation | L0 toy value |
| `comfortable_core` | 37 | °C | [35, 39] | Core temperature felt as neither cold nor hot | L0 toy value |
| `thermal_span` | 2 | °C | [0.1, 10] | Core deviation felt as extreme cold or heat | L0 toy value |
| `noise` | 0.01 | normalized | [0, 1] | SD of interoceptive noise (inverse of interoceptive accuracy) | L0 toy value |
| `seed` | 1 | — | [0, ∞] | Random seed of the noise | run setting |

## `soma.circadian`

`unbodysoma.soma.circadian.Circadian`

| 參數 | 預設值 | 單位 | 有效範圍 | 說明 | 來源 |
|---|---|---|---|---|---|
| `period_h` | 24 | h | [20, 28] | Period of the rhythm (intrinsic human period averages ≈ 24.2 h) | entrained 24 h; Czeisler et al. (1999) for the intrinsic period |
| `peak_hour` | 19 | h | [0, 24] | Clock hour of the circadian alerting peak | calibrated |
| `start_hour` | 8 | h | [0, 24] | Clock time at t = 0 | run setting |

## `soma.sleep`

`unbodysoma.soma.sleep.SleepHomeostat`

| 參數 | 預設值 | 單位 | 有效範圍 | 說明 | 來源 |
|---|---|---|---|---|---|
| `tau_wake_h` | 18.2 | h | [1, 100] | Time constant of sleep-pressure build-up | Daan, Beersma & Borbély (1984) |
| `tau_sleep_h` | 4.2 | h | [0.5, 24] | Time constant of sleep-pressure decline | Daan, Beersma & Borbély (1984) |
| `initial_pressure` | 0.14 | normalized | [0, 1] | Sleep pressure at t = 0 (about one hour after waking) | calibrated |

## `soma.cardio`

`unbodysoma.soma.cardio.Cardio`

| 參數 | 預設值 | 單位 | 有效範圍 | 說明 | 來源 |
|---|---|---|---|---|---|
| `resting_bpm` | 65 | bpm | [30, 120] | Resting heart rate | L0 toy value |
| `max_bpm` | 190 | bpm | [100, 230] | Ceiling of the heart-rate response | L0 toy value |
| `k_adrenaline` | 40 | bpm | [0, 150] | Heart-rate gain per unit adrenaline | L0 toy value |
| `k_exertion` | 70 | bpm | [0, 150] | Heart-rate gain per unit exertion | L0 toy value |
| `tau` | 5 | s | [0.1, 120] | Time constant of heart-rate changes | L0 toy value |
| `sleep_bpm_drop` | 8 | bpm | [0, 30] | Fall of the resting heart rate during sleep | L0 toy value |
| `rsa_amplitude` | 3 | bpm | [0, 20] | Respiratory sinus arrhythmia amplitude at rest | L0 toy value |
| `respiration_hz` | 0.25 | Hz | [0.05, 1] | Breathing rate that paces the RSA | L0 toy value |
| `lf_sigma` | 2 | bpm | [0, 20] | SD of slow heart-rate fluctuation at rest | L0 toy value |
| `lf_tau` | 10 | s | [0.5, 300] | Correlation time of slow heart-rate fluctuation | L0 toy value |
| `hrv_suppression` | 0.8 | — | [0, 1] | Share of HRV removed at full adrenaline | L0 toy value |
| `seed` | 2 | — | [0, ∞] | Random seed of the fluctuation | run setting |

## `soma.endocrine`

`unbodysoma.soma.endocrine.Endocrine`

| 參數 | 預設值 | 單位 | 有效範圍 | 說明 | 來源 |
|---|---|---|---|---|---|
| `cortisol_baseline` | 0.2 | normalized | [0, 1] | Cortisol level without threat | L0 toy value |
| `cortisol_circadian_amplitude` | 0.1 | normalized | [0, 0.2] | Daily swing of the cortisol baseline | L0 toy value |
| `cortisol_peak_hour` | 8 | h | [0, 24] | Clock hour of the daily cortisol peak | L0 toy value |
| `cortisol_gain` | 0.75 | — | [0, 1] | Share of the headroom above baseline reached at full threat | L0 toy value |
| `adrenaline_tau_rise` | 3 | s | [0.1, 60] | Time constant of adrenaline release | L0 toy value |
| `adrenaline_tau_fall` | 40 | s | [1, 600] | Time constant of adrenaline clearance | L0 toy value |
| `cortisol_tau_rise` | 300 | s | [10, 7200] | Time constant of cortisol release | L0 toy value |
| `cortisol_tau_fall` | 1800 | s | [60, 36000] | Time constant of cortisol clearance | L0 toy value |

## `soma.metabolism`

`unbodysoma.soma.metabolism.Metabolism`

| 參數 | 預設值 | 單位 | 有效範圍 | 說明 | 來源 |
|---|---|---|---|---|---|
| `initial_reserve` | 0.8 | fraction | [0, 1] | Energy reserve at t = 0 | L0 toy value |
| `hours_to_empty_at_rest` | 48 | h | [1, 500] | Time for a full reserve to drain at rest | calibrated: about three meals a day |
| `exertion_cost` | 4 | — | [0, 20] | Extra drain per unit exertion, relative to basal | L0 toy value |
| `shiver_cost` | 3 | — | [0, 20] | Extra drain per unit shivering, relative to basal | L0 toy value |
| `sleep_metabolic_factor` | 0.9 | — | [0.5, 1] | Basal drain during sleep, relative to awake rest | L0 toy value |
| `glucose_setpoint` | 90 | mg/dL | [60, 130] | Defended fasting glucose | L0 toy value |
| `k_adrenaline` | 40 | mg/dL | [0, 150] | Glucose mobilized per unit adrenaline | L0 toy value |
| `glucose_tau` | 120 | s | [1, 3600] | Time constant of glucose regulation | L0 toy value |
| `glucose_defense_reserve` | 0.1 | fraction | [0.01, 1] | Reserve below which glucose can no longer be defended | L0 toy value |

## `soma.fluid`

`unbodysoma.soma.fluid.FluidBalance`

| 參數 | 預設值 | 單位 | 有效範圍 | 說明 | 來源 |
|---|---|---|---|---|---|
| `initial_hydration` | 0.9 | fraction | [0, 1] | Hydration at t = 0 | L0 toy value |
| `hours_to_empty_at_rest` | 48 | h | [1, 500] | Time for a full reserve to be lost at rest without drinking | calibrated: a few drinks a day |
| `exertion_cost` | 2 | — | [0, 20] | Extra loss per unit exertion, relative to basal | L0 toy value |
| `sweat_cost` | 6 | — | [0, 50] | Extra loss per unit sweating, relative to basal | L0 toy value |
| `sleep_loss_factor` | 0.8 | — | [0.3, 1] | Basal loss during sleep, relative to awake rest | L0 toy value |
| `osmolality_at_full` | 285 | mOsm/kg | [250, 320] | Osmolality when fully hydrated | L0 mapping onto the normal range |
| `osmolality_span` | 40 | mOsm/kg | [1, 100] | Osmolality rise from full to empty reserve | L0 mapping onto the normal range |

## `soma.thermo`

`unbodysoma.soma.thermo.Thermoregulation`

| 參數 | 預設值 | 單位 | 有效範圍 | 說明 | 來源 |
|---|---|---|---|---|---|
| `setpoint` | 37 | °C | [35, 39] | Defended core temperature | L0 toy value |
| `initial_temperature` | 37 | °C | [30, 45] | Core temperature at t = 0 | L0 toy value |
| `basal_heat` | 2.25 | °C/h | [0, 50] | Warming rate from resting metabolism | calibrated: 37 °C at 22 °C |
| `exertion_heat` | 2 | — | [0, 20] | Extra heat per unit exertion, relative to basal | L0 toy value |
| `conductance` | 0.15 | 1/h | [0.01, 10] | Heat loss per °C of core-to-ambient difference | L0 toy value |
| `shiver_heat` | 4 | °C/h | [0, 50] | Warming rate at full shivering | L0 toy value |
| `sweat_cooling` | 8 | °C/h | [0, 100] | Cooling rate at full sweating | L0 toy value |
| `shiver_offset` | 0.3 | °C | [0, 3] | How far below the setpoint shivering starts | L0 toy value |
| `sweat_offset` | 0.2 | °C | [0, 3] | How far above the setpoint sweating starts | L0 toy value |
| `response_span` | 0.8 | °C | [0.05, 5] | Deviation beyond the onset at which a response is maximal | L0 toy value |

## `psyche.appraisal`

`unbodysoma.psyche.appraisal.Appraisal`

| 參數 | 預設值 | 單位 | 有效範圍 | 說明 | 來源 |
|---|---|---|---|---|---|
| `arousal_bias` | 0.5 | — | [0, 5] | How much arousal amplifies perceived threat (trait anxiety) | L0 toy value |
| `tau` | 0.5 | s | [0.01, 60] | Time constant of appraisal | L0 toy value |

## `psyche.affect`

`unbodysoma.psyche.affect.Affect`

| 參數 | 預設值 | 單位 | 有效範圍 | 說明 | 來源 |
|---|---|---|---|---|---|
| `baseline_valence` | 0.1 | normalized | [-1, 1] | Valence with no threat or need (trait affect) | L0 toy value |
| `w_cardiac_arousal` | 0.6 | — | [0, 1] | Weight of felt cardiac activation in arousal | L0 toy value |
| `w_threat_arousal` | 0.4 | — | [0, 1] | Weight of appraised threat in arousal | L0 toy value |
| `w_threat_valence` | 0.9 | — | [0, 2] | Valence lost per unit appraised threat | L0 toy value |
| `w_hunger_valence` | 0.5 | — | [0, 2] | Valence lost per unit hunger | L0 toy value |
| `w_thirst_valence` | 0.5 | — | [0, 2] | Valence lost per unit thirst | L0 toy value |
| `w_thermal_valence` | 0.4 | — | [0, 2] | Valence lost per unit thermal discomfort | L0 toy value |
| `tau` | 2 | s | [0.01, 600] | Time constant of affect | L0 toy value |
| `valence_sigma` | 0.03 | normalized | [0, 0.5] | SD of spontaneous valence fluctuation | L0 toy value |
| `arousal_sigma` | 0.02 | normalized | [0, 0.5] | SD of spontaneous arousal fluctuation | L0 toy value |
| `fluctuation_tau` | 60 | s | [1, 36000] | Correlation time of spontaneous fluctuation | L0 toy value |
| `seed` | 3 | — | [0, ∞] | Random seed of the fluctuation | run setting |

## `psyche.drives`

`unbodysoma.psyche.drives.Drives`

| 參數 | 預設值 | 單位 | 有效範圍 | 說明 | 來源 |
|---|---|---|---|---|---|
| `threshold` | 0.2 | normalized | [0, 1] | Energy deficit below which no hunger is felt | L0 toy value |
| `span` | 0.6 | normalized | [0.01, 1] | Deficit above threshold that is felt as maximal hunger | L0 toy value |
| `tau` | 30 | s | [0.1, 3600] | Time constant of hunger and thirst | L0 toy value |
| `sleep_hunger_suppression` | 0.5 | — | [0, 1] | Share of felt hunger and thirst suppressed in sleep | L0 toy value |
| `thirst_threshold` | 0.15 | normalized | [0, 1] | Water deficit below which no thirst is felt | L0 toy value |
| `thirst_span` | 0.5 | normalized | [0.01, 1] | Deficit above threshold felt as maximal thirst | L0 toy value |
| `thermal_deadband` | 0.1 | normalized | [0, 1] | Felt temperature deviation that is still comfortable | L0 toy value |
| `thermal_span` | 0.5 | normalized | [0.01, 1] | Deviation beyond the deadband felt as maximal discomfort | L0 toy value |
| `thermal_tau` | 60 | s | [0.1, 3600] | Time constant of thermal discomfort | L0 toy value |
| `sleepiness_tau` | 300 | s | [1, 7200] | Time over which felt sleepiness is integrated | L0 toy value |
| `sleep_onset_pressure` | 0.573 | normalized | [0, 1] | Mean upper threshold H0 of sleep pressure | calibrated: 16 h wake / 8 h sleep, onset ≈ 23:00 |
| `wake_pressure` | 0.193 | normalized | [0, 1] | Mean lower threshold L0 of sleep pressure | calibrated: 16 h wake / 8 h sleep, onset ≈ 23:00 |
| `circadian_amplitude` | 0.1 | normalized | [0, 0.5] | How far the circadian signal moves both thresholds | calibrated: 16 h wake / 8 h sleep, onset ≈ 23:00 |

## `psyche.action`

`unbodysoma.psyche.action.ActionSelection`

| 參數 | 預設值 | 單位 | 有效範圍 | 說明 | 來源 |
|---|---|---|---|---|---|
| `temperature` | 0.015 | — | [0, 5] | Choice temperature: 0 = always the best action, higher = more random | L0 toy value |
| `stickiness` | 0.1 | — | [0, 2] | Utility bonus for continuing the current action | L0 toy value |
| `reconsideration_rate` | 0.0166667 | 1/s | [0, 10] | Rate of switching between two equally good actions | L0 toy value |
| `k_flee` | 2.5 | — | [0, 20] | Utility gain of fleeing per unit threat above threshold | L0 toy value |
| `flee_threshold` | 0.4 | normalized | [0, 1] | Appraised threat at which fleeing breaks even | L0 toy value |
| `k_eat` | 2 | — | [0, 20] | Utility gain of eating per unit hunger above threshold | L0 toy value |
| `eat_threshold` | 0.35 | normalized | [0, 1] | Hunger at which starting to eat breaks even | L0 toy value |
| `eat_commitment` | 0.4 | — | [0, 2] | Extra bonus for continuing a meal (sets how sated it ends) | L0 toy value |
| `k_explore` | 1.5 | — | [0, 20] | Utility gain of searching for food per unit hunger | L0 toy value |
| `explore_threshold` | 0.4 | normalized | [0, 1] | Hunger at which searching for food breaks even | L0 toy value |
| `k_drink` | 2 | — | [0, 20] | Utility gain of drinking per unit thirst above threshold | L0 toy value |
| `drink_threshold` | 0.3 | normalized | [0, 1] | Thirst at which starting to drink breaks even | L0 toy value |
| `drink_commitment` | 0.4 | — | [0, 2] | Extra bonus for continuing to drink (sets how sated it ends) | L0 toy value |
| `k_seek_water` | 1.5 | — | [0, 20] | Utility gain of searching for water per unit thirst | L0 toy value |
| `seek_water_threshold` | 0.35 | normalized | [0, 1] | Thirst at which searching for water breaks even | L0 toy value |
| `k_shelter` | 1.5 | — | [0, 20] | Utility gain of going to shelter per unit thermal discomfort | L0 toy value |
| `shelter_threshold` | 0.3 | normalized | [0, 1] | Thermal discomfort at which sheltering breaks even | L0 toy value |
| `k_home` | 4 | — | [0, 50] | Utility gain of going home to sleep per unit sleepiness | L0 toy value |
| `home_onset` | 0.8 | normalized | [0, 1] | Sleepiness at which going home to sleep breaks even | L0 toy value |
| `outside_penalty` | 0.5 | — | [0, 5] | Utility lost by falling asleep outside a known shelter | L0 toy value |
| `k_sleep` | 8 | — | [0, 50] | How sharply sleep wins once sleepiness passes sleep_onset | L0 toy value |
| `sleep_onset` | 0.95 | normalized | [0, 1] | Sleepiness at which falling asleep breaks even | L0 toy value |
| `sleep_depth` | 5 | — | [0, 50] | Utility of staying asleep per unit sleepiness | L0 toy value |
| `sleep_cap` | 1 | — | [0, 10] | Maximum utility of staying asleep (below a full threat's) | L0 toy value |
| `resume_window` | 1800 | s | [0, 14400] | How long after waking unfinished sleep can resume | L0 toy value |
| `unfinished_sleep` | 0.05 | normalized | [0, 1] | Sleepiness above which an awakening is premature | L0 toy value |
| `food_seen` | 0.5 | normalized | [0, 1] | Sensed food level that counts as food within reach | L0 toy value |
| `water_seen` | 0.5 | normalized | [0, 1] | Sensed water level that counts as water within reach | L0 toy value |
| `shelter_seen` | 0.5 | normalized | [0, 1] | Sensed level that counts as inside / knowing a shelter | L0 toy value |
| `flee_exertion` | 0.8 | normalized | [0, 1] | Exertion while fleeing | L0 toy value |
| `explore_exertion` | 0.3 | normalized | [0, 1] | Exertion while searching or travelling | L0 toy value |
| `tau` | 1 | s | [0.01, 60] | Time constant of exertion changes | L0 toy value |
| `seed` | 4 | — | [0, ∞] | Random seed of the choices | run setting |

## `world.grid`

`unbodysoma.world.grid.GridWorld`

| 參數 | 預設值 | 單位 | 有效範圍 | 說明 | 來源 |
|---|---|---|---|---|---|
| `max_speed` | 1 | cells/s | [0, 10] | Speed at a full movement command | L0 toy value |
| `reach` | 0.5 | cells | [0.05, 5] | Distance at which food can be eaten | L0 toy value |
| `sense_radius` | 6 | cells | [0, 100] | Distance at which food and hazards are perceived | L0 toy value |
| `depletion_per_s` | 0.00166667 | 1/s | [0, 1] | Share of a patch eaten per second of eating | L0 toy value |
| `open_threshold` | 0.25 | fraction | [0, 1] | Share of capacity at which a patch is worth approaching | L0 toy value |
| `empty_threshold` | 0.05 | fraction | [0, 1] | Share of capacity at which a patch being eaten runs out | L0 toy value |
| `temperature_mean` | 15 | °C | [-40, 50] | Daily mean outside temperature | L0 toy value |
| `temperature_amplitude` | 8 | °C | [0, 30] | Half the day-night temperature swing | L0 toy value |
| `warmest_hour` | 15 | h | [0, 24] | Clock hour of the warmest outside temperature | L0 toy value |
| `comfortable_temperature` | 20 | °C | [0, 40] | Temperature a shelter buffers toward | L0 toy value |
| `start_hour` | 8 | h | [0, 24] | Clock time at t = 0 | run setting |

## `psyche.navigation`

`unbodysoma.psyche.navigation.Navigation`

| 參數 | 預設值 | 單位 | 有效範圍 | 說明 | 來源 |
|---|---|---|---|---|---|
| `walk_fraction` | 0.5 | normalized | [0, 1] | Speed while exploring, as a share of full speed | L0 toy value |
| `flee_fraction` | 1 | normalized | [0, 1] | Speed while fleeing, as a share of full speed | L0 toy value |
| `wander_sigma` | 0.3 | rad/√s | [0, 10] | How fast the wandering heading diffuses | L0 toy value |
| `direction_seen` | 0.5 | unit | [0, 1] | Length of a sensed direction that counts as known | L0 toy value |
| `seed` | 5 | — | [0, ∞] | Random seed of the wandering | run setting |
