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
| `extero.threat` | normalized | [0, 1] | `interface.exteroception` | `psyche.appraisal` | Sensed threat cue |
| `intero.cardiac_arousal` | normalized | [0, 1] | `interface.interoception` | `psyche.affect` | Felt cardiac activation |
| `intero.energy_deficit` | normalized | [0, 1] | `interface.interoception` | `psyche.drives` | Felt shortage of energy |
| `motor.eating` | normalized | [0, 1] | `psyche.action` | `world.food` | Eating behaviour (1 = eating) |
| `motor.exertion` | normalized | [0, 1] | `psyche.action` | `soma.cardio`, `soma.metabolism` | Physical effort being exerted |
| `psyche.affect.arousal` | normalized | [0, 1] | `psyche.affect` | `psyche.appraisal` | Core affect: activation |
| `psyche.affect.valence` | normalized | [-1, 1] | `psyche.affect` | —（預留） | Core affect: pleasant (+) vs unpleasant (-) |
| `psyche.appraisal.threat` | normalized | [0, 1] | `psyche.appraisal` | `psyche.action`, `psyche.affect`, `soma.endocrine` | Appraised threat |
| `psyche.drive.hunger` | normalized | [0, 1] | `psyche.drives` | `psyche.action`, `psyche.affect` | Felt urgency of eating |
| `soma.cardio.heart_rate` | bpm | [0, 300] | `soma.cardio` | `interface.interoception` | Heart rate |
| `soma.endocrine.adrenaline` | normalized | [0, 1] | `soma.endocrine` | `soma.cardio`, `soma.metabolism` | Circulating adrenaline (sympathetic arousal) |
| `soma.endocrine.cortisol` | normalized | [0, 1] | `soma.endocrine` | —（預留） | Circulating cortisol (HPA axis) |
| `soma.metabolism.energy_reserve` | fraction | [0, 1] | `soma.metabolism` | `interface.interoception` | Lumped energy store (1 = full) |
| `soma.metabolism.glucose` | mg/dL | [0, 600] | `soma.metabolism` | —（預留） | Blood glucose |
| `world.food_available` | normalized | [0, 1] | `world.scripted` | `interface.exteroception`, `world.food` | Food within reach (1 = plenty) |
| `world.food_intake` | fraction/s | [0, 1] | `world.food` | `soma.metabolism` | Energy entering the body, as reserve fraction per second |
| `world.threat` | normalized | [0, 1] | `world.scripted` | `interface.exteroception` | Objective threat present in the environment |
<!-- END GENERATED -->
