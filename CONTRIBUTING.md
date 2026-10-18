# 貢獻指南 Contributing

歡迎任何形式的貢獻：討論設計、指出理論或生理上的錯誤、補充文獻、撰寫模組或測試。

## 開發環境

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

pytest                     # 測試
ruff check .               # lint
ruff format .              # 格式化
```

## 新增一個模組

1. 選擇所屬的層（`soma/`、`interface/`、`psyche/`、`world/`），遵守 [ARCHITECTURE.md](docs/ARCHITECTURE.md) 中各層的讀寫規則。
2. 繼承 `unbodysoma.core.Module`，宣告 `name`、`rate_hz`、`reads`、`writes`，以及所有會在 `step` 中改變的屬性 `state_fields`（無法直接深複製的狀態如亂數產生器，請覆寫 `get_state` / `set_state`，見 [ADR-0004](docs/adr/0004-explicit-module-state.md)）。
3. 在 docstring 中寫明**保真度等級（L0 / L1 / L2）**；L1 以上須附參考文獻。
4. 新增或修改訊號時，同步更新 [docs/SIGNALS.md](docs/SIGNALS.md)。
5. 加入測試：至少一個行為測試，描述「在什麼情境下，這個模組應該讓系統表現出什麼」；若模組有可變狀態，把它加入 preset 或撰寫快照還原測試。
6. 在 [docs/SOMA.md](docs/SOMA.md) 或 [docs/PSYCHE.md](docs/PSYCHE.md) 中更新對應的方程式與狀態。

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
