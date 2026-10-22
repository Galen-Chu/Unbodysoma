# 參數 Parameters

> 本文件由 `python -m unbodysoma.catalog` 從模組的 `ParamSpec` 自動產生，**請勿手動編輯**。
> 預設值目前都是 L0 玩具值；個體差異與族群分布的規劃見 [VARIABILITY.md](VARIABILITY.md)。

## `world.food`

`unbodysoma.world.food.FoodSource`

| 參數 | 預設值 | 單位 | 有效範圍 | 說明 | 來源 |
|---|---|---|---|---|---|
| `intake_rate` | 0.0003 | fraction/s | [0, 0.01] | Reserve refilled per second of eating (≈ 0.3 per 15 min) | L0 toy value |

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
| `noise` | 0.01 | normalized | [0, 1] | SD of interoceptive noise (inverse of interoceptive accuracy) | L0 toy value |
| `seed` | 1 | — | [0, ∞] | Random seed of the noise | run setting |

## `soma.cardio`

`unbodysoma.soma.cardio.Cardio`

| 參數 | 預設值 | 單位 | 有效範圍 | 說明 | 來源 |
|---|---|---|---|---|---|
| `resting_bpm` | 65 | bpm | [30, 120] | Resting heart rate | L0 toy value |
| `max_bpm` | 190 | bpm | [100, 230] | Ceiling of the heart-rate response | L0 toy value |
| `k_adrenaline` | 40 | bpm | [0, 150] | Heart-rate gain per unit adrenaline | L0 toy value |
| `k_exertion` | 70 | bpm | [0, 150] | Heart-rate gain per unit exertion | L0 toy value |
| `tau` | 5 | s | [0.1, 120] | Time constant of heart-rate changes | L0 toy value |

## `soma.endocrine`

`unbodysoma.soma.endocrine.Endocrine`

| 參數 | 預設值 | 單位 | 有效範圍 | 說明 | 來源 |
|---|---|---|---|---|---|
| `cortisol_baseline` | 0.2 | normalized | [0, 1] | Cortisol level without threat | L0 toy value |
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
| `hours_to_empty_at_rest` | 16 | h | [1, 500] | Time for a full reserve to drain at rest | L0 toy value |
| `exertion_cost` | 4 | — | [0, 20] | Extra drain per unit exertion, relative to basal | L0 toy value |
| `glucose_setpoint` | 90 | mg/dL | [60, 130] | Defended fasting glucose | L0 toy value |
| `k_adrenaline` | 40 | mg/dL | [0, 150] | Glucose mobilized per unit adrenaline | L0 toy value |
| `glucose_tau` | 120 | s | [1, 3600] | Time constant of glucose regulation | L0 toy value |
| `glucose_defense_reserve` | 0.1 | fraction | [0.01, 1] | Reserve below which glucose can no longer be defended | L0 toy value |

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
| `tau` | 2 | s | [0.01, 600] | Time constant of affect | L0 toy value |

## `psyche.drives`

`unbodysoma.psyche.drives.Drives`

| 參數 | 預設值 | 單位 | 有效範圍 | 說明 | 來源 |
|---|---|---|---|---|---|
| `threshold` | 0.2 | normalized | [0, 1] | Energy deficit below which no hunger is felt | L0 toy value |
| `span` | 0.6 | normalized | [0.01, 1] | Deficit above threshold that is felt as maximal hunger | L0 toy value |
| `tau` | 30 | s | [0.1, 3600] | Time constant of hunger | L0 toy value |

## `psyche.action`

`unbodysoma.psyche.action.ActionSelection`

| 參數 | 預設值 | 單位 | 有效範圍 | 說明 | 來源 |
|---|---|---|---|---|---|
| `flee_on` | 0.5 | normalized | [0, 1] | Appraised threat that starts flight | L0 toy value |
| `flee_off` | 0.3 | normalized | [0, 1] | Appraised threat below which flight stops | L0 toy value |
| `flee_exertion` | 0.8 | normalized | [0, 1] | Exertion while fleeing | L0 toy value |
| `eat_on` | 0.4 | normalized | [0, 1] | Hunger that starts eating when food is near | L0 toy value |
| `eat_off` | 0.1 | normalized | [0, 1] | Hunger below which eating stops (satiety) | L0 toy value |
| `food_seen` | 0.5 | normalized | [0, 1] | Sensed food level that counts as food within reach | L0 toy value |
| `tau` | 1 | s | [0.01, 60] | Time constant of exertion changes | L0 toy value |
