# Specialized Financial and Economic Database Cleaning Recipes

Read this reference when ingesting, cleaning, merging, or auditing datasets from standard financial, micro, and macroeconomic databases. General data cleaning rules apply, but each database contains institutional idiosyncrasies and convention traps that distort empirical estimates if ignored.

---

## 1. WRDS: CRSP & Compustat Merging (CCM)

Merging CRSP (security prices) with Compustat (firm accounting fundamentals) requires the CRSP/Compustat Merged (CCM) link table. Never merge directly on ticker or raw CUSIP (historical CUSIP changes over time; use 8-digit historical CUSIP or permanent identifiers `PERMNO` and `GVKEY`).

### Critical Rules
1. **CCM Link Filtering**:
   - Filter `linktype` in `('LU', 'LC')` (`LU`: Link researched; `LC`: Link official). Avoid `LD`, `LN`, or `LX` unless explicitly studying defunct linkages.
   - Filter `linkprim` in `('P', 'C')` (`P`: Primary link; `C`: Primary link to individual class).
   - Date range match: `linkdt <= datadate <= linkenddt` (where `linkenddt IS NULL` or `'E'` denotes current active link).
2. **CRSP Price & Return Hygiene**:
   - Negative prices in CRSP: A negative price in CRSP `prc` indicates the closing price was not available and represents the **bid-ask midpoint**. Always take the absolute value: `abs(prc)` when calculating market equity.
   - Shares outstanding (`shrout`): Expressed in **thousands**. Market Equity (in \$) $= |\text{prc}| \times \text{shrout} \times 1,000$.
   - Delisting Returns (`dlret`): When a firm delists, its final return must incorporate delisting return: $R_{adj} = (1 + R)(1 + dlret) - 1$. If $dlret$ is missing and delisting is for performance reasons (delisting codes 500, 520–584), standard practice (Shumway 1997) assigns a $-30\%$ replacement return.
3. **Compustat Fiscal Year Lag Conventions (Fama & French)**:
   - Firms report annual financials with a reporting lag (SEC 10-K deadline is 60–90 days after fiscal year-end).
   - Standard convention: Match accounting data from fiscal year ending in calendar year $t-1$ to stock returns from **July of year $t$ to June of year $t+1$**. This ensures market participants actually had access to the 10-K filings.
