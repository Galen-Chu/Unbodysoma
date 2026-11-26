# 訊號 Signals

模組之間唯一的溝通方式是訊號匯流排上的命名訊號。本文件是訊號的命名規範與登記表。

## 命名規範

```
<namespace>.<subsystem>.<quantity>
```

| 命名空間 | 意義 | 誰可以寫 |
|---|---|---|
| `world.*` | 環境的客觀狀態 | World |
| `extero.*` | 外感受：心智對環境的感知 | Interface |
| `soma.*` | 身體的客觀生理狀態 | Soma |
| `intero.*` | 內感受：心智對身體的感知（正規化、有雜訊） | Interface |
| `psyche.*` | 心智內部狀態 | Psyche |
| `motor.*` | 運動指令：心智對身體 / 環境的作用 | Psyche |
| `neuro.*` | 神經調節物（規劃中） | Soma / Psyche |

規則：

- 全部小寫、以 `_` 分隔單字。
- 生理量使用**原始單位**（bpm、mg/dL、°C）；感知量與心理量使用**正規化範圍**（`[0, 1]` 或 `[-1, 1]`）。
- 每個訊號只能有**一個**寫入模組（引擎會強制檢查）。
- 每個寫入的訊號都要有一個 `SignalSpec`（單位、有效範圍、說明），宣告在寫入模組的 `signal_specs` 中。
- 下表**由程式自動產生**：修改 `SignalSpec` 後執行 `python -m unbodysoma.catalog`；測試會檢查此表是否與程式碼一致。
- 健康監控會自動依 `SignalSpec` 的有效範圍檢查每個訊號（見 [OBSERVABILITY.md](OBSERVABILITY.md)）。

## 登記表

