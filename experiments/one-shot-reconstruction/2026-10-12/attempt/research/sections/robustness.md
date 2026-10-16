
Sensitivity checks address specific measurement and composition threats. Alternative part-time weights change the mapping from headcounts to labor input. Excluding managers changes both the outcome and the complete-component sample. Omitting permanent closures conditions on survival and therefore addresses a different population; it is not preferred because it can remove part of a policy response. Interview-mode and shore restrictions examine reporting and seasonal-composition differences. Leave-one-chain-out estimates test dependence on a chain's weight, and winsorization reduces the influence of extreme changes. Every variant is displayed without selecting on its standard error. % [claim:C_ROBUST]

\begin{table}[htbp]\centering
\caption{Sensitivity of the employment contrast}\label{tab:robust}
\begin{tabular}{lrrr}
\toprule
Variant & Estimate & HC1 SE & N \\
\midrule
Part-time weight 0.4 & \result{robust_pt04.estimate}{2.82} & \result{robust_pt04.std_error}{1.36} & \result{robust_pt04.n}{384} \\
Part-time weight 0.6 & \result{robust_pt06.estimate}{2.68} & \result{robust_pt06.std_error}{1.34} & \result{robust_pt06.n}{384} \\
Exclude managers & \result{robust_no_managers.estimate}{2.94} & \result{robust_no_managers.std_error}{1.32} & \result{robust_no_managers.n}{391} \\
Omit permanent closures & \result{robust_no_permanent.estimate}{2.72} & \result{robust_no_permanent.std_error}{1.34} & \result{robust_no_permanent.n}{378} \\
Phone interviews & \result{robust_phone_only.estimate}{2.58} & \result{robust_phone_only.std_error}{1.39} & \result{robust_phone_only.n}{353} \\
Omit shore locations & \result{robust_no_shore.estimate}{2.97} & \result{robust_no_shore.std_error}{1.34} & \result{robust_no_shore.n}{352} \\
Omit Burger King & \result{robust_omit_chain1.estimate}{1.55} & \result{robust_omit_chain1.std_error}{1.34} & \result{robust_omit_chain1.n}{225} \\
Omit KFC & \result{robust_omit_chain2.estimate}{3.56} & \result{robust_omit_chain2.std_error}{1.56} & \result{robust_omit_chain2.n}{305} \\
Omit Roy Rogers & \result{robust_omit_chain3.estimate}{2.90} & \result{robust_omit_chain3.std_error}{1.61} & \result{robust_omit_chain3.n}{290} \\
Omit Wendy's & \result{robust_omit_chain4.estimate}{2.64} & \result{robust_omit_chain4.std_error}{1.50} & \result{robust_omit_chain4.n}{332} \\
Winsorized changes & \result{robust_winsor_changes.estimate}{2.48} & \result{robust_winsor_changes.std_error}{1.26} & \result{robust_winsor_changes.n}{384} \\
\bottomrule
\end{tabular}
% [claim:C_ROBUST]

\begin{minipage}{.95\linewidth}\small\medskip
Notes: Each row changes one rule from the primary contrast. All coefficients are NJ minus PA mean changes. Removing managers allows records missing manager counts to enter. Winsorization caps pooled changes at the first and ninety-ninth percentiles. Subset results change the target population and remain subject to the same comparison assumptions.
\end{minipage}
\end{table}
% [claim:C_ROBUST]

All displayed sensitivity coefficients remain positive. Their magnitudes are not identical: omitting Burger King yields \result{robust_omit_chain1.estimate}{1.55}, while omitting KFC yields \result{robust_omit_chain2.estimate}{3.56}. Consequently, a single common effect across chains is not established. The closure-excluding contrast is \result{robust_no_permanent.estimate}{2.72}. Stability of these signs cannot refute a shared differential state shock or measurement error common to multiple variants. % [claim:C_ROBUST] [claim:C_LIMIT]

A diagnostic compares Pennsylvania restaurants with the \result{highwage.n_nj}{25} New Jersey complete-pair restaurants whose initial wage is at least the new minimum. The contrast is \result{highwage.estimate}{-2.57} with HC1 standard error \result{highwage.std_error}{2.12}. This differs in direction from the full sample and is imprecise. High-wage establishments are a selected group, not an untreated experiment: wage spillovers and differing trends remain possible. The diagnostic therefore cautions against interpreting one uniform state effect and does not validate or reject parallel trends by itself. % [claim:C_DIAGNOSTIC] [claim:C_LIMIT]

Table~\ref{tab:outcomes} shows a starting-wage change contrast of \result{outcome_starting_wage.estimate}{0.50} dollars per hour. Figure~\ref{fig:wages} displays the distributions, including the new wage floor. These wage observations provide evidence of changed reported entry pay. They do not measure hours paid, productivity, turnover, profits, or total payroll. The meal-price contrast is \result{outcome_meal_price.estimate}{0.10} dollars; opening hours and full-time share show different changes. These are auxiliary reduced-form descriptions on outcome-specific samples, and the paper does not claim to establish a pass-through, monopsony, or turnover mechanism. % [claim:C_AUX]

\begin{table}[htbp]\centering
\caption{Other reported restaurant outcomes}\label{tab:outcomes}
\begin{tabular}{lrrr}
\toprule
Outcome change & NJ--PA & HC1 SE & N \\
\midrule
Starting wage (dollars/hour) & \result{outcome_starting_wage.estimate}{0.50} & \result{outcome_starting_wage.std_error}{0.05} & \result{outcome_starting_wage.n}{370} \\
Opening hours/day & \result{outcome_opening_hours.estimate}{-0.11} & \result{outcome_opening_hours.std_error}{0.10} & \result{outcome_opening_hours.n}{399} \\
Meal price (dollars) & \result{outcome_meal_price.estimate}{0.10} & \result{outcome_meal_price.std_error}{0.04} & \result{outcome_meal_price.n}{356} \\
Full-time share (fraction) & \result{outcome_fulltime_share.estimate}{0.06} & \result{outcome_fulltime_share.std_error}{0.04} & \result{outcome_fulltime_share.n}{378} \\
\bottomrule
\end{tabular}
% [claim:C_ROBUST]

\begin{minipage}{.95\linewidth}\small\medskip
Notes: Outcome-specific complete pairs; all contrasts are unweighted changes. Meal price sums soda, small fries, and entree prices including tax. Full-time share includes managers and is undefined for zero total headcount. The reported standard errors condition on restaurant independence.
\end{minipage}
\end{table}
% [claim:C_ROBUST]

\begin{figure}[htbp]\centering
\includegraphics[width=.9\linewidth]{../../output/figures/wages.pdf}
\caption{Reported starting wages in the two survey waves}\label{fig:wages}
\small Notes: Histograms use all observed starting wages in each state and wave. The dotted line marks the new NJ floor. The displayed wage range does not impose a restriction on estimation samples.
\end{figure}
% [claim:C_ROBUST]

