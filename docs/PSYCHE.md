# 心智層 Psyche

「心智能力」是個很大的詞。本文件把它拆成一條**可以逐層建造、逐層驗證**的階梯，並說明每一層與身體的關係。

## 1. 心智能力階梯

每一層都建立在下一層之上，而且必須能說明它**服務哪一個身體需求**。

| 層級 | 能力 | 與身體的關係 | 狀態 |
|---|---|---|---|
| 微生物級（M0 之下） | 趨性偏置、習慣化、敏感化（非聯結學習） | 身體狀態調整趨性的偏置與反應強度——線蟲、草履蟲、黏菌都有的最簡學習 | ✅（2026-11-18，ADR-0013） |
| M0 反射 | 刺激 → 固定反應 | 直接連結感覺與效應器 | ✅（逃跑、趨近食物） |
| M1 恆定驅力 | 飢餓、口渴、疲倦、體溫不適 | 身體變數偏離設定點的「被感受到的急迫度」 | ✅（飢餓、睡意，皆已閉環） |
| M2 核心情感 | valence（好 / 壞）× arousal（激動 / 平靜） | 內感受的整體摘要 | ✅ |
| M3 評估與注意 | 威脅 / 機會評估、注意力分配 | 身體狀態偏置知覺（高喚醒放大威脅） | ✅（注意力 2026-11-26 補完，§4.12） |
| M4 學習與記憶 | 制約、強化學習、情節記憶、語意記憶 | 以身體狀態改善為獎賞；情緒強度調節記憶強度 | ⬜ |
| M5 預測與規劃 | 預期未來身體狀態、多步規劃 | allostasis：在需求出現前先行動 | ⬜ |
| M6 自我模型 | 身體擁有感、自我 / 非自我區分、後設認知 | 對「自己這個身體」的整合模型 | ⬜ |
| M7 語言與社會 | 自述、溝通、心智理論 | 以語言描述與調節內在狀態；他人作為身體需求的來源 | ⬜ |

> M0–M3 是 Phase 0–1 的範圍；微生物級與 M4 的地基是 Phase 3–4（無脊椎動物級）；M5 是 Phase 5（脊椎動物級）；M6–M7 是 Phase 6（人類級）。階段沿生物能力帶組織，每一階都以可對照文獻行為數據的驗收測試為完成標準（[ADR-0013](adr/0013-subsystem-focus-track.md)）。

## 2. 理論對應

| 理論 | 核心主張 | 在 Unbodysoma 中的對應 |
|---|---|---|
| 軀體標記假說（Damasio） | 身體狀態的訊號引導決策 | 決策模組讀取情感與內感受，而不只讀外部刺激 |
| 情緒建構論（Barrett） | 情緒由核心情感 + 情境概念化建構而成 | 核心情感（M2）與情緒類別分開；情緒類別留給 M4 以上的概念學習 |
| 內感受推論（Seth） | 情緒與自我感來自對身體狀態的預測 | `interface/interoception` 是心智認識身體的唯一途徑，精確度可調 |
| 自由能原理 / 主動推論（Friston） | 生物體透過感知與行動最小化預測誤差 | Phase 5 的統一框架候選：每個模組都改寫為 預測 → 誤差 → 更新 |
| Allostasis（Sterling） | 調節是預測性的，不只是回饋 | M5：根據預期需求提前調整身體 |
| 全域工作空間理論（Baars） | 意識內容 = 在全域廣播中勝出的資訊 | M3 注意力的候選架構：模組競爭進入工作空間 |
| 情感環狀模型（Russell） | 情感可用 valence × arousal 兩軸描述 | `psyche.affect.valence` / `psyche.affect.arousal` |
| 認知架構（ACT-R、Soar、LIDA） | 記憶、產生式規則、認知循環 | M4–M5 記憶與決策結構的參考 |

## 3. 關鍵設計取捨：模組化 vs. 統一原理

**選項 A：模組化認知架構** —— 驅力、情感、評估、記憶各自是一個手寫動態的模組。
✅ 好理解、好除錯、可逐步建造。❌ 參數大量手調，模組間的一致性靠人維持。

