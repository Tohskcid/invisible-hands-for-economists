# 頂刊研究問題的一次委派復原實驗

完成評估：2026-10-16。**兩個案例均復原核心內容並產生可審查的獨立論文，但均未完整復原原文，也未通過全部 package gates。** 這輪證明部分執行能力，沒有證明從一句問題可靠完成頂刊論文。

## 實驗怎麼做

從 harness 的十刊 registry 選 AER 實證與 Econometrica 理論各一篇。將目前工作樹的 SKILL、references、scripts、library 共 75 個檔案原樣複製並保存 SHA-256；最終核對固定副本與原 repo 全部相符，沒有先修補 harness。

兩個全新 context 的執行 agent 各自只取得一句科學問題、目標期刊及相同的操作協議；沒有收到原文題名、作者、原文、資料 URL、原始分析程式、已發表數值或評估答案。允許自行搜尋資料，禁止閱讀目標論文或答案式 replication；有披露的模型記憶與搜尋污染，詳見下文。這是指令隔離的共享檔案系統，並非作業系統權限隔離。

- 實證問題：「1992年紐澤西州提高最低工資，如何影響當地速食餐廳的就業？」
- 理論問題：「完全資訊、無限期、輪流出價且各自承擔等待成本的兩人談判，均衡分配與達成協議的時點如何決定？」

原始執行預算分別為 30／25 分鐘、最多 12 次實質分析修訂；首次用量中斷後依使用者「繼續」恢復，各給 20 分鐘。其後再次用量中斷，最終對照與乾淨重跑於 10 月 16 日完成；暫停時間不當成有效研究時間。不能稱為嚴格無中斷 one-shot 成功，也沒有足夠紀錄估計總 token 成本。

## 實際結果

| 案例 | 已完成與驗證 | 尚未復原 | 完整原文／全部交付 gates |
|---|---|---|---|
| Card–Krueger，AER 1994 | 自行找到公開資料；410 筆來源、384 完整配對；就業差分 2.75 FTE，與原文平衡樣本一致；獨立 R 的 116 個數值與 Python 吻合；10 頁稿、12 個 central claims、逐頁視覺 review | 原文 357 筆回歸樣本及完整規格組；部分地區檢驗；另外的開店及 CPS 分析 | 未達成／未通過 |
| Rubinstein，Econometrica 1982 | 14 頁稿；折現均衡、全歷史唯一性論證、固定成本案例、多重均衡及延遲反例；獨立 agent 接受 10 個 central claims、11 個已列證明義務；逐頁視覺 review | 原文較弱一般偏好假設下的完整區間刻畫；部分原始 Nash／零折現處理 | 未達成／未通過 |

