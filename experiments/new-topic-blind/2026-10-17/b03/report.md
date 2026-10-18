# b03：多代理已發表論文盲測

**結果：未通過完整頂刊論文重建。** 作者端從一句研究問題寫出八頁理論論文，獨立 AI 盲審按 *The Review of Economic Studies* 標準判 **Reject**；揭盲後按預先封存的五項評分表得到 **4/10**。稿件的部分命題在自身模型內成立，但沒有重建原文的主要充要分類與修復定理。repo 的完整研究流程重播也回傳 `blocked`。本次沒有真人外部領域審稿。

## 題目與分工

只交給研究端的問題是：「在雇主雇用不可分割的勞動者、政府可依雇用組合或薪資設計稅補的市場中，財政措施何時會保留或恢復需求替代性及其均衡基礎？」[公開任務](public-task.json)固定理論模式、目標期刊、1,200 秒預算與受限來源規則。封存原文是 [Kojima、Sun、Yu (2024), *Job Matching with Subsidy and Taxation*](https://academic.oup.com/restud/article/91/1/372/7056201)，*The Review of Economic Studies* 91(1):372–402。[實驗協議](protocol.md)載明作者端、選題員與審稿員各自可讀範圍。

六個原生代理分工完成選題封存、背景文獻、模型與驗算、[LaTeX 撰稿](attempt/paper/manuscript/main.tex)及[八頁 PDF](attempt/paper/build/main.pdf)、[獨立盲審](review/independent-report.md)、[揭盲逐項評分](evaluation/unblinded-report.md)。選題員在撰稿前封存原文主文、附錄和[評分表](sealed/rubric.json)；[公開雜湊承諾](public-hashes.json)的四檔 SHA-256 均已重算相符。[投稿鎖](submission-lock.json)列出的 14 檔也全數與現值相符。完整角色及產物見[代理紀錄](agent-ledger.json)。

## 評分與科學判斷

| 預先封存的要點 | 分數 | 投稿相對於原文的缺口 |
|---|---:|---|
| 不可分割勞動者、稅補、需求替代性模型 | 2/2 | 基本原語及 EX ⇒ GS 關係清楚。 |
| 薪資無關轉移的普遍保留類 | 1/2 | 證明模組化轉移與加法產值下的頭數特例；沒有對所有 GS 產值的充要分類。 |
| 生產資訊與群組結構 | 0/2 | 沒有群組分離、群組凹性或至少三群時的分類。 |
| 薪資相依轉移 | 1/2 | 只有逐人有效薪資單調的充分條件；缺普遍必要性及全員受雇邊界。 |
| 頭數凹性轉移修復 GS | 0/2 | `g=q-v` 是無限制校正；沒有精確人數下的 substitutes 與巢狀需求鏈充要條件。 |
| **合計** | **4/10** | 原文核心 Theorems 1–5 未完整重建。 |

[機器可讀評分](evaluation/comparison-score.json)及[揭盲報告](evaluation/unblinded-report.md)列出原文 PDF 頁碼、定理、投稿位置與每項給分理由。獨立審稿在揭盲前逐頁檢查 PDF，認為明述的命題與反例大致有效，但一般 EX 估值的均衡存在仍缺組態線性規劃整數性證明；政策可實施性、財政限制與新穎性也沒有充分建立。因此「稿件內部部分正確」不能推成「原文重建成功」或「頂刊可發表」。這是 AI 代理的審稿模擬，不是期刊決定。

## 工作流程與可稽核限制

[文獻題目調查](attempt/research/literature/topic-survey-check.json)在盲測期間回傳 `blocked`、`contribution_class=unresolved`，沒有錯誤；揭盲後，原文已發表，該題不能被當作新的可投稿貢獻。[證據清單](attempt/research/manifest.jsonl)通過格式和論證圖檢查，30 筆紀錄保留一般均衡的未解義務。後鎖補正的[文獻歸檔檢查](attempt/research/post-lock/literature-archive-check.json)顯示四篇最終引用文獻已歸檔；這項補正**不算**封存投稿的通過項目。

[隔離副本中的完整 workflow 重播](evaluation/workflow-replay-result.json)為 `blocked`：原投稿缺少 mechanism audit、coverage、logic review、mechanism review、team report、substantive review 六類機器可讀文件；逐頁視覺檢查雖已由審稿代理完成，但其 JSON 格式不符合 `check_latex.py` 的 finalize schema，且重編 PDF 與受檢的封存 PDF 雜湊不同。[缺件清單](evaluation/missing-artifacts.json)逐項記錄。原封存編譯報告的 BibTeX 輸入雜湊與鎖中 `references.bib` 也不同；這是來源可重現性問題，不能因 PDF 可讀而略過。

嚴格盲性與限時證明各有缺口。[污染日誌](attempt/research/literature/contamination-log.tsv)顯示文獻代理在搜尋結果層級看到疑似目標論文的標題／網址，沒有開啟或傳給建模與寫作代理的證據；研究代理共用檔案系統，封存區靠指令隔離，無權限屏障。[起始紀錄](run-start.json)為 02:39:37 UTC，20 分鐘名目截止為 02:59:37 UTC。稿件與 PDF 最後寫入時間在期限內，但投稿鎖直到 08:36:47 UTC 才建立，且作者最終交接訊息缺失；因此不能認證「20 分鐘時已不可更改封稿」。這些限制不改動內容分數，但限制把本次稱作嚴格、零污染、限時盲測。

本次實驗回答的是一個已發表理論題的歷史重建能力。它顯示多代理可產出可編譯、部分正確且可審的研究稿；也實測出從一句問題到頂刊完整性之間仍缺核心定理搜尋與證明、文獻新意核查，以及在交稿前真正通過所有 Audit Gate。單一案例不能估計整個 harness 的成功率。

**時間基準補正（不改原盲測分數）：** 上述「揭盲後原題不能當新投稿」是 2026 年的**當前投稿新意**判斷，不是 KSY 論文在其發表當時缺乏原創性的判斷。歷史原創性應只與目標論文首次期刊公開日前已公開的其他研究比較，並排除目標自己的早期版本；更晚研究不能倒算為先行文獻。嚴格盲測的作者可見資料還須截止於目標**最早公開版本之前**。[時間基準補充協議](evaluation/historical-novelty-addendum.md)及[獨立先行文獻稽核](evaluation/historical-prior-art.md)記錄這項事後方法修正與有限文獻對照。原作者交接曾包含晚於目標初稿的文獻，所以 b03 不能被追認為時間隔離合格；原 4/10 仍只是原規則的內容重建分數。
