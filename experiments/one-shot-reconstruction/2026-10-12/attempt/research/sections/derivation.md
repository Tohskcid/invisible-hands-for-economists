
The following derivations are algebraic consequences of stated assumptions. They are not formal kernel-checked proofs of an economic model, and they do not verify the assumptions from the data. Main-text equations~\eqref{eq:did} and~\eqref{eq:reg} rely on this appendix. % [claim:C_ESTIMAND]

\subsection{Potential-outcome decomposition}
Let $Y_{i1}(d)$ be post-wave employment under policy state $d\in\{0,1\}$ and $Y_{i0}(0)$ the baseline outcome without anticipation. For the observed treated sample assume $Y_{i0}=Y_{i0}(0)$ and $Y_{i1}=Y_{i1}(1)$. For the comparison sample assume $Y_{i0}=Y_{i0}(0)$ and $Y_{i1}=Y_{i1}(0)$, including the absence of spillovers. All expectations below condition on $R_i=1$; let $E_d[\cdot]=E[\cdot\mid D_i=d,R_i=1]$. % [claim:C_ESTIMAND]

Start with the observed contrast and substitute consistency:
\begin{align}
\delta_{\mathrm{obs}}
 &=E_1[Y_{i1}(1)-Y_{i0}(0)]
   -E_0[Y_{i1}(0)-Y_{i0}(0)].\label{eq:stepone}
\end{align}
Add and subtract $E_1[Y_{i1}(0)]$, which is permitted when the expectations are finite:
\begin{align}
\delta_{\mathrm{obs}}
 &=E_1[Y_{i1}(1)-Y_{i1}(0)]\notag\\
 &\quad+E_1[Y_{i1}(0)-Y_{i0}(0)]
       -E_0[Y_{i1}(0)-Y_{i0}(0)].\label{eq:steptwo}
\end{align}
Define $\tau_R=E_1[Y_{i1}(1)-Y_{i1}(0)]$ and $b_R$ as the difference of the final two expectations. Linearity of expectation therefore gives $\delta_{\mathrm{obs}}=\tau_R+b_R$. Parallel mean untreated changes means $b_R=0$, which implies $\delta_{\mathrm{obs}}=\tau_R$. If anticipation changes the baseline, the first substitution fails; if Pennsylvania responds to the policy, the comparison substitution fails. If $R_i$ depends on treatment, the conditioning populations may differ across potential states and $\tau_R$ cannot automatically be interpreted as an effect for a stable principal stratum. These are separate identifying requirements, not conclusions derived from the regression. % [claim:C_ESTIMAND] [claim:C_LIMIT]

\subsection{OLS and the difference in changes}
Write $z_i=\Delta Y_i$. OLS minimizes
\begin{equation}
Q(\alpha,\delta)=\sum_{D_i=0}(z_i-\alpha)^2
 +\sum_{D_i=1}(z_i-\alpha-\delta)^2.
\end{equation}
The derivative with respect to $\delta$ is $-2\sum_{D_i=1}(z_i-\alpha-\delta)$. Setting it to zero gives $\alpha+\delta=\bar z_1$, provided the treated sample is nonempty. The derivative with respect to $\alpha$ is minus twice the sum of both groups' residuals. The treated residual sum is already zero, so the control residual sum must also be zero, giving $\alpha=\bar z_0$ when the control sample is nonempty. Subtracting yields $\widehat\delta=\bar z_1-\bar z_0$. The design matrix has full rank because both treatment values occur. The objective is then strictly convex in the two fitted group means, ensuring this solution is the unique OLS minimizer. % [claim:C_ESTIMAND]

For a constant sample, $\bar z_d=\bar Y_{d1}-\bar Y_{d0}$ by linearity of finite sums with the same denominator. Substituting into the last identity produces the usual four-cell difference-in-differences expression. If baseline and post observations use different samples, this equality need not hold. That is why the main analysis fixes complete pairs and labels the available-case contrast separately. % [claim:C_ESTIMAND] [claim:C_DATA]

\subsection{Sampling variance and the omitted state shock}
Assume changes are independent within and across groups, have finite variances $\sigma_d^2$, and the group sizes $n_d$ are fixed. Variance of a mean is $\sigma_d^2/n_d$, because independent observations have zero pairwise covariance. Variance of the difference is therefore
\begin{equation}
\operatorname{Var}(\widehat\delta)=\frac{\sigma_1^2}{n_1}
 +\frac{\sigma_0^2}{n_0}.
\end{equation}
Replacing each population variance by its within-group sample variance gives the separate-group standard error reported in the results file. The HC1 matrix estimator is
\begin{equation}
\widehat V_{\mathrm{HC1}}
=\frac{n}{n-k}(X'X)^{-1}
 \left(\sum_i x_i x_i'\widehat u_i^2\right)(X'X)^{-1},
\end{equation}
with $k$ fitted coefficients. Its state-coefficient element uses the OLS residuals and applies a degrees-of-freedom multiplier. The homoskedastic estimator instead replaces the central matrix by $(X'X)\widehat\sigma^2$, with $\widehat\sigma^2=\sum_i\widehat u_i^2/(n-k)$, resulting in $\widehat\sigma^2(X'X)^{-1}$. These formulas are implemented directly and independently verified in base R. % [claim:C_INFERENCE] [claim:C_REPRO]

Now let $z_i=\mu_d+a_d+e_i$, where $a_d$ is a common state change shock and $e_i$ is an independent restaurant disturbance. Averaging gives $\bar z_d=\mu_d+a_d+\bar e_d$. Subtracting yields $\widehat\delta=(\mu_1-\mu_0)+(a_1-a_0)+(\bar e_1-\bar e_0)$. Increasing restaurant counts reduces the variance of the last term but leaves $a_1-a_0$ intact. Restaurant resampling holds both common shocks fixed, so it cannot estimate the uncertainty that those shocks create. With only two observed jurisdictions, the present design does not consistently learn their distribution. % [claim:C_INFERENCE] [claim:C_LIMIT]

