# 身體層 Soma

身體層負責「需要被維持的東西」。它定義了心智存在的理由：如果沒有會偏離設定點的變數，就沒有驅力、沒有情感，也沒有需要做的決策。

## 1. 子系統規劃

| 子系統 | 主要狀態變數 | 對心智的意義 | 目前 | 候選 L1 模型 |
|---|---|---|---|---|
| 心血管 Cardio | 心率、心率變異、血壓、心輸出量 | 喚醒度最主要的內感受來源 | ✅ L0（心率 + HRV） | Guyton 循環調節模型 |
| 內分泌 Endocrine | 腎上腺素、皮質醇、胰島素、昇糖素、褪黑激素 | 壓力反應、能量動員、身心雙向橋梁 | ✅ L0（腎上腺素、有晝夜節律的皮質醇） | HPA 軸動態模型 |
| 代謝 Metabolism | 血糖、肝醣、脂肪、能量儲備 | 飢餓、疲勞、認知資源 | ✅ L0（單一能量池 + 血糖） | Bergman 最小模型 |
| 晝夜節律 Circadian | 晝夜相位、時鐘時間 | 警覺度、睡眠時機、荷爾蒙節律 | ✅ L0（無光照輸入的正弦節律） | 光照驅動的振盪器模型 |
| 睡眠恆定 Sleep | 睡眠壓力（process S） | 疲倦、睡眠時機 | ✅ L1 時間常數（Daan 等人，1984） | Borbély 雙歷程模型的完整版本 |
| 呼吸 Respiratory | 呼吸頻率、潮氣量、血氧、CO₂ | 窒息感、恐慌、呼吸調節情緒 | ⬜（目前只有固定的呼吸頻率帶動 RSA） | 化學感受器回饋模型 |
| 體溫 Thermoregulation | 核心 / 皮膚溫度 | 冷熱不適、行為性體溫調節 | ⬜ | Stolwijk 體溫調節模型 |
| 水分與電解質 | 血漿滲透壓、血容量 | 口渴 | ⬜ | — |
| 免疫 Immune | 發炎指標 | 生病行為（疲倦、退縮、食慾下降） | ⬜ | 細胞激素簡化模型 |
| 肌肉骨骼 | 肌力、疲勞、乳酸 | 費力感、運動成本 | ⬜ | — |
| 痛覺 Nociception | 組織損傷 | 疼痛、迴避學習 | ⬜ | — |

## 2. 目前的模型

以下方程式大多是**示意用的玩具模型（L0）**。`relax(x, x*, dt, τ)` 表示 x 以時間常數 τ 指數逼近目標 x*；`OU(τ, σ)` 表示平均為 0、標準差 σ、相關時間 τ 的 Ornstein–Uhlenbeck 過程（兩者都用解析解，任意步長下皆穩定）。
方程式中的數字都是預設參數值；每個參數的名稱、單位、有效範圍與來源見自動產生的 [PARAMETERS.md](PARAMETERS.md)。

### 2.1 心血管 `soma/cardio.py`

```
floor = HR_rest − 8·sleeping                                    （睡眠時靜止心率下降）
HR̄*  = clamp(floor + 40·adrenaline + 70·exertion, floor, 190)
HR̄   ← relax(HR̄, HR̄*, dt, τ = 5 s)                              （平均水準）
HR    = HR̄ + (1 − 0.8·adrenaline) · (3·sin(2π · 0.25 Hz · t) + OU(10 s, 2 bpm))
```

最後一行是**心率變異（HRV）**：呼吸性竇性心律不整（RSA，隨呼吸起伏）加上較慢的波動。腎上腺素會抑制 HRV，如同真實的交感神經活化。靜止時的短期指標約為 SDNN ≈ RMSSD ≈ 37 ms；壓力下 RMSSD 降到約 1 ms（`observe/metrics.py`、`tests/test_variability.py`）。

### 2.2 內分泌 `soma/endocrine.py`

```
adrenaline ← relax(adrenaline, threat, dt, τ = 3 s（上升）/ 40 s（下降）)
baseline   = 0.2 + 0.1 · cos(2π · (hour − 8) / 24)                （早上 8 點最高）
cortisol*  = baseline + (1 − baseline)·0.75·threat
cortisol   ← relax(cortisol, cortisol*, dt, τ = 300 s（上升）/ 1800 s（下降）)
```

