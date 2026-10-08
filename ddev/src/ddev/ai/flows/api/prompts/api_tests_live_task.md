---
type: prompt
name: api_tests_live_task
---
Perform the live-environment verification for **${integration}** and gather final test evidence.

## PRD

${prd}

## Design handoff

${api_design_memory}

## Build handoff

${api_build_memory}

Start from current files and actual prepared environment assets. Design/build handoffs and the
preceding task summary are relevant evidence, not authoritative conclusions. Inspect current files
and assets to decide whether their results still apply. Do not repeat or weaken offline assertions
from the preceding task. If the design is BLOCKED, make no edits or test claims.

Use ddev_env_show first unless an exact, still-applicable discovery result is available in recorded
tool output or a readable run log. If discovery identifies an applicable environment, inspect its
Docker assets and run ddev_env_test for that exact environment unless a still-applicable result or
the same external setup failure is already recorded with unchanged prerequisites. A shared setup
failure may explain why E2E is unavailable, but an integration-test pass cannot establish an E2E
pass. Retrieve the recorded output before relying on it; if it cannot be retrieved, run the
attainable missing selection. Repair only defects demonstrated by the environment or its E2E tests,
with a single repair attempt each, then rerun the focused test. An E2E assertion must observe
Agent-produced telemetry or logs through the repository's Agent test helpers, not merely a reachable
vendor container. Find and reuse the shared metric assertion helper in the integration's test
modules: every deterministically produced metric with expected tags, justified exclusions only,
symmetric metadata, and all metrics covered. Do not invent a topology, compose variable, endpoint,
or environment name, and do not rename or add an environment to escape existing ddev lifecycle
state. If no applicable environment exists, state E2E as unavailable/unrun and explain the evidence;
do not call an E2E tool speculatively.

Check generated integration artifacts against applicable repository guidance, and report any
build-phase defect rather than rewriting it here. Summarize separately: unit and Docker-backed
integration results inherited only when their recorded command evidence is still applicable, E2E
discovery/result, all observed counts and failures, repaired paths, log/cache/restart coverage,
remaining gaps, and the exact customer-visible limitations the README must preserve. Do not repeat
an already recorded, unchanged external setup failure just because this is final verification or a
goal review follows. Rerun it only after a relevant repair or evidence that its condition changed.
If the prior result is insufficient to assess, retrieve the missing evidence or run the affected
selection when attainable; otherwise explain why the tier remains unverified. Classify every
failed command as integration-owned and repaired, integration-owned and unresolved, or external
and unrun.

Complete all final file inspection during this task or its reviewer repairs, while tools are
available. Keep the final response to a concise reviewer summary of the results and gaps above;
reserve the documentation-author handoff for the memory step.
