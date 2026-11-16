# 0010. 世界來源：手工情境��或外部產生器的 TOML

- 狀態：已採用
- 日期：2026-11-16

## 背景

世界層的資源（食物、水、庇護所、危險區）由情境檔手工列舉（ADR-0008）。[WORLDGEN.md](../WORLDGEN.md) 的分析指出：族群實驗（Phase 2）與學習心智（Phase 3）需要「同一套規則、不同種子」的世界變體，而程序化世界生成不是本引擎的職責。2026-11 起，[sanctuary-g-code](https://github.com/Galen-Chu/sanctuary-g-code) 以獨立專案實作決定論世界產生器，其輸出即本專案的情境檔格式（管線血統：abyssal-garden，見 WORLDGEN.md）。

## 決定

- 世界來源有兩種，地位等價：(1) 手工描述的情境檔（現狀）；(2) 外部產生器產生的情境檔。兩者都只是 TOML，通過同一套嚴格驗證（config.py 的允許鍵清單）。
- **本專案不對任何世界產生器建立程式相依**：耦合只存在於 TOML 鍵集契約，由產生器端單向保證（sanctuary 的 `toml_out` 與其 tomllib 往返測試），本專案以驗證器把關。
- sanctuary-g-code 為參考實作；任何輸出能通過驗證的產生器一視同仁。
- 產生的世界可以收進 `scenarios/`（供驗證與示範），檔頭必須保留產生器的 provenance 註記（產生器版本、preset@版本、種子、重現指令）；作為資料檔提交，不構成外部相依。

## 後果

- ✅ 族群實驗可以「N 個體 × M 個世界」：種子同時決定個體與世界，兩者都在 `meta.json` 的可追溯鏈內。
- ✅ 世界生成的演化（統計驗收、地形、3D）在 sanctuary 進行，不增加本引擎的複雜度。
- ✅ `scenarios/` 的 CI 驗證自動覆蓋外部世界（首例：`sanctuary_meadow_s1.toml`）。
- ❌ 鍵集契約是雙邊凍結的：本專案改動 `_WORLD`／`_FOOD`／`_WATER`／`_SHELTER`／`_HAZARD` 允許清單時，需同步 sanctuary 的 `toml_out`（其測試會抓出），反之亦然；破壞性變更應先在此以 ADR 提出。
