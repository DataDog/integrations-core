---
type: memory_prompt
name: api_build_memory
---
Write the tester handoff directly from final-file evidence, commands, and reviewer repairs already
in this conversation. This memory step has no tools, and the response is saved verbatim; do not
request inspection, announce future work, or claim a fresh file read. State missing evidence and
its consequence instead of inventing results.

Make this an evidence-backed testing guide. The tester receives the PRD and design handoff
separately and can inspect current code. Carry forward implementation decisions and deviations,
test-critical contracts, evidence locations, and gaps without duplicating large endpoint, metric,
or configuration catalogs. Use compact tables and shared rules. Include local probe method/URL/
body or Docker command, observed status/outcome, and saved response path where relevant; cite
reusable evidence once. The handoff is context, not authority: the tester must inspect current
code and verify evidence relevant to each asserted contract, resolving disagreements.

Include:

- integration identity, check/client classes, namespace, and paths needed to find material code;
- implemented collectors and missing or divergent required behavior, grouped by shared contract;
- HTTP, pagination, response, join, metric, missing/zero/counter, and failure semantics that
  affect test expectations, with metadata location;
- each implemented log stream's delivery state and restart behavior needing a test;
- relevant configuration options/templates, generated paths, and fixture origins;
- exact commands and observed outcomes or a readable run-log reference, including generation and
  lint failures; summarize repeated successful runs by the final applicable result while retaining
  distinct failures and their resolution;
- design deviations, assumptions, unsupported requirements, known bugs, and the highest-value
  mocked-client, stub-client, cursor/restart, and Docker/E2E checks with reasons.

Scaffold existence does not prove implementation. Preserve uncertainty and failures explicitly.
