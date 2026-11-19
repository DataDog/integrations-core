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

Read the README if present, plus the current client/check, metadata, spec/generated example, tests, and environment
assets. Reconcile all claims against those sources because the test phase may have repaired or
reduced the original implementation.

Create the README if missing; otherwise replace scaffold placeholders under the standing documentation
contract. Use the standard structure: Overview;
Setup with Installation, Configuration, and Validation; Data Collected with Metrics, Events, and
Service Checks; Troubleshooting; and reference-link style.

In the reviewer summary, identify evidence checked and unresolved claims without repeating the
README or phase handoffs.
