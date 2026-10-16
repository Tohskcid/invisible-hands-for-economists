
Run \texttt{python3 scripts/run\_all.py} from the attempt directory. The master verifies the frozen raw checksums, recomputes the processed data, regressions, bootstrap, tables and figures, regenerates this manuscript from its source template, then invokes the unchanged research harness. The master reports actual return codes; failure of a delivery gate does not delete or suppress computed results. Dependencies and the seed are recorded in the environment file. All analysis paths are relative to the attempt directory. % [claim:C_REPRO]

The code-to-exhibit mapping is direct: \path{scripts/analyze.py} generates the employment means, regression table, sensitivity table, auxiliary-outcome table, and both figures. The manuscript builder, \path{scripts/build_package.py}, inserts those generated tables and binds displayed numbers to \path{research/results.json}. Data construction uses fixed-width fields and explicit complete-component rules. The code's primary coefficient equals a separately calculated difference of group means to numerical tolerance. The base-R check reproduces the coefficient and both reported analytical standard errors. % [claim:C_REPRO]

The design gate remains nonpassing where the data cannot resolve anticipation, parallel trends, spillovers, and policy-level inference. Bibliographic discovery is constrained and does not reproduce the target article's argument or every original table. Search-result numeric exposure and model familiarity are retained in \texttt{research/contamination.json}; nothing in the pipeline can erase that exposure. The manuscript is a bounded reconstruction with disclosed limitations, not evidence of an uncontaminated historical discovery or journal acceptance. % [claim:C_SCOPE] [claim:C_LIMIT] [claim:C_REPRO]

\subsection*{Data availability}
The original producer's public dataset page is \url{https://davidcard.berkeley.edu/data_sets.html}, which links the archived \texttt{njmin.zip}. The replication acquisition script downloads that archive and reads only the eligible raw data and documentation. A checksum manifest identifies the exact retrieved bytes. No confidential addresses or telephone numbers are available in the consumed public file, and no private data are used. Reusers should verify applicable redistribution permissions; this local analysis does not supply a new license. % [claim:C_DATA] [claim:C_REPRO]

\bibliographystyle{plainnat}
\bibliography{../references}
% [claim:C_SCOPE] [claim:C_POLICY] [claim:C_INFERENCE]
\end{document}