**選項 B：統一的主動推論** —— 整個心智是一個階層式生成模型，所有行為來自最小化變分自由能。
✅ 理論優雅、跨模組一致。❌ 很難從零做到可用，計算成本高，除錯困難。

**目前的決定：A 起步，朝 B 演進。**

- Phase 0–2 使用模組化設計，確保迴路完整、行為可解釋。
- 每個模組的介面設計成可以被改寫為「預測 + 預測誤差 + 精確度」的形式（例如內感受訊號未來會同時發布 `value` 與 `precision`）。
- Phase 5 起，逐一將模組替換為主動推論版本，並用同一組行為測試比較兩者。

這個決定已於 2026-11-26 重新檢視：[ADR-0014](adr/0014-modular-primary-through-phase5.md)——模組化維持主架構至 Phase 5 結束，預測編碼由內感受介面滲透引入。

## 4. 目前的模組

### 4.1 評估 Appraisal `psyche/appraisal.py`

```
threat* = clamp(extero.threat · (1 + 0.5·NE) + 1.0·learned)    NE = neuro.norepinephrine（警覺）
                                                               learned = 制約的威脅預期（§4.7）
threat  ← relax(threat, threat*, dt, τ = 0.5 s)
```

警覺（正腎上腺素，整合威脅、痛與心喚醒，見 SOMA §2.10）放大威脅評估 —— 這是身體影響知覺最小的可運作範例，也是一個正回饋迴路，增益刻意保持有界。受傷的個體因此高估輕微線索（過度警覺，`tests/test_neuro.py`）；學會的預期（制約）則像知覺線索一樣進入評估（`tests/test_conditioning.py`）。

### 4.2 情感 Affect `psyche/affect.py`

```
arousal* = clamp(0.6·intero.cardiac_arousal + 0.4·threat + 0.3·pain + 0.15·novelty)
valence* = clamp(0.1 + 0.1·dopamine + 0.4·(serotonin − 0.5) − 0.9·threat − 0.5·hunger − 1.2·pain, −1, 1)
                                                                                      （負面項以飽和聯集合成，見 §5）
τ = 2 s
```

權重都是可調參數（`w_cardiac_arousal`、`w_threat_arousal`、`w_pain_arousal`、`w_novelty_arousal`、`w_threat_valence`、`w_hunger_valence`、`w_pain_valence`、`w_dopamine_valence`、`w_serotonin_valence`，見 [PARAMETERS.md](PARAMETERS.md)）。多巴胺讓「復原感覺良好」（獎賞＝恆定誤差移除，SOMA §2.10）；血清素提供慢速的情緒色調；新奇（習慣化後的刺激效價，§4.6）是朝向反應的來源。
兩個目標值各自加上一個緩慢的自發波動 `OU(60 s, σ = 0.03 / 0.02)`，所以即使什麼事都沒發生，心情也不會是一條直線。

### 4.3 驅力 Drives `psyche/drives.py`

```
hunger*     = clamp((intero.energy_deficit − 0.2) / 0.6) · (1 − 0.5·sleeping)
hunger      ← relax(hunger, hunger*, dt, τ = 30 s)
thirst*     = clamp((intero.water_deficit − 0.15) / 0.5) · (1 − 0.5·sleeping)
thirst      ← relax(thirst, thirst*, dt, τ = 30 s)
discomfort* = clamp((|intero.thermal| − 0.1) / 0.5)          （冷或熱都算）
discomfort  ← relax(discomfort, discomfort*, dt, τ = 60 s)

H = 0.573 + 0.1·C,  L = 0.193 + 0.1·C                 （入睡 / 起床門檻，C = intero.circadian）
sleepiness* = clamp((S − L) / (H − L), −1, 1)          （S = intero.sleep_pressure）
sleepiness  ← relax(sleepiness, sleepiness*, dt, τ = 300 s)
```

