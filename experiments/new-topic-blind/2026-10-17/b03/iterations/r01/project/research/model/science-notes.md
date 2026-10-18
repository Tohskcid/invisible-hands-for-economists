# r01 scientific revision notes (2026-10-17)

This is a post-unblind development revision of a historical reconstruction exercise, not a new blind trial. This note uses only the b03 attempt, independent review, local research standards, and the local Murota source listed below. It makes no priority or journal-suitability claim.

## Exact external mathematical dependencies

Source: Kazuo Murota, *Discrete Convex Analysis: A Tool for Economics and Game Theory*, arXiv:2212.03598v1 (7 December 2022), local attempt PDF `research/literature/murota_2022.pdf`, SHA-256 `785705146c280834f458e5dca243eff059c33661be9dc53cb9f74f47d1616e1a`. This is an author-written mathematical survey with exact theorem statements and a proof of the convolution result. The revised manuscript cites its existing `Murota2022` bibliography entry. Its numbered pages below are printed page numbers.

| Locator | Exact role | Hypothesis match |
|---|---|---|
| §3.1, (3.1)–(3.3), p. 5 | Defines set-function M-natural exchange | Identical move-or-swap disjunction to manuscript Definition EX; all bundles have finite real value. |
| §4.1, (4.2)–(4.4), p. 17 | Identifies binary-domain set functions with integer-vector M-natural-concave functions | Extend each `h_f` by `-∞` outside `{0,1}^N`; `N` finite. |
| Theorem 6.1(9), p. 32 | Supremal integer convolution preserves M-natural concavity | Each extended employer valuation and zero dummy valuation has finite effective domain, hence convolution is finite on its effective domain and never `+∞`; finite induction covers all employers. No monotonicity, nonnegative values, or integer-valued payoffs are required. |
| Theorem 9.4, p. 55 | Real-valued M-natural intersection gives a common supporting price | Aggregate convolution `H` and singleton-domain indicator `J` are M-natural-concave; `e=1_N` lies in both effective domains and maximizes `H+J`. The theorem gives a real price vector, with no integer-value or monotonicity condition. |

The complete reduction is in `paper/manuscript/main.tex`, Appendix `app:lp`. The dummy employer holds unused workers. At the supporting price, any decomposition maximizing `H(e)` individually maximizes each employer's price-adjusted value: otherwise its sum would fall below the sum of the individual maxima. Dummy optimality gives nonnegative prices for real-assigned workers and nonpositive prices for dummy-held workers. Replacing the latter prices by zero preserves every real firm's chosen bundle, because only prices of workers absent from that bundle rise. This gives nonnegative equilibrium wages and zero wages for unassigned workers. An integral primal allocation and the corresponding employer-profit/wage dual have equal objectives, discharging the configuration-LP integrality obligation.

This is a `complete paper proof` conditional on the stated external theorems, not an independent proof of those theorems and not `formally proved` in Lean. The earlier conditional LP argument alone was insufficient; it is superseded only in r01.

## Restricted fiscal result

Proposition `prop:rebate` uses two workers, at least two firms, a certified common upper bound `κ` on each firm's production complementarity, a uniform nonnegative rebate `r` for singleton hiring only, and an ex-ante spending cap `B` across every feasible allocation. Spending's exact maximum is `2r`. The two-worker EX threshold requires `2r≥κ` robustly over all allowed valuations. Therefore an admissible policy exists exactly when `B≥κ`. A firm with `v(1)=v(2)=0` and `v(12)=κ` proves the necessity; when `B<κ`, every admissible `r` gives strict EX and all-real-price GS failure. The complete proof and counterexample are in Appendix `app:rebate`.

This threshold is specific to uniform singleton rebates and worst-case expenditure; taxes, contingent transfers, more workers, and welfare are outside the claim. The schedule does not require the full table of firm values, but the certified bound is a maintained information assumption. The cap is a fiscal outlay constraint, not a financing model or budget-balance equation. General bundle correction `g=q-v` remains only an unrestricted algebraic benchmark.

## Remaining obligations and checks

| Obligation | Status |
|---|---|
| EX-to-general equilibrium and configuration-LP integral optimum | Discharged by the paper reduction using external Murota Theorems 6.1(9) and 9.4. |
| Restricted capped rebate threshold and strict counterexample | Discharged by the manuscript's complete paper proof. |
| Government financing, incidence, social-welfare comparison | Unresolved/out of scope; no welfare primitive. |
| Equilibrium under employer-specific wage-dependent transfers | Unresolved; the existing result is demand-only. |
| Novelty against all related fiscal theory | Unresolved; no priority claim. |
| Lean kernel verification | Not run; no formally proved claim. |
| LaTeX compilation, PDF inspection, package/review gates | Not run by this science agent; assigned to PI. |
