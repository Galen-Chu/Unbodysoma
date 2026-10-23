# 0009. 快照存檔、重播驗證與選用的視覺化相依

- 狀態：已採用
- 日期：2026-10-25

## 背景

[ADR-0004](0004-explicit-module-state.md) 讓模擬可以在記憶體中存檔與倒帶，但留下兩個缺口：快照無法寫入磁碟（長時間模擬無法中斷後續跑），也沒有辦法驗證「一份執行紀錄真的能被重現」。另外，即時觀看模擬需要外部工具，而 [ADR-0001](0001-python-first-prototype.md) 要求核心零外部相依。

## 決定

1. **快照檔**（`core/persist.py`）：`save_snapshot` / `load_snapshot` 寫出嚴格 JSON（`allow_nan=False`）。JSON 無法直接表示的值以標記物件保存並可完整還原：亂數產生器 `{"__random__": …}`、tuple `{"__tuple__": […]}`、非有限浮點數 `{"__float__": "inf"}`。無法保存的型別與衝突的保留鍵會直接報錯，而不是默默遺失狀態。
2. **重播驗證**（`config.replay`、`python -m unbodysoma replay <紀錄>`）：執行紀錄保存情境檔原文、SHA-256、種子與實際執行長度；重播時以同一份設定重跑，並逐位元比對 `signals.csv` 與 `events.jsonl`，回報第一個不一致的位置。原文與雜湊不符時拒絕重播。版本或 git commit 不同時只發出警告，因為那正是重播要檢查的情況。
3. **視覺化是選用相依**：`observe/rerun.py` 只在被使用時才匯入 `rerun`；安裝方式為 `pip install "unbodysoma[viz]"`，版本固定在 `rerun-sdk==0.40.*`，因為 Rerun 的 API 在小版本之間會變動（例如 0.23 起 `set_time_seconds` → `set_time`、`Scalar` → `Scalars`）。核心仍然零外部相依。

## 後果

- ✅ 多日模擬可以存檔、關閉程式、之後接著跑，結果與不中斷完全相同（`test_a_saved_snapshot_resumes_exactly_in_a_new_process`）。
- ✅ 可重現性從「應該成立」變成「可以檢查」：竄改紀錄中的一個數值（1e-9 的差異）也會被抓到。
- ✅ 不需要安裝視覺化工具也能使用全部核心功能；沒有安裝時會給出明確的安裝提示。
- ❌ 快照檔與模組的狀態欄位綁定：模組的 `state_fields` 改變後，舊的快照檔無法載入到新版本。目前不做格式遷移；需要時另立 ADR。
- ❌ Rerun 升級到新的小版本時，轉接器需要重新對照 API 並更新版本限制。