原文依據：[Card–Krueger 作者公開原文](https://davidcard.berkeley.edu/papers/njmin-aer.pdf)、[Rubinstein 作者公開原文](https://arielrubinstein.tau.ac.il/papers/11.pdf)。評估端查核原文，執行端未取得 holdout。完整事實與頁碼在 `holdout/`；對照結果在 `research/empirical-comparison.json` 與 `research/theory-comparison.json`。

### 實證數字不是從記憶抄寫

獨立執行 referee 從 raw fixed-width records 重新解析，用 base R 的 QR／OLS、手算組間差分及 sandwich covariance 核算 116 個數值，最大差異約 9.24e-14。主估計 2.75、HC1 SE 1.337725、N=384（NJ 309、PA 75）。餐廳抽樣 SE 只是在觀察到的兩州路徑下的條件不確定性，不能代替州層級政策識別或隨機化推論。

10 月 16 日再把 attempt 複製到乾淨暫存專案，刪除 processed data、結果、生成表格與部分 metadata，重跑分析、base-R 核算與稿件生成。結果樹完全一致，四份表格與最終 `.tex` 的 SHA-256 完全一致；這個測試不等同全部 package 通過，沒有用舊結果充作新計算。證據：`research/clean-replay.json`。既有 PDF 的另外一次 scratch compile 也有 hash-match 紀錄；本次乾淨計算重跑本身未再編譯 PDF。

對照的五個核心數值均落在事前定義 0.05 容差內；平衡樣本差分精確顯示為 2.75。所有可用樣本的差分為 2.753606，原文印 2.76：在容差內，但不是完全相同的兩位小數，沒有隱藏這個差異。其他回歸因樣本與規格不同，不能把它們算成原文回歸復原。

### 理論的通過範圍

獨立 fresh-context agent 審查支持明示模型類別內的完整紙本論證，包括不限於 stationary 的偏離檢查與固定成本延遲構造。這是 agent 對可讀證明的審查，未經人類專家或 Lean kernel 驗證。原文的一般偏好區間定理沒有被同等一般地復原；不能用「找到著名公式」宣稱全部原文完成。

## 交付檢查實際卡在哪裡

兩份最終 `.tex`／manifest／PDF 均與獨立 reviewer 的 hash 一致，現時 logic 和 retained-PDF visual finalize 都通過。實證稿的舊 summary／gate snapshot 寫「review 尚未收到」，是用量中斷前的紀錄；`research/reviews/final-artifact-audit.json` 與 `research/scorecard.json` 才是最終狀態，沒有覆寫舊失敗紀錄。

1. **文獻與研究範圍。** 實證 topic record 是合法的 blocked record，並非 approved survey；理論沒有完成 baseline/frontier survey。禁讀 target 使 nearest-work 驗證受限，但未跑完整搜尋不能全部歸因於禁讀規則。理論唯一概念引用的合法全文取得也失敗，與 target 禁讀是不同限制。
2. **實證強因果義務。** 平行趨勢、預期、外溢、可比反事實及只有兩州的政策推論仍 unresolved；描述性結果與條件性識別推導可讀，不代表已證實政策因果效果。
3. **生成的執行程式需要完成自我修補。** 實證 master 把不支援的 `--json` 傳給 package checker，舊 exit 2 是呼叫錯誤。評估端已用正確 CLI 真正重跑，沒有把 usage error 當成內容 gate。原 frozen master 保留原樣供檢查。
4. **編譯設定沒有沿用到底。** 實證單獨指定 `pdflatex` 可成功，package 的 auto engine 另選 Tectonic，因快取依賴缺失而失敗；這是可重現的配置／環境差異。
5. **最終 build／review／package 仍未閉合。** 理論已審 PDF 本身可 finalize，但 package 在另一個臨時目錄重編得到不同 PDF hash，視覺 binding 再度失敗。不能用一份已審 PDF 替另一份未綁定 build 宣稱 pass。

這輪最直接支持的修補順序是：明確的研究交付 profile與 claim 範圍 → 同一份 build 的 review/release → engine/runtime設定一貫傳遞 → 自動解析失敗並修復生成腳本 → 可持久續跑、更新最後摘要。資料缺口、原文完整性及原創貢獻則要另外評估，不能只靠增加 schema 或讓 JSON 通過處理。這些是實驗後建議，尚未修改核心 harness。

## 這次不能證明什麼

- 兩位 worker 都立即認出經典文章；理論記得候選公式與證明套路，實證搜尋還暴露了估計值／樣本資訊。數值確實重算、證明確實重寫，但不能聲稱無訓練記憶的發現能力。
- 一句問題不唯一決定原作者所有樣本剔除、附加資料或一般性假設；與原文不同不必然代表計算或推論錯誤。
- 只有十刊中的兩刊、無 finance／structural 案例、無「不使用 harness」對照；不能估計總成功率或 harness 的因果增益。
- 中斷與續跑、模型記憶、受限來源及有限預算均保留於紀錄；沒有證明不中斷單次執行能完成完整頂刊論文，更沒有證明可被期刊接受。

## 產物與重跑

- [實證稿 PDF](attempt/output/pdf/main.pdf)／[完整 TeX](attempt/paper/manuscript/main.tex)／[replication 說明](attempt/README_replication.md)
- [理論稿 PDF](attempt-theory/output/pdf/main.pdf)／[完整 TeX](attempt-theory/paper/manuscript/main.tex)／[重跑說明](attempt-theory/research/reproduction.md)
- [最終 scorecard](research/scorecard.json)／[最終 artifact 審計](research/reviews/final-artifact-audit.json)／[獨立 proof/logic/layout 審查](research/reviews/fresh-manuscript-referee.json)

從 repository root 執行：

```bash
python3 experiments/one-shot-reconstruction/2026-10-12/scripts/verify_snapshot.py
python3 experiments/one-shot-reconstruction/2026-10-12/scripts/compare_empirical.py
python3 experiments/one-shot-reconstruction/2026-10-12/scripts/clean_replay.py
```

`clean_replay.py` 使用本機已凍結 raw input 與 Python／R，不重新取得未驗來源，不修改作者成果。它重建計算與 TeX，並非宣告完整 package pass。兩案的所有既有硬性 fail 均保留，最終結論是「核心復原有證據、完整原文與全 gate 交付未達成」。
