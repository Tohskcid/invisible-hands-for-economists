# Research library protocol

Read this reference only when the task needs a reusable theorem, identification result, estimator, computational method, or known counterexample. The bundled library is a candidate generator, not evidence that a result applies.

## Retrieval

1. State the current obligation before searching: object, desired conclusion, maintained assumptions, and the failure that must be avoided. Translate non-English requests into concise English search concepts because the bundled cards use English canonical terminology.
2. Query by problem and mathematical or econometric property, not only by author or title:

```bash
python3 scripts/search_library.py "monotone choice single crossing" --mode theory
python3 scripts/search_library.py "staggered adoption heterogeneous effects" --mode empirical
```

3. Search returns three compact candidates by default. Do not open `library/index.jsonl` or scan `library/papers/` wholesale. Select the most plausible card, then load only that card:

```bash
python3 scripts/search_library.py --show milgrom-shannon-monotone-comparative-statics
```

Use `--limit 5` only when three candidates are insufficient. Compare the selected card's assumptions, conclusion, failure conditions, and source locator with the current contract.
4. Record `applies`, `adaptable`, or `not applicable` with the assumption mismatch. Verify the selected result in the primary source before relying on it.
5. Link any adopted card to the project's proof obligation, estimand, experiment, or provenance manifest. Never cite a result card as the scholarly source.

No result follows from similarity alone. Do not silently add an assumption to make a card fit, and do not infer novelty from the absence of a search hit. Search current literature separately when novelty or coverage matters.

## Blind proof mode

For independent reconstruction, run the compact search normally, then use `scripts/search_library.py --show CARD_ID --blind`. Before saving the independent proof attempt, do not open the underlying Markdown card by another route. Blind output may expose the theorem statement, core assumptions, failure conditions, and source identity, but hides proof-strategy, solution-outline, and author-proof-locator sections. Record any prior exposure as contamination.

## Maintenance

Run `python3 scripts/validate_library.py` after changes. Cards require a primary-source locator and verification level. Add corrections and counterexamples as relations rather than overwriting older cards. Keep copyrighted PDFs and restricted full text outside Git; catalog only lawful metadata and locators.
