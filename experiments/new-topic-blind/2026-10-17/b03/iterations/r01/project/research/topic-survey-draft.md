# 非目標背景文獻調查草稿（歷史重建盲測）

原題：「在雇主雇用不可分割的勞動者、政府可依雇用組合或薪資設計稅補的市場中，財政措施何時會保留或恢復需求替代性及其均衡基礎？」

檢索截止與實際檢索日：2026-10-17 UTC；建議 7 天後刷新工作論文通道。模型類別是有限不可分割勞工、多雇主、可轉移薪資與政府政策；欲判別政策後雇主需求的 gross substitutes／契約替代性與均衡存在，而非預設正結論。本文僅做非目標背景掃描；不得據此宣稱研究新穎或已排除重複。受限來源禁令優先於文獻檢索完整性。

## 實際檢索範圍與來源

以網路檢索分離了 (i) 基準：Kelso–Crawford、Hatfield–Milgrom、不可分割品均衡的相關經典結果；(ii) 前沿通道 A：arXiv 的離散凸分析與替代性均衡；(iii) 前沿通道 B：NBER 工作論文中的異質勞工、薪資及媒合均衡。所用一般查詢概念為「job matching gross substitutes」、「matching with contracts substitutes wages」、「discrete convex analysis equilibrium indivisible goods」、「arXiv substitutes competitive equilibrium」、「NBER labor market matching wages amenities」。沒有使用引文數作篩選。檢索工具為 `web.run`；來源取得工具為 Python `urllib.request`；取得時間、HTTPS URL、狀態、檔案位元組數與 SHA-256 均存於 [`literature/sources.json`](literature/sources.json)。可下載 PDF 存於同目錄。原始結果中的疑似受限連結僅在獨立污染紀錄中記 URL/時間，未開啟、閱讀摘要或供下游使用；該紀錄不得傳給作者。

## 最近工作矩陣

