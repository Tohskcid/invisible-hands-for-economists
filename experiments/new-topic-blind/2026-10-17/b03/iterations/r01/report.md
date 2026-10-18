# b03 r01：blocked 後的實際迭代

前一次停在 `blocked` 是我的執行判斷錯誤：當時仍有可修的證明和封裝缺口，應沿著 workflow 的 `next_tasks` 再做一次。此 runner 會產出 `next_tasks`／`rework_plan`，但不會自行召回研究代理；我當時沒有接手執行這一步。這次保留 b03 原封存投稿和 4/10 歷史盲測，另開 **揭盲後開發修訂 r01**，讓寫作、證明、文獻重疊、審稿及評分各由不同代理處理；r01 **不是第二次盲測**。

| 項目 | b03 初次結果 | r01 修訂後 |
|---|---|---|
| 一般 EX 調整估值的均衡及組態 LP 證明 | 缺少完整依據 | 已補入稿件命題 7；獨立 AI 審稿按 Murota 定理逐步核對，障礙標記 `resolved` |
| 具體新命題 | 無財政硬上限的精確結論 | 命題 8：在兩名工人、至少兩家雇主、同一非負單人補貼與所有可行配置支出上限的窄模型中，robust 可行當且僅當 `B≥κ`；審稿認為成立但增量不足 |
| 稿件與研究資料封裝 | 缺六項必需 artifact；PDF 審視不匹配 | 文獻檔案、35 筆 manifest、15 段 coverage、team、claim audit、PDF 均建置；10 頁 PDF 的最終視覺審視通過 |
| 全套 package gate | `blocked` | 11 項中 6 項通過、5 項未通過；[完整重跑結果](workflow-pass2.json)仍為 `blocked` |
| 獨立審稿 | Reject | [r01 審稿](review/independent-report.md)仍為 Reject：原題和已發表研究直接重疊；預算結果太窄；福利、資訊與機制論證不足 |
| 原定重建評分 | 4/10 | [相同 rubric 逐項複評](reconstruction-rescore.md)仍為 4/10，沒有把補強的均衡證明冒充原論文其他未重建的定理 |

五個未過的 package gate 有明確原因：題目調查的 `decision=stop, contribution_class=duplicate`；coverage 的文獻段因新意未立而未標 `ready`；substantive review 為 Reject；logic review 對**整篇投稿**給 Reject；mechanism audit 的「原市場可能已有 EX 性質」替代解釋仍無法排除。這些結果不是 JSON 格式或編譯失敗；不能靠修改 gate 標籤或重跑相同題目得到可信的 pass。`check_latex.py` 的 `delivery_ready=true` 僅指 PDF 編譯與視覺檢查通過，**不是**研究包或投稿通過。

r01 的研究時限是從 `iteration.json` 開始的 3,600 秒真實時間。runner 回報的 `spent_budget=0.539` 秒只累計它執行子程序的時間，未計入代理閱讀、寫作與審稿；因此不能拿該數字表示整輪只花不到一秒。這是 harness 仍需修正的預算記帳缺口。

揭盲後的[逐項重疊稽核](overlap-audit.md)指出，Kojima、Sun、Yu（2024）《Job Matching with Subsidy and Taxation》已處理幾乎相同的雇傭市場稅補、替代性保留／修復與均衡問題，且有比本稿更廣的充要分類。r01 作者稿尚未直接引用這篇目標論文；因此目前只能用作開發稿／教學推導，不能呈現為原創頂刊投稿。新加的 `B≥κ` 是可檢驗的受限基準，尚未證出共同政策、總市場預算、福利與資訊限制下的新一般結果。審稿者是**獨立 AI 代理，不是外部人類領域審稿人**。

這一段只評估 **2026 年 r01 若作為新投稿**的狀態；不能用目標論文本身否定它在最初發表時的歷史原創性。歷史比較須以目標的首次期刊公開日為截止，並把目標自己的早期版本排除；詳見 b03 的[時間基準補充協議](../../evaluation/historical-novelty-addendum.md)。

下一個真正的研究迴圈應換成一個與已發表結果可區分的問題：例如政府只觀察雇用人數、採全市場共用政策、受硬預算約束時，最小可行預算和福利損失是什麼。先查與預算受限替代性／配對相關的先行文獻，再固定資訊、預算、所有均衡的量詞，求必要充分條件或反例，獨立審稿，若仍重複再換題。這是**新研究提案**，不是 r01 已完成的定理，也不能回填 b03 的盲測成績。

完整追蹤：[r01 計畫](plan.md)、[第一次 workflow](workflow-pass1.json)、[第二次 workflow](workflow-pass2.json)、[實驗紀錄](experiments.tsv)、[修訂稿 PDF](project/paper/build/main.pdf)、[修訂稿來源](project/paper/manuscript/main.tex)、[獨立審稿](review/independent-report.md)、[評分 JSON](reconstruction-rescore.json)。修訂稿來源 SHA-256 `7a3dc698f06938c34ba50b66eec0e717c9e8a2203b40e4f1c395440961fec5ab`，PDF SHA-256 `e4c5929b812dc2c309b4e5ced4dac4e75e07b147ad35f7c8aecfd617372bd8ee`。原 b03 封存檔 SHA-256 與[鎖定清單](../../submission-lock.json)逐項一致。

驗證：`python3 -m unittest tests.test_manuscript_coverage tests.test_research_package` 通過 19 項；同時修正兩個 harness 解析問題（LaTeX 不套用 Markdown 數字掃描、巢狀 `\ref` 的 section 標題可被正確識別）。
