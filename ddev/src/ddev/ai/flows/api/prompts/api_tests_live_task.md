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

Start from current files and actual prepared environment assets. Do not repeat or weaken offline
assertions from the preceding task. If the design is BLOCKED, make no edits or test claims.

Use ddev_env_show first unless a still-applicable discovery result is recorded. If discovery
identifies an applicable environment, inspect its Docker assets and run ddev_env_test for that
exact environment, following your standing rule on reusing recorded results. A shared setup failure
may explain why E2E is unavailable, but an integration-test pass cannot establish an E2E pass.
Repair only defects demonstrated by the environment or its E2E tests,
with a single repair attempt each, then rerun the focused test. An E2E assertion must observe
Agent-produced telemetry through the repository's Agent test helpers, or file-log tailing in the
Agent status, not merely a reachable vendor container. Find and reuse the shared metric assertion
helper in the integration's test modules: every deterministically produced metric with expected
tags, justified exclusions only, symmetric metadata, and all metrics covered. Do not invent a
topology, compose variable, endpoint, or environment name, and do not rename or add an environment
to escape existing ddev lifecycle state. If no applicable environment exists, state E2E as
unavailable/unrun and explain the evidence; do not call an E2E tool speculatively.

Check generated integration artifacts against applicable repository guidance, and report any
build-phase defect rather than rewriting it here. Finish with a concise reviewer summary that
separates unit and Docker-backed integration results (inherited only when their record still
applies), E2E discovery and result, all observed counts and failures, repaired paths,
log/cache/restart coverage, remaining gaps, and candidate user-facing limitations for the
documenter. Classify every failed command as integration-owned and repaired, integration-owned and
unresolved, or external and unrun.
