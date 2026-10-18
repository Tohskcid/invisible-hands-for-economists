# 真實頂刊問題驗證：2026-10-17 重跑紀錄與下一輪方案

基準 commit：`8704e3d6ee76372fcf77c4cbeeeb43630ce02a53`。本輪在臨時副本執行，不修改 2026-10-12 原始先導實驗。驗證命題分成三層：歷史結果復原、獨立完成可信研究稿、產生有新意且有頂刊水準的貢獻。第一層成功不推出後兩層成功；期刊接受也不是軟體 gate 能認證的結果。

## 本輪實際執行

題目取自 Card 與 Krueger 的 [AER 1994 最低工資研究](https://www.nber.org/papers/w4509)：1992 年紐澤西州的最低工資上升如何影響速食餐廳就業？另檢查 Rubinstein 的 [Econometrica 1982 談判研究](https://arielrubinstein.org/vitae.html)之既有理論產物。這兩題已在模型知識與前一輪 pilot 中曝光，不能當新盲測題。

| 檢查 | 本輪結果 | 可以支持的結論 |
|---|---|---|
| 凍結的舊 harness 快照 | 75 個檔案的雜湊均吻合；相對目前 repo，有 13 個舊檔案已變動 | 舊先導實驗可定位到當時版本；不能冒稱由現版生成 |
| AER 原文數值對照 | 事前容差 0.05 下，五個核心數值 5/5 符合；原文完整復原仍為 `partial` | 平衡樣本等核心量測算對，不代表原文全部規格或因果識別完成 |
| AER 乾淨重跑 | `passed=true`；結果樹、四張表與 TeX 位元組一致；Python 與 base R 的主估計相符。估計 2.75 FTE，N=384 | 固定原始資料與程式的計算可復現；這是舊稿重跑，不是新的一句話委派 |
| 理論補充數值檢查 | 重新執行 `verify_and_package.py`，退出碼 0，10 個 central claims 的 metadata 重新產生 | 有限理性案例檢查成功；不是一般偏好定理或 Lean 證明 |
| 現版 checker 查舊實證稿 | `valid=false`：topic survey、limitations coverage、DiD 診斷及 LaTeX/review 等關卡未通過 | 舊稿未達現版完整交付要求；搬動快照後的 LaTeX 失敗可能另有路徑／環境因素 |
| 現版 checker 查舊理論稿 | `valid=false`：topic survey、文獻存檔、limitations coverage 及 LaTeX/review 等關卡未通過 | 舊稿未達現版完整交付要求 |
| 將舊設定明確標成現版 `manuscript` profile | 實證缺 `latex_build_dir`、`release_pdf`、`replication`、`substantive_review`、`team_report`；理論缺前兩項及後兩項 | profile 會拒絕以舊設定跳過現版必要義務；這是舊產物的相容性檢查，非新研究結果 |
| **只輸入一句真實問題給現版 CLI runner** | [`status=in-progress`](question-only-result.json)；只新增 contract、ledger、rework state，`package_audit=null`；沒有產生文獻、資料、分析或稿件 | 單獨執行 runner 不會生成論文。Skill 需要宿主研究 agent 實際完成 `next_tasks`，本項沒有測試宿主加 Skill 的完整能力。CLI 退出碼為 0，但不表示研究完成；須檢查 `status` |

以上數值重跑在已保存的原始資料和程式上進行。題目獨立發現、資料取得、選定模型、完整原文對照、頂刊新意與人類審稿均未由本輪重跑驗證。舊先導實驗的[原始報告](../../one-shot-reconstruction/2026-10-12/report.md)記錄兩個 worker 的模型記憶、搜尋污染、用量中斷與未通過的 gates；不能把本輪重跑改寫成嚴格 one-shot 成功。

重跑方式：先將 `experiments/one-shot-reconstruction/2026-10-12` 複製到暫存目錄，再於該副本執行 `scripts/compare_empirical.py`、`scripts/clean_replay.py` 與 `attempt-theory/scripts/verify_and_package.py`。現版關卡使用 repo 根目錄的 `scripts/check_research_package.py --root <暫存副本>/attempt --config research/package.json`，理論案則以 `attempt-theory` 作 root。只給問題的 CLI 試驗使用 `scripts/run_research_workflow.py --root <空白專案> --contract research/contract-input.json --json`；完整 JSON 結果已保存。

## 下一輪驗證設計

1. **復現能力（可先執行）**：從 repo 十刊名單另選未曝光、可合法取得原始資料或完整定理的論文；只給研究問題、期刊、相同來源權限與預算。原文、標題、作者、數值和原始程式放在作業系統權限隔離的 holdout。事前固定要復原的主要估計／定理、樣本與容差。評估者事後對照，不讓 worker 接觸答案。
2. **可信研究完成率（主要產品終點）**：題目可不要求與歷史原文逐字相同，但必須有真實資料、可重跑分析或完整可審證明、限制、近作文獻與有效識別／假設審查。獨立領域評審判斷是否仍有致命錯誤；機器 gate 只判必要證據與交付是否齊全。
3. **原創貢獻（另列探索終點）**：使用尚無公開答案的新問題，先判近作重疊，再評增量、重要性與能否被反駁。已發表題目的精確復原只能測執行能力，不能當成發現新貢獻。
4. **歸因於 harness 的效果**：同題、同模型、相同工具／資料權限／時間及多代理預算下，比較通用 agent、凍結舊版 harness、現版 harness；依題目區組隨機分派，保留所有失敗與中斷。外部盲審採共同 rubric，不以各版本自家的 JSON gate 分數作唯一終點。

下一個實作步驟是先做一題真正未曝光的 blind pilot，凍結契約、原始輸入和 holdout，再啟動宿主 agent 使用 Skill／MCP 完成研究。若當前宿主沒有可證明的目標材料隔離，該題只能標成污染風險試跑，不計入盲測完成率。十刊各兩題、三臂各兩次的確認性比較需要在 pilot 之後凍結版本、題庫、評分與預算，不能用這兩個經典舊案估成功率。