<!-- BEGIN GENERATED: python -m unbodysoma.catalog -->
| 訊號 | 單位 | 範圍 | 寫入者 | 讀取者 | 說明 |
|---|---|---|---|---|---|
| `extero.food` | normalized | [0, 1] | `interface.exteroception` | `psyche.action` | Sensed food within reach |
| `extero.food_dir_x` | normalized | [-1, 1] | `interface.exteroception` | `psyche.navigation` | Sensed direction to the nearest food (x) |
| `extero.food_dir_y` | normalized | [-1, 1] | `interface.exteroception` | `psyche.navigation` | Sensed direction to the nearest food (y) |
| `extero.in_shelter` | normalized | [0, 1] | `interface.exteroception` | `psyche.action` | Sensed being inside a shelter |
| `extero.shelter_dir_x` | normalized | [-1, 1] | `interface.exteroception` | `psyche.navigation` | Remembered direction to the nearest shelter (x) |
| `extero.shelter_dir_y` | normalized | [-1, 1] | `interface.exteroception` | `psyche.navigation` | Remembered direction to the nearest shelter (y) |
| `extero.shelter_known` | normalized | [0, 1] | `interface.exteroception` | `psyche.action` | Knowing a shelter exists |
| `extero.threat` | normalized | [0, 1] | `interface.exteroception` | `psyche.appraisal` | Sensed threat cue |
| `extero.threat_dir_x` | normalized | [-1, 1] | `interface.exteroception` | `psyche.navigation` | Sensed direction to the strongest threat (x) |
| `extero.threat_dir_y` | normalized | [-1, 1] | `interface.exteroception` | `psyche.navigation` | Sensed direction to the strongest threat (y) |
| `extero.water` | normalized | [0, 1] | `interface.exteroception` | `psyche.action` | Sensed water within reach |
| `extero.water_dir_x` | normalized | [-1, 1] | `interface.exteroception` | `psyche.navigation` | Sensed direction to the nearest water (x) |
| `extero.water_dir_y` | normalized | [-1, 1] | `interface.exteroception` | `psyche.navigation` | Sensed direction to the nearest water (y) |
| `intero.cardiac_arousal` | normalized | [0, 1] | `interface.interoception` | `psyche.affect`, `soma.neuro` | Felt cardiac activation |
| `intero.circadian` | normalized | [-1, 1] | `interface.interoception` | `psyche.drives` | Felt circadian alerting signal |
| `intero.energy_deficit` | normalized | [0, 1] | `interface.interoception` | `psyche.drives`, `soma.neuro` | Felt shortage of energy (store minus satiety plus glucose dip) |
| `intero.pain` | normalized | [0, 1] | `interface.interoception` | `psyche.action`, `psyche.affect`, `psyche.instrumental`, `psyche.memory`, `psyche.place_memory`, `soma.neuro` | Felt pain |
| `intero.sleep_pressure` | normalized | [0, 1] | `interface.interoception` | `psyche.drives`, `soma.neuro` | Felt tiredness (homeostatic sleep pressure) |
| `intero.thermal` | normalized | [-1, 1] | `interface.interoception` | `psyche.drives`, `soma.neuro` | Felt body temperature (- cold, + hot) |
| `intero.water_deficit` | normalized | [0, 1] | `interface.interoception` | `psyche.drives`, `soma.neuro` | Felt shortage of water |
| `motor.drinking` | normalized | [0, 1] | `psyche.action` | `world.water` | Drinking behaviour (1 = drinking) |
| `motor.eating` | normalized | [0, 1] | `psyche.action` | `world.food`, `world.grid` | Eating behaviour (1 = eating) |
| `motor.exertion` | normalized | [0, 1] | `psyche.action` | `soma.cardio`, `soma.fluid`, `soma.metabolism`, `soma.respiration`, `soma.thermo` | Physical effort being exerted |
| `motor.move_x` | normalized | [-1, 1] | `psyche.navigation` | `world.grid` | Movement command (x); length 1 = full speed |
| `motor.move_y` | normalized | [-1, 1] | `psyche.navigation` | `world.grid` | Movement command (y); length 1 = full speed |
| `motor.sleeping` | indicator | [0, 1] | `psyche.action` | `psyche.drives`, `soma.cardio`, `soma.endocrine`, `soma.fluid`, `soma.metabolism`, `soma.respiration`, `soma.sleep` | 1 while asleep |
| `neuro.dopamine` | normalized | [0, 1] | `soma.neuro` | `psyche.affect` | Dopamine: phasic reward from homeostatic relief |
| `neuro.norepinephrine` | normalized | [0, 1] | `soma.neuro` | `psyche.appraisal` | Norepinephrine: vigilance |
| `neuro.relief` | normalized | [0, 1] | `soma.neuro` | `psyche.conditioning`, `psyche.instrumental` | Relief: homeostatic error falling below its slow baseline |
| `neuro.serotonin` | normalized | [0, 1] | `soma.neuro` | `psyche.affect` | Serotonin: slow mood tone |
| `psyche.action.p_drink` | probability | [0, 1] | `psyche.action` | —（預留） | Probability of choosing drink |
| `psyche.action.p_eat` | probability | [0, 1] | `psyche.action` | —（預留） | Probability of choosing eat |
| `psyche.action.p_explore` | probability | [0, 1] | `psyche.action` | —（預留） | Probability of choosing explore |
| `psyche.action.p_flee` | probability | [0, 1] | `psyche.action` | —（預留） | Probability of choosing flee |
| `psyche.action.p_idle` | probability | [0, 1] | `psyche.action` | —（預留） | Probability of choosing idle |
| `psyche.action.p_seek_shelter` | probability | [0, 1] | `psyche.action` | —（預留） | Probability of choosing seek_shelter |
| `psyche.action.p_seek_water` | probability | [0, 1] | `psyche.action` | —（預留） | Probability of choosing seek_water |
| `psyche.action.p_sleep` | probability | [0, 1] | `psyche.action` | —（預留） | Probability of choosing sleep |
| `psyche.action.selected_drink` | indicator | [0, 1] | `psyche.action` | `psyche.instrumental` | 1 while drink is chosen |
| `psyche.action.selected_eat` | indicator | [0, 1] | `psyche.action` | `psyche.instrumental` | 1 while eat is chosen |
| `psyche.action.selected_explore` | indicator | [0, 1] | `psyche.action` | `psyche.instrumental`, `psyche.navigation` | 1 while explore is chosen |
| `psyche.action.selected_flee` | indicator | [0, 1] | `psyche.action` | `psyche.instrumental`, `psyche.navigation` | 1 while flee is chosen |
| `psyche.action.selected_idle` | indicator | [0, 1] | `psyche.action` | `psyche.instrumental` | 1 while idle is chosen |
| `psyche.action.selected_seek_shelter` | indicator | [0, 1] | `psyche.action` | `psyche.instrumental`, `psyche.navigation` | 1 while seek_shelter is chosen |
| `psyche.action.selected_seek_water` | indicator | [0, 1] | `psyche.action` | `psyche.instrumental`, `psyche.navigation` | 1 while seek_water is chosen |
| `psyche.action.selected_sleep` | indicator | [0, 1] | `psyche.action` | `psyche.instrumental` | 1 while sleep is chosen |
| `psyche.affect.arousal` | normalized | [0, 1] | `psyche.affect` | `psyche.memory` | Core affect: activation |
| `psyche.affect.valence` | normalized | [-1, 1] | `psyche.affect` | `psyche.memory` | Core affect: pleasant (+) vs unpleasant (-) |
| `psyche.appraisal.threat` | normalized | [0, 1] | `psyche.appraisal` | `psyche.action`, `psyche.affect`, `soma.endocrine`, `soma.neuro` | Appraised threat |
| `psyche.conditioning.defense_a` | normalized | [0, 1] | `psyche.conditioning` | —（預留） | Defensive association of cue A |
| `psyche.conditioning.defense_b` | normalized | [0, 1] | `psyche.conditioning` | —（預留） | Defensive association of cue B |
| `psyche.conditioning.reward_prediction` | normalized | [0, 1] | `psyche.conditioning` | `soma.neuro` | Relief predicted by present cues |
| `psyche.conditioning.threat_expectation` | normalized | [0, 1] | `psyche.conditioning` | `psyche.appraisal` | Learned threat predicted by present cues |
| `psyche.drive.hunger` | normalized | [0, 1] | `psyche.drives` | `psyche.action`, `psyche.affect` | Felt urgency of eating |
| `psyche.drive.sleepiness` | normalized | [-1, 1] | `psyche.drives` | `psyche.action` | Felt need for sleep (1 = sleep onset, 0 = wake point) |
| `psyche.drive.thermal_discomfort` | normalized | [0, 1] | `psyche.drives` | `psyche.action`, `psyche.affect` | Felt cold or heat |
| `psyche.drive.thirst` | normalized | [0, 1] | `psyche.drives` | `psyche.action`, `psyche.affect` | Felt urgency of drinking |
| `psyche.habituation.novelty` | normalized | [0, 1] | `psyche.habituation` | `psyche.affect` | Felt novelty of the current stimulus |
| `psyche.instrumental.value_drink` | utility | [-1, 1] | `psyche.instrumental` | `psyche.action` | Learned value of drink |
| `psyche.instrumental.value_eat` | utility | [-1, 1] | `psyche.instrumental` | `psyche.action` | Learned value of eat |
| `psyche.instrumental.value_explore` | utility | [-1, 1] | `psyche.instrumental` | `psyche.action` | Learned value of explore |
| `psyche.instrumental.value_flee` | utility | [-1, 1] | `psyche.instrumental` | `psyche.action` | Learned value of flee |
| `psyche.instrumental.value_idle` | utility | [-1, 1] | `psyche.instrumental` | `psyche.action` | Learned value of idle |
| `psyche.instrumental.value_seek_shelter` | utility | [-1, 1] | `psyche.instrumental` | `psyche.action` | Learned value of seek_shelter |
| `psyche.instrumental.value_seek_water` | utility | [-1, 1] | `psyche.instrumental` | `psyche.action` | Learned value of seek_water |
| `psyche.instrumental.value_sleep` | utility | [-1, 1] | `psyche.instrumental` | `psyche.action` | Learned value of sleep |
| `psyche.memory.episodes` | count | [0, 64] | `psyche.memory` | —（預留） | Episodes currently held |
| `psyche.memory.mood_congruence` | normalized | [-1, 1] | `psyche.memory` | `psyche.affect` | Signed reactivation of stored episodes by the current context (negative memories pull down) |
| `psyche.place_memory.avoid_x` | unit | [-1, 1] | `psyche.place_memory` | `psyche.navigation` | Repulsion from nearby danger (x) |
| `psyche.place_memory.avoid_y` | unit | [-1, 1] | `psyche.place_memory` | `psyche.navigation` | Repulsion from nearby danger (y) |
| `psyche.place_memory.danger` | normalized | [0, 1] | `psyche.place_memory` | —（預留） | Learned danger at the current position |
| `soma.cardio.heart_rate` | bpm | [0, 300] | `soma.cardio` | `interface.interoception` | Heart rate |
| `soma.circadian.clock_hour` | h | [0, 24] | `soma.circadian` | `soma.endocrine` | Local clock time |
| `soma.circadian.drive` | normalized | [-1, 1] | `soma.circadian` | `interface.interoception` | Circadian alerting signal (+1 at its daily peak) |
| `soma.endocrine.adrenaline` | normalized | [0, 1] | `soma.endocrine` | `soma.cardio`, `soma.metabolism`, `soma.respiration` | Circulating adrenaline (sympathetic arousal) |
| `soma.endocrine.cortisol` | normalized | [0, 1] | `soma.endocrine` | —（預留） | Circulating cortisol (HPA axis) |
| `soma.fluid.hydration` | fraction | [0, 1] | `soma.fluid` | `interface.interoception` | Body-water reserve (1 = well hydrated) |
| `soma.fluid.osmolality` | mOsm/kg | [250, 350] | `soma.fluid` | —（預留） | Plasma osmolality |
| `soma.metabolism.energy_reserve` | fraction | [0, 1] | `soma.metabolism` | `interface.interoception` | Net glucose balance (1 = full store) |
| `soma.metabolism.glucose` | mg/dL | [0, 600] | `soma.metabolism` | `interface.interoception` | Blood glucose |
| `soma.metabolism.insulin` | μU/mL | [0, 400] | `soma.metabolism` | `interface.interoception` | Plasma insulin |
| `soma.nociception.burning` | normalized | [0, 1] | `soma.nociception` | —（預留） | Second pain: slow, tracks tissue state |
| `soma.nociception.injury` | fraction | [0, 1] | `soma.nociception` | —（預留） | Tissue injury (1 = maximally injured) |
| `soma.nociception.pain` | normalized | [0, 1] | `soma.nociception` | `interface.interoception` | Felt pain intensity (sensitized) |
| `soma.nociception.sharp` | normalized | [0, 1] | `soma.nociception` | —（預留） | First pain: fast, tracks the stimulus |
| `soma.respiration.minute_ventilation` | L/min | [2, 120] | `soma.respiration` | —（預留） | Minute ventilation |
| `soma.respiration.rate` | breaths/min | [4, 60] | `soma.respiration` | `soma.cardio` | Breathing rate |
| `soma.respiration.spo2` | % | [70, 100] | `soma.respiration` | —（預留） | Arterial oxygen saturation |
| `soma.sleep.pressure` | normalized | [0, 1] | `soma.sleep` | `interface.interoception` | Homeostatic sleep pressure (process S) |
| `soma.thermo.core_temperature` | °C | [30, 45] | `soma.thermo` | `interface.interoception` | Core body temperature |
| `soma.thermo.shivering` | normalized | [0, 1] | `soma.thermo` | `soma.metabolism` | Shivering intensity (heat production, energy cost) |
| `soma.thermo.sweating` | normalized | [0, 1] | `soma.thermo` | `soma.fluid` | Sweating intensity (heat loss, water cost) |
| `world.ambient_temperature` | °C | [-60, 60] | `world.grid`, `world.scripted` | `soma.thermo` | Temperature where the organism is |
| `world.damage` | normalized | [0, 1] | `world.grid`, `world.scripted` | `psyche.conditioning`, `soma.nociception` | Nociceptive intensity at the organism (0 inside a shelter) |
| `world.food_available` | normalized | [0, 1] | `world.grid`, `world.scripted` | `interface.exteroception`, `world.food` | Food within reach (1 = plenty) |
| `world.food_dir_x` | unit | [-1, 1] | `world.grid` | `interface.exteroception` | Direction to the nearest perceived food (x); 0 if none |
| `world.food_dir_y` | unit | [-1, 1] | `world.grid` | `interface.exteroception` | Direction to the nearest perceived food (y); 0 if none |
| `world.food_intake` | fraction/s | [0, 1] | `world.food` | `soma.metabolism` | Energy entering the body, as reserve fraction per second |
| `world.food_stock` | patches | [0, 4] | `world.grid` | —（預留） | Total food left in the world |
| `world.in_shelter` | indicator | [0, 1] | `world.grid`, `world.scripted` | `interface.exteroception` | 1 inside a shelter |
| `world.outside_temperature` | °C | [-60, 60] | `world.grid` | —（預留） | Outside air temperature |
| `world.position_x` | cells | [0, 20] | `world.grid` | `psyche.place_memory` | Organism position (x) |
| `world.position_y` | cells | [0, 20] | `world.grid` | `psyche.place_memory` | Organism position (y) |
| `world.shelter_dir_x` | unit | [-1, 1] | `world.grid` | `interface.exteroception` | Direction to the nearest shelter (x); 0 inside or if none |
| `world.shelter_dir_y` | unit | [-1, 1] | `world.grid` | `interface.exteroception` | Direction to the nearest shelter (y); 0 inside or if none |
| `world.shelter_known` | indicator | [0, 1] | `world.grid`, `world.scripted` | `interface.exteroception` | 1 if the world has a shelter (its way is remembered) |
| `world.stimulus` | normalized | [0, 1] | `world.grid`, `world.scripted` | `psyche.conditioning`, `psyche.habituation` | Cue A: innocuous stimulus intensity (none in the grid world yet) |
| `world.stimulus_b` | normalized | [0, 1] | `world.grid`, `world.scripted` | `psyche.conditioning` | Cue B: a second innocuous stimulus channel |
| `world.threat` | normalized | [0, 1] | `world.grid`, `world.scripted` | `interface.exteroception` | Objective threat at the organism's position |
| `world.threat_dir_x` | unit | [-1, 1] | `world.grid` | `interface.exteroception` | Direction to the strongest perceived hazard (x) |
| `world.threat_dir_y` | unit | [-1, 1] | `world.grid` | `interface.exteroception` | Direction to the strongest perceived hazard (y) |
| `world.water_available` | normalized | [0, 1] | `world.grid`, `world.scripted` | `interface.exteroception`, `world.water` | Water within reach |
| `world.water_dir_x` | unit | [-1, 1] | `world.grid` | `interface.exteroception` | Direction to the nearest perceived water (x); 0 if none |
| `world.water_dir_y` | unit | [-1, 1] | `world.grid` | `interface.exteroception` | Direction to the nearest perceived water (y); 0 if none |
| `world.water_intake` | fraction/s | [0, 1] | `world.water` | `soma.fluid` | Water entering the body, as hydration fraction per second |
<!-- END GENERATED -->
