---
type: goal
name: api_tests_goal
---
Read the target client, check, design/build contracts, tests, fixtures, and prepared Docker/E2E
environment. Verify both test architecture and actual results.

Treat handoffs as relevant evidence, not source authority. Resolve a disagreement by inspecting
current code and tests, recorded API responses, and cited official API evidence. A design constraint
limits required behavior only when that primary evidence supports it; otherwise report the contract
gap rather than preserving an earlier assumption.

The goal is met only when:

0. The target has the integration artifacts required by applicable repository guidance. A
   scaffold or identity defect is reported as build-phase work, not authored by the test phase.
1. Custom-client tests instantiate the real client with mocked RequestsWrapper and validate the
   exact HTTP contract, envelopes, pagination/poll/download behavior, and relevant errors without
   instantiating the check.
2. Check tests replace the client with an autospecced or strict stub, execute the real check, and
   assert intended metrics/logs/tags/state rather than self.http details or implementation constants.
3. Metric tests cover representative values/types/tags and metadata consistency without hiding
   broken emitted metrics behind exclusions.
   They prove filters reach dependent collection calls, distinguish current state from historical
   windows, and never accept fabricated zeros after an optional source fails.
4. Implemented API logs are tested with logs enabled and disabled, actual log payload assertions,
   stable independent streams, designed cursor/tie-breaker progression, fresh-instance restart,
   bounded first run, and no advancement past failed pages/files/jobs. Tests do not claim exactly
   once when the design promises at-least-once.
5. Synthetic data is identified; vendor captures are unchanged; every network operation is mocked
   in unit tests.
6. ddev_test ran explicit unit and Docker-backed integration selections where those tiers are
   attainable. A recorded result may satisfy this only when its exact command outcome and readable
   output or run-log reference are present and relevant code, tests, and environment assets remain
   unchanged. Retrieve the evidence or run an attainable missing selection; do not accept a summary
   claim alone.
7. ddev_env_show/ddev_env_test ran genuine Agent E2E where an environment is attainable, and the
   suite did not count skipped or unrun E2E as a pass. A reachable vendor container was not
   reported as E2E success.
8. Docker integration and E2E tests assert every deterministically produced metric with expected
   tag values or keys, exclude only comment-justified timing/state-dependent metrics, and verify
   symmetric metadata over the remaining set plus `assert_all_metrics_covered()`. Docker fixtures
   pass `wait_for_health=True`.
9. Hatch matrix entries, environment names, and supported version labels are unchanged; no repair
   worked around global ddev lifecycle state or host bind-mount behavior.
10. Every failed command is classified as integration-owned and repaired, integration-owned and
    unresolved, or external and unrun. External failures include the exact command, observed
    error, readable output or run-log reference, and unchanged prerequisite; they are not retried
    without a relevant change or evidence of a transient recovery.
11. Config/models/metadata validation and format/lint results are truthful, and repairs stay scoped.

Return `valid: false` with a concrete fix when an assertion is weak, a client operation is untested,
a cursor can skip data, Docker wiring is integration-owned and wrong, or an attainable required run
fails. An unchanged external failure may be an honestly reported, unverified handoff gap without
making the goal invalid; it is not successful live validation. Do not require behavior the
validated design says the API does not have, unavailable fixtures, invented execution logs, or a
blanket rerun solely because a reviewer is independent.
