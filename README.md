# Unbodysoma

> 一個「心智從身體長出來」的模擬人體引擎。
> *An embodied human simulation engine in which the mind emerges from — and feeds back into — the regulation of a simulated body.*

![status](https://img.shields.io/badge/status-Phase%200%20%C2%B7%20pre--alpha-orange)
![python](https://img.shields.io/badge/python-3.11%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)

---

## 這是什麼？

多數「人體模擬」只做生理（心血管、代謝、藥物動力學），多數「AI 心智」則是沒有身體的符號或語言模型。
**Unbodysoma 想做的是兩者之間的那條迴路**：

- 身體有需要維持的狀態（血糖、體溫、心率、荷爾蒙……）；
- 心智的首要工作是**預測並調節**這些狀態（allostasis），而不是在身體之外下棋；
- 情緒是身體狀態被感知後的結果（interoception → affect），反過來又改變感知、決策與身體本身。

> 核心假設：**心智能力不是外掛在身體上的軟體，而是一個為了讓身體活下去而演化出的調節系統。**
> 詳見 [docs/VISION.md](docs/VISION.md)。

## 目前狀態：Phase 0 — 架構雛形

目前只有一個刻意簡化（L0 玩具等級）但**完整閉環**的最小生物體，用來驗證引擎架構：

```text
環境威脅 → 外感受 → 評估(threat) → 腎上腺素 → 心率↑ → 內感受 → 喚醒度↑ ─┐
                         ↑                                            │
                         └──────── 高喚醒讓同樣的刺激看起來更危險 ◄───────┘
                     評估 → 行動選擇(逃跑) → 體力消耗 → 心率↑、能量↓
```

執行範例（威脅在 60–90 秒出現）的部分輸出：

```text
       t  stimulus    threat   adrenal   HR(bpm)  exertion   arousal   valence
   50.00      0.00      0.01      0.01     65.49      0.00      0.04      0.09
   80.00      0.90      1.00      1.00    157.58      0.80      0.97     -0.80
  120.00      0.00      0.01      0.48     87.30      0.00      0.18      0.09
  300.00      0.00      0.01      0.01     65.61      0.00      0.04      0.09
```

> ⚠️ 現階段所有生理參數都是**示意用的玩具模型**，未經驗證，**不可用於任何醫療用途**。

## 快速開始

```bash
git clone https://github.com/Galen-Chu/Unbodysoma.git
cd Unbodysoma
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

python examples/fear_response.py          # 執行恐懼反應情境
python examples/fear_response.py --csv runs/fear.csv
python examples/lesion_study.py --runs runs/lesion_study   # 干預實驗 + 執行紀錄 + 健康監控
pytest                                     # 執行測試
```

核心引擎**零外部相依**（僅 Python 標準函式庫）。

## 架構總覽

```mermaid
flowchart LR
    subgraph WORLD["World 環境層"]
        W["Scenario<br/>環境刺激"]
    end
    subgraph IFACE["Interface 介面層"]
        EXT["Exteroception<br/>外感受"]
        INT["Interoception<br/>內感受"]
    end
    subgraph PSYCHE["Psyche 心智層"]
        AP["Appraisal 評估"]
        AF["Affect 情感"]
        DR["Drives 驅力"]
        AC["Action 行動選擇"]
    end
    subgraph SOMA["Soma 身體層"]
        EN["Endocrine 內分泌"]
        CV["Cardio 心血管"]
        ME["Metabolism 代謝"]
    end
    W --> EXT --> AP
    AP --> AF
    AP --> AC
    AP --> EN
    AC -->|motor| CV
    AC -->|motor| ME
    EN --> CV
    EN --> ME
    CV --> INT
    ME --> INT
    INT --> AF
    INT --> DR
    DR --> AF
    AF -.->|arousal bias| AP
```

所有模組只透過一條**雙緩衝訊號匯流排（Signal Bus）**溝通，各自以不同頻率運行（神經毫秒級、心血管秒級、內分泌分鐘級、代謝小時級）。

## 觀測與監控

模擬可以被**記錄、監控、倒帶與干預**，而且觀察不會改變結果：

```python
engine = build_minimal_human([Event(60, 90, "world.threat", 0.9)])
HealthMonitor(halt_on="critical").attach(engine)  # 生理 / 數值合理性警報
engine.lesion("interface.interoception")  # 干預：讓心智感覺不到身體
with RunWriter("runs/demo").attach(engine):  # meta.json · signals.csv · events.jsonl
    engine.run(300, until=lambda bus: bus.read("soma.cardio.heart_rate") > 180)
```

詳見 [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md)。
詳見 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 專案結構

```text
src/unbodysoma/
├── core/        引擎核心：Engine、SignalBus、Module 契約、快照、干預
├── soma/        身體層：cardio、endocrine、metabolism …
├── interface/   介面層：exteroception、interoception（未來：motor、proprioception）
├── psyche/      心智層：appraisal、affect、drives、action（未來：memory、attention、self-model）
├── world/       環境層：腳本化情境
├── observe/     觀測：執行紀錄、健康監控（未來：即時儀表板、重播）
└── presets.py   預組裝的生物體
examples/        可執行範例
tests/           單元測試與行為回歸測試
docs/            設計文件與架構決策紀錄（ADR）
```

## 文件索引

| 文件 | 內容 |
|---|---|
| [VISION.md](docs/VISION.md) | 願景、核心假設、設計原則、範圍與非目標 |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | 分層架構、訊號匯流排、排程、模型保真度分級 |
| [SOMA.md](docs/SOMA.md) | 身體層：子系統規劃與目前的模型方程式 |
| [PSYCHE.md](docs/PSYCHE.md) | 心智層：心智能力階梯、理論對應、設計取捨 |
| [SIGNALS.md](docs/SIGNALS.md) | 訊號命名規範與目前的訊號表 |
| [OBSERVABILITY.md](docs/OBSERVABILITY.md) | 觀測與監控：執行紀錄、健康監控、快照倒帶、干預實驗、儀表板規劃 |
| [VARIABILITY.md](docs/VARIABILITY.md) | 變異與統計真實性：避免「平均人」與眾數塌縮、候選參數、分布層級驗收（討論草案） |
| [ROADMAP.md](docs/ROADMAP.md) | 分階段路線圖與待討論的開放問題 |
| [ETHICS.md](docs/ETHICS.md) | 醫療免責、意識宣稱、模擬負面狀態的倫理準則 |
| [REFERENCES.md](docs/REFERENCES.md) | 理論與既有模型參考文獻 |
| [adr/](docs/adr/) | 架構決策紀錄 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 開發流程與規範 |

## 路線圖摘要

| 階段 | 目標 |
|---|---|
| **Phase 0**（目前） | 引擎骨架、最小閉環生物體、文件 |
| Phase 1 | 最小可行生物體：晝夜節律與睡眠、體溫、進食行為、情境設定檔；觀測機制（執行紀錄、健康監控、干預 ✅，儀表板） |
| Phase 2 | 生理保真度：文獻模型（L1）、對照文獻曲線驗證、外部生理引擎轉接 |
| Phase 3 | 會學習的心智：記憶、以內感受為獎賞的學習、預測處理 / 主動推論 |
| Phase 4 | 具身於 3D 世界：感覺運動迴路、物理模擬 |
| Phase 5 | 自我模型、語言與社會互動 |

完整內容見 [docs/ROADMAP.md](docs/ROADMAP.md)。

## 授權

[MIT License](LICENSE) © 2026 Galen Chu

## 免責聲明

本專案為研究與教育用途的軟體實驗。它**不是**醫療器材、**不**提供醫療建議，也**不**宣稱模擬出的系統具有意識或感受。詳見 [docs/ETHICS.md](docs/ETHICS.md)。
