# 0008. 以 TOML 情境檔描述實驗

- 狀態：已採用
- 日期：2026-10-24

## 背景

每個實驗原本都要寫一支 Python 腳本：選預設生物體、改參數、排事件、加干預、掛監控。這讓非程式背景的研究者難以參與，也讓「這次實驗到底是什麼設定」散落在程式碼裡。

## 決定

- 實驗以 TOML 檔描述（格式見 [SCENARIOS.md](../SCENARIOS.md)），由 `unbodysoma.config` 解析、建構並執行；Python 標準函式庫內建 `tomllib`，核心仍零外部相依。
- **嚴格驗證**：未知的鍵、型別錯誤、只適用於其他預設的區段（例如網格預設用了 `[[events]]`）都會報錯，並指出位置（例如 `events[0]: unknown key(s) ['strt']`）。載入時就實際建構一次引擎，讓未知的模組、參數、訊號與超出範圍的參數在執行前就被抓到。實驗定義中被默默忽略的錯字，比當場報錯更糟。
- **與 Python API 完全等價**：情境檔只是 `build_minimal_human` / `build_grid_human`、`clamp` / `lesion`、`HealthMonitor` 的另一種寫法，同一個實驗兩種寫法的結果逐位元相同（`test_a_scenario_file_is_exactly_the_python_experiment`）。
- **可追溯**：執行紀錄的 `meta.json` 保存情境檔的完整原文與 SHA-256。
- 命令列：`python -m unbodysoma run <檔案> [--out 目錄] [--seed N] [--hours H]` 與 `python -m unbodysoma validate <檔案…>`。

## 後果

- ✅ 實驗設定是一份可閱讀、可 diff、可審查的資料檔；CI 會驗證 `scenarios/` 中的每一份檔案。
- ✅ 一份執行紀錄就足以重建它來自哪個實驗。
- ❌ 情境檔只能使用既有的預設生物體；要組裝全新的模組組合仍需寫 Python。未來若需要，可再加入 `[[modules]]` 區段，屆時另立 ADR。
- ❌ 解析器的允許鍵清單需與 `FoodPatch`、`Hazard` 等資料類別同步維護；欄位不一致會由測試抓出。
