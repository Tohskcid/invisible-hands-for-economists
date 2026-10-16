# 自動論文工作流：工程實驗紀錄

執行時間：2026-10-16T16:17:59.265918+00:00

此批使用小型合成或示意資料，測試重跑、編譯、gate、修補與中斷恢復。它不衡量真實論文品質。

| 案例 | 重跑 | 自動編譯 | 完整 package | 狀態 |
|---|---|---|---|---|
| Case 1: Synthetic DiD engineering fixture | True | True | False | blocked |
| Case 2: Bargaining manuscript fixture | — | True | False | blocked |
| Case 3: Synthetic event-return engineering fixture | True | True | False | blocked |
| Case 4: Bounded Self-Patching for CLI Flag Defect | — | — | — | engineering test |
| Case 5: Interruption & Budget Control | — | — | — | engineering test |

## 未通過的關卡

- Case 1: Synthetic DiD engineering fixture：
  - check_topic_survey.py：schema_version must be '2'; question must be a non-empty string; scope must be a non-empty string；其餘見 report.json
  - check_data_provenance.py：schema_version must be '1'; generated_at must be an ISO-8601 timestamp with timezone; datasets must be a non-empty list
  - check_literature_archive.py：schema_version must be '1'; generated_at must be an ISO-8601 timestamp with timezone; papers must be a list
  - check_manuscript_coverage.py：required empirical roles missing: ['appendix', 'conclusion', 'data', 'identification', 'limitations', 'literature', 'robustness']
  - check_research_team.py：missing research roles: ['data_acquisition', 'data_cleaning', 'interpretation', 'literature', 'model', 'planning', 'review', 'validation', 'writing']; manuscript delivery requires two research agents and one independent review agent; substantive review reviewer_id must match the team review agent；其餘見 report.json
  - check_substantive_review.py：review does not bind the current manuscript; review does not bind the current topic survey; review requires reviewer_id；其餘見 report.json
  - check_logic_review.py：overall_verdict must be pass, revise, or reject
  - check_design_audit.py：diagnostic 'anticipation' has invalid status; diagnostic 'assignment' has invalid status; diagnostic 'comparison-groups' has invalid status；其餘見 report.json
  - check_latex.py：visual review status must be pass; visual review must cover every PDF page exactly once
- Case 2: Bargaining manuscript fixture：
  - check_topic_survey.py：schema_version must be '2'; question must be a non-empty string; scope must be a non-empty string；其餘見 report.json
  - check_literature_archive.py：schema_version must be '1'; generated_at must be an ISO-8601 timestamp with timezone; papers must be a list
  - validate_research_manifest.py：line 2: run_ids entry 'r-1' must reference a run
  - check_manuscript_coverage.py：section 'results' role 'results' requires one of ['proof']; section 'appendix' ready section requires a section_packet artifact; required theory roles missing: ['conclusion', 'limitations', 'literature', 'model']
  - check_research_team.py：missing research roles: ['interpretation', 'literature', 'model', 'planning', 'review', 'validation', 'writing']; manuscript delivery requires two research agents and one independent review agent; substantive review reviewer_id must match the team review agent；其餘見 report.json
  - check_substantive_review.py：review does not bind the current manuscript; review does not bind the current topic survey; review requires reviewer_id；其餘見 report.json
  - check_logic_review.py：overall_verdict must be pass, revise, or reject
  - check_latex.py：visual review status must be pass; visual review must cover every PDF page exactly once
- Case 3: Synthetic event-return engineering fixture：
  - check_topic_survey.py：schema_version must be '2'; question must be a non-empty string; scope must be a non-empty string；其餘見 report.json
  - check_data_provenance.py：schema_version must be '1'; generated_at must be an ISO-8601 timestamp with timezone; datasets must be a non-empty list
  - check_literature_archive.py：schema_version must be '1'; generated_at must be an ISO-8601 timestamp with timezone; papers must be a list
  - validate_research_manifest.py：line 2: run_ids entry 'r-1' must reference a run
  - check_manuscript_coverage.py：required empirical roles missing: ['appendix', 'conclusion', 'data', 'identification', 'limitations', 'literature', 'robustness']
  - check_research_team.py：missing research roles: ['data_acquisition', 'data_cleaning', 'interpretation', 'literature', 'model', 'planning', 'review', 'validation', 'writing']; manuscript delivery requires two research agents and one independent review agent; substantive review reviewer_id must match the team review agent；其餘見 report.json
  - check_substantive_review.py：review does not bind the current manuscript; review does not bind the current topic survey; review requires reviewer_id；其餘見 report.json
  - check_logic_review.py：overall_verdict must be pass, revise, or reject
  - check_design_audit.py：diagnostic 'event-time' has invalid status; diagnostic 'information-leakage' has invalid status; diagnostic 'confounding-news' has invalid status；其餘見 report.json
  - check_latex.py：visual review status must be pass; visual review must cover every PDF page exactly once

完整 package 的結果以表格與上述逐項關卡為準；未完成的研究義務不可由工程 fixture 代替。
案例 4 僅測不支援 CLI 旗標的有限修補；案例 5 僅測已記錄成本與待辦保留。
`build_passed` 只代表自動 LaTeX 檢查；本批沒有人工或獨立 agent 的逐頁審閱。
原始輸入是合成 fixture，不能推論政策因果效果、有效群聚標準誤、正式理論證明或頂刊貢獻。

詳細機器結果見 `report.json`；每個案例的 artifacts 保留在同一目錄。
