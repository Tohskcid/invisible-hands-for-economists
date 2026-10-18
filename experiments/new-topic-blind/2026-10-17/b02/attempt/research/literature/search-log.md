# Blind literature search log

- Question (verbatim): 「在交易者具有私人品質資訊、可同時聯繫多個交易對手的市場中，增加可聯繫對象數量會如何影響分離或混同均衡、交易效率與福利？」
- Retrieval date: 2026-10-16 UTC / 2026-10-17 Asia/Taipei. Cutoff: 2026-10-17 Asia/Taipei. Refresh after: 30 days. Citation policy: never-exclude. Frontier window: 2022–2026.
- Tools: `web.run` search/open against publisher, NBER, CEPR and IZA pages; Python `urllib.request` downloaded original PDFs; `pdftotext` for source inspection. Source checksums and download timestamps are in `source-manifest.json`.
- Blind constraint: no target title was queried. A search result exposed a likely direct target; that exposure is documented **only** in `contamination-log.md`, and its text was excluded from all comparisons and claims below.

## Baseline lane: published work

| Query as submitted | Canonical verified results | What was checked |
|---|---|---|
| `Rothschild Stiglitz 1976 equilibrium competitive insurance markets imperfect information original paper` | [Rothschild–Stiglitz (1976)](https://doi.org/10.2307/1885326) | Oxford publisher metadata and reproduced article PDF. |
| `Wilson 1977 theory of insurance markets imperfect information separating pooling original` | [Wilson (1977)](https://doi.org/10.1016/0022-0531(77)90004-7) | Elsevier publisher metadata/abstract; no full text saved, so excluded from detailed matrix. |
| `Akerlof 1970 market for lemons quality uncertainty quarterly journal economics` | [Akerlof (1970)](https://doi.org/10.2307/1879431) | Oxford/JSTOR publisher metadata; background only. |
| `Burdett Judd 1983 equilibrium price dispersion Econometrica official publisher` | [Burdett–Judd (1983)](https://doi.org/10.2307/1912045) | JSTOR issue record and scanned article PDF. |
| `Guerrieri Shimer Wright 2010 adverse selection competitive search equilibrium Econometrica published paper` | [Guerrieri–Shimer–Wright (2010)](https://doi.org/10.3982/ECTA8535) | Wiley publisher page, NBER full paper. |
| `Sarah Auster Piero Gottardi 2019 adverse selection search many-on-one equilibrium published` | [Auster–Gottardi (2019)](https://doi.org/10.3982/TE2921) | Wiley full article and Econometric Society published PDF. |

Backward chains were inspected only through **non-target** papers: GSW cites Akerlof and Rothschild–Stiglitz; Albrecht et al. discuss GSW and Auster–Gottardi. These are documented links, not evidence that the chain is exhaustive. Forward comparison was made through the frontier candidates below. Search results that directly displayed the likely target were neither opened nor used; see isolated log.

## Frontier lane: two independent working-paper channels

| Query as submitted | Primary source | Status/limit |
|---|---|---|
| `site:cepr.org/publications/dp adverse selection market design search 2023 2024` | [Albrecht et al. (2024), CEPR DP19467](https://cepr.org/publications/dp19467) | Metadata corroboration; full paper obtained independently from [IZA DP17246](https://docs.iza.org/dp17246.pdf). |
| `"Competitive Search with Private Information: Can Price Signal Quality?" pdf` | [IZA DP17246](https://docs.iza.org/dp17246.pdf) | Full text downloaded and checked. Public version dated August 2024. |
| `site:nber.org/papers adverse selection decentralized trading 2024` | [Kong–Layton–Shepard (2024), NBER WP33187](https://www.nber.org/papers/w33187) | Full paper downloaded and checked; different institution and estimand. |
| `"Adverse Selection and (un)Natural Monopoly in Insurance Markets" pdf NBER` | [NBER WP33187 PDF](https://www.nber.org/system/files/working_papers/w33187/w33187.pdf) | Full text verified. Public version dated November 2024. |

Other attempted broad queries mixed disparate results and were not used for positive novelty claims. The search covers English-language indexed theory and working papers reached by these formulations. It does not establish absence of other work, and the blind rule deliberately excludes the apparent direct match.

