# 情境檔 Scenarios

情境檔用 TOML 描述一次實驗：哪個生物體、什麼參數、環境發生什麼、施加哪些干預、記錄與監控什麼。設計理由見 [ADR-0008](adr/0008-toml-scenario-files.md)。

## 命令列

```bash
python -m unbodysoma validate scenarios/*.toml                    # 只檢查，不執行
python -m unbodysoma run scenarios/fear_response.toml             # 執行並印出摘要
python -m unbodysoma run scenarios/grid_72h.toml --out runs/grid  # 同時寫出執行紀錄
python -m unbodysoma run scenarios/feeding.toml --seed 3 --hours 0.2
python -m unbodysoma replay runs/grid                              # 重跑並逐位元驗證可重現
python -m unbodysoma run scenarios/grid_72h.toml --rerun           # 以 Rerun 即時觀看（需要 unbodysoma[viz]）
```

結束碼：`0` 完成（`replay`：結果相同）、`1` 被健康監控停止（`replay`：結果不同）、`2` 情境檔或紀錄有錯。

## 隨附的情境

| 檔案 | 內容 |
|---|---|
| `fear_response.toml` | 60–90 秒出現威脅：評估、逃跑、恢復 |
| `fear_without_interoception.toml` | 同上，但內感受被抑制：身體有反應，心智感覺不到 |
| `feeding.toml` | 飢餓的生物體找到食物、被威脅打斷、吃到飽 |
| `grid_72h.toml` | **Phase 1 完成情境**：在網格世界自主生活 72 小時（睡眠、覓食、飲水、體溫調節、躲避掠食者） |

## 格式

```toml
[scenario]                  # 必填
name = "my_experiment"      # 預設為檔名
description = "…"
duration_h = 24             # duration_s 與 duration_h 二擇一
seed = 0                    # 非負整數；每個隨機串流以此為基礎
base_dt = 0.05              # 選填；預設依預設生物體而定（minimal 0.01、grid 0.05）

[organism]                  # 必填
preset = "minimal"          # "minimal"（腳本化世界）或 "grid"（網格世界）

[organism.overrides."soma.metabolism"]   # 任一模組的參數，見 PARAMETERS.md
initial_reserve = 0.4

# --- 只用於 preset = "minimal" ---------------------------------------------
# 可用的訊號：world.threat、world.food_available、world.water_available、world.in_shelter、
# world.shelter_known、world.ambient_temperature（基準 22 °C，事件的值會加在基準上）
[[events]]                  # 在 [start, end) 秒之間，把 value 加到訊號 key 上
start = 60
end = 90
key = "world.threat"        # 或 "world.food_available"
value = 0.9

# --- 只用於 preset = "grid" ------------------------------------------------
[world]
width = 20                  # 環面世界：邊界相接
height = 20
start = [10, 10]

[[world.food]]
x = 4
y = 4
capacity = 1.0              # 選填
regrow_per_hour = 0.25      # 選填：每小時長回容量的比例

[[world.water]]             # 不會枯竭的水源；必須在感覺範圍內才看得到
x = 10
y = 4

[[world.shelters]]          # 庇護所：緩衝外面的溫度、擋住危險；生物體永遠記得回家的路
x = 10
y = 10
radius = 1.0                # 選填
insulation = 0.8            # 選填：擋掉外面溫度偏離舒適溫度的比例

[[world.hazards]]
x = 13
y = 13
radius = 3                  # 威脅在中心為 strength，到 radius 處降為 0
strength = 0.9
start = 0                   # 選填：出現的時間窗 [start, end)（秒）
end = 3600
every = 86400               # 選填：時間窗每隔 every 秒重複一次

# --- 干預（兩種預設皆可） ----------------------------------------------------
[[interventions]]
type = "clamp"              # 固定訊號
key = "soma.cardio.heart_rate"
value = 65
start = 0                   # 選填
end = 300                   # 選填，預設為無限

[[interventions]]
type = "lesion"             # 讓模組停止運作
module = "interface.interoception"
mode = "silence"            # 或 "freeze"

# --- 觀測 ------------------------------------------------------------------
[observe]
record_every = 1.0          # 執行紀錄的取樣間隔（秒）
monitor = true              # 是否掛上健康監控
monitor_every = 1.0         # 監控的檢查間隔（秒）；多日模擬建議 10
halt_on = "critical"        # "info"、"warning"、"critical" 或 "none"
```

## 錯誤訊息

所有錯誤都會指出位置，例如：

```text
error: events[0]: unknown key(s) ['strt']; allowed: ['end', 'key', 'start', 'value']
error: organism: soma.cardio.resting_bpm = 500 outside [30, 120]
error: interventions[1]: unknown signal 'soma.liver'
error: world: a world layout is only available with preset = 'grid'
```
