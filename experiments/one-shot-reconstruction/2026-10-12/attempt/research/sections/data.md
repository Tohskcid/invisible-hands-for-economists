
The source is the public archive offered on David Card's researcher webpage, with documentation attributing the New Jersey--Pennsylvania surveys to the original project. The acquisition script extracts only the raw ASCII file, codebook, readme, and survey instruments. The SAS program in the archive is excluded. SHA-256 hashes freeze each consumed file, the acquisition script, and the schema. Public download access is verified; no express redistribution license accompanies the source, so the package does not claim an open license for republishing the archive. The data-availability statement gives the access route. % [claim:C_DATA] [claim:C_REPRO] [data:D_RAW]

The raw file contains \result{audit.n_raw}{410} rows, comprising \result{nj.n_raw}{331} New Jersey and \result{pa.n_raw}{79} Pennsylvania establishments in Burger King, KFC, Roy Rogers, and Wendy's. A fixed-width parser uses the codebook's exact column positions and treats a dot as missing. The codebook labels the sheet number as unique, but two source rows share that identifier. They are preserved because they are distinct records; a generated source-row key prevents an unintended merge or deletion. The supplied sample is not treated as a probability sample of all restaurants. Entry of new restaurants and establishments outside the surveyed chains are not observed. % [claim:C_DATA]

The survey asks separately about full-time and part-time nonmanagement workers and managers or assistant managers. Define FTE headcount as full-time workers plus managers plus one-half of part-time workers. This is a headcount conversion, not observed paid hours. The calculation requires every included component to be observed; missing components are not replaced with zero. All \result{audit.permanent_closed}{6} permanently closed restaurants have post-wave employment components recorded as zero and remain in the primary calculation when baseline employment is observed. Temporary closure statuses do not automatically imply zero employment. % [claim:C_DATA]

Complete employment pairs are available for \result{primary.n}{384} establishments. The available-case baseline means and post-wave means use different samples: Pennsylvania has \result{pa.n_pre}{77} baseline and \result{pa.n_post}{77} post-wave employment observations, and New Jersey has \result{nj.n_pre}{321} and \result{nj.n_post}{319}. Table~\ref{tab:means} instead reports a constant sample within each state. Selection into complete pairs is a limitation because missingness may depend on employment changes. The analysis reports observation counts explicitly for each outcome and variant. % [claim:C_DATA] [claim:C_LIMIT]

\begin{table}[htbp]\centering
\caption{Employment on a constant restaurant sample}\label{tab:means}
\begin{tabular}{lrrrrr}
\toprule
State & Source rows & Pairs & Pre FTE & Post FTE & Change \\
\midrule
Pennsylvania & \result{pa.n_raw}{79} & \result{pa.n_pair}{75} & \result{pa.paired_pre}{23.38} & \result{pa.paired_post}{21.10} & \result{pa.change}{-2.28} \\
New Jersey & \result{nj.n_raw}{331} & \result{nj.n_pair}{309} & \result{nj.paired_pre}{20.43} & \result{nj.paired_post}{20.90} & \result{nj.change}{0.47} \\
\bottomrule
\end{tabular}
% [claim:C_DATA]

\begin{minipage}{.95\linewidth}\small\medskip
Notes: FTE is full-time nonmanagers plus managers plus one-half of part-time nonmanagers. Means and changes are unweighted. Source rows refer to the complete downloaded file; pairs require all employment components in both waves. Permanent closures with recorded zero post employment are retained.
\end{minipage}
\end{table}
% [claim:C_DATA]

Starting wages refer to a nonmanagement entrant, not mean wages or the wage bill. Meal price is the sum of the reported soda, small fries, and entree prices, including tax; it is not a quantity-weighted price index. Opening hours are daily hours open. The full-time share includes managers in the numerator and all reported workers in the denominator. A closed establishment has no defined employment share and is omitted from that particular outcome. These distinctions matter when interpreting adjustment margins. % [claim:C_DATA] [claim:C_AUX]

