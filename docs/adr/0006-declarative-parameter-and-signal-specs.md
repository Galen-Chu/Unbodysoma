# 0006. 參數與訊號的宣告式規格

- 狀態：已採用
- 日期：2026-10-22

## 背景

在此之前，參數只是各模組 `__init__` 的預設值，訊號的單位與範圍只寫在人工維護的 `SIGNALS.md`。這造成三個問題：

1. **可重現性缺口：** 執行紀錄 `meta.json` 只記錄模組類別，沒記錄參數值。改了一個參數，紀錄裡看不出來。
2. **文件會脫節：** 人工維護的訊號表已經漏掉讀取者（例如 `psyche.affect` 讀取 `psyche.appraisal.threat`，但表上沒寫）。
3. **後續工作缺少基礎：** TOML 設定檔需要知道哪些參數可以設定；[VARIABILITY.md](../VARIABILITY.md) 的族群抽樣需要每個參數的範圍與來源；健康監控需要每個訊號的合理範圍。

## 決定

- 新增 `core/specs.py`：
  - `ParamSpec(name, default, unit, lo, hi, description, source)`：一個可調參數。
  - `SignalSpec(key, unit, lo, hi, description)`：一個輸出訊號的意義與有效範圍。
- 模組宣告 `params`（每個 `__init__` 參數一個 `ParamSpec`，並以同名屬性保存）與 `signal_specs`（描述它寫入的訊號）。原本寫死在 `step()` 裡的權重（例如情感模組的 0.6 / 0.4 / 0.9 / 0.5）一律改為宣告的參數。
- `Engine.add()` 在註冊之前驗證：參數值落在有效範圍內、`signal_specs` 只描述自己寫入的訊號。驗證失敗時引擎狀態不變。
- `RunWriter` 在 `meta.json` 中記錄每個模組的參數值（`ScriptedWorld` 則記錄事件時間軸）與所有訊號規格。
- `HealthMonitor` 預設依 `SignalSpec` 的範圍為每個訊號加上一條 critical 規則：超出有效範圍代表模型錯誤，不是生理異常。
- `python -m unbodysoma.catalog` 由規格產生 `SIGNALS.md` 的登記表與整份 `PARAMETERS.md`；`--check` 供 CI 使用。

保留明確的 `__init__` 參數，而不是由規格自動產生建構子：這讓型別檢查與 IDE 補全照常運作。代價是預設值寫了兩次，因此以測試把關。

## 後果

- ✅ 執行紀錄完整描述了「用什麼參數、什麼情境」跑出這個結果。
- ✅ 文件由程式碼產生，測試與 CI 會擋下過時的文件。
- ✅ 參數有了範圍與來源欄位，族群抽樣與設定檔可以直接建立在上面。
- ❌ `ParamSpec` 與 `__init__` 預設值重複；`test_param_specs_match_the_constructor` 會抓出兩者不一致。
- ❌ 目前所有來源都是「L0 toy value」。來源欄位要等 L1 模型引入文獻參數後才有實質內容。
- 🔁 `ParamSpec` 目前只有單一預設值；[VARIABILITY.md](../VARIABILITY.md) 規劃的族群分布（分布族、標準差、相關）會在族群執行器實作時擴充，屆時另立 ADR。

## 相關

同一輪開發中，觀察者與中斷條件改為接收唯讀的 `BusReader`，[ADR-0005](0005-read-only-observation-logged-intervention.md) 所述「觀察者不得寫入目前只是約定」的限制因此改由程式強制。
