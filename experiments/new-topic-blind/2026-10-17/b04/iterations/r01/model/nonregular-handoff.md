# r01 model handoff: a nonregular-score solution

This is an independent extension of the frozen manuscript's Section 4 model, using only that manuscript and its blind review. It does **not** change the frozen source. The result below closes its nonregular allocation gap for independent types, scalar values multiplying known slot quality, DSIC, ex post IR, and no positive transfers. It does not address literature priority, correlated types, caps on charges, or extra allocation constraints.

## Definitions and theorem

For each observed group \(g\), retain the manuscript's integrable virtual score

\[
S_g(v)=\lambda v-\lambda\frac{1-F_g(v)}{f_g(v)}
+\frac{\int_v^{\bar v_g}\mu_g(t)f_g(t)\,dt}{f_g(v)}.
\]

Let \(x=F_g(v)\in[0,1]\) be the **lower** value quantile, let \(v_g(x)=F_g^{-1}(x)\), and write \(s_g(x)=S_g(v_g(x))\), defined almost everywhere. It is integrable even if \(S_g\) is unbounded where density is small. Define

\[
H_g(x)=\int_0^x s_g(t)\,dt,
\qquad G_g=\operatorname{GCM}(H_g),
\qquad \bar s_g(x)=G'_{g,+}(x)
\]

where \(G_g\) is the greatest convex function lying at or below the continuous \(H_g\) on \([0,1]\). Set its endpoint values equal to \(H_g(0)\) and \(H_g(1)\). The one-sided derivative at endpoints is immaterial; on the interior, the convex derivative exists almost everywhere and is nondecreasing. For implementation choose any nondecreasing version of \(\bar S_g(v)=\bar s_g(F_g(v))\), with a fixed deterministic convention at its jump points.

**Theorem (ironed weighted-quality allocation; complete paper proof conditional on the stated convex-envelope lemma).** Under the frozen manuscript's assumptions, replace every raw group score by \(\bar S_g\). At each reported value profile, assign the highest quality to the largest positive ironed score, then successive qualities to successive positive scores; leave remaining slots vacant. Break every score tie by a fixed priority that does not depend on reports. Ignore reports of \(w\). Charge agent \(i\) the envelope amount

\[
p_i(v_i,v_{-i})=v_i Q_i(v_i,v_{-i})-\int_0^{v_i}Q_i(t,v_{-i})dt.
\]

This mechanism is feasible, DSIC, ex post IR, and has nonnegative charges. It maximizes the frozen manuscript's welfare \(W\) over **all** mechanisms in that class, including randomized mechanisms. The conclusion covers finite \(n\), any finite list \(q_1\ge\cdots\ge q_m>0\), heterogeneous group priors, and flat or falling raw scores. No regularity of raw \(S_g\) is required.

## Convex-envelope lemma (the key finite-dimensional fact)

