# 自動論文工作流：實作與工程驗證狀態

更新：2026-10-18。對應[研究計劃](harness-optimization-plan.md)。這份紀錄區分「檢查程式可運作」與「研究成果已成立」。

## 2026-10-18 新增實作與邊界

新增 [`run_research_team.py`](../../scripts/run_research_team.py) 作為有預算與輪次上限的真實 Codex CLI 多代理入口。每個角色有獨立 CLI 執行紀錄及 handoff 雜湊；文獻調查後另派獨立全文審查代理，topic survey 和 [`check_prior_art_review.py`](../../scripts/check_prior_art_review.py) 未通過時，不派研究設計或寫作代理。稿件審查也使用新代理程序，並核對新建／更新的審查檔、指定 reviewer ID 和 handoff 雜湊。每輪探索須在 [`experiments.tsv`](../../references/research_protocol.md) 保留舊紀錄並新增有證據雜湊的假說測試與下一步；研究失敗仍可能正確地停止。

本次試點的獨立審稿指出「數值正確、原創性不足」後，研究迴圈新增 `publication_goal`：以原創稿為目標時，先驗審查若只支持重做，會在設計前寫入 `research/contribution-branches.jsonl` 並於剩餘輪次內重新派文獻與全文審查；後期創見／重複否決也回到此分支。設計或推論否決會攜帶審稿理由回到設計。輪次或預算用盡則回報 `contribution-unresolved`，不把換年份或修飾文字當成新貢獻。

新自主稿件須在 `research/package.json` 宣告 `protocol_version: "2"`、`prior_art_review`、`exploration_ledger`。先驗文獻閘門核最近作品的留存 PDF／HTML、來源摘錄與 PDF 頁碼、每個主張和近作的比較；交付時審過的主張須與 manifest 所有核心主張一致。這可查漏與發現部分偽填資料，不能證明下載檔就是網址所示的論文、頁面解釋正確、或真正達到原創。未宣告版本的舊 package 仍按 v1 回放，報告標為 `legacy_protocol: true`；它不是新版自主流程的完成證據。

真實資料試點在 [`experiments/real-data-pilot/2026-10-18`](../../experiments/real-data-pilot/2026-10-18)：使用 BLS 官方失業率與職缺率月度 API 原始 JSON，保留擷取程式、快照雜湊、清理與分析、圖表、LaTeX／PDF 和限制。此案例只做已知 Beveridge 曲線的描述性重現，用來檢驗來源至稿件的鏈條；它不是盲題、因果識別或頂刊原創性成功案例。最終 gate 與代理審核狀態見[案例驗證報告](../../experiments/real-data-pilot/2026-10-18/validation-summary.md)，未通過者照實保留。

此更新後 `python3 -m unittest discover -s tests -p 'test_*.py'` 為 **222 tests OK，4 skipped**；獨立審稿代理另核實實際 Codex CLI 派工收據並從 BLS 原始快照重算結果。它否決此案例作為頂刊原創論文；這一科學判斷不因程式門檻通過而改變。CLI 代理共享檔案系統，仍欠 OS 級隔離、可獨立驗證的來源身分與大樣本受控盲測。以下工程結果是 2026-10-17 的歷史紀錄，不應視為新功能未實作。

目前交付的是 **Skill 指導的研究迴圈、MCP 工具入口與確定性執行／審計核心**，不是從一句研究問題無條件產出頂刊論文。`scripts/run_research_workflow.py` 讀取研究契約，記錄狀態與實際耗時，執行科學障礙測試、乾淨重跑、LaTeX 編譯／審閱檢查與 package 審計，並為失敗關卡產生 `next_tasks`。Agent 依任務繼續蒐證、分析、改稿、重驗；執行器本身不生成研究內容。科學障礙的測試指令成功只表示指令已執行，仍需具名審定與雜湊綁定證據才可標成 `resolved`。完整完成須通過所宣告的全部關卡。

## 工程結果

最新一次[工程實驗報告](../../experiments/workflow-experiments/runs/20261016T161755986577Z/report.md)保存五個案例的產物與失敗原因：

| 案例 | 已驗證 | 未達成 |
|---|---|---|
| 合成 DiD | 結果與表格在臨時副本可重跑；自動 PDF build 通過 | topic／資料來源／文獻／章節覆蓋／診斷／邏輯與逐頁審閱未通過 |
| 談判模型示意稿 | 自動 PDF build 通過 | 非完整論文、非完整證明；文獻、論證圖、章節與逐頁審閱未通過 |
| 合成事件報酬 | 結果與表格在臨時副本可重跑；自動 PDF build 通過 | 無真實事件、有效群聚推論或來源驗證；其餘關卡未通過 |
| CLI 錯誤 | 模擬器可記錄並修補一次不支援的旗標 | 沒有驗證一般性自動除錯能力 |
| 中斷與預算 | 已記錄成本與待辦可在模擬器中保留 | 沒有涵蓋任意程序中斷和外部服務計費 |