4. **Book Equity ($BE$) Construction (Davis, Fama, & French 2000)**:
   - $BE = \text{Stockholders' Equity} (SEQ) - \text{Preferred Stock} + \text{Deferred Taxes and Investment Tax Credit} (TXDITC)$.
   - Preferred Stock priority order: Redemption Value ($PSTKRV$), Liquidating Value ($PSTKL$), or Carrying Value ($PSTK$).
   - If $SEQ$ is missing, fallback to: $\text{Common Equity} (CEQ) + PSTK$, or $\text{Total Assets} (AT) - \text{Total Liabilities} (LT)$.

---

## 2. Taiwan Economic Journal (TEJ 台灣經濟新報)

TEJ is the primary source for Taiwan stock market (TWSE & TPEx) and corporate financial statements.

### Critical Rules
1. **Stock Code Alignment**:
   - Common stock codes in Taiwan are 4-digit numbers (e.g., `2330`).
   - Preferred stocks and warrants append characters (e.g., `2882A`). For standard corporate finance studies, exclude preferred shares, DRs, and ETFs.
2. **Price Adjustment for Dividends/Splits**:
   - TEJ provides both unadjusted close (`收盤價`) and adjusted close (`除權息調整收盤價` / `日收盤價(元)_報酬率用`). Always use adjusted series for capital gains and holding period returns.
3. **Cumulative vs. Single Quarter Accounting (累計數轉單季)**:
   - Taiwan corporate financial reports (under IFRS) report cumulative year-to-date numbers for Q2 and Q3 (e.g., Q2 net income is cumulative Q1+Q2; Q3 is Q1+Q2+Q3).
   - For quarterly flow variables (Revenue, Net Income, Operating Cash Flow), compute **discrete single-quarter** numbers:
     $$\text{Flow}_{Q2} = \text{Cum}_{Q2} - \text{Cum}_{Q1}, \quad \text{Flow}_{Q3} = \text{Cum}_{Q3} - \text{Cum}_{Q2}, \quad \text{Flow}_{Q4} = \text{Annual} - \text{Cum}_{Q3}$$
   - Balance sheet items (Assets, Debt) are stock variables and do not require subtraction.
4. **Industry Classification**:
   - Use TSE/OTC standard industry codes (`證券主產業別`), or TEJ sub-industry codes (`TEJ主產業名`). Financial and insurance firms (`金控業`, `銀行業`, `保險業`) have fundamentally different balance sheet structures and must be analyzed separately or excluded in non-financial corporate empirical studies.

---

## 3. China: CSMAR (國泰安數據庫)

CSMAR is the standard database for Chinese A-share listed firms (Shanghai, Shenzhen, Beijing exchanges).

### Critical Rules
1. **A-Share Board Classification**:
   - Filter by stock code prefix:
     - Shanghai Main Board (`600xxx`, `601xxx`, `603xxx`, `605xxx`)
     - Shenzhen Main Board (`000xxx`, `001xxx`)
     - ChiNext / 創業板 (`300xxx`)
     - STAR Market / 科創板 (`688xxx`)
     - Beijing Stock Exchange (`8xxxxx`, `4xxxxx`)
   - ChiNext and STAR markets have different IPO, listing, and daily price fluctuation limit rules (20% limit vs. 10% on main boards).
2. **ST and Financial Firm Screening**:
   - Always track Special Treatment (`ST` or `*ST`) status via `ST_status` or trading state indicators. Standard practice drops `ST` / `*ST` firms due to abnormal trading constraints and delisting distress.
   - Exclude financial industry firms (CSRC 2012 industry code `J` / 金融業).
3. **Return Series Selection**:
   - Use `Dretwd` (Daily Return with Cash Dividend Reinvested / 考慮現金紅利再投資的日個股回報率) for total shareholder return.
   - Do not use `Dretnd` (without cash dividend) unless specifically studying dividend yield effects.
4. **Quarterly Financial Aggregations**:
   - Chinese GAAP quarterly reports are cumulative year-to-date. Decompose Q2, Q3, and Q4 into stand-alone quarterly figures before panel estimation.

---

## 4. Micro & Survey Data: CFPS & US Census / ACS (via IPUMS)

Micro-level survey and census microdata require strict handling of sampling designs and longitudinal panel keys.

### A. China Family Panel Studies (CFPS)
- **Panel Tracking**:
  - Individual unique ID is `pid`; household ID is `fid[year]` (e.g., `fid18`, `fid20`).
  - Households split and merge across waves. Link individuals across waves using immutable `pid`. Never assume household composition is static over time.
- **Survey Weights**:
  - CFPS uses multi-stage stratified probability-proportionate-to-size (PPS) sampling.
  - Always use wave-specific sampling weights (`rweight` for cross-sectional analysis, `pweight` for longitudinal panel analysis) to correct for unequal selection probabilities and non-response attrition.

### B. US Census & ACS (via IPUMS NHGIS / USA)
- **FIPS Code Normalization**:
  - State FIPS must be 2 digits with leading zero (`01` to `56`).
  - County FIPS must be 3 digits with leading zeroes (`001` to `840`).
  - Combined County FIPS must be a **5-digit zero-padded string** (e.g., `str_pad(fips, width=5, pad="0")` or `f"{fips:05d}"`). Converting to integer drops leading zeros and breaks spatial merges (e.g., Connecticut `09001` becomes `9001`).
- **Longitudinal County Boundary Harmonization**:
  - County boundaries change over time (e.g., Virginia independent cities, Alaska boroughs, Broomfield County CO created in 2001).
  - When comparing counties across 1990, 2000, 2010, and 2020, use standardized crosswalks (e.g., IPUMS NHGIS crosswalk files) rather than raw FIPS.
- **Weights**:
  - Use `PERWT` for individual-level regressions and `HHWT` for household-level regressions.
  - Compute standard errors using survey cluster design (`CLUSTER`) and strata (`STRATA`) when available.

---

## 5. Macroeconomic Aggregates: FRED & Penn World Table (PWT)

### A. Federal Reserve Economic Data (FRED)
- **Seasonal Adjustment**:
  - Distinguish Seasonally Adjusted (`SA` / `SAAR`) from Not Seasonally Adjusted (`NSA`). Never mix SA and NSA series in the same model.
- **Frequency Aggregation Rules**:
  - Flow variables (GDP, Industrial Production): Aggregate by **sum** or **flow rate**.
  - Stock variables (Debt, Money Supply): Aggregate using **end-of-period** value.
  - Prices / Rates (CPI, Treasury Yields, Exchange Rates): Aggregate using **period average** (`mean`).

### B. Penn World Table (PWT 10.x)
Never choose real GDP variables arbitrarily; PWT provides distinct series for distinct questions (Feenstra, Inklaar, & Timmer 2015):
- **`rgdpe` (Expenditure-side real GDP)**:
  - Measures consumer and government living standards and purchasing power across countries. Use for comparing welfare or standard of living.
- **`rgdpo` (Output-side real GDP)**:
  - Measures productive capacity across countries at constant national prices. **Use for estimating production functions, TFP growth, or economic productivity.**
- **`cgdpe` / `cgdpo`**:
  - Current-price real GDP measures (comparable across countries in a single year, not across time).
- **`pl_con` / `pl_gdpo`**:
  - Price levels relative to the US (US $= 1$). Useful for real exchange rate and Balassa-Samuelson analyses.

---

## 6. Energy, Electricity Grid, & Environmental Economics

### A. US Energy Information Administration (EIA-860 & EIA-923)
- **Generator-Level Linkage (EIA-860)**:
  - Unit key: `Utility ID` + `Plant Code` (ORISPL code) + `Generator ID`.
  - Distinguish **Nameplate Capacity** (design capacity in MW) from **Net Summer / Net Winter Capacity** (actual deliverable capacity accounting for ambient temperature and cooling derating).
  - Filter `Operating Status`: Operating (`OP`), Standby (`SB`), Retired (`RE`), or Planned (`PL`).
  - Prime Mover Codes: Combined Cycle (`CC`, `CA`, `CT`), Gas Turbine (`GT`), Steam Turbine (`ST`), Photovoltaic (`PV`), Wind (`WT`), Nuclear (`ST`).
- **Generation & Fuel Consumption (EIA-923)**:
  - File schedules: Schedule 1 (generation & fuel by plant/prime mover) vs. Schedule 2 (fuel receipts and costs).
  - Flow vs. stock: Net Generation (`Netgen`) is in **MWh**; Fuel Heat Input is in **MMBtu**.
  - Heat Rate Calculation: $\text{Heat Rate (Btu/kWh)} = \frac{\text{Fuel Consumed (MMBtu)} \times 1,000,000}{\text{Net Generation (kWh)}}$. Flag implausible outliers ($< 6,000$ or $> 25,000$ Btu/kWh for thermal units).

### B. EPA Continuous Emission Monitoring System (CEMS) & eGRID
- **Hourly Smokestack Emissions (CEMS / CAMPD)**:
  - Hourly observations at `ORISPL` + `Unit ID` level for facilities $\ge 25$ MW.
  - Reportable pollutants: $SO_2$ (lbs), $NO_x$ (lbs), $CO_2$ (short tons, $1 \text{ short ton} = 2,000 \text{ lbs}$).
  - Merge to EIA: `ORISPL` in CEMS equals `Plant Code` in EIA, but `Unit ID` (boiler/stack) does not always map 1:1 to EIA `Generator ID`. Use the EPA-EIA Crosswalk (e.g., published by EPA/NREL) when aggregating to generator level.
- **Emissions & Grid Mix (eGRID)**:
  - Level of aggregation: Balancing Authority Area (BAA) and eGRID Subregion (e.g., `CAMX`, `ERCT`, `RFCW`, `SRMW`).
  - Distinguish total output emission rate from **non-baseload emission rate** (marginal emission factor approximation for displaced load).

### C. Wholesale Electricity Markets & Locational Marginal Pricing (LMP)
- **ISO / RTO Nodal Prices (PJM, ERCOT, CAISO, NYISO, MISO, ISO-NE, SPP)**:
  - LMP Decomposition:
    $$\text{LMP}_{n, t} = \text{LMP}_{energy, t} + \text{LMP}_{congestion, n, t} + \text{LMP}_{loss, n, t}$$
  - Negative LMP Conventions: Negative prices occur during periods of high non-dispatchable renewable supply (wind/solar) or minimum generation constraints. Never take log of raw LMP; use level prices, hyperbolic sine transformation ($\text{asinh}$), or truncate with explicit indicator flags.
  - Timezone & Clock Change (DST) Alignment:
    - RTO timestamps are reported in Eastern Standard Time (EST / UTC-5) or prevailing local clock time.
    - Spring transition day has **23 hours** (missing hour 2:00–3:00 AM); Autumn transition day has **25 hours** (duplicate hour 1:00–2:00 AM marked with suffix `A`/`B` or duplicate timestamp). Standardize all time indices to UTC or fixed standard time (e.g., EST) before panel estimation.

---

## 7. Patent & Innovation Economics (USPTO PatentsView / Google Patents / NBER)

### A. Assignee Entity Disambiguation
- Raw assignee names in patent databases suffer from spelling variants, corporate entity suffixes (`Inc`, `Corp`, `LLC`), and foreign language transliterations.
- Use disambiguated identifiers (`assignee_id` in PatentsView; GVKEY/PERMNO crosswalk via Kogan et al. 2017 or Arora et al. 2021).
- Account for corporate mergers and acquisitions (M&A): patents granted to a subsidiary belong to the parent firm's corporate portfolio at the time of invention.

### B. Truncation Bias & Grant Lags
- **Application Year vs. Grant Year**:
  - Always measure innovation timing by **application/filing year** (when the invention was actually conceived), not grant year.
  - Grant delay: A patent takes 2 to 5 years from application to grant. In the most recent 3–4 years of any patent dataset, applications that were eventually granted will be systematically missing (truncation bias).
  - Truncation Adjustment: Drop the last 3–4 years of the panel or apply Hall, Jaffe, and Trajtenberg (2001) citation-lag weight adjustments:
    $$\text{Adjusted Citations}_{i, t} = \frac{\text{Observed Citations}_{i, t}}{\hat{P}(\text{citation received within } T-t \text{ years})}$$

### C. Technology Classification & Fractional Attribution
- Cooperative Patent Classification (CPC) / International Patent Classification (IPC).
- Patents frequently span multiple 4-digit or 6-digit technology classes.
- When aggregating patents to industry/technology level, apply **fractional weighting** ($1/K$ weight if patent lists $K$ subclasses) to avoid double-counting innovative output.

---

## 8. Audit & Checksum Protocol

When preparing cleaned datasets from these sources:
1. Preserve the raw downloaded files in `data/raw/` with zero modifications.
2. Record SHA-256 hashes in `data/raw/checksums.sha256`.
3. Script all transformations (filtering, merging, winsorizing) deterministically with explicit random seeds.
4. Save the resulting analytic dataset in `data/clean/` or `data/processed/`.
