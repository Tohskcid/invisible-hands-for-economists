# b03 揭盲比對與評分

**結論：4/10。** 依事前封存的五項各 0/1/2 分規則，模型 2、無條件簡單轉移 1、資訊結構 0、薪資相依 1、恢復替代性 0。這是歷史論文的實質重建分數，並非稿件數學正確率或真實投稿錄取機率。未因題目接近、原文題名、審稿結論或事後所知更改門檻。

## 封存與來源

先以 SHA-256 核對公開承諾 `public-hashes.json`，四檔全部相符：`sealed/target.json` = `894650d555b8cedbbb0635e401701cd160330f90540d3a7ad60784fe2a5c8078`；`sealed/rubric.json` = `df958a2eccc84286acec02e8eda39d7009d5c577c31b6b073fc4362ca69b6494`；主文 PDF = `87d138f3f49a9c0cb45941cf8ee2ec80290d8e032a9302622b9cab9bfb0f66c1`；線上附錄 PDF = `ff7d33d0e15f6d7f354a6c10c6ffab7896b48d2cdc691f373d44f156b84ff1b6`。對象為 Kojima、Sun、Yu，〈Job Matching with Subsidy and Taxation〉，*The Review of Economic Studies* 91(1), 2024, 372–402，DOI [10.1093/restud/rdad032](https://doi.org/10.1093/restud/rdad032)。來源：[期刊文章頁](https://academic.oup.com/restud/article/91/1/372/7056201)、[封存主文原址](https://www.restud.com/wp-content/uploads/2023/02/Transfer_KSY_main_text.pdf)、[線上附錄原址](https://oup.silverchair-cdn.com/oup/backfile/Content_public/Journal/restud/91/1/10.1093_restud_rdad032/1/rdad032_supplementary_data.pdf)。以下頁數均指 PDF 頁碼；主文同頁的印刷頁碼在抽取頁面中一致。投稿稿件 SHA-256：`main.tex` = `2f5664debdcfedb208fdcc83dd688fbca16bc22d0fa6fb17489903138d07b89d`，八頁 `main.pdf` = `88c112eae123cf3a2ffed0b3de1abe9a975f1bbdfed673d0c1d30f5e1a9dec10`。

## 五項逐條判定

| 原 rubric 項目 | 分數 | 已發表論文與投稿對照 |
|---|---:|---|
| 有限不可分割勞動者模型 | **2/2** | 主文 PDF pp.7–9 §2、Definitions 1–2：集合產值、薪資、轉移、利潤最大需求與薪資上升時的 substitutes；p.8 註 12 指出其均衡存在作用。投稿 `main.tex` §3「Environment and definitions」式 (3.1)–(3.2) 與三個 Definitions、§4「Exchange implies demand substitutes」及其附錄證明建立對應模型與 EX ⇒ GS。投稿只把一般 EX 均衡的 LP 整數性列為未證條件，但本項的模型和經濟理由已清楚。 |
| 薪資無關轉移的普遍保留類 | **1/2** | 主文 PDF p.9 Definition 2 明確量化「對所有 GS 產值」；pp.10–11 Proposition 1、Theorem 1 給出**充要**類：工人加法項 + 邊際弱遞減的頭數項。p.9 另展示轉移本身 GS 仍未必可與 GS 產值相加；附錄 PDF p.7 證明 Theorem 1。投稿 §4「Modular fiscal schedule」與 §5「Nonmodular headcount transfers」正確證明模組化保留 EX，及加法產值加頭數函數時的遞減增量充要式；但後者只針對加法基底，沒有對**所有** GS 產值的必要性與充分性，也沒有區分「轉移本身 GS」的非封閉反例。故給正確但不完整的 1 分。 |
| 生產資訊與群組結構 | **0/2** | 主文 PDF pp.13–14 §4.1、Theorem 2：固定工人群組下，group-separable 產值的保留類為工人加法 + group-cardinal 且 GS 的 group-concave 項；p.15 §4.2、Theorem 3：**至少三群**且 group-concave 產值時，為 group-separable + cardinally concave；p.15–16 說明兩群界限，附錄 PDF p.17 證明。投稿 §3–§5 沒有群組分割、群組產值假設或相應轉移分類。 |
| 薪資相依轉移 | **1/2** | 主文 PDF pp.18–21 §5、Proposition 3、Theorem 4；p.19 個別雇用成本需在全實數薪資域嚴格遞增；p.21 充要類為 own-worker salary-dependent additivity + C-cardinally concave，並明述**全員受雇**情形的受限薪資相依例外；附錄 PDF p.22 開始 Theorem 4 證明。投稿 §4「Separable wage-dependent schedule」及附錄給有效價格逐人弱遞增、僅非負工資域的正確充分條件。它沒有普遍必要性、全員邊界，也沒有任意聯合薪資稅失敗的具體有效反例；故只給部分分。 |
| 頭數凹性修復 GS | **0/2** | 主文 PDF pp.24–26 §6.2–6.3、Definitions 4–6、Propositions 7–9、Theorem 5：存在頭數凹性轉移能修復 GS **當且僅當**原產值同時滿足每個精確雇用人數下的 substitutes 與相鄰人數最適集合的巢狀 demand-chain；可修復的缺項是 scale concavity。附錄 PDF pp.30–33 為 Theorem 5 證明。投稿 §4 的 `g=q-v` 可對任意已知產值作無限制、集合別校正，§4 兩人門檻和 §5 頭數命題也是特例；均未界定精確人數 GS 與巢狀鏈，更未證頭數凹轉移修復的充要條件。 |

## 科學判斷與盲性稽核

投稿的 EX ⇒ GS、模組化不變性、兩工人門檻、加法估值均衡及逐人有效工資充分條件在明示範圍內大致成立，亦誠實標出一般 EX 均衡所需 LP 整數性尚未證明。獨立 AI 審稿 `review/independent-report.md`（SHA-256 `a5842fbca2bc61330085672384b2e5dab27cf4b0b9ef33742dc89594da5d5ee8`）作了公式和反例核對，建議以頂刊標準 **Reject**：主要擔憂是核心結果離原文的普遍分類甚遠、一般均衡論證未完、`q-v` 校正需要完整私有產值資訊而無財政限制，以及相對背景理論的新貢獻沒有建立。這是 AI 代理的匿名審稿模擬，**不是**真人外部審稿或實際期刊決定。模型交接 `attempt/research/model/handoff.md`（SHA-256 `7f1b9e44bcab409267c13ca73ca006878a67004841ed9f565ca315fd89ea79c7`）同樣把一般均衡列為條件性，不能把「模型內有效」推成「原文核心已重建」或「頂刊可投稿」。

文獻 scout 的 `attempt/research/literature/contamination-log.tsv` 記錄 2026-10-17 02:40:31 UTC 的 SciSpace 搜尋結果 URL 暴露，網址標題對應目標論文；`safe-handoff.md` 只轉交非目標文獻，`topic-survey.json` 說沒有開啟或使用該結果內容。投稿 `main.tex` 與模型交接未見目標題名、作者、DOI 或 sealed 路徑；獨立 AI 審稿自述在揭盲前未讀目標或封存內容，只看到隔離後的污染通知。可確定的是**搜尋結果層級的部分污染**，不能把它寫成完全零暴露；也沒有證據支持作者使用目標全文。全體共用同一主機檔案系統，`sealed/` 僅有指令隔離，並無存取權限屏障，因此無法從這些紀錄證明嚴格盲性。

`run-start.json` 是 02:39:37.993983 UTC、預算 1,200 秒，名目截止 02:59:37.993983 UTC。`submission-lock.json` 記 `main.tex` 最後寫入 02:44:12.251838 UTC、PDF 02:44:22.844649 UTC，均在名目時限內；目前這兩檔與鎖定 SHA-256 相符。然而 submission lock 實際建立於 **08:36:47.778811 UTC**，比名目截止晚約 5 小時 37 分；作者最終訊息缺失，獨立審稿也在遲到的鎖之後。因此只能說現存稿件的檔案時間與鎖中記錄支持「初稿在時限內形成」，不能單靠遲鎖證明 20 分鐘時已有不可更動的封稿。此稽核限制不改動五項內容分數，但限制實驗對嚴格限時、嚴格盲性結果的主張。
