# Invisible Hands for Economists：完整驗證紀錄

日期：2026-10-17（台北）。基準 commit：`8704e3d6ee76372fcf77c4cbeeeb43630ce02a53`；本輪有一行未提交的工程修正，見下文。本報告的「完整」指已執行 repo 提供的全部主要工程檢查，並以真實論文題目測試可取得的研究與交付路徑；它不把尚未完成的盲測或外部審稿寫成成功。

## 結果

| 層次 | 執行證據 | 判定 |
|---|---|---|
| Python／MCP 整合測試 | `uv run --no-project --with 'mcp>=2,<3' python -m unittest discover -s tests -q` | 186 項通過；含 in-memory MCP tools、resource、prompt、gate 修復流程 |
| Skill 與文獻庫 | 已驗證安裝鏡像及將 repo 作為 `econ-research-lab` 目錄時的 Skill；`validate_library.py --json` | Skill 有效；19 篇條目、19 項結果、10 條關係均有效 |
| 五個工程案例 | [修正後報告](engineering-rerun/report.md)及 [JSON](engineering-rerun/report.json) | 5 案執行無未處理錯誤。合成 DiD 與事件報酬的計算可乾淨重跑；三個示意稿自動 LaTeX 編譯通過，完整 package 均正確維持 `blocked`。有限 CLI 修補及累計預算／待辦保留通過 |
| 真實文獻發現 | [Crossref 擷取](literature-crossref.json)及兩份 `raw/` 回應，兩份 raw SHA-256 均吻合 | 兩個問題式查詢取得 20 筆 metadata；Card–Krueger 原研究的 NBER 版本出現在合併結果第 3 筆。這足以提醒該歷史題目已被研究，不構成完整 frontier survey |
| 本機真實資料與既有復原 | `check_data_provenance.py --require-real` 對保存的 AER 案通過，1 個真實資料集；[前一輪重跑](../../validation-rerun/2026-10-17/report.md) | 本機凍結資料的主估計為 2.75 FTE、N=384；5 個核心數值在預設容差內，Python／base R 與生成表格可重跑。原文完整復原仍只有 `partial` |
| 從 Git commit 乾淨重建 AER 案 | [機器摘要](clean-clone-results.json)與[資料 gate](clean-clone-data-provenance.json) | 公開 raw 可重新下載且 hash 相符；但來源網頁快照不在 Git，資料 provenance gate 失敗。README 指定 master 先因缺 `data/processed` 目錄失敗；手動建立輸出目錄後分析與 R 通過，稿件 builder 又因未重新取得的引用 PDF 失敗。GitHub 版本目前無法一鍵完整復現舊案 |
| 現版 package 查既有真實稿 | [AER 檢查](real-empirical-package.json)；[Econometrica 檢查](real-theory-package.json) | 兩案均 `valid=false`。AER 主要阻於 topic、limitations coverage、DiD 設計診斷及 LaTeX/review；理論案阻於 topic、文獻存檔、limitations coverage 及 LaTeX/review。這些是舊版產物經現版 checker 的結果，不是現版重新生成的論文 |
| 一句問題到稿件 | [輸入契約](question-only/research/contract-input.json)及[執行結果](question-only-result.json) | `status=in-progress`、`package_audit=null`；只建立契約／ledger／rework state，沒有搜尋、資料、分析或稿件。CLI 退出碼 0 不等於研究完成；須讀取 `status` |

## 執行中發現並修正的問題

第一次指定相對 `--output-dir` 跑五個工程案例時，兩個分析腳本在其案例 cwd 下再次拼接相對路徑，產生 `CalledProcessError`。[第一次失敗紀錄](engineering/report.json)已保留。將 `run_experiments.py` 的輸出 base 在建立目錄前轉成絕對路徑後，新的獨立目錄重跑成功；原五案的科學性 package fail 沒有被改為 pass。修正後重新執行 186 項測試、Skill 格式驗證、Python 編譯與 `git diff --check`，均通過。

## 對「研究問題 → 頂刊水準論文」的判斷

目前**未驗證成功**。已證明部分數值復原、真實資料來源檢查、工程重跑和硬性 gate 能工作；未證明從一個新問題自主完成文獻、資料、研究設計、撰稿與獨立審查。已有 AER／Econometrica 兩個經典題目受模型記憶與搜尋暴露影響，且均未完整復原或通過全部交付 gate；不能當成未見題盲測。直接用已發表的原問題啟動新研究時，合格的 novelty gate 應先辨識「已有人做過」，再走 replication／延伸或停止，而不是冒稱全新貢獻。

下一輪要衡量頂刊級能力，需先凍結未曝光題目、可用來源、原文 holdout、預期估計或定理、時間／成本上限與外部評分 rubric；以宿主 agent 加 Skill／MCP 實際產出稿件，保留全部失敗和污染紀錄。歷史復原、可信完整論文與新貢獻必須分開評分；對照組要在相同模型、工具、資料與多代理預算下執行。現有[研究計劃](../../../docs/research/harness-optimization-plan.md)的 6 題 pilot、36 次執行及後續 20 題確認比較尚未完成，因此不能推估 one-shot 成功率或頂刊接受機率。

優先修復的交付缺口是：讓已凍結歷史實驗從 GitHub 乾淨副本建立必要輸出目錄、合法重新取得必要來源或明確阻斷，並讓 provenance 的來源證據可重建。歷史原始產物應保留；修復應以新的可版本化 replay 路徑驗證，避免把過去失敗改寫成成功。
