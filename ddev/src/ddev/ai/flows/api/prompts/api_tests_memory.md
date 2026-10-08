---
type: memory_prompt
name: api_tests_memory
---
Write the documentation-author handoff directly from file evidence, command results, and repairs
already in this conversation. This memory step has no tools, and the response is saved verbatim;
do not request inspection, announce future work, or claim a fresh file read. State missing
evidence and its consequence instead of inventing results.

Make this an evidence-backed guide to what the README may claim and what needs review. The
documenter receives the PRD and earlier handoffs separately and can inspect current files. Carry
forward customer-visible findings, supporting validation evidence, and unresolved gaps without
repeating test assertions, fixture catalogs, or prior contracts. Use compact tables and shared
rules. Include local probe method/URL/body or Docker command, observed status/outcome, and saved
response path where relevant; cite reusable evidence once. The handoff is context, not authority:
the documenter must check current README inputs and evidence relevant to each claim.

Include:

- tested API, metric/tag, filtering, failure, and log cursor behavior supporting customer claims;
- fixture origins, distinguishing synthetic from vendor-observed data;
- Docker integration and Agent E2E environments attempted, the live compatibility each result
  established, and blockers;
- exact commands and concise outcomes, with counts where available; group repeated passes by the
  final applicable result while retaining distinct failures and their resolution;
- repaired paths, customer-visible limitations, coverage gaps, assumptions, known design/build
  gaps, and required human follow-up.

Distinguish unit, integration, and E2E results. Label skipped or unrun tiers and environmental
failures accurately; none is a pass.
