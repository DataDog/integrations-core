---
type: goal
name: api_tests_offline_goal
---
Read the target client, check, design/build contracts, tests, fixtures, and actual command
results. Verify the deterministic unit and Docker-backed integration work owned by this task.
Agent E2E belongs to the next task and is not required here.

Treat handoffs as relevant evidence, not source authority. Resolve a disagreement by inspecting
current code and tests, recorded API responses, and cited official API evidence. A design constraint
limits required behavior only when that primary evidence supports it; otherwise report the contract
gap rather than preserving an earlier assumption.

The goal is met only when:

1. The target has the integration artifacts required by applicable repository guidance. A
   scaffold or identity defect is reported as build-phase work, not authored by the test phase.
2. Custom-client tests instantiate the real client with a mocked RequestsWrapper and validate
   the exact HTTP contract, envelopes, pagination/poll/download behavior, and relevant errors
   without instantiating the check.
3. Check tests replace the client with an autospecced or strict stub, execute the real check,
   and assert intended metrics/logs/tags/state rather than self.http details or implementation
   constants.
4. Metric tests cover representative values/types/tags and metadata consistency without hiding
   broken emitted metrics behind exclusions. They prove filters reach dependent collection
   calls, distinguish current state from historical windows, and never accept fabricated zeros
   after an optional source fails.
5. Implemented API logs are tested with logs enabled and disabled, actual payload assertions,
   stable independent streams, designed cursor/tie-breaker progression, fresh-instance restart,
   bounded first run, and no advancement past failed pages/files/jobs. Tests do not claim exactly
   once when the design promises at-least-once.
6. Synthetic data is identified; vendor captures are unchanged; every network operation is
   mocked in unit tests.
7. ddev_test ran explicit unit and Docker-backed integration selections where those tiers are
   attainable. A recorded result may satisfy this only when its exact command outcome and readable
   output or run-log reference are present and relevant code, tests, and Docker assets remain
   unchanged. Retrieve the evidence or run an attainable missing selection; do not accept a summary
   claim alone. An unavailable Docker environment is reported as external and unrun, never as
   passing. Docker fixtures pass `wait_for_health=True`, every long-running compose service has a
   healthcheck, and integration tests assert every deterministically produced metric through the
   shared helper.
8. Config/models/metadata validation and format/lint results are truthful, repairs stay scoped,
   and every failed command is classified as integration-owned and repaired, integration-owned
   and unresolved, or external and unrun. External failures include the exact command, observed
   error, readable output or run-log reference, and unchanged prerequisite; they are not retried
   without a relevant change or evidence of a transient recovery.
9. The handoff names test paths, exact command outcomes and counts, remaining failures or unrun
   work, and the environment information the E2E task needs.

Return `valid: false` with a concrete fix when an assertion is weak, a client operation is
untested, a cursor can skip data, Docker wiring is integration-owned and wrong, or an attainable
integration-owned run fails. An unchanged external failure is an unverified gap rather than a
passing result, but does not by itself make the goal invalid once attainable work is complete.
Do not require Agent E2E, behavior absent from the validated design, unavailable fixtures,
invented execution logs, or a blanket rerun solely because a reviewer is independent.
