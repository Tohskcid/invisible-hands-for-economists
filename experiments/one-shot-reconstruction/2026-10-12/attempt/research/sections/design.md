
Let $D_i$ indicate a New Jersey restaurant, and let $t=0,1$ denote the baseline and late-year observations. The primary observable target is
\begin{equation}
\delta_{\mathrm{obs}}=E[\Delta Y_i\mid D_i=1,R_i=1]
-E[\Delta Y_i\mid D_i=0,R_i=1],
\label{eq:did}
\end{equation}
where $R_i=1$ means complete employment components in both waves. It is a contrast on the retained sample. Under no relevant baseline anticipation, consistency, no spillovers to Pennsylvania, and equality of mean untreated changes for these sampled groups, the contrast equals an average effect for the observed treated group. Appendix~\ref{app:derivation} shows exactly where those assumptions enter. Conditioning on complete pairs introduces an additional selection requirement if treatment changes whether an outcome is observed. The estimand is not silently extended to all original establishments. % [claim:C_ESTIMAND] [claim:C_LIMIT]

The estimator is the coefficient on $D_i$ in
\begin{equation}
\Delta Y_i=\alpha+\delta D_i+u_i.
\label{eq:reg}
\end{equation}
OLS here equals the difference in mean changes. No weights, post-treatment controls, restaurant-level trend terms, or exposure-driven sample search are used. A supporting regression adds baseline chain indicators and company ownership. A second supporting specification uses the initial wage gap $G_i=D_i\max\{(5.05-w_i)/w_i,0\}$ in place of the state indicator. The gap coefficient is an association per unit of proportional exposure, not an instrumented elasticity: initial wages may reflect demand, productivity, or measurement error. % [claim:C_ESTIMAND] [claim:C_GAP]

With only one baseline wave, pre-policy trends cannot be estimated. A non-significant comparison of baseline levels would not test parallel trends; levels need not match under difference-in-differences. Similarly, unchanged starting wages in Pennsylvania would establish a wage comparison, not identical counterfactual employment trends. The design audit therefore marks parallel trends, anticipation, and spillovers inconclusive. It does not manufacture placebo dates or a pretrend test from unavailable observations. % [claim:C_LIMIT]

The table reports the conventional homoskedastic OLS standard error and the HC1 restaurant-level sandwich standard error. A stratified restaurant bootstrap resamples establishments separately within each state using a fixed seed. These procedures condition on the two observed state paths and assume appropriate restaurant independence. They do not represent random assignment of the policy and do not absorb a shared state-by-time shock. The number of policy jurisdictions is \result{audit.state_clusters}{2}, so a many-state cluster asymptotic argument is unavailable. No statewide significance test is claimed. % [claim:C_INFERENCE]

A useful sensitivity interpretation is algebraic. If the mean untreated employment change in New Jersey would have exceeded that in Pennsylvania by $b$ FTE workers, then the policy effect consistent with the observed contrast is $\delta_{\mathrm{obs}}-b$. Thus a differential untreated change equal to the estimated contrast accounts for it entirely. The data do not identify $b$. This exposes the untestable comparison assumption without assigning a probability to it. % [claim:C_ESTIMAND] [claim:C_LIMIT]