- 睡意在 S 碰到入睡門檻時為 1、降到起床門檻時為 0，再低就轉為負值（休息足夠），這正是結束睡眠的訊號。
- 睡意必須經過時間積分：把每一刻的感知雜訊直接送進行動選擇的指數型轉換率，會讓睡眠在半夜隨機結束（見 [ADR-0007](adr/0007-probabilistic-action-selection.md)）。
- 睡眠時感受到的飢餓與口渴減半，醒來後約 30 秒內恢復，形成「起床就想吃早餐」的行為。
- 情感的 valence 也會因口渴（權重 0.5）與溫度不適（權重 0.4）而下降。

### 4.4 行動選擇 ActionSelection `psyche/action.py`

八個行動以效用競爭（[ADR-0007](adr/0007-probabilistic-action-selection.md)）；只有前提成立的行動才可選：

| 行動 | 前提 | 效用 | 輸出 |
|---|---|---|---|
| `idle` | — | 0（基準） | — |
| `flee` | — | `2.5 · (threat − 0.4) + 1.0 · pain` | `motor.exertion → 0.8` |
| `eat` | 感覺到食物在手邊 | `2.0 · (hunger − 0.35)` | `motor.eating = 1` |
| `explore` | 手邊沒有食物 | `1.5 · (hunger − 0.4)`（覓食） | `motor.exertion → 0.3` |
| `drink` | 感覺到水在手邊 | `2.0 · (thirst − 0.3)` | `motor.drinking = 1` |
| `seek_water` | 手邊沒有水 | `1.5 · (thirst − 0.35)`（找水） | `motor.exertion → 0.3` |
| `seek_shelter` | 知道有庇護所，且不在裡面 | `max(1.5 · (discomfort − 0.3), 4 · (sleepiness − 0.8), 1.0 · pain)` | `motor.exertion → 0.3` |
| `sleep` | — | 清醒時 `8 · (sleepiness − 0.95)`，在已知庇護所之外再減 0.5；睡著時 `min(1, 5 · sleepiness)` | `motor.sleeping = 1` |

- 目前的行動有 `stickiness = 0.1` 的加成，進食與飲水再各加 `0.4` 的承諾加成，形成「吃（喝）到飽才停」的遲滯。
- 回庇護所有三個理由：冷熱不適、「快想睡了」、或受傷了（痛覺驅動的退避）。睡意那條讓生物體在入睡門檻前先回家，所以在網格世界中 100% 的睡眠都發生在庇護所內；痛覺那條讓被掠食者擦撞到的個體回家休息（`tests/test_nociception.py`）。
- **切換是連續時間的過程**：從 a 轉到 b 的速率為 `r₀ · exp((u_b − u_a) / 2T)`，`T = 0.015`、`r₀ = 1/60 s⁻¹`。行為因此不受決策頻率影響，長期的時間分配等於 `softmax(u, T)`（即發布的 `psyche.action.p_*`），`T = 0` 則重現眾數塌縮。
- 睡眠的效用上限（1.0）低於完全威脅下的逃跑效用（1.5），所以危險永遠叫得醒。
- 被提早叫醒時（睡意仍 > 0.05），30 分鐘內可以再度入睡；自然醒（睡意 ≤ 0）則不會。
- 例：逃跑會打斷進食，威脅過去後若仍飢餓就回去吃（`examples/feeding.py`）；同一情境下不同種子的個體結束一餐時的飽足程度不同（`tests/test_policy.py`）。

### 4.5 導航 Navigation `psyche/navigation.py`（網格世界）

把選中的行動變成移動指令 `motor.move_x / move_y`：

- `flee`：朝感覺到的威脅反方向全速跑；
- `explore` / `seek_water`：朝感覺到的最近食物 / 水源走（半速）；感覺範圍內沒有時，以相關隨機漫步搜尋（方向以 `wander_sigma` 擴散）；
- `seek_shelter`：朝庇護所走。庇護所的方向**永遠已知**，這是刻意的假設，代表動物記得自己巢穴的位置（歸巢能力）；食物與水則必須在感覺範圍內才看得到；
- 其他行動：停在原地。

