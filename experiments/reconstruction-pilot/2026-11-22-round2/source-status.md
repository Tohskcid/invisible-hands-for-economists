# 期刊論文來源與資料可用性

外部查找紀錄封存於 2026-11-21T20:54:51.534001+00:00，本地檔案清查完成於 2026-11-21T20:59:32.795712+00:00。這份查找進行中的快照涵蓋目錄內全部 15,168 個相異 DOI。每列對應一篇目錄紀錄。檔案身分、實驗所需資料與重建結果分開記錄。

| 來源狀態 | DOI 數 | 判定依據 |
| --- | ---: | --- |
| 已辨識文章版本 | 169 | 已逐檔核對雜湊、標題、作者、正文與末頁。出版版、接受稿及工作論文的分類另見 reviewed_pdf_versions。 |
| 有待辨識的本地全文候選 | 427 | 已有 PDF 線索或含 DOI 與正文的 NIH 文章 XML，仍待完整來源核對。 |
| 尚無匹配的本地主要全文 | 14,572 | 此時只見書目、附件或尚待處理的外部線索。 |

OpenAlex 查詢了 15,168 個 DOI，精確匹配 14,780 個，其中 6,775 個帶有開放取用線索。Crossref、OpenAlex 與 PMC 的授權和版本資料目前支持 1,088 個 DOI 的 1,477 個 PDF 位置。已從 352 個位置取得 PDF。同篇文章可以有多個位置，取得的檔案也可能是附錄或資料說明。

NIH/NLM/NCBI PubMed Central Article Datasets 提供 238 篇有本地 JATS 全文的文章，其中 233 份為作者稿，5 份為出版版。研究檔保存來源授權、提供者校驗碼與本地 SHA-256。原始資料供應者為美國國家衛生研究院、國家醫學圖書館暨國家生物技術資訊中心。 [PMC 官方資料說明](https://pmc.ncbi.nlm.nih.gov/tools/pmcaws/) · [資料條款](https://pmc-oa-opendata.s3.amazonaws.com/README.txt)

逐篇檢索時，可用 local_pdf_status 和 pmc_jats_versions 查找不同格式，用 local_supplement_pdfs 和 local_documentation_pdfs 辨別附件，用 case_readiness 和 data_reason 檢查已知的研究前提。實驗判定以各案的盲測與獨立評閱紀錄為準。未評估的資料可用性保留為 unassessed。

[下載完整 DOI 表](source-status.tsv.gz) · [統計、主機回應與來源雜湊](source-status-summary.json)