上升快、下降慢的不對稱時間常數，是壓力荷爾蒙「來得快去得慢」的最小表現。皮質醇的基線有晨間高峰（早上約 0.30、晚上約 0.11）。皮質醇目前尚無下游讀者，是為記憶鞏固、免疫抑制、代謝等未來模組預留的慢速訊號。

### 2.3 代謝 `soma/metabolism.py`

```
drain    = (1 / 48 h) · (1 + 4·exertion) · (0.9 if sleeping else 1)
reserve  ← clamp(reserve + (food_intake − drain)·dt)
glucose* = (90 + 40·adrenaline) · min(1, reserve / 0.1)
glucose  ← relax(glucose, glucose*, dt, τ = 120 s)
```

48 小時的儲備（校準為一天約三餐）讓一天的消耗約為儲備的一半，夜間 8 小時的睡眠只消耗約 0.15，起床後會餓但不會挨餓。

能量攝取 `world.food_intake` 由環境層的 `world/food.py` 計算：只有在**食物在手邊**且**正在進食**時才有攝取。

```
food_intake = 3×10⁻⁴ /s · world.food_available · motor.eating      （約每 15 分鐘補回 0.3 的儲備）
```

飢餓迴路因此是閉合的：儲備下降 → 內感受的能量不足 → 飢餓 → 看到食物就進食 → 攝取 → 儲備回升 → 飢餓消退。

### 2.4 晝夜節律 `soma/circadian.py`（process C）

```
drive = cos(2π · (hour − 19) / 24)        （晚上 7 點最高，早上 7 點最低）
```

模擬從 `start_hour`（預設早上 8 點）開始。人類內在週期平均約 24.2 小時（Czeisler 等人，1999）；目前沒有光照輸入，因此固定為已同步的 24 小時，時差與輪班要等光照感測模組加入後才能模擬。

### 2.5 睡眠恆定 `soma/sleep.py`（process S）

```
清醒：S ← 1 − (1 − S) · exp(−dt / 18.2 h)
睡眠：S ← S · exp(−dt / 4.2 h)
```

兩個時間常數來自 Daan、Beersma 與 Borbély（1984）。睡意與入睡 / 起床的門檻在心智層的 `Drives` 計算（見 [PSYCHE.md](PSYCHE.md) §4.3），因為那是大腦對 S 與 C 的解讀。門檻值是我們自己的校準（清醒 16 小時、睡 8 小時、約 23 點入睡），**不是**文獻數值。實際行為：每晚約 22:00–22:45 入睡，睡 7.3–7.9 小時，約 06:00 起床；剝奪睡眠後，壓力會累積到在下午強迫入睡（`tests/test_sleep.py`）。

## 3. 從 L0 走向 L1 的工作方式

1. 在 `docs/` 中寫下要採用的已發表模型、方程式與參數表，並附上引用。
2. 實作新模組，**讀寫同一組訊號**（必要時新增訊號並更新 [SIGNALS.md](SIGNALS.md)）。
3. 加入行為測試：重現文獻中的典型反應（例：口服葡萄糖耐受試驗的血糖曲線形狀與峰值時間）。
4. 在模組 docstring 標註保真度等級，在 `ParamSpec.source` 標註每個參數的來源。
5. 除了平均值，也記錄參數的**族群分布**（標準差、範圍、與其他參數的相關）與個體內的**自然波動**，作為日後抽樣個體的依據（見 [VARIABILITY.md](VARIABILITY.md)）。

## 4. 外部生理引擎

Pulse Physiology Engine（Kitware）與 BioGears 都是開源、經驗證的全身生理引擎。與其從零重寫所有器官，長期可行的路線是：

- 以轉接器把外部引擎包成一個（或一組）`Module`，將其輸出映射到 `soma.*` 訊號；
- 自己實作的部分集中在**外部引擎沒有、但對心智重要的介面**：內感受、神經調節、身心雙向耦合。

此路線的取捨（授權、效能、時間步長對齊）會在實際進行時以 ADR 記錄。