在網格世界裡，這讓「飢餓 → 搜尋 → 找到食物點 → 進食」與「掠食者出現 → 逃離 → 稍後回來」成為完整的感覺運動迴路（`scenarios/grid_72h.toml`）。

### 4.6 習慣化 Habituation `psyche/habituation.py`（2026-11-18）

```
habit'  = 0.12·stimulus − habit / τ_recovery        （τ_recovery = 150 s）
novelty = clamp((1 − habit) · stimulus)
```

最簡單的學習形式，從線蟲到人都有：重複出現的無害刺激失去朝向價值。`world.stimulus` 是無害刺激的強度（劇本世界以事件驅動；網格世界暫為 0），暴露量隨呈現累積、休息時以分鐘級時間常數自發恢復；被感受到的新奇（novelty）以小權重（0.15）進入情感的 arousal——第一次的敲擊讓人一驚，第十次就無感。與痛覺模組內建的敏感化一起，構成 Phase 3 非聯結學習的完整一對。錨點：Rankin 等（2009）的行為準則與線蟲敲擊退縮文獻（Ardel & Rankin, 2010）。實測（`tests/test_habituation.py`）：第十次呈現的新奇降至首次的四成以下；二十分鐘休息後大幅恢復；呈現間隔越短習慣化越深。單一刺激通道，因此刺激特異性與去習慣化（dishabituation）留給 Phase 4 的線索身分。

### 4.7 制約 `psyche/conditioning.py`（2026-11-26，Phase 4）

```
ΔVᵢ = 0.05 · csᵢ · (λ·US − Σⱼ Vⱼ·csⱼ)     （連續時間版 Rescorla–Wagner：預測誤差驅動、線索顯著性加權）
防禦軌道：US = world.damage，λ = 1.0
獎賞軌道：US = neuro.relief，λ = 1.0（預測與 relief 同尺度，餵給多巴胺 RPE）
deep ← 非對稱弛豫向 V（上升 τ = 900 s、下降 τ = 24 h）        （固化痕跡）
休息（線索持續缺席 > 120 s）時：V 單向漂移回 0.7·deep（τ = 600 s）  （自發恢復）
```

兩條線索（`world.stimulus`＝A、`world.stimulus_b`＝B；情境檔可用 `[[stimuli]]` 糖衣，見 SCENARIOS.md）。**防禦軌道**的總預測進入評估模組（`w_learned_threat`＝1.0）——制約線索單獨出現即引發威脅評估、負面情感與逃跑傾向（制約恐懼），消弱後隨之消失。**獎賞軌道**的預測進入多巴胺：δ＝relief−預測（Schultz 等, 1997）——被預測的復原不再驚喜，線索單獨出現則瞬間低於基線（遺漏 dip，且被證偽的預測在數十秒內自我消弱）。實測（`tests/test_conditioning.py`）：獲得（20 次配對 V→0.87）、消弱（15 次未增強呈現降至 0.2 以下）、自發恢復（20 分鐘休息部分恢復）、阻斷（Kamin：已確立線索使新線索只學到對照組的四成以下）、制約恐懼的情感與逃跑效應、預測壓制 DA 爆發與遺漏 dip。

**界限（誠實聲明）**：純 RW 沒有時序信用——US 之前的線索時間會被當作消弱（配對因此採同時呈現），跨試次的預期性多巴胺（爆發移到線索出現時）需要 TD(λ) 的狀態表徵，與注意／規劃一起留給 Phase 5。

### 4.8 操作制約 `psyche/instrumental.py`（2026-11-26，Phase 4）

```
eligibility[a] ← max(selected_a, eligibility · e^(−dt/20 s))        （行動中的資格痕跡）
rising  = max(0, pain − pain_trailing（τ = 5 s))                     （痛覺的上升沿＝新傷害）
outcome = neuro.relief − 1.0·rising
value[a] ← clamp(value[a] + dt·0.01·eligibility[a]·outcome − dt·value[a]/1800 s, −1, 1)
u_a ← u_a + 0.5·value[a]                                            （行動選擇的效用項）
```

