---
type: goal
name: api_tests_goal
---
Read the target client, check, design/build contracts, tests, fixtures, and prepared Docker/E2E
environment. Verify the Agent E2E work and the final verification results.

Treat handoffs as relevant evidence, not source authority. Resolve a disagreement by inspecting
current code and tests, recorded API responses, and cited official API evidence. A design constraint
limits required behavior only when that primary evidence supports it; otherwise report the contract
gap rather than preserving an earlier assumption.

The offline_tests goal already accepted the client, check, metric, log, fixture, and unit and
Docker-backed integration criteria. Re-check one of those only when its files changed after that
acceptance or E2E work exposed a defect in it.

The goal is met only when:

1. ddev_env_show/ddev_env_test ran genuine Agent E2E where an environment is attainable, and the
   suite did not count skipped or unrun E2E as a pass. A reachable vendor container was not
   reported as E2E success. Any environment started with ddev_env_start was stopped.
2. Docker integration and E2E tests assert every deterministically produced metric with expected
   tag values or keys, exclude only comment-justified timing/state-dependent metrics, and verify
   symmetric metadata over the remaining set plus `assert_all_metrics_covered()`. Docker fixtures
   pass `wait_for_health=True`.
3. Every compose variable that selects an image or runtime version (inspect each `{VAR}` in image
   tags) comes from a Hatch matrix axis, and tests read it without a hard-coded fallback; no
   environment was renamed, removed, or added to work around global ddev lifecycle state or host
   bind-mount behavior.
4. Every failed command is classified as integration-owned and repaired, integration-owned and
   unresolved, or external and unrun. External failures record the exact command, observed error,
   and output or run-log reference.
5. Config/models/metadata validation and format/lint results are truthful, and repairs stay scoped.

Return `valid: false` with a concrete fix when an E2E assertion is weak, Docker or E2E wiring is
integration-owned and wrong, or an attainable required run fails. An unchanged external failure
may be an honestly reported, unverified handoff gap without making the goal invalid; it is not
successful live validation. Do not require behavior the validated design says the API does not
have, unavailable fixtures, or invented execution logs.

Before running any test tier yourself, check the run log: if it shows the exact selection
passing after the last edit to relevant code, tests, configuration, or Docker assets, cite that log
line and do not rerun it. Rerun only a selection whose record is missing, failed, or stale.
