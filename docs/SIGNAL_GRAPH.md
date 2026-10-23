# 訊號依賴圖 Signal graph

> 本文件由 `python -m unbodysoma.catalog` 從模組的 `reads` / `writes` 宣告自動產生，**請勿手動編輯**。
> 每條邊代表「寫入者 → 讀取者」，標籤是經過的訊號（省略最外層的命名空間，例如 `soma.cardio.heart_rate` 寫成 `cardio.heart_rate`）；訊號的意義見 [SIGNALS.md](SIGNALS.md)。

## minimal：腳本化世界

```mermaid
flowchart LR
    subgraph world["World 環境層"]
        world_scripted["world.scripted"]
        world_food["world.food"]
        world_water["world.water"]
    end
    subgraph interface["Interface 介面層"]
        interface_exteroception["interface.exteroception"]
        interface_interoception["interface.interoception"]
    end
    subgraph soma["Soma 身體層"]
        soma_circadian["soma.circadian"]
        soma_sleep["soma.sleep"]
        soma_cardio["soma.cardio"]
        soma_endocrine["soma.endocrine"]
        soma_metabolism["soma.metabolism"]
        soma_fluid["soma.fluid"]
        soma_thermo["soma.thermo"]
    end
    subgraph psyche["Psyche 心智層"]
        psyche_appraisal["psyche.appraisal"]
        psyche_affect["psyche.affect"]
        psyche_drives["psyche.drives"]
        psyche_action["psyche.action"]
    end
    interface_exteroception -->|"food, in_shelter +2"| psyche_action
    interface_exteroception -->|"threat"| psyche_appraisal
    interface_interoception -->|"cardiac_arousal"| psyche_affect
    interface_interoception -->|"circadian, energy_deficit +3"| psyche_drives
    psyche_action -->|"sleeping"| psyche_drives
    psyche_action -->|"exertion, sleeping"| soma_cardio
    psyche_action -->|"exertion, sleeping"| soma_fluid
    psyche_action -->|"exertion, sleeping"| soma_metabolism
    psyche_action -->|"sleeping"| soma_sleep
    psyche_action -->|"exertion"| soma_thermo
    psyche_action -->|"eating"| world_food
    psyche_action -->|"drinking"| world_water
    psyche_affect -->|"affect.arousal"| psyche_appraisal
    psyche_appraisal -->|"appraisal.threat"| psyche_action
    psyche_appraisal -->|"appraisal.threat"| psyche_affect
    psyche_appraisal -->|"appraisal.threat"| soma_endocrine
    psyche_drives -->|"drive.hunger, drive.sleepiness +2"| psyche_action
    psyche_drives -->|"drive.hunger, drive.thermal_discomfort +1"| psyche_affect
    soma_cardio -->|"cardio.heart_rate"| interface_interoception
    soma_circadian -->|"circadian.drive"| interface_interoception
    soma_circadian -->|"circadian.clock_hour"| soma_endocrine
    soma_endocrine -->|"endocrine.adrenaline"| soma_cardio
    soma_endocrine -->|"endocrine.adrenaline"| soma_metabolism
    soma_fluid -->|"fluid.hydration"| interface_interoception
    soma_metabolism -->|"metabolism.energy_reserve"| interface_interoception
    soma_sleep -->|"sleep.pressure"| interface_interoception
    soma_thermo -->|"thermo.core_temperature"| interface_interoception
    soma_thermo -->|"thermo.sweating"| soma_fluid
    soma_thermo -->|"thermo.shivering"| soma_metabolism
    world_food -->|"food_intake"| soma_metabolism
    world_scripted -->|"food_available, in_shelter +3"| interface_exteroception
    world_scripted -->|"ambient_temperature"| soma_thermo
    world_scripted -->|"food_available"| world_food
    world_scripted -->|"water_available"| world_water
    world_water -->|"water_intake"| soma_fluid
```

## grid：網格世界

```mermaid
flowchart LR
    subgraph world["World 環境層"]
        world_grid["world.grid"]
        world_food["world.food"]
        world_water["world.water"]
    end
    subgraph interface["Interface 介面層"]
        interface_exteroception["interface.exteroception"]
        interface_interoception["interface.interoception"]
    end
    subgraph soma["Soma 身體層"]
        soma_circadian["soma.circadian"]
        soma_sleep["soma.sleep"]
        soma_cardio["soma.cardio"]
        soma_endocrine["soma.endocrine"]
        soma_metabolism["soma.metabolism"]
        soma_fluid["soma.fluid"]
        soma_thermo["soma.thermo"]
    end
    subgraph psyche["Psyche 心智層"]
        psyche_appraisal["psyche.appraisal"]
        psyche_affect["psyche.affect"]
        psyche_drives["psyche.drives"]
        psyche_action["psyche.action"]
        psyche_navigation["psyche.navigation"]
    end
    interface_exteroception -->|"food, in_shelter +2"| psyche_action
    interface_exteroception -->|"threat"| psyche_appraisal
    interface_exteroception -->|"food_dir_x, food_dir_y +6"| psyche_navigation
    interface_interoception -->|"cardiac_arousal"| psyche_affect
    interface_interoception -->|"circadian, energy_deficit +3"| psyche_drives
    psyche_action -->|"sleeping"| psyche_drives
    psyche_action -->|"action.selected_explore, action.selected_flee +2"| psyche_navigation
    psyche_action -->|"exertion, sleeping"| soma_cardio
    psyche_action -->|"exertion, sleeping"| soma_fluid
    psyche_action -->|"exertion, sleeping"| soma_metabolism
    psyche_action -->|"sleeping"| soma_sleep
    psyche_action -->|"exertion"| soma_thermo
    psyche_action -->|"eating"| world_food
    psyche_action -->|"eating"| world_grid
    psyche_action -->|"drinking"| world_water
    psyche_affect -->|"affect.arousal"| psyche_appraisal
    psyche_appraisal -->|"appraisal.threat"| psyche_action
    psyche_appraisal -->|"appraisal.threat"| psyche_affect
    psyche_appraisal -->|"appraisal.threat"| soma_endocrine
    psyche_drives -->|"drive.hunger, drive.sleepiness +2"| psyche_action
    psyche_drives -->|"drive.hunger, drive.thermal_discomfort +1"| psyche_affect
    psyche_navigation -->|"move_x, move_y"| world_grid
    soma_cardio -->|"cardio.heart_rate"| interface_interoception
    soma_circadian -->|"circadian.drive"| interface_interoception
    soma_circadian -->|"circadian.clock_hour"| soma_endocrine
    soma_endocrine -->|"endocrine.adrenaline"| soma_cardio
    soma_endocrine -->|"endocrine.adrenaline"| soma_metabolism
    soma_fluid -->|"fluid.hydration"| interface_interoception
    soma_metabolism -->|"metabolism.energy_reserve"| interface_interoception
    soma_sleep -->|"sleep.pressure"| interface_interoception
    soma_thermo -->|"thermo.core_temperature"| interface_interoception
    soma_thermo -->|"thermo.sweating"| soma_fluid
    soma_thermo -->|"thermo.shivering"| soma_metabolism
    world_food -->|"food_intake"| soma_metabolism
    world_grid -->|"food_available, food_dir_x +11"| interface_exteroception
    world_grid -->|"ambient_temperature"| soma_thermo
    world_grid -->|"food_available"| world_food
    world_grid -->|"water_available"| world_water
    world_water -->|"water_intake"| soma_fluid
```
