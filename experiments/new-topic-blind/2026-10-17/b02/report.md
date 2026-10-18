# 新題盲測：已發表頂刊論文的問題 → 本 repo → 獨立投稿

**結果：未通過頂刊重建標準。** 研究代理從一句問題產出可編譯的 7 頁理論稿，該稿在自己設定的簡化模型內有可檢查的均衡與福利證明；獨立盲審代理驗算後給 **Reject（頂刊尺度）**。原文的核心機制與結果沒有被重建，固定評分為 **3/10**（[逐項機器可讀分數](comparison-score.json)）。本 repo 的完整 workflow 回傳 `blocked`，不能把生成稿或 PDF 視作通過 Audit Gate。真正由團隊外經濟學者提供的審稿尚未取得。

## 試驗設計與盲性

- 問題（只給作者）：**在交易者具有私人品質資訊、可同時聯繫多個交易對手的市場中，增加可聯繫對象數量會如何影響分離或混同均衡、交易效率與福利？**
- 已發表標準答案：[Auster, Gottardi, Wolthoff (2025), *Simultaneous Search and Adverse Selection*, Review of Economic Studies 92(6):3541–3573](https://academic.oup.com/restud/article/92/6/3541/8045204)，DOI 10.1093/restud/rdaf014；[原文 PDF](holdout/target-published.pdf)，SHA-256 `0273be038411fbfaac331f388041af4e916f11e16bc4d18f2b6c6d5f6a4a659d`。
- 題目、1,200 秒預算與五項 10 分評分表在投稿前固定。[預先註冊評分表](preregistered-rubric.json)的 SHA-256 為 `21cde8109c55809e954ab7eb9558074b6402fd35293687d036acaed195628544`；投稿鎖定時間為 2026-10-16 17:15:19 UTC，[SHA-256 清單](submission-lock.json)。評分表在作者交件後才放入本試驗目錄；獨立盲審代理被明確禁止閱讀，並回報未閱讀。原文 PDF 則在獨立盲審交件後才放入。
- b01 初始合約把 `mechanism_scope` 寫成無效值，研究輸出之前即另開 b02，保留 [技術錯誤紀錄](../b01/INIT_ERROR.md)。問題、預算和評分標準未變。這是試驗設置缺陷，非研究代理造成的科學結果。
- 文獻代理搜尋時，在結果列表看見標準答案的**題名**，沒有開啟原文/摘要或傳給作者；[污染日誌](attempt/research/literature/contamination-log.md)留存。因此**整個團隊的嚴格盲性已受損**，但作者回報未接觸標準答案，作者稿仍是問題輸入下的獨立嘗試。盲性僅靠 fresh-context 代理及指令，沒有檔案系統隔離。
- 兩名研究代理分別完成 [文獻調查](attempt/research/topic-survey-draft.md)及 [LaTeX 稿](attempt/manuscript/main.tex)／[PDF](attempt/manuscript/main.pdf)。之後獨立審稿代理只讀封存稿、模型與文獻草稿，[盲審報告](review/independent-agent-report.md)的 SHA-256 為 `c975ffed9a4c43088884bf66ba18d89947a19baf27d24b243a824a7b3cdff5c9`。首次審稿嘗試因平台用量限制失敗；重試才交出報告，未把首次失敗計成審稿。

## 事先固定的重建評分

每項最多 2 分；1 分表示只重建一部分，0 分表示核心條件或結論缺席。此計分是**原文重建程度**，不是稿件內部證明的真偽，也不代表外部審稿結果。

| 預註冊要點 | 得分 | 投稿與原文的對照 |
|---|---:|---|
| 兩種私人型別、張貼工資、公司進入、同時投多份申請且至多接受一份 | **1/2** | 投稿有兩種私人品質、同時多接觸、最多賣一單位；沒有張貼工資策略、公司進入或申請組合。原文 §2 有這些市場階段。 |
| 增加接觸同時緩解協調摩擦、削弱依市場流動性的篩選 | **0/2** | 投稿把多接觸壓縮成外生可用率 `A_n=1-(1-a)^n`；沒有不同工資／佇列可用來篩選。原文摘要及 §1 的核心取捨缺席。 |
| 輕微與嚴重逆向選擇下，分離／部分混同的條件及多重均衡 | **1/2** | 投稿導出進入門檻與「低型別獨自交易／兩型別交易」多重均衡；它的「分離」是高型別不進場，不是原文的不同工資子市場。原文 Proposition 1–2（PDF 頁 12、14）處理篩選與部分混同。 |
| 增加接觸可能降低福利 | **1/2** | 投稿只給任意從 `n=1` 混同切到 `n=2` 分離的跨均衡選擇例子；每條固定均衡分支福利反而上升，沒有選擇規則。原文 Proposition 3（PDF 頁 18）給高型別效用可能隨申請數增加而下降的條件。 |
| 大接觸極限下的 Akerlof 結果、持續摩擦與過度進入 | **0/2** | 投稿未分析原文 Proposition 4–6（PDF 頁 19–22）的極限；模型沒有內生公司進入，因此無法重建過度進入。 |
| **總分** | **3/10** | 低於預定 8/10 門檻；完整性及審稿門檻亦未通過。 |

## 稿件本身與 repo gate

投稿的模型給出統一精算公平價格、外生且獨立的買方可用率、私人品質賣方進場成本。作者證明進場門檻 `z_n=c_H+k_H/A_n`、純／混合參與均衡和自身模型內的福利排序；[例子腳本](attempt/research/analysis/check_example.py)的精確分數計算可重跑。編譯報告顯示 7 頁 PDF；[LaTeX 完成報告](attempt/research/analysis/latex-final.json)為 `delivery_ready=true`。沒有 Lean 證明，故只能稱紙本推導，不能稱形式驗證。

[獨立代理盲審](review/independent-agent-report.md)逐式驗算後認為上述**限制模型內**的定理、邊界及數值例子成立，同時判定頂刊 Reject：新意未確立；多重接觸只改變外生配對機率；跨均衡福利下降沒有選擇機制；「完整均衡集合」只在投稿自訂的價格概念內成立。這是與寫作代理分離的 AI 代理審稿，不是團隊外真人領域審稿。

文獻調查因已發表直接命中而判 `blocked/reframe`，這是正確的重複風險阻擋；歷史重建任務仍可作為測試繼續，但不能改寫為新研究可投稿。[workflow 最終輸出](attempt/research/workflow-final.json)為 `blocked`，首先報缺少機器可讀的 `research/topic-survey.json`，後續還有 [10 項未交付 artifact](missing-artifacts.json)，包含 claim manifest、coverage、獨立 substantive review、團隊 handoff 和 mechanism audit。它的 `spent_budget=0.051` 秒只計腳本執行，不計代理實際研究時間，不能當作試驗成本。按預註冊標準，本次**不通過**完整性、科學重建、Audit Gate 及頂刊成功條件。

## 外部領域審稿狀態

[可直接送審的資料包](external-review-packet.md)與[邀請函草稿](external-review-request.txt)已準備，含封存投稿、原文、盲性紀錄、固定 rubric 及要求審查的六個面向。**目前沒有團隊外經濟學者的回覆，因此不能聲稱完成外部人類審稿。** 待指定研究者／平台及取得實際回覆後，應保留原始評語、署名／專長、日期與投稿 hash，不得把獨立代理審稿改標為外部人類審稿。

此單一理論題的失敗不能估計 harness 對所有經濟學題目的成功率。它具體顯示：從問題到簡化可證模型可做到；要重建頂刊的制度細節、核心取捨、福利與極限定理，以及交齊機器可稽核證據，現行自主迴圈尚未做到。
