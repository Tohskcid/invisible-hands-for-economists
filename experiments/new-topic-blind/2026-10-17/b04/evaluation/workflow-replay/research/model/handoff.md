# Independent model handoff (b04; 2026-10-17)

## Scope and interpretation

The public question asks how to allocate scarce publicly provided resources of heterogeneous quality when willingness to pay and social welfare weights are unobserved, group labels are observed, and payments *to* individuals are constrained. I interpret the resources as rival assignable slots, rather than a nonrival public good; a negative charge is a payment to an individual. The core restriction is no positive transfers, and the extension allows a subsidy of at most \(B_i\). These are modeling choices, not facts supplied by the question. No external source was consulted; no novelty claim is possible from this handoff.

## Primitives

There are \(n\) agents and \(m\le n\) objects, with publicly known qualities \(q_1\ge\cdots\ge q_m>0\); unassigned quality is zero. Agent \(i\)'s observable label is \(g_i\). Their private type is \((v_i,w_i)\), with \(v_i\in[0,\bar v_{g_i}]\) and \(w_i\ge0\). If assigned expected quality \(Q_i\) and charged \(p_i\), utility is \(u_i=v_iQ_i-p_i\). The normative objective is

\[
  \mathbb E\!\left[\sum_i w_i(v_iQ_i-p_i)+\lambda\sum_i p_i\right],\qquad \lambda\ge0.
\]

Thus \(w_i\) weights the person's *net utility* and \(\lambda\) values public revenue. This accounting makes the transfer constraint consequential. Types are independent across agents conditional on the observed group vector. Within group \(g\), \(v\) has atomless, positive density \(f_g\), CDF \(F_g\), and \(\mu_g(v)=\mathbb E[w_i\mid v_i=v,g_i=g]\) is finite. A direct mechanism must be feasible (a lottery over matchings), dominant-strategy incentive compatible (DSIC), ex post individually rational (IR), and satisfy \(p_i\ge-B_i\). The no-positive-transfer core sets \(B_i=0\). The reported \(w\) has no direct effect on utility; no verification or other payoff from that report is assumed.

## Information limit: private welfare weights cannot be robustly elicited

