"""Supplementary exact checks and hash-bound metadata; never a proof kernel."""
from pathlib import Path
from fractions import Fraction as Q
import hashlib
import json
import math
import re

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"
MAIN = ROOT / "paper/manuscript/main.tex"

def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()

def write(name, value):
    (RESEARCH / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")

# Exact arithmetic checks are falsification aids; their finite grid is not a proof.
discount_checks = 0
for d1 in [Q(1, 20), Q(1, 2), Q(9, 10), Q(99, 100)]:
    for d2 in [Q(1, 10), Q(1, 3), Q(4, 5), Q(999, 1000)]:
        p1 = (1 - d2) / (1 - d1 * d2)
        p2 = (1 - d1) / (1 - d1 * d2)
        assert p1 == 1 - d2 * p2 and p2 == 1 - d1 * p1
        assert 0 < p1 < 1 and 0 < p2 < 1
        assert p1 > d1 * (1 - p2) and p2 > d2 * (1 - p1)
        discount_checks += 1

additive_checks = 0
for c1 in [Q(1, 10), Q(2, 5), Q(1), Q(3, 2), Q(2)]:
    for c2 in [Q(1, 5), Q(3, 5), Q(1), Q(4, 3), Q(3)]:
        if c1 == c2 and c1 < 1:
            continue
        if c1 < c2:
            p1, p2 = Q(1), min(c1, Q(1))
        elif c2 < c1:
            p1, p2 = min(c2, Q(1)), Q(1)
        else:
            p1, p2 = Q(1), Q(1)
        assert p1 == 1 - max(p2 - c2, 0)
        assert p2 == 1 - max(p1 - c1, 0)
        assert p1 + p2 + c1 > 1 and p1 + p2 + c2 > 1
        additive_checks += 1

c = Q(1, 10)
for p1 in [c, Q(1, 2), Q(9, 10), Q(1)]:
    p2 = 1 - p1 + c
    assert p1 == 1 - max(p2 - c, 0) and p2 == 1 - max(p1 - c, 0)
assert Q(4, 5) - c == Q(7, 10)
assert Q(1, 5) - c == Q(1, 10)
assert Q(7, 10) > Q(1, 10) > -c
limit_checks = []
for h in [0.1, 0.01, 0.001, 0.0001]:
    value = -math.expm1(-3*h) / -math.expm1(-5*h)
    limit_checks.append({"h": h, "p1": value, "limit": 0.6})
assert abs(limit_checks[-1]["p1"] - 0.6) < 0.0001
write("numerical-checks.json", {
    "schema_version": "1", "status": "pass", "authority": "supplementary only; not proof",
    "discount_rational_cases": discount_checks, "additive_rational_cases": additive_checks,
    "equal_cost_fixed_points_checked": 4, "delayed_example": "exact rational checks pass",
    "short_period_checks": limit_checks, "code_sha256": digest("scripts/verify_and_package.py")})

claim_specs = [
    ("C_SCOPE", "The question does not specify a unique waiting preference; the result is a bounded reconstruction with disclosed prior familiarity and no novelty claim.", "conclusion", [], "research/model.md", "Question-only input and explicit class restrictions"),
    ("C_MODEL", "The maintained game has a unit divisible pie, alternating discrete offers, complete histories, specified terminal and disagreement utilities and subgame perfection.", "premise", [], "research/model.md", "Maintained assumptions, not findings"),
    ("C_GENERAL", "Strictly increasing contractive stationary delay equivalents imply a unique pure SPE, the reservation fixed point and immediate agreement at every proposer history.", "conclusion", ["C_MODEL"], "paper/manuscript/main.tex#app:general", "Pure strategies and q_i in (0,1); no claim for arbitrary waiting preferences"),
    ("C_DISCOUNT", "For positive strict linear discounts the unique behavioral SPE has proposer shares (1-delta_j)/(1-delta1*delta2), with complete threshold strategies.", "conclusion", ["C_MODEL"], "paper/manuscript/main.tex#app:discount", "All measurable behavioral SPE; factors in (0,1)"),
    ("C_TIMING", "Strict discounting yields probability-one immediate agreement in every proposer subgame, including off-path subgames.", "conclusion", ["C_DISCOUNT"], "paper/manuscript/main.tex#app:discount", "Strict discount domain only"),
    ("C_LIMIT", "The first share increases in own patience, decreases in opponent patience, equals 1/(1+delta) under symmetric factors and tends to r2/(r1+r2) for short exponential periods.", "conclusion", ["C_DISCOUNT"], "paper/manuscript/main.tex#app:algebra", "Positive rates; limits of discrete games, not a continuous-time game theorem"),
    ("C_ADDITIVE", "Positive unequal additive costs, or both costs at least the pie, yield a unique immediate behavioral SPE; the lower-cost proposer keeps all and the other proposer gets min(lower cost,1).", "conclusion", ["C_MODEL"], "paper/manuscript/main.tex#app:additive", "c_i>0; equal costs below one excluded from uniqueness"),
    ("C_EQUAL", "For equal additive costs c in (0,1), the stationary immediate SPE family is p1 in [c,1], p2=1-p1+c.", "conclusion", ["C_MODEL"], "paper/manuscript/main.tex#app:equal", "Characterizes stationary immediate SPE, not all history-dependent SPE"),
    ("C_DELAY", "At c1=c2=1/10 a fully specified history-dependent pure SPE agrees at date one with shares (4/5,1/5) and utilities (7/10,1/10).", "conclusion", ["C_EQUAL"], "paper/manuscript/main.tex#app:equal", "Existence counterexample; no exhaustive equal-cost characterization"),
    ("C_BOUNDARY", "A single patient player can receive the entire pie after any finite delay; two patient players can sustain any division after any finite delay.", "conclusion", ["C_MODEL"], "paper/manuscript/main.tex#app:boundaries", "Existence constructions, not a full boundary characterization; exact-zero discounts excluded")
]

# The unchanged strict-numbers checker treats TeX mathematics as prose. Bind each
# paragraph to the appropriate section claim, including displayed derivations.
text = MAIN.read_text()
paragraphs = text.split("\n\n")
current_claim = "C_SCOPE"
annotated = []
for paragraph in paragraphs:
    if "\\section{Game and preferences}" in paragraph:
        current_claim = "C_MODEL"
    elif "\\section{Contractive waiting preferences}" in paragraph or "\\subsection{Fixed point" in paragraph:
        current_claim = "C_GENERAL"
    elif "\\section{Exponential discounting}" in paragraph or "\\subsection{Behavioral discounting" in paragraph:
        current_claim = "C_DISCOUNT"
    elif "\\section{Constant waiting costs}" in paragraph or "\\subsection{Positive additive" in paragraph:
        current_claim = "C_ADDITIVE"
    elif "\\subsection{Exact algebra" in paragraph:
        current_claim = "C_LIMIT"
    elif "\\section{Boundary cases" in paragraph or "\\subsection{Perfect-patience" in paragraph:
        current_claim = "C_BOUNDARY"
    elif "\\subsection{Equal-cost" in paragraph:
        current_claim = "C_EQUAL"
    elif "For the delayed example" in paragraph:
        current_claim = "C_DELAY"
    elif "\\section{Conclusion}" in paragraph or "\\subsection{Definitions" in paragraph or "\\subsection{Proof-obligation" in paragraph:
        current_claim = "C_SCOPE"
    if re.search(r"\d", paragraph) and "[claim:" not in paragraph:
        paragraph = "% [claim:" + current_claim + "]\n" + paragraph
    annotated.append(paragraph)
MAIN.write_text("\n\n".join(annotated))

records = [{"id": "E_QUESTION", "type": "evidence", "source": "Frozen question and explicit authored model contract", "locator": "research/model.md", "verified_at": "2026-10-12", "relation": "supports", "access_status": "local", "sha256": digest("research/model.md")}]
for cid, statement, role, premises, locator, scope in claim_specs:
    evid = "E_" + cid[2:]
    path = locator.split("#")[0]
    records.append({"id": evid, "type": "evidence", "source": "Independently authored model/complete step-by-step paper argument", "locator": locator, "verified_at": "2026-10-12", "proof_status": "candidate complete paper proof; independent referee pending", "relation": "supports", "sha256": digest(path)})
    records.append({"id": cid, "type": "claim", "statement": statement, "premise_ids": premises, "evidence_ids": [evid], "central": True, "role": role, "status": "supported", "scope": scope, "uncertainty": "Human-readable derivation; not kernel verified; independent referee must validate completeness."})
(RESEARCH / "manifest.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))

sections = [
    ("introduction", "introduction", ["Introduction"], ["C_SCOPE"], "model"),
    ("literature", "literature", ["Solution concept and source boundary"], ["C_SCOPE"], "literature"),
    ("model", "model", ["Game and preferences"], ["C_MODEL"], "model"),
    ("general", "results", ["Contractive waiting preferences"], ["C_GENERAL"], "proof"),
    ("discount", "results", ["Exponential discounting"], ["C_DISCOUNT", "C_TIMING", "C_LIMIT"], "proof"),
    ("additive", "results", ["Constant waiting costs"], ["C_ADDITIVE", "C_EQUAL", "C_DELAY"], "proof"),
    ("boundary", "results", ["Boundary cases and interpretation"], ["C_BOUNDARY"], "proof"),
    ("conclusion", "conclusion", ["Conclusion"], ["C_SCOPE"], "model"),
    ("appendix", "appendix", ["Complete derivations and proofs"], [s[0] for s in claim_specs], "appendix")
]
coverage = []
for sid, role, headings, cids, kind in sections:
    packet = f"research/sections/{sid}.md"
    (ROOT / packet).write_text("# Section packet\n\n" + ", ".join(headings) + "\n\nClaims: " + ", ".join(cids) + "\n\nThe mathematical evidence is the complete appendix in the authoritative manuscript. The model restrictions are in research/model.md. Literature access remains restricted; this section explains the restriction and makes no survey/novelty claim.\n")
    supporting = "research/model.md" if kind == "model" else "paper/manuscript/main.tex"
    coverage.append({"id": sid, "role": role, "status": "ready", "headings": headings, "claim_ids": cids, "artifacts": [{"kind": "section_packet", "path": packet, "sha256": digest(packet)}, {"kind": kind, "path": supporting, "sha256": digest(supporting)}]})
write("manuscript-coverage.json", {"schema_version": "1", "mode": "theory", "manuscript_sha256": digest("paper/manuscript/main.tex"), "sections": coverage})

obligations = [
    ("G1", "Domains, normalization and disagreement", "sec:model"),
    ("G2", "Reservation fixed-point existence, uniqueness and interiority", "app:general"),
    ("G3", "Complete pure strategies and all future deviations", "app:general"),
    ("G4", "Global pure envelopes and immediate agreement", "app:general"),
    ("D1", "Behavioral existence, feasibility, envelopes and no mixing delay", "app:discount"),
    ("D2", "Exact algebra and comparative statics/limits", "app:algebra"),
    ("A1", "Additive stationary candidate existence against full deviations", "app:additive"),
    ("A2", "Nonnegative equilibrium payoff and finite expected waiting", "app:additive"),
    ("A3", "Unequal/high additive cost global behavioral uniqueness", "app:additive"),
    ("A4", "Equal-cost stationary characterization and delayed off-path construction", "app:equal"),
    ("B1", "Patient boundary strategies and finite delay", "app:boundaries")
]
write("proof-obligations.json", {"schema_version": "1", "manuscript_sha256": digest("paper/manuscript/main.tex"), "proof_status": "candidate complete paper proof; independent review pending", "kernel_verified": False, "lean_available": False, "obligations": [{"id": oid, "statement": statement, "assumptions": "Exact model-class assumptions restated in the referenced appendix subsection", "locator": f"paper/manuscript/main.tex#{loc}", "status": "discharged", "argument": "Full human-readable derivation in appendix", "unresolved_gap": None} for oid, statement, loc in obligations], "external_results": ["Completeness and order completeness of the real numbers", "Geometric-series summation", "Expectation monotonicity/conditioning for the specified measurable laws", "Differentiability of exponential at zero"], "outside_scope": ["Noncontractive general time preferences", "Lottery preferences for nonlinear ordinal delay maps", "Full set of history-dependent equal-additive-cost equilibria", "Exact-zero globally dated discount factors", "Zero additive costs in the additive uniqueness theorem"], "independent_review": "pending"})

print(json.dumps({"status": "generated", "manuscript_sha256": digest("paper/manuscript/main.tex"), "manifest_sha256": digest("research/manifest.jsonl"), "supplementary_checks": "pass", "central_claims": len(claim_specs)}, indent=2))
