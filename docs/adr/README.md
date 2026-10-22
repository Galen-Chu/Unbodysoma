# 架構決策紀錄 ADR

每一個難以反悔、或會影響多個模組的決策，都用一份簡短的 ADR 記錄「當時的背景、決定了什麼、為什麼、代價是什麼」。

| # | 標題 | 狀態 |
|---|---|---|
| [0001](0001-python-first-prototype.md) | 以 Python 撰寫原型，核心零外部相依 | 已採用 |
| [0002](0002-double-buffered-signal-bus.md) | 模組只透過雙緩衝訊號匯流排溝通 | 已採用 |
| [0003](0003-multi-rate-fixed-step-scheduling.md) | 固定步長、多速率排程 | 已採用 |
| [0004](0004-explicit-module-state.md) | 模組必須明確宣告可變狀態 | 已採用 |
| [0005](0005-read-only-observation-logged-intervention.md) | 觀察只讀，干預經由引擎並被記錄 | 已採用 |
| [0006](0006-declarative-parameter-and-signal-specs.md) | 參數與訊號的宣告式規格 | 已採用 |

## 格式

新增 ADR 時複製以下結構，檔名為 `NNNN-kebab-case-title.md`：

```markdown
# NNNN. 標題

- 狀態：提議中 / 已採用 / 已取代（被 NNNN 取代）
- 日期：YYYY-MM-DD

## 背景
## 決定
## 後果
```

ADR 一經採用就不修改內容；若決定改變，新增一份 ADR 並把舊的標為「已取代」。
