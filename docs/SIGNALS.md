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
- 新增或修改訊號時，必須同步更新下表。

## 登記表

| 訊號 | 單位 / 範圍 | 寫入者 | 讀取者 |
|---|---|---|---|
| `world.threat` | [0, 1] | `world.scripted` | `interface.exteroception` |
| `world.food_intake` | 能量儲備比例 / s | `world.scripted` | `soma.metabolism` |
| `extero.threat` | [0, 1] | `interface.exteroception` | `psyche.appraisal` |
| `soma.cardio.heart_rate` | bpm | `soma.cardio` | `interface.interoception` |
| `soma.endocrine.adrenaline` | [0, 1] | `soma.endocrine` | `soma.cardio`, `soma.metabolism` |
| `soma.endocrine.cortisol` | [0, 1] | `soma.endocrine` | —（預留） |
| `soma.metabolism.energy_reserve` | [0, 1] | `soma.metabolism` | `interface.interoception` |
| `soma.metabolism.glucose` | mg/dL | `soma.metabolism` | —（預留） |
| `intero.cardiac_arousal` | [0, 1] | `interface.interoception` | `psyche.affect` |
| `intero.energy_deficit` | [0, 1] | `interface.interoception` | `psyche.drives` |
| `psyche.appraisal.threat` | [0, 1] | `psyche.appraisal` | `soma.endocrine`, `psyche.action` |
| `psyche.affect.valence` | [-1, 1] | `psyche.affect` | — |
| `psyche.affect.arousal` | [0, 1] | `psyche.affect` | `psyche.appraisal` |
| `psyche.drive.hunger` | [0, 1] | `psyche.drives` | `psyche.affect` |
| `motor.exertion` | [0, 1] | `psyche.action` | `soma.cardio`, `soma.metabolism` |

> 未來可考慮由程式自動產生此表（模組已宣告 `reads` / `writes`），避免文件與程式碼脫節。
