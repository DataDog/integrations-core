---
type: memory_prompt
name: api_readme_memory
---
Write the final human-review handoff directly from file reads, command results, and repairs
already in this conversation. This memory step has no tools, and the response is saved verbatim;
do not request inspection, announce future work, or claim a fresh file read. State missing
evidence and its consequence instead of inventing results.

Make this an evidence-backed review guide rather than a phase transcript or restatement of the
PRD and earlier handoffs. Point to material files, official sources, and readable command results
without reproducing metric catalogs, endpoint schemas, or routine inventories. Use compact tables
or shared rules where helpful. This handoff is context, not authority; reviewers must inspect the
final files and cited evidence before accepting its conclusions.

Include integration identity and material paths; implemented, incomplete, unsupported, or
divergent requirements; customer-visible behavior actually documented; README changes and
official references used or missing; captured versus synthetic test coverage; tester repairs,
assumptions, source/config defects, and focused review steps. For API-polled logs, include only
customer-visible transport, enablement, restart, and delivery risks. Report exact unit, Docker
integration, Agent E2E, validation, and lint outcomes with available counts, distinguishing
passes, skips, failures, unavailable environments, and unrun work. Preserve earlier gaps that
still matter to review without treating a generated draft or passing subset as release ready.
