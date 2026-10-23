# 貢獻指南 Contributing

歡迎任何形式的貢獻：討論設計、指出理論或生理上的錯誤、補充文獻、撰寫模組或測試。

## 開發環境

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pip install -e ".[viz]"      # 選用：Rerun 即時檢視

pytest                     # 測試（含數分鐘的多日模擬）
pytest -m "not slow"       # 快速測試：略過多日模擬
ruff check .               # lint
ruff format .              # 格式化
mypy                       # 型別檢查（strict）
python -m unbodysoma.catalog   # 修改參數或訊號規格後，重新產生 docs/SIGNALS.md 與 docs/PARAMETERS.md
python -m unbodysoma validate scenarios/*.toml   # 檢查情境檔
python -m unbodysoma replay runs/<紀錄>          # 驗證一份執行紀錄可以逐位元重現
```

CI 會依序執行 lint、格式、型別檢查、文件是否過時、測試與所有範例；請在提交前先在本機跑過。

## 新增一個模組

1. 選擇所屬的層（`soma/`、`interface/`、`psyche/`、`world/`），遵守 [ARCHITECTURE.md](docs/ARCHITECTURE.md) 中各層的讀寫規則。
2. 繼承 `unbodysoma.core.Module`，宣告 `name`、`rate_hz`、`reads`、`writes`，以及所有會在 `step` 中改變的屬性 `state_fields`（無法直接深複製的狀態如亂數產生器，請覆寫 `get_state` / `set_state`，見 [ADR-0004](docs/adr/0004-explicit-module-state.md)）。
3. 為每個 `__init__` 參數宣告一個 `ParamSpec`（同名、同預設值，並以同名屬性保存），為每個寫入的訊號宣告一個 `SignalSpec`。不要把數值常數寫死在 `step()` 裡；可調的值都應該是參數（見 [ADR-0006](docs/adr/0006-declarative-parameter-and-signal-specs.md)）。
4. 若模組使用亂數，每個獨立的通道使用各自的亂數串流，避免新增通道改變既有結果。隨機性若會進入行動選擇等**指數型**的環節，先做時間積分（見 [ADR-0007](docs/adr/0007-probabilistic-action-selection.md)）。建構子中描述結構而非可調模型值的參數（例如世界配置、感覺通道），列在 `config_args`，不需要 `ParamSpec`。
5. 在 docstring 中寫明**保真度等級（L0 / L1 / L2）**；L1 以上須在 `ParamSpec.source` 與 [REFERENCES.md](docs/REFERENCES.md) 附上參考文獻。
6. 執行 `python -m unbodysoma.catalog` 重新產生 [docs/SIGNALS.md](docs/SIGNALS.md) 與 [docs/PARAMETERS.md](docs/PARAMETERS.md)。
7. 加入測試：至少一個行為測試，描述「在什麼情境下，這個模組應該讓系統表現出什麼」；若模組有可變狀態，把它加入 preset 或撰寫快照還原測試。
8. 在 [docs/SOMA.md](docs/SOMA.md) 或 [docs/PSYCHE.md](docs/PSYCHE.md) 中更新對應的方程式與狀態。

## 新增一個情境

在 `scenarios/` 加一份 TOML 檔（格式見 [docs/SCENARIOS.md](docs/SCENARIOS.md)），以 `python -m unbodysoma validate` 檢查；測試會自動驗證 `scenarios/` 中的每一份檔案。若情境代表一個行為主張，請另外寫驗收測試（例：`tests/test_phase1.py`）。

## 架構決策

影響多個模組或難以反悔的決定（新的訊號型別、排程方式、外部相依、核心語言……），請先在 Issue 中討論，再以 [ADR](docs/adr/) 記錄。

## Commit 規範

採用 [Conventional Commits](https://www.conventionalcommits.org/)：

```
feat(soma): add Borbély two-process sleep model
fix(core): reject zero rate_hz
docs(psyche): describe attention module design
test: add circadian regression scenario
```

## 行為準則

保持尊重與建設性。批評針對想法與程式碼，不針對人。