| 文獻／主來源 | 問題與定理或方法 | 機制、模型類別及主要結果 | 與本題的可核差異／關係 | 來源證據 |
|---|---|---|---|---|
| [Kelso & Crawford 1982](https://doi.org/10.2307/1913392), *Econometrica* 50:1483–1504 | 異質企業／勞工的職位媒合；工資調整及穩定均衡。 | 雇主視勞工為 gross substitutes 時，即使勞工不可分割，均衡存在且穩定；亦研究調整程序與比較靜態。 | **最近基準／adjacent**。本題必須將任何稅補後命題明確對照其原始 GS 前提；此基準本身沒有內生政策作用的分類。 | 作者提供[全文](https://econweb.ucsd.edu/~vcrawfor/KelsoCrawford82EMT.pdf)，`kelso_crawford_1982.pdf`，SHA `5de5e5dff2c1965de584a9c065a0f434de0d3deb049b29ec051fa4a43caeb0e6`。掃描版 PDF，摘要與書目由原文及作者來源核對。 |
| [Hatfield & Milgrom 2005](https://www.aeaweb.org/articles?id=10.1257/0002828054825466), *AER* 95:913–935 | 具有條款的媒合，包含工資契約；替代性與 aggregate-demand law。 | 以契約作為可選對象統一勞動媒合等模型，給出替代性及需求法則下的配置／程序結果。 | **最近替代／extension 風險**。若政策僅改變企業對契約的選擇函數，政策後的替代性命題可能已落入其一般定理；稿件須從政策原始參數推出可檢驗條件。 | 作者提供[全文](https://milgrom.people.stanford.edu/wp-content/uploads/2005/09/Matching-with-Contracts-AER.pdf)，`hatfield_milgrom_2005.pdf`，SHA `1ebc2b3ee2a0a410057d798a780b1e311c7ea8cba092634b0f11c3f629140a71`。 |
| [Murota 2022](https://arxiv.org/abs/2212.03598), arXiv:2212.03598 | 離散凸分析與經濟學綜述。 | 說明 M♮-concavity 與 gross substitutes 的等價／關聯，以及離散分離、對偶、固定點方法對均衡的用途。 | **adjacent，數學重複風險高**。若稅補保持 M♮-concavity 只是已知封閉性，本題不能把轉譯本身當作新定理。 | [arXiv 全文](https://arxiv.org/pdf/2212.03598)，`murota_2022.pdf`，SHA `785705146c280834f458e5dca243eff059c33661be9dc53cb9f74f47d1616e1a`；摘要頁 SHA `c308ee2724d0594628ea4da625110bf9c27d7af52f16fc9202d84c4fc1dc69e6`。首次公開：2022-12-07（arXiv v1；稿內另有 2016/2022 的歷史標記）。 |
| [Chen, Choo, Galichon & Weber 2023](https://arxiv.org/abs/2309.11416), arXiv:2309.11416 | 一般非參數、非可分競爭系統中的均衡存在與唯一性。 | weak substitutes、pivotal substitutes、responsiveness 作為存在條件，並應用於完全指派配對與離散選擇。 | **adjacent**。其替代條件和均衡工具可能吸收一般存在說法；但模型是一般供給系統，並非本題特定稅補對企業集合需求的變換。 | [arXiv 全文](https://arxiv.org/pdf/2309.11416)，`chen_etal_2023.pdf`，SHA `8112f3d169dba6cb0bd42a7bff4686d7fa4bff2983b6c8410ce9e8a253ee7a22`；摘要頁 SHA `7b6e46d8b992147c3c527b4ab84c2730e742367b706f4370db2c491ee8d71c4d`。首次公開：2023-09-20。 |
| [Lamadon, Lise, Meghir & Robin 2024](https://www.nber.org/papers/w32687), NBER WP 32687（2026-01 修訂） | 異質勞工／企業、工資、非工資待遇與媒合的結構均衡模型。 | 估計與匹配的雇主—雇員行政資料相容的模型；用來解釋工資、流動與排序。 | **adjacent**。可界定現實勞動市場中工資及配對的模型背景；不是本題的離散集合需求或政策下 GS 分類定理。 | [NBER 全文](https://www.nber.org/system/files/working_papers/w32687/w32687.pdf)，`lamadon_etal_2024.pdf`，SHA `19ca15969ea633886da0de4cfe779a85f6156e88a0b535aa9c7c57e2c30b8e72`；頁面 SHA `2c5c62fdf80dfcf830ada270cfd7337672c6ca6aabffb8fc7e40200b82e38dd5`。首次公開：2024-07；現有版修訂 2026-01。 |

## 最近工作的研究動作與影響

**Kelso–Crawford。** 先前障礙是不可分割勞工帶來非凸性，價格調整不必有穩定結果。其關鍵動作是在企業的集合需求上施加可驗證的 gross substitutes 條件，取得均衡存在及調整過程。其影響是為本題提供必須保留或重新建立的精確性質。驗證方式是原論文的定理與證明；我們沒有重作證明。

**Hatfield–Milgrom。** 先前各種配對、勞工薪資與拍賣模型使用不同對象。關鍵動作是把契約條款納入匹配物件，並以 choice-function substitutability 和 aggregate-demand law 得到統一結論。其一般性正是本題的高度重疊來源；若只把稅補編碼成契約價值函數，可能完全是既有框架的特例。驗證方式是發表原文的定義與命題。

**Murota。** 非凸集合函數缺少連續凸分析的交換與對偶工具。其整理的 M-concavity／M♮-concavity 語言把 gross substitutes 與離散凸方法連接，廣泛供均衡和拍賣分析重用。作為本題工具，其價值在於逐項檢查政策轉換是否守住交換公理；不可將綜述所述既有等價性當作本題貢獻。

**Chen et al.。** 一般競爭替代系統中，既有唯一性分析不自動提供存在性。其動作是建立 weak/pivotal substitutes 與 responsiveness 的組合條件、存在結果及算法，供配對與離散選擇重用。若本題嘗試從較弱替代條件取得均衡，須先檢查它是否直接落入該定理。

**Lamadon et al.。** 勞工與企業異質性、待遇及匹配同時進入可估計均衡模型困難。其動作是用行政匹配資料識別和估計模型，顯示實證勞動市場的工資與待遇維度。驗證基於工作論文本身；與本題純理論的直接重疊較小。

## 前沿候選判斷（2021–2026 窗口）

| 候選 | 實質品質訊號（不以作者、期刊或引文數為據） | 可反駁的前沿關聯及稿件動作 |
|---|---|---|
| Murota 2022，arXiv | 明確交換／對偶工具；覆蓋不可分割模型的定理橋接。 | 若政策後目標函數的交換不等式可等價為 M♮-concavity，則既有離散凸工具已給出至少部分結論。**cite/discuss**，用以界定工具與重複風險。 |
| Chen et al. 2023，arXiv | 一般替代系統的可反駁充分條件；含存在、唯一性與計算方法。 | 若政策後雇主需求可嵌入其 weak/pivotal substitutes 系統，可能直接由現有結果得均衡。**cite/discuss**，明確檢查假設映射。 |
| Lamadon et al. 2024，NBER | 工資與非工資待遇同時進入模型；行政配對資料可對模型含義作外部檢驗。 | 若稿件談現實薪資機制或實證適用性，該工作提醒純理論條件與異質性模型間的落差。**discuss** 作限制背景；不支持核心定理。 |

## 重複風險與可防守邊界

1. **極高：政策後替代性被直接假設。** 從「稅後需求滿足 GS」推均衡只回到 Kelso–Crawford 或 Hatfield–Milgrom。必須從稅補函數及稅前原始生產／成本推導 GS 保持或失敗條件，並給出嚴格反例。
2. **高：契約模型的現成涵蓋。** 任意工資相依政策可作為契約收益的變化；若命題只用一般契約選擇替代性，Hatfield–Milgrom 可能已完全涵蓋。貢獻須落在可操作的政策函數分類、尖銳界限或反例，而非框架重述。
3. **高：離散凸分析的已知等價或封閉性。** 單純把稅補寫為可分離項或線性價格移位，可能由 M♮-concavity 的標準工具立即得出。需核實具體封閉命題與新推論，不能以術語轉換作新穎性主張。
4. **中：一般替代性存在定理。** 若欲建立均衡基礎，應精確對照 Chen et al. 的條件；本題可能只需引用現成存在定理並將真正新工作放在政策轉換。
5. **未解：受限直接相關文獻。** 盲測禁令使完整重複審核不可進行。此項不可被解讀為「沒有更近工作」，也不能繞過禁令補查。

可考慮的三條**待研究**路線：對稅補函數給出非同義反覆的充要或足夠條件；證明某些組合稅補確實破壞 GS 並給最小反例；將政策後替代性與均衡定理之間的額外條件明確拆開。以上均非本次文獻調查已支持的貢獻主張。

調查限制：僅兩個前沿通道且時間有限；Kelso–Crawford 作者提供 PDF 為影像掃描；Gul–Stacchetti (1999) 的出版社頁曾在瀏覽器檢到但直接存檔回傳 403，故本矩陣不據其做細節判斷。尚未核查受限直接工作；不得進行該核查。研究者的 scope/contribution/design/claim locks 不由本文獻代理代答。