For a continuous \(H:[0,1]\to\mathbb R\), its greatest convex minorant \(G\) exists, is continuous, and has \(G(0)=H(0)\), \(G(1)=H(1)\). Every connected component \((a,b)\) of \(\{x:G(x)<H(x)\}\) is an *ironing interval*: \(G\) is affine on \([a,b]\), with \(G(a)=H(a)\) and \(G(b)=H(b)\). Thus \(\bar s=G'\) is constant inside it. One construction that also proves endpoint contact is the lower convex-envelope formula

\[
G(x)=\inf_{0\le a\le x\le b\le1}
 \left\{\frac{b-x}{b-a}H(a)+\frac{x-a}{b-a}H(b)\right\}, \tag{A}
\]

where \(a=b=x\) is interpreted as \(H(x)\). The infimum is attained because \(H\) is continuous and the chord value extends continuously at coinciding endpoints. Formula (A) is the smallest expected \(H(X)\) over distributions on \([0,1]\) with mean \(x\): an extreme feasible distribution has support on at most two points. That value is convex (mixtures of mean-constrained distributions show convexity), is below \(H\) (choose \(X=x\)), and dominates every convex minorant by Jensen's inequality. At \(x=0,1\), the only feasible distribution is degenerate, giving endpoint equality. If \(G(x)<H(x)\), an attaining chord has \(a<x<b\). Convexity and equality at interior \(x\) force \(G\) to equal that chord throughout \([a,b]\), and its endpoints contact \(H\). This proves the lemma. (An author may replace this paragraph with a standard convex-envelope citation if its source is verified within the historical cutoff.)

## Proof of theorem

**1. Ironing inequality for every incentive-compatible allocation.** Fix agent \(i\) and every opponents' report. DSIC makes their expected quality \(Q_i(v)\) nondecreasing in \(v\). Hence \(q_i(x)=Q_i(v_g(x))\) is bounded and nondecreasing. The frozen manuscript's virtual-welfare identity applies; its contribution from this agent is \(\int_0^1s_g(x)q_i(x)dx\). Put \(D_g=H_g-G_g\ge0\), whose endpoint values are zero. Integration by parts for an absolutely continuous primitive and a bounded monotone function gives

\[
 \int_0^1\bar s_g(x)q_i(x)dx
 -\int_0^1s_g(x)q_i(x)dx
 =-\int_0^1 D_g'(x)q_i(x)dx
 =\int_{[0,1]}D_g(x)\,dq_i(x)\ge0. \tag{B}
\]

The Stieltjes integral is well-defined because \(q_i\) has bounded variation. Endpoint atoms or jumps cause no difficulty because \(D_g(0)=D_g(1)=0\). Thus actual welfare is at most expected ironed virtual surplus for *every* DSIC mechanism, even when its allocation is randomized. Independence allows the same group-specific transform after conditioning on opponents' reports.

**2. Pointwise upper bound with heterogeneous qualities.** For each realized value vector, no feasible matching or lottery can yield more than \(\sum_i\bar S_{g_i}(v_i)Q_i\) under the descending-score assignment stated above. Swapping scores \(a\ge b\) between qualities \(q_h\ge q_l\) changes ironed surplus by \((a-b)(q_h-q_l)\ge0\); assigning a positive-quality slot to a nonpositive score cannot improve it. A lottery is a convex combination of matchings. Therefore the expected pointwise ironed maximum is an upper bound on actual welfare of every admissible mechanism by (B).

**3. Implementation and equality in ironing.** Each \(\bar S_g\) is nondecreasing in value. Holding opponents' reports fixed, an agent's score can only rise with their value, and fixed tie priority ensures their assigned quality cannot fall. The frozen manuscript's envelope argument therefore gives DSIC, ex post IR, and \(p_i\ge0\). On every ironing interval \((a,b)\), the agent's ironed score is constant. Holding opponents' reports fixed, their position in the score ranking, allocated quality, and charge-relevant quality \(q_i(x)\) are consequently constant throughout that interval: ties against another agent's score are resolved by priority, not by the agent's within-interval value. The measure \(dq_i\) thus has no mass inside any component of \(\{D_g>0\}\); outside their union, \(D_g=0\). Equation (B) holds with equality for the constructed mechanism. It attains both the pointwise ironed maximum and the raw-welfare upper bound, proving global optimality.

The argument is **ex post in opponents' reports** and therefore is not merely an interim relaxation. Unequal slot qualities enter only the pointwise exchange step; they do not break the constancy of an agent's assigned quality on a flat ironed-score interval. Cross-group ties are harmless with report-independent priority. A tie rule based on the raw value inside a flat interval would generally destroy equality in (B), even if it maintained weak DSIC.

## A sharp simple implication

**Corollary (all scores weakly falling).** If every group's raw score \(S_g(v)\) has a nonincreasing version, then every \(H_g\) is concave. Its greatest convex minorant is the chord joining its endpoints, so \(\bar S_g\) is constant and equals

\[
H_g(1)-H_g(0)=\int_0^1s_g(x)dx
=\mathbb E[w_i v_i\mid g_i=g].
\]

The last equality follows by applying the frozen virtual-welfare identity to the constant allocation \(Q\equiv1\), whose envelope charge is zero; it also follows by integrating the score formula directly. An optimum therefore ignores all value and weight reports: rank agents by their group's expected weighted value \(\mathbb E[w v\mid g]\), assign qualities in descending order, and charge zero. With equal scores, use fixed priority or a report-independent lottery. This conclusion is conditional on **every** relevant group score falling; a mixture of falling and other scores is covered by the general ironing theorem, with a fully pooled score for each falling group. Independence and the absence of additional assignment constraints remain essential.

For \(v\sim U[0,1]\), constant weight \(w=a\), and \(a>2\lambda\), the frozen paper gives \(s(x)=(2\lambda-a)x+(a-\lambda)\), strictly decreasing. Thus \(H\) is strictly concave and its greatest convex minorant is the endpoint chord; the ironed score is constant:

\[
\bar s(x)=H(1)-H(0)=a/2,\qquad 0<x<1.
\]

In the paper's two-agent, one-unit-slot example with \(a=3,\lambda=1\), both ironed scores are \(3/2\). A fixed-priority free allocation (or a report-independent lottery) is therefore optimal and has welfare \(3/2\). The raw rule's reversal is fixed by fully pooling values within this group. For heterogeneous qualities, fixed priority assigns fixed qualities to these fully ironed agents unless another group's score outranks them; if the other group's report changes, the assignment responds to that report, while remaining constant in each fully ironed agent's own report.

## Proof status and limits

The argument is a **complete paper proof** using the explicitly stated convex-envelope lemma, the frozen manuscript's virtual-welfare identity, and elementary Stieltjes integration. It has **not** been Lean/Mathlib verified and is not labeled formally proved. The lower-quantile orientation matters: the required transform is the **greatest convex minorant of \(H(x)=\int_0^x s\)**, not a concave majorant of that primitive. A concave hull belongs to an upper-tail quantile convention with adjusted signs.

The theorem's limits are material: cross-agent dependence can alter conditional scores after opponents' reports; atoms in value need a discrete IC/ironing treatment; multidimensional values, nonrival goods, fairness constraints, shared transfer budgets, or caps on charges change the program. An arbitrary tie rule may fail the equality step. The result supplies no evidence of historical novelty or policy desirability.
