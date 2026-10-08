---
type: prompt
name: api_tests_task
---
Build and run the offline test coverage for **${integration}**, repairing scoped defects.

## PRD

${prd}

## Design handoff

${api_design_memory}

## Build handoff

${api_build_memory}

This task owns deterministic unit and Docker-backed integration coverage; the next task owns
Agent E2E discovery and execution. Treat design/build handoffs as relevant evidence, then inspect
the current files before acting. If the design is BLOCKED, make no edits or execution claims.

Apply the standing layered-test contract. Test each public custom-client operation through a
mocked shared HTTP wrapper, then test check orchestration through an autospecced or strict client
stub. Derive cases from the PRD, cited design decisions, and current implementation, including
pagination, response errors, filters, joins, current-state versus history windows, partial
failures, valid zero/missing values, and every implemented log cursor/cache/restart transition.
Preserve captured responses and label synthetic edge payloads. Add Docker-backed integration tests
only when the prepared environment assets define a
runnable local API and its setup/health behavior. Put the shared metric assertion helper
in a test module so the E2E task can find and reuse it from files.

Run explicit unit and integration selections with ddev_test. Run config, models, and metadata
validation, then formatting and lint. Repair implementation, test, metadata, or spec ownership as
needed; regenerate only through validation tools. Finish with test paths, client/check boundaries,
fixture provenance, exact command outcomes and counts, repairs, failures, unrun work, and the
specific environment information that the E2E task must inspect. Do not run ddev_env tools here.
For every external failure, state the exact command, observed error, and the files/environment
condition that would make a retry meaningful. The E2E task may reuse this evidence after
confirming those inputs are unchanged.
