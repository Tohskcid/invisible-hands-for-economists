
Table~\ref{tab:main} reports a primary contrast of \result{primary.estimate}{2.75} FTE workers with HC1 standard error \result{primary.std_error}{1.34} and homoskedastic standard error \result{primary.se_homoskedastic}{1.15}. The normal restaurant-level interval is [\result{primary.normal_low}{0.13}, \result{primary.normal_high}{5.37}], while the stratified bootstrap interval is [\result{primary.bootstrap_low}{0.19}, \result{primary.bootstrap_high}{5.27}]. These are conditional uncertainty summaries under restaurant independence. The observed pattern is inconsistent with a negative relative sample employment change, but uncertainty about the counterfactual state paths prevents treating that observation as an unconditional causal conclusion. % [claim:C_MAIN] [claim:C_INFERENCE]

\begin{table}[htbp]\centering
\caption{Employment-change regressions}\label{tab:main}
\begin{tabular}{lrrrr}
\toprule
Specification & Estimate & HC1 SE & OLS SE & N \\
\midrule
State contrast & \result{primary.estimate}{2.75} & \result{primary.std_error}{1.34} & \result{primary.se_homoskedastic}{1.15} & \result{primary.n}{384} \\
Chain/ownership controls & \result{controlled.estimate}{2.78} & \result{controlled.std_error}{1.34} & \result{controlled.se_homoskedastic}{1.16} & \result{controlled.n}{384} \\
Initial wage gap & \result{gap.estimate}{16.36} & \result{gap.std_error}{5.98} & \result{gap.se_homoskedastic}{5.92} & \result{gap.n}{368} \\
Gap with controls & \result{gap_controlled.estimate}{15.88} & \result{gap_controlled.std_error}{6.32} & \result{gap_controlled.se_homoskedastic}{6.04} & \result{gap_controlled.n}{368} \\
\bottomrule
\end{tabular}
% [claim:C_MAIN]

\begin{minipage}{.95\linewidth}\small\medskip
Notes: Outcome is the change in FTE employment. Controls are baseline chain indicators and company ownership. The wage-gap specifications replace the state indicator with the proportional distance of the initial NJ wage below the new minimum; Pennsylvania exposure is zero. Gap coefficients are not directly comparable in units to state-indicator coefficients. Standard errors assume restaurant-level independence.
\end{minipage}
\end{table}
% [claim:C_MAIN]

The controlled state coefficient is \result{controlled.estimate}{2.78}, close to the raw contrast. Figure~\ref{fig:employment} shows why the relative comparison is positive: the New Jersey paired-sample mean changes modestly, while the Pennsylvania paired-sample mean declines. The available-case four-cell contrast is \result{crosssection.estimate}{2.75}, close numerically to the paired estimate despite using changing samples. That proximity is a sample diagnostic, not evidence that missing outcomes are ignorable. % [claim:C_MAIN] [claim:C_ROBUST]

\begin{figure}[htbp]\centering
\includegraphics[width=.8\linewidth]{../../output/figures/employment.pdf}
\caption{Mean employment before and after the wage-floor change}\label{fig:employment}
\small Notes: Unweighted means for the same complete-pair restaurants used in the primary regression. Connecting two observations illustrates changes; it does not provide an event study or a test of trends.
\end{figure}
% [claim:C_MAIN]

The estimated gap slope is \result{gap.estimate}{16.36}, with \result{gap.n}{368} observations, and is \result{gap_controlled.estimate}{15.88} after chain and ownership controls. These positive associations are consistent with larger gains at more exposed restaurants, but they are not a separate source of exogenous assignment. In particular, noisy initial wages, wage-dependent establishment composition, or a recovery at initially low-wage locations can produce such a gradient. The paper does not identify a dose-response curve for arbitrary minimum-wage changes. % [claim:C_GAP]

