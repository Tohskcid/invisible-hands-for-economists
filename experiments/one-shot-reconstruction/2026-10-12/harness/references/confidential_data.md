# Restricted data and enclave protocol

Read this reference when data are confidential, licensed, personally identifying, contract-restricted, or too large to inspect directly.

## Approved boundary

Record the governing DUA, IRB or organizational policy; approved host, users, tools and model endpoint; network and telemetry restrictions; retention period; and permitted exports. "Local" is not automatically approved. Never send rows, identifiers, secrets, residual excerpts, logs, embeddings, or derived small cells outside the approved boundary merely because they fit in context.

## Synthetic-first development

Develop against a synthetic fixture that matches schema, types, keys, units, missingness classes, category cardinality and important edge cases without reproducing real people or rare records. Use it to test interfaces, joins, estimators, failure paths and resource estimates. Synthetic success does not validate real-data support, identification, disclosure risk, runtime or estimates.

Create a portable handoff containing code, environment lock, configuration template, input schema, expected artifact schema, deterministic tests and hashes—never source data. Run the unchanged bundle inside the enclave. Any necessary change creates a new reviewed bundle or ledger entry.

## Enclave execution and export

- Disable unapproved network access, telemetry and remote model calls.
- Read data by path or query inside the enclave; do not paste observations into prompts.
- Start with a schema-only audit and a resource-bounded pilot. Sampling is for engineering checks, not automatic inferential validity.
- Use chunked or database-native operations and checkpoint long jobs; record peak memory, runtime, failures and resume state.
- Export only allowlisted aggregate artifacts after disclosure review, including logs and figures.
- Have an authorized researcher review sample construction, diagnostics and the final export before making claims.

If the policy is unclear or the approved environment lacks required execution capability, mark the run `blocked`; synthetic output must not be substituted for the confidential-data result.
