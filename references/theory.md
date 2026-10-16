# Pure theory mode

Use for microeconomic theory, games, information, contracts, matching, mechanism design, or other theorem-led research.

## Contract additions

Freeze primitives, domains, timing, information, strategy spaces, equilibrium or solution concept, welfare criterion, target theorem, and allowed assumptions. Separate definitions, maintained assumptions, conjectures, and established results.

## Workflow

1. Map the theorem's lineage: nearest propositions, definitions, proof strategies, counterexamples, and the exact assumption or conclusion changed.
2. Reproduce the closest known benchmark and limiting cases before claiming an extension.
3. State the conjecture with complete quantifiers and hypotheses.
4. Search Mathlib documentation and the local environment for existing definitions, lemmas, and naming conventions before recreating them. If already configured, LeanSearch/Loogle or LeanDojo-v2 may assist premise search; do not install or contact a service without authority.
5. Search analytically and computationally for boundary cases or counterexamples.
6. Write a paper proof and dependency manifest: assumptions, imported results, critical lemmas, Mathlib/Lean version when relevant, and unresolved obligations. Put the complete step-by-step proof in a numbered appendix, cross-reference it from the theorem or proposition in the main text, and use the completeness gate below when the requested deliverable is a full proof.
7. For agent-generated formal proofs, read [lean_harness.md](lean_harness.md), freeze and lock the theorem task, and place that contract outside the proving agent's mutation scope.
8. Formalize only the candidate proof term in Lean 4 + Mathlib. Run the locked checker and preserve its JSON artifact.
9. Derive comparative statics, welfare implications, and testable predictions only within the proved domain.
10. Run the shared referee checkpoint against assumptions, equilibrium selection, necessity of conditions, and the complete paper-proof gate.

Add economic definitions and lemmas only when an active proof requires them. Keep each reusable primitive in the proof project's tested Lean library with explicit namespace, assumptions and theorem users; do not scaffold a broad `EconLib` that the installed Lean/Mathlib version cannot compile.

## Complete paper-proof gate

When the user requests a proof rather than a sketch, write a self-contained proof at the intended audience's level and preserve it as an artifact. It must:

- restate the theorem with domains, quantifiers, definitions, and assumptions before the argument;
- list every external theorem used and map each of its hypotheses to established facts in the model;
- prove each nontrivial intermediate lemma, or cite an exact established result that closes it;
- justify `without loss of generality`, existence, uniqueness, divisions, limit/interchange steps, and omitted cases whenever they carry the conclusion;
- cover boundary, equality, degenerate, and off-equilibrium cases that lie in the stated domain;
- show the algebraic, optimization, probability, or fixed-point steps on which the result turns, while omitting only routine expansions that a reader can reconstruct unambiguously;
- present those steps in order in the appendix, with every displayed equality, inequality, implication, and case transition justified where it first appears;
- end with an obligation table marking every dependency `discharged`, `external result`, or `unresolved`.

The proof is a `complete paper proof` only when no obligation is unresolved and an independent proof referee can reconstruct every conclusion from the stated premises. Words such as “obvious,” “standard,” or “similarly” do not discharge an obligation by themselves. If a gap remains, label the result `proof sketch` and name the gap. Completeness requires sufficient detail, not maximum length: keep the full derivation in the proof artifact and pass other agents only the theorem ID, obligation statuses, checker result, uncertainty, and artifact path.

## Proof status

Use exactly these labels:

- `conjecture`: no complete proof;
- `proof sketch`: informal argument with unresolved obligations;
- `complete paper proof`: all obligations are discharged in an auditable human-readable argument, but the result is not kernel-verified;
- `formally proved`: the locked theorem compiles, its hashes match, and its transitive axioms pass the allowlist;
- `disproved`: a valid counterexample violates the claim under its stated assumptions.

Lean 4 + Mathlib is the sole formal proof authority for this skill. The locked checker isolates the proof term, rejects local proof escapes, invokes Lean with a timeout, and checks `#print axioms` transitively against the task allowlist. Computer algebra or numerical search may simplify expressions and find counterexamples, but cannot upgrade proof status. If Lean is absent, do not install it without authorization and do not label a theorem formally proved.

## Independent reconstruction

When asked to prove a published claim without consulting its proof, freeze the statement, definitions, and allowed background results before proof search. Keep the author proof inaccessible to the proof attempt; use a fresh context or independent agent when available. Run a separate counterexample attack. Compare with the author proof only after saving the independent argument. If the acting agent has already seen the proof, disclose contamination and do not call its reconstruction blind.

## Iteration

For each attempt, use three checkpoints: the planner chooses one lemma or strategy, the prover changes only the proof term, and the rater consumes the checker status and diagnostic. These may be stages of one agent; do not simulate role dialogue. Change one definition, assumption, lemma, or proof strategy at a time. Keep a change only if the target theorem remains economically meaningful and the checked result becomes stronger, simpler, or more general. Do not weaken assumptions silently merely to make Lean succeed; record any scope change as a new locked task.