**Proposition 1 — complete paper proof under the preceding rectangular type domain.** Fix an agent, opponents' reports, and a true value \(v\). DSIC across reports \((v,w)\) requires the agent's utility \(U(v,w)\) to be identical for every \(w\): the two IC inequalities for any \(w,w'\) point in opposite directions and yield equality. Write the common value \(U(v)\). For any fixed reported \(w\), value IC implies

\[
 U(v)=\sup_{r\in[0,\bar v]}\{vQ(r,w)-p(r,w)\}.
\]

It follows directly that \(U\) is convex, and the truthful expected quality \(Q(v,w)\) is a subgradient of \(U\) at \(v\): for every \(z\), \(U(z)\ge U(v)+(z-v)Q(v,w)\). A finite convex function on an interval is differentiable almost everywhere. At any differentiability point, its subgradient is unique, so \(Q(v,w)=U'(v)\) for **every** report \(w\), and \(p(v,w)=vU'(v)-U(v)\). Since \(v\) is atomless, the reports of \(w\) cannot affect expected quality or charge with positive probability in any DSIC mechanism. (At a kink, reports could select different subgradients; atoms at that value would require separate treatment.) Lotteries with the same expected quality might differ in distribution but are equivalent for the linear utility and objective here. This is an information impossibility, not a claim that \(w\) is statistically independent of \(v\).

The implication is to use \(\mu_g(v)\), the posterior mean weight inferred from an incentive compatible value report and observable group, not the unverifiable reported weight itself. The proof does not exclude elicitation if weights enter preferences, are verified, or are correlated with additional verifiable signals.

## Envelope and objective reduction

Fix opponents' reports and omit their arguments. DSIC in \(v\) is equivalent to nondecreasing \(Q(v)\) plus the envelope/payment identity

\[
 U(v)=U(0)+\int_0^v Q(t)\,dt,\qquad
 p(v)=vQ(v)-U(0)-\int_0^v Q(t)\,dt. \tag{1}
\]

Necessity follows from the subgradient inequalities in both directions and integration of the almost-everywhere derivative. Sufficiency follows because a nondecreasing \(Q\) makes \(U\) convex and the truthful quality its subgradient. Since \(0\le Q\le q_1\), all integrals exist. Equation (1) gives \(p(0)=-U(0)\), and \(p(v)+U(0)=vQ(v)-\int_0^vQ(t)dt\ge0\) by monotonicity. Thus ex post IR plus \(p\ge-B_i\) is exactly \(0\le U(0)\le B_i\) for this conditional menu. With no positive transfers, \(U(0)=0\), and (1) gives nonnegative charges at every value.

For any fixed group, put \(\beta_g(v)=\lambda-\mu_g(v)\) and \(M_g(v)=\int_v^{\bar v_g}\mu_g(t)f_g(t)dt\). By substituting (1), conditioning on value, and reversing the order of integration,

\[
\begin{aligned}
 \mathbb E[w_i v_iQ_i+(\lambda-w_i)p_i\mid g]
 &=\int_0^{\bar v_g} f_g(v) S_g(v)Q_i(v)\,dv
  -\{\lambda-\mathbb E[w_i\mid g]\}U_i(0),\\
 S_g(v)&=\lambda v-\lambda\frac{1-F_g(v)}{f_g(v)}
              +\frac{M_g(v)}{f_g(v)}. \tag{2}
\end{aligned}
\]

Here \(Q_i(v)\) and \(U_i(0)\) still depend on opponents' reports. Independence ensures that conditioning on those reports does not change \(\mu_g\) or \(f_g\). Formula (2) is the relevant weighted virtual score; using \(\mu_g(v)v\) alone would miss the welfare effect of informational rents. For \(B_i=0\), the last term vanishes. For finite \(B_i\), its optimal conditional value is \(U_i(0)=B_i\) if \(\mathbb E[w_i\mid g_i]>\lambda\), zero if the inequality reverses, and any value in the tie, provided the same \(B_i\) applies at every value and there is no additional budget constraint. That subsidy is a fixed transfer and does not affect allocation incentives.

## A solvable regular case

**Proposition 2 — complete paper proof given score regularity.** Suppose every \(S_g(v)\) in (2) is nondecreasing, and \(B_i=0\). On each report profile, rank agents by \(S_{g_i}(v_i)\), assign the highest-quality objects in order to the highest *positive* scores, and leave any remaining objects unassigned. Break ties by a fixed rule independent of agents' reports. Set payments by (1) with \(U_i(0)=0\). This mechanism is feasible, DSIC, ex post IR, satisfies no positive transfers, and maximizes the displayed expected objective among all such mechanisms.

Proof: With nonnegative qualities and at most one object per agent, the rearrangement inequality (or pairwise swap: \((S_a-S_b)(q_h-q_l)\ge0\)) shows that the stated ranking maximizes \(\sum_i S_iQ_i\) on every profile; assigning an object to a nonpositive score cannot improve it. As an agent raises \(v_i\), their score weakly rises while others' scores stay fixed, so their assigned quality weakly rises. Formula (1) therefore implements the rule and yields IR and nonnegative charges. Every feasible DSIC mechanism satisfies (2) and its realized matching has virtual surplus no larger than the pointwise maximum. Taking expectations proves optimality. The tie rule must preserve monotonicity in value; fixed agent priority does so. This proof uses the finite matching polytope only through its lotteries over matchings, whose linear objective cannot exceed its best deterministic matching.

For illustration, if a group has constant \(w=a_g\) and \(v\sim U[0,1]\), (2) reduces to \(S_g(v)=(2\lambda-a_g)v+(a_g-\lambda)\). When \(\lambda\le a_g\le2\lambda\), this score is nonnegative and nondecreasing, so every object should be used if an eligible agent exists, but rank can depend on group weights. When \(a_g<\lambda\), a single-agent reserve threshold is \(v\ge(\lambda-a_g)/(2\lambda-a_g)\), and the charge equals that threshold for unit quality. When \(a_g>2\lambda\), the score decreases, exposing the need for ironing rather than the raw ranking. This example is algebraic illustration, not evidence.

## Limits, counterexample, and next obligations

The regularity assumption is substantive. With two agents and one object, an agent's raw \(S_g\) can fall as value rises; against a fixed rival score strictly between its two scores, pointwise ranking would lower the first agent's allocation when their value rises. The two value IC inequalities imply \((v_H-v_L)(Q_H-Q_L)\ge0\), so the raw pointwise rule is then **disproved** as DSIC. For a concrete distribution, take uniform \(v\in[0,1]\), constant \(w=a>2\lambda>0\). Then \(S(v)=(2\lambda-a)v+(a-\lambda)\) falls strictly. Give a fixed rival a score between \(S(v_L)\) and \(S(v_H)\) for some \(v_L<v_H\); the raw rule violates monotonicity. An optimum for irregular scores requires an ironed allocation or a direct optimization over monotone interim allocation rules. No general ironing theorem is asserted here.

The following are unresolved if a paper is pursued: (i) characterize the ironed score and tie/flat-region randomization for heterogeneous group priors; (ii) determine whether dominant-strategy implementation of an interim ironed optimum preserves the same objective under correlated types; (iii) analyze a cap on charges *from* individuals, \(p_i\le C_i\), if that was the intended payment restriction—the core solution only imposes a cap on payments *to* individuals; (iv) allow nonrival public goods, multidimensional private value for qualities, or group fairness constraints; (v) verify pre-cutoff literature before any distinctiveness claim. No Lean/Mathlib checker was run, so neither proposition is labeled formally proved. The first two arguments are self-contained paper proofs for their stated model; the broader research program remains provisional.