Thorndike 效果律的最小形式：資格痕跡把行動與數十秒後到達的結果橋接起來，滿足（relief）增強該行動的價值、厭惡（痛的**上升沿**）削弱之；價值隨時間遺忘（消弱）。懲罰以「新出現的痛」為準而非持續的悶痛——帶傷回家一整天的個體不該因此學會討厭走路、睡覺與進食（grid_72h 的教訓：持續痛懲罰一切行動會讓生物體癱瘓至餓死）。實測（`tests/test_instrumental.py`）：逃跑被疼痛懲罰後，輕微線索引發的逃跑傾向降為對照組的一半以下；進食帶來復原後，進食行動獲得價值；痕跡衰減後的結果得不到信用；無增強時價值遺忘。**界限**：信用只在行動層級——逃跑時追上來的痛也會稍微懲罰逃跑（痕跡無法知道逃跑是對痛的*反應*）；地點層級的信用是場所記憶（§4.10）的工作，兩者互補。

### 4.9 情節記憶 `psyche/memory.py`（2026-11-26，Phase 4）

```
intensity = max(|valence|, pain, 0.5·arousal)
capture：intensity > 0.55 且距上次 > 300 s → 存（t, valence, arousal, pain, strength = intensity）
strength ← strength·(1 − dt/τ)（τ = 48 h）；容量 64，滿則遺忘最弱者
mood_congruence = Σ strength·similarity(現在, 情節)·sign(情節.valence)
valence += 0.1·mood_congruence                                      （情境一致的回憶染當下）
```

BACKLOG §5「情節記憶表徵」的最小答案：**符號—混合**——每個情節是時間戳記的核心情感與痛覺快照，強度由情緒強度決定（McGaugh, 2004：情緒激發的事件固化更強、記得更久），提取具情境一致性（現在的狀態重新啟動相似的情節，其符號拉動 valence——低落的心情召回低落的記憶，也是低落自我延續的機制）。向量嵌入、重播式固化與前瞻使用（Phase 5 的 allostasis）待有消費者再引入。實測（`tests/test_memory.py`）：平靜的一小時不留任何情節；強威脅各留一個且第二次威脅時提取為負；強事件的提取大於弱事件；有記憶者重訪壞情境時 valence 低於失憶對照；情節衰減但比事件本身長命。

### 4.10 場所記憶 `psyche/place_memory.py`（2026-11-26，Phase 4）

```
rising  = max(0, pain − pain_trailing（τ = 10 s))                    （痛覺上升沿——傷在何處發生）
danger[cell] ← clamp(danger[cell] + 0.02·rising·dt)（全場衰減 τ = 3 天）
avoid = Σ 鄰近 danger·(反方向)/dist²        （半徑 4 格內的排斥向量場）
導航：目標方向 + clamp(1.5·avoid, |·| ≤ 0.6)  （折向遠離，但鉗制在目標強度之下）
```

認知地圖的最小形式（O'Keefe & Nadel, 1978 的譜系）：一張覆蓋世界的純量危險場，痛的上升沿在事發位置沉積（帶著舊傷走過的地方不會被誤標）、以天為尺度衰減；導航把目標導向的移動折向遠離附近的危險質量，且**鉗制在目標強度之下**——謹慎減慢並彎折接近的路徑，但飢餓的個體永遠能穿過已知的危險覓食場（風險敏感覓食；grid_72h 的教訓：未鉗制的排斥會把生物體擋在進食半徑外活活餓死）。威脅知覺迴避*看到的*危險，這裡迴避*經歷過的*危險——Phase 4 的場所趨避閉環。實測（`tests/test_place_memory.py`）：痛標記該地；排斥向量指向離開危險的方向；危險以天衰減；**對稱的兩個食物點、其中一個會痛——一天半後，有記憶的個體把進食移往安全點，失憶的孿生子持續兩邊餵食**。

### 4.11 預期 `psyche/anticipation.py`（2026-11-26，Phase 5）

