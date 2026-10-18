# 0004. 模組必須明確宣告可變狀態

- 狀態：已採用
- 日期：2026-10-18

## 背景

存檔、倒帶、分支實驗與重播，都需要能取出並還原「整個模擬在某一刻的完整狀態」。在 [ADR-0002](0002-double-buffered-signal-bus.md) 之下，匯流排只包含模組的**輸出**；模組內部的積分狀態、遲滯旗標、亂數產生器都藏在各自的 Python 物件裡，引擎無從得知。

MuJoCo 的做法是把模型（`mjModel`，不變）和狀態（`mjData`，會變）完全分開，所有狀態都集中在一份資料結構中。

## 決定

採用較輕量的版本，不強迫模組把狀態搬進共用陣列，而是要求模組**明確宣告**哪些屬性是可變狀態：

- `Module.state_fields: tuple[str, ...]` 列出所有會在 `step` 中改變的屬性；預設的 `get_state` / `set_state` 會對這些屬性做深複製。
- 狀態無法用屬性直接表示時（例如 `random.Random`），模組覆寫 `get_state` / `set_state`。
- `Engine.snapshot()` 回傳 `Snapshot(tick, signals, modules, active_interventions)`；`Engine.restore()` 還原它。
- 以測試把關：執行一段時間後還原快照，比對每個模組的全部屬性，任何漏宣告的狀態都會被抓出來。

## 後果

- ✅ 模擬可以倒帶、分支、從同一點重跑，且結果逐位元相同。
- ✅ 模組作者仍然可以用一般的 Python 屬性撰寫模組。
- ❌ 新增可變屬性卻忘了宣告時，問題只會在測試中被發現，型別系統抓不到。`test_every_mutable_attribute_is_covered_by_module_state` 會涵蓋 preset 中的所有模組；新模組加入 preset 時自然受到保護。
- ❌ 快照目前只存在記憶體中。寫入磁碟需要可序列化的狀態格式（特別是亂數狀態），留待需要時另立 ADR。
- 🔁 若未來為了效能（批次運算、GPU）需要把狀態搬進連續陣列，`state_fields` 已提供了遷移所需的完整清單。
