# b04 已發表論文時控重建測試

## 結果

從一個中性研究問題出發，作者代理在預設 1,200 秒限額內提交 10 頁理論論文及 PDF。獨立評分代理依封存的五項準則給 **4/10**（2、1、1、0、0）；獨立 AI 盲審認為主要證明在明示假設下大致成立，但建議 *Journal of Political Economy* 拒稿。這是部分內容重建，並非「給一個新題目即可 one-shot 產生頂刊論文」的證據。

揭盲目標是 Akbarpour、Dworczak 與 Kominers 的 [*Redistributive Allocation Mechanisms*](https://www.journals.uchicago.edu/doi/full/10.1086/728111)，出版社記載首次期刊線上公開為 2024-05-10；[SSRN 紀錄](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3609182) 記載目標稿最早可核實公開日為 2020-06-18。這兩個日期分別控制歷史文獻比較和作者可見來源。

## 時間與封存

- 公開題目：[`public-task.json`](public-task.json)。保守起算時間為 2026-10-17 13:50:55 UTC；名義截止時間 14:10:55 UTC。
- 作者回報 13:57:34 UTC 封稿；協調者於 13:57:55 UTC 複製全套作者檔案並建立 [`submission-lock.json`](submission-lock.json)。稿件和 PDF 的最後寫入時間分別是 13:56:59 及 13:57:31 UTC，均在截止時間前。
- 封存稿：[`LaTeX`](evaluation/frozen-submission/paper/manuscript/main.tex)、[`PDF`](evaluation/frozen-submission/paper/pdf/main.pdf)。SHA-256 分別是 `deb717de94a350fe44e79d1006106b91bab978ad75e2eec1f6f96e6de5468bb4`、`04207ecf0f7deafb607a17507ff638c461138b7d8793c46d5ebb0d0e3cdb881f`。
- 目標全文與評分表在作者派遣前加密封存；封稿後解封，密文與明文雜湊均核對通過。詳見 [`public-hashes.json`](public-hashes.json) 與 [`comparison-score.json`](evaluation/comparison-score.json)。

## 分開看的三種判斷

1. **內容重建：4/10。** 完成異質品質、可觀察群組、隱藏福利權重、支付限制和虛擬福利推導。僅在虛擬分數單調的有限代理模型中解出排序規則；沒有完整解出目標的組內凹化與隨機池化、組間品質分配及免費隨機區間條件。[逐項證據](evaluation/comparison-score.md)。
2. **目標發表當時的歷史原創性：有條件的判斷。** 目標期刊首次線上公開是 2024-05-10；應與這一天之前已公開的**其他**作品比較，排除目標自身 2020 工作論文及後續版本。經核實的 Condorelli 2013 與同團隊不同論文的 2018 工作稿有實質先例，但本次搜尋不窮盡，不能據此裁決整篇目標的優先權。[時間線與文獻審計](evaluation/historical-prior-art.md)。
3. **這份 2026 年稿件的新投稿風險：高。** 目標的 2020 年公開稿已包含與本稿代數上相同的加權虛擬分數，且處理本稿留下的非單調情況。兩稿的有限代理／連續人口與 DSIC／interim 假設不同，但本稿未建立其變體的獨立貢獻。[歷史審計](evaluation/historical-prior-art.md)；[獨立 AI 盲審](evaluation/blind-review/independent-report.md)。

## 盲測及 harness 閘門的限制

作者來源清單只有 Myerson 1981 與 Saez–Stantcheva 2016，兩者均在目標可核實最早公開日 2020-06-18 之前；[`source-preflight.json`](author/source-preflight.json) 與 [`historical-timeline-check.json`](evaluation/historical-timeline-check.json) 通過時間資格檢查。這只證明交接清單的時間合格，並不證明文獻覆蓋充分。第一位文獻搜尋代理曾在搜尋結果看見目標標題／網址，但未開啟或交給作者；紀錄在 [`contamination-log.md`](evaluation/contamination-log.md)。共用檔案系統、網路與模型記憶均無技術隔離，因此不能宣稱零洩漏。

作者 PDF 由 LaTeX 工具成功編譯並逐頁檢查，哈希與封稿一致。但作者沒有交付理論論文 profile 所需的 manifest、覆蓋表、文獻歸檔、邏輯／機制審核、團隊與實質審核等資料。封稿後建立的**獨立 replay 設定**沒有捏造這些證據；[`workflow-gaps.json`](evaluation/workflow-gaps.json) 列出缺項，完整 package gate 因缺檔而拒絕開始，故不能把 PDF 可編譯誤報成整個 harness 已通關。

這次的題目策展、來源隔離、代理分工、封稿、審稿與評分由協調代理逐步發動；`run_research_workflow.py` 只建立研究 contract，沒有從一句題目自動啟動整個團隊。測到的是「harness 加人工編排的代理流程」，不是 repo 單一命令的無人值守執行。初次啟動還發現明確傳入錯誤 contract 路徑時，runner 靜默改用預設經驗研究設定；錯誤狀態保存在 [`initialization-error/`](evaluation/initialization-error/)，runner 現已改成明確報錯，相關單元測試通過。

這次還暴露了題目資訊不足的結構問題：同一個一句話問題容許多種合理模型。作者選擇最低支付意願為零、有限代理與單調分數的特例；目標的免費隨機分配命題則依賴正的最低支付意願與更一般的凹化問題。即使作者稿的特例正確，也不會由一句題目唯一推出目標的定理組。後續測試應把「題目探索能力」與「已固定模型下的定理重建能力」分開評分。

本次審稿人與評分員都是相互分開的 AI 代理，沒有真實期刊外審、編輯決定或接受率估計。

## 後續迭代

封稿後只把獨立盲審意見交給修訂代理，保留原稿不動：

| 版本 | 內容重建 | 審核結果 |
| --- | ---: | --- |
| 原始 one-shot | **4/10** | 10 頁；核心推導大致成立，非單調情況未解，AI 盲審建議拒稿。 |
| [r01](iterations/r01/rescore.md) | **5/10** | 14 頁；增加有限代理的分位數凹化與遞減分數定理；盲審指出群組條件分布及端點定義兩處缺口。 |
| [r02](iterations/r02/rescore.md) | **5/10** | 修補兩處缺口；[獨立 AI 盲審](iterations/r02/independent-review.md)未再找到重大定理錯誤，仍建議 JPE 拒稿。 |

修訂補強了正確性，沒有重建目標未得分的核心結果，也沒有解決與目標 2020 公開版本的重疊。r01／r02 都在揭盲後產生，只能算事後迭代，不能回填 one-shot 成績。依 [`Audit Gate`](evaluation/audit-gate-decision.json)，此方向應回到題目與先行研究審查；繼續修飾同一篇稿不會自動產生可辯護的新意。兩輪的完整 package gate 仍被缺少的真實研究／獨立審查證據阻擋，沒有以自評檔案偽造通過。