在含官方 MCP SDK 的環境中，完整單元／整合測試通過 186 個案例，包含計劃 §8.1 的十類工程情境、預算中止、審閱後文獻修改失效、舊 build 報告不可綁定新稿、缺欄位的 manifest 不得令驗證器崩潰、feasibility profile 的正向完成案例，以及 MCP 工具修復真實失敗 gate 的端到端測試。新增測試確認實證交付拒絕 proxy、稿件需要限制段落、團隊交接綁定檔案雜湊、獨立審查與失敗階段回退。正向案例僅是合成格式測試，不表示來源實質可信。實驗資料均為合成或示意資料；`build_passed` 只代表自動編譯／渲染檢查，沒有真實逐頁審閱。完整 package 在三個稿件案例均維持 `blocked`，這是正確的驗收結果。

`python3 scripts/validate_library.py --json` 回報 19 篇條目與 10 條關係皆有效；`uvx --from skills-ref agentskills validate skills/econ-research-lab` 通過 skill 格式驗證。

## 已落地的安全邊界

- `research/contract.json` 凍結輸入契約；後續更改會中止。package 的研究類型、交付型態與主張範圍須與契約一致。
- 完整稿件必須有至少兩名研究代理與一名獨立審查代理的具名、PI 驗收、雜湊綁定交接。審查須涵蓋創見、重複、設計、推論／證明、邏輯、完整性及稿件中的明確限制。程式可驗證紀錄，無法證明代理身分或審查品質；主代理須用宿主工具實際派工並保留收據。
- 實證、描述、結構估計與重做研究只接受已核驗的真實或受限資料；模擬輸入只供理論驗證或隔離的工程測試。失敗後的 `rework_plan` 寫入 `research/rework-state.json`，指出最早須重做的階段及其下游；主代理需保留舊產物並實際重做。
- 重跑會先複製專案至臨時目錄，移除副本中的指定輸出，再比較原始結果、數值與產物位元組；原工作樹的指定輸出不會被清除。這是**工作副本隔離**，不是作業系統沙箱：帶絕對路徑的腳本仍可寫入其他位置。
- budget 以 ledger 記錄的 wall-clock 秒數累計；各階段後會停止後續工作。單個外部指令仍可能耗時超過剩餘額度，且此數值不是 API 金額。
- Dream-RSI 的候選動作隊列與執行中收據寫入 `research/discovery_tree.state.json`；重啟可接續未完成隊列，遇到執行中斷則先停止核對副作用。有限 CLI 修補會把首次嘗試與重試成本一起計入；多程序並行執行尚未受到跨程序鎖保護。
- MCP 以官方 Python SDK 提供本地 stdio 工具、工作流資源與提示；server 啟動時固定單一 project root。它與 Skill 共用既有 Python gate，不建立第二套研究判準。
- LaTeX 編譯結果與其輸入雜湊綁定，包括 TeX recorder 找到的表格和 BibTeX 文獻。PDF 的視覺審閱須有真實 reviewer、逐頁紀錄與相同雜湊，並需與 release PDF 一致。
- 實驗每次建立新目錄，不覆蓋舊紀錄；未取得的 PDF、資料、授權或審閱不會用虛構內容補齊。

## 下一階段工作

1. **WP1–WP6 的剩餘整合**：建立可由外部審核的契約與不可回寫的證據鏈；補上跨程序鎖、執行中斷後的審核／重試介面與更嚴格的成本預留；將重跑命令放入真正的程序／檔案系統沙箱。驗證器之間需以同一份來源清單與相同版本的結果作為關卡輸入。
2. **WP7 真實研究來源鏈**：依期刊與研究問題蒐集可核驗文獻、資料與授權，保留無法取得來源的缺口。重建一個公開可重跑的原始論文結果，再做有效的設計與推論審查；合成 fixture 不能替代。
3. **WP8 與計劃 §5–6 的受控評估**：凍結題庫與提示，區分有／無 harness 條件，記錄實際成本、停止原因與盲審評分；以完整 working paper／replication package 的真實通過率作主要終點。既有五個工程案例僅是早期 smoke test，不能估計 one-shot 成功率。

執行工程實驗：`python3 experiments/workflow-experiments/run_experiments.py`。每次的 `report.md`、`report.json` 與五個案例的產物會存到新的 `experiments/workflow-experiments/runs/<UTC timestamp>/`。
