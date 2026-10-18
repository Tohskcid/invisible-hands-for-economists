# 真實資料試點驗證結果（2026-10-18）

這個案例以 BLS 官方月度失業率與職缺率的留存 API 快照，製作一篇三頁 Beveridge 曲線描述性重做稿。研究問題、文獻、原始資料、清理程式、結果、表圖、LaTeX／PDF、探索紀錄與代理審稿分別留存。它刻意檢驗已知問題的研究鏈條，**不構成從新研究問題 one-shot 產出頂刊論文的成功證據**。

## 結果

| 驗證面向 | 結果 | 證據 |
| --- | --- | --- |
| 先驗文獻與時間 | 通過「描述性重做」分類；`novelty_certified=false` | [`research/prior-art-review.json`](research/prior-art-review.json)、[`research/topic-survey.json`](research/topic-survey.json)；獨立代理核對 3 篇全文、12 個主張×文獻對照格。NBER 來源只支持 2023 年 10 月，故保留月份精度。 |
| 真實資料及重算 | 通過 | [`data/raw/`](data/raw/)、[`research/data-provenance.json`](research/data-provenance.json)、[`research/replication.json`](research/replication.json)。288 個配對月份；主要帶寬的前期 48 個月均值 4.095833%，後期 35 個月均值 5.700000%，差 1.604167 個百分點。獨立代理另從原始 JSON 重算相同數值。 |
| 試錯與限制 | 通過紀錄驗證 | [`research/experiments.tsv`](research/experiments.tsv) 留存兩輪試驗及被放棄的持續性假說；稿件明確限制帶寬、期別選擇、失業率帶內分布、資料修訂與非因果解釋。 |
| 引用、稿件與 PDF | 通過 | 9 筆引用的完整來源封存、結果綁定、乾淨重跑、LaTeX 編譯與三頁逐頁檢查通過；[`paper/pdf/manuscript.pdf`](paper/pdf/manuscript.pdf) SHA-256 為 `195e5e98c0dae40a3df1a152449cfe02c4266214996a43c4edde070d659053c5`，與建置紀錄一致。 |
| 完整團隊交接 | 未通過 | 本試點由部分代理協作完成，沒有符合 `check_research_team.py` 的九個研究角色及具名 PI 驗收交接；不可把單一獨立審稿當成完整研究團隊。 |
| 獨立學術審查 | 否決頂刊原創稿 | [`review/independent-report.md`](review/independent-report.md)、[`research/substantive-review.json`](research/substantive-review.json)、[`research/logic-review.json`](research/logic-review.json)。描述性算術可信，但核心現象及其後續下降已有先行研究，缺少新的估計目標、識別、機制或重要實證發現。 |

[`research/package-audit.json`](research/package-audit.json) 為最後一次整包機器審計：**15 項中 12 項通過，3 項未通過**。未通過的是完整團隊交接，以及兩項必須給出 `pass` 才能交付的代理審查。代理已提交 `reject` 判定與具體理由，故此狀態是預期的學術閘門攔截，不應改寫成通過。獨立代理的 Codex CLI thread ID 為 `01a14d30-0bad-75d1-a6f1-82aa78ede55f`；執行收據留在 `review/cli-events.jsonl`、`review/cli-followup-events.jsonl`、`review/cli-final-events.jsonl`。

## 可重跑範圍與下一步

從 repo 根目錄執行 `python3 scripts/check_research_package.py --root experiments/real-data-pilot/2026-10-18 --config research/package.json` 可重跑所有宣告關卡。對這份稿件，預期整包退出碼為 1，因審稿否決仍有效；計算與 PDF 子關卡可通過。

此案例只驗證一個真實資料題目的來源到稿件鏈條。它不測量新題 one-shot 成功率，也沒有證明任何新研究方向足以達頂刊。下一階段須用事先凍結的多題題庫、發表當時截止的文獻視窗、完整團隊收據與外部人類盲審，記錄成功率、成本和停止原因。自動執行器也仍是共享檔案系統的 CLI 派工，缺乏 OS 級代理隔離。