```
bin[h] ← bin[h] + (實測值 − bin[h])·dt/τ_exposure（τ = 3 h 的暴露）
hunger_pred / threat_pred = bin[當前時鐘小時 + 1]
hunger* += 0.6·hunger_pred                                    （餐前飢餓——頭期效應的最小形式）
u_seek_shelter += 1.0·threat_pred                              （危險時段前先回家）
```

Allostasis 的最小誠實形式（Sterling, 2012）：以 24 個小時格學習飢餓與痛的晝夜輪廓（暴露約三天收斂），讀**下一小時**的預測——在需求發生前先行動。預期飢餓進入驅力（在慣常用餐時刻前就覺得餓，事先覓食）、預期痛進入庇護所效用（在慣常的掠食者時刻前回家）。實測（`tests/test_anticipation.py`）：三天的固定時刻痛教會該小時；站在 10:54 就預期即將到來的飢餓；連續兩天固定時刻供餐後，第三天餐前一小時飢餓上升；**網格完成情境：每天同一時刻造訪的掠食者，第三天生物體在其時刻前一小時已經在庇護所**——當下沒有任何線索，只有學到的時刻表。

### 4.12 注意力 `psyche/attention.py`（2026-11-26，M3 補完）

```
salience_d = 該域強度（威脅、痛、飢餓、口渴、冷熱、睡意）
share ← softmax((salience + 0.5·salience_focus)/0.1)，贏家切換需超越 0.15（遲滯）
threat* ×= 1 + 0.5·(share_threat − 1/6)                        （被注意的威脅讀起來更大）
choice temperature ×= 1 − 0.3·focus_share                      （專注使選擇更果斷）
```

全域工作空間的最小形式（Baars, 1988）：六個域以顯著性競爭廣播，softmax 份額有界、贏家的持續加成**乘以其自身顯著性**（空場會釋放焦點而非鎖死幽靈）、挑戰者需明確超越才換焦（遲滯）。兩個消費者：評估（注意到的威脅讀起來更大——注意力偏置知覺）與行動選擇（專注降低選擇溫度）。實測（`tests/test_attention.py`）：痛占據廣播且痛過去後放手；強痛之下輕微威脅搶不走焦點、痛退後威脅接手；同一輕微威脅，注意力被痛占走時讀值顯著低於注意力空閒時。

## 5. 待討論的問題

- 情緒類別（恐懼、憤怒、悲傷……）要預先定義，還是讓它從核心情感 + 情境中被學出來？
- 記憶要用什麼表徵？向量嵌入、符號事件，還是兩者並存？
- 學習的獎賞訊號是「恆定誤差的減少」就夠了，還是需要額外的好奇心 / 資訊增益項？——**最小版已實作（2026-11-18）**：`neuro.dopamine`＝被移除的總恆定誤差（能量 0.4／水分 0.3／體溫 0.15／睡壓 0.15 的加權，SOMA §2.10），以誤差低於自身慢基線（τ = 300 s）度量「正在復原」；好奇心項保持開放。
- 語言模型若要接入，如何確保它是「被身體約束的表達」而不是「無視身體的角色扮演」？
- 語言模型有眾數塌縮的傾向：需要符合人類分布的**選擇**應由心智層的機率模型決定，LLM 只負責表達（見 [VARIABILITY.md](VARIABILITY.md) §9）。
- **多個需求應如何合成情感？——已決定（2026-11-16，飽和式）。** 原問題：valence 若是各需求代價的線性加總，三個「中等」需求就會變成「強烈負面」，72 小時情境中清晨又餓、又渴、又冷地出門時出現數分鐘 valence < −0.5。以行為資料裁決（`grid_72h` 對照實驗）：線性加總下，清醒時段 valence < −0.5 占 0.37 %、最低 −0.71；飽和聯集 `1 − ∏(1 − pull)` 下占 0.17 %、最低 −0.53——多需求人工產物減半，而單一威脅下的反應不變（恐懼情境 valence 仍 < −0.5）。實作為 `Affect.need_saturation`（0＝線性、1＝飽和，可連續混合），預設 1.0。
