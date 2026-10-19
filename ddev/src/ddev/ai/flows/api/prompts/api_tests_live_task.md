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
assertions from the preceding task.

Use ddev_env_show to discover valid E2E environments unless a still-applicable result is recorded.
If applicable environments exist, use ddev_env_test for real Agent E2E; otherwise record E2E as
unavailable/unrun and do not call it.
The test tool runs with local integration code and manages environment lifecycle; use a specific
discovered environment when appropriate. An E2E test must use dd_agent_check and assert telemetry/
log behavior observable from the Agent. A healthy vendor container is environment validation, not a
passed E2E test. A skipped E2E test, Docker failure, image pull failure, or unavailable environment
is not a pass—report it accurately.

dd_agent_check cannot observe file logs. When log files are mounted, start the environment with
ddev_env_start (`dev=true`), check the Agent status inside its `dd_<integration>_<environment>`
container with `docker exec` until each file is tailed with bytes read, run ddev_env_test for it,
and always finish with ddev_env_stop. Use only commands that return; never follow or stream logs. If
tailing cannot be observed, report log collection as unverified.

Reuse the shared metric assertion helper from the integration's test modules under the standing
assertion contract. A shared setup failure may explain E2E unavailability; an integration-test pass
cannot establish an E2E pass. Repair defects demonstrated by this task under the standing repair
policy, then rerun the affected selection. Do not invent topology, compose variables, endpoints,
or environment names.

Check generated integration artifacts against applicable repository guidance, and report any
build-phase defect rather than rewriting it here. Finish with a concise reviewer summary that
separates unit and Docker-backed integration results (inherited only when their record still
applies), E2E discovery and result, all observed counts and failures, repaired paths,
log/cache/restart coverage, remaining gaps, and candidate user-facing limitations for the
documenter. Classify every failed command as integration-owned and repaired, integration-owned and
unresolved, or external and unrun.
