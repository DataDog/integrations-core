---
type: prompt
name: api_readme_task
---
Document the implemented API integration for **${integration}** and prepare its human handoff.

## PRD

${prd}

## Design handoff

${api_design_memory}

## Build handoff

${api_build_memory}

## Tests and repairs handoff

${api_tests_memory}

Read the current README, client/check, metadata, spec/generated example, tests, and environment
assets. Handoffs are relevant context and source indexes, not authority over current code, vendor
documentation, or observed results. Reconcile all claims against those sources because the test
phase may have repaired or reduced the original implementation. If the design remained BLOCKED and
no valid integration was built, make no edits and preserve the blockers.

Apply your standing documentation contract to replace scaffold placeholders while preserving the
standard README structure. Document only implemented metrics, events, service checks, log mechanism,
configuration, permissions, versions, and customer-visible limitations supported by evidence.

Complete final file inspection and evidence reconciliation during this task and any reviewer
repairs, while tools are available. Finish with a concise reviewer summary of the README path,
changes, evidence checked, and remaining gaps. Reserve the human-review handoff for the
memory step. Do not create a separate report file.
