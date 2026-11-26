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
Agent E2E discovery and execution.

Derive cases from the PRD, cited design decisions, and current implementation. Read the current
client/check, tests, fixtures, and prepared environment assets before editing.

## Maintain two strict unit-test layers

Test the custom product client independently from the check. Instantiate it with a mocked or
spec'd Agent RequestsWrapper and assert its public contract: exact method and URL, parameters or
JSON/body, product-specific headers it owns, status handling, response-envelope validation,
normalization, pagination tokens/pages/termination, safe continuation URLs, export polling,
downloads, and documented errors. Mock every network operation, including POST and downloads.
Do not instantiate the check in client tests and do not retest generic RequestsWrapper internals.

Test the check separately with the custom client patched at the import location, preferably using
`create_autospec(<Product>Client, instance=True)` or an explicit strict stub. Do not mock self.http
in these check tests. Configure deterministic client return values, run the real check with
dd_run_check, and assert Datadog behavior with the aggregator/datadog_agent: metric values and
types, tags, units/conversions, filters, joins, valid zero versus missing values, fatal versus
optional failures, log payloads, events when designed, and cache/cursor transitions. A stub must
fail on unexpected operations so a new request cannot silently escape coverage. Find a current
integration that uses this two-layer pattern, but test the new integration's public contract rather
than reproducing another integration's fixture layout.

Inspect `datadog_checks_base/tests/base/checks/test_agent_check.py` for log payload/cursor assertions;
`mac_audit_logs/tests/test_unit.py` for interrupted file, same-timestamp, and final-cursor cases;
`lustre/tests/test_unit.py` for independent stream cursors; and `octopus_deploy/tests/test_unit.py`
for logs_enabled and datadog_agent.assert_logs behavior. Adapt their principles to this design.

Captured API responses are observed vendor data, not an exhaustive schema. Keep captures unchanged and
organize them by operation/page/case. Synthetic edge payloads are encouraged when needed, but label
them clearly in a helper docstring or test comment and never present them as vendor captures.
Reusable loaders/builders belong in a helper module, not imported from conftest.py. Avoid tests that
only construct the check, inventory constants, repeat metadata names without executing behavior, or
re-test bounds, defaults, and required options the spec declares.

Test failures must retain their semantics. A fatal failure raises from `dd_run_check`; an optional
failure, including failed metadata, completes the run with its warning and without its dependent
metrics. In particular, prove that an optional failed source does not manufacture zero-valued
dependent metrics; that filters apply to every dependent collection, server-side or client-side; and
that current-state metrics are not incorrectly constrained by an activity window. For a join, test
both a complete input and a missing or failed enrichment input. For any cache or cursor, assert
timestamps, expiry/size bounds, corrupt-state recovery, progress after reaching a page or work
bound, and that a cache entry cannot advance past an authoritative log cursor or delivery boundary.

## Pagination, failures, metrics, and logs

Select cases from the actual design rather than imposing a generic checklist. Paginated clients
normally need initial request, continuation propagation, multiple pages, terminal condition,
loop/limit safety, later-page failure policy, and, when the client follows response-supplied
URLs, one foreign-origin case proving no request leaves the configured origin. Async exports
need create/status terminal states, bounded polling, download validation, parsing, and retryable
failure. Joins, filters, counter resets, rate limits, malformed records, and partial collection
need tests only when the integration implements them.

For metrics, assert representative values, submission types, stable tags, transformations, and
valid zero/missing behavior. Use metadata helpers to verify emitted metrics are declared and types
agree. Require symmetric inclusion only when the fixture set actually exercises the entire metric
catalog; explain legitimate fixture gaps rather than excluding a broken emitted metric.

For direct API logs, set the Agent logs flag deliberately and assert both enabled and disabled
behavior. Assert complete safe payloads through `datadog_agent.assert_logs`, including message,
the stub's normalized millisecond timestamp, ddtags, and check-supplied safe fields such as status
or stage—not only that send_log was called. Validate `type: integration`, source, and any service
setting separately in spec.yaml/generated configuration; send_log does not inject them into payloads.
Also isolate stateful collector tests by controlling get_log_cursor and observing send_log cursors.
Verify stable independent stream names, per-record next-resume cursors, compound timestamp/ID or
file offsets, final-only artifact completion, and no log endpoint calls while logs are disabled.

Use a dictionary-backed persistent cache or a fresh check instance to simulate restart. Exercise
the designed first run, second collection, equal timestamps, dedup/overlap, cache absence/corruption,
vendor cursor resets when applicable, and failure during a page/file/export. A failed fetch, parse,
or partial artifact must not advance past the last successfully submitted record. Assert the
documented at-least-once behavior and possible duplicates; never claim exactly-once delivery merely
because one unit test sees no duplicate. Manual export-job state must not outrun the log cursor.

For each implemented log work budget, supply more valid records or source items than fit in one
run. Assert that the first run respects the budget and retains an unfinished cursor, subsequent
runs deliver the remainder, and a fresh check using persisted state also resumes correctly.
Cover a mid-artifact boundary where applicable. Assert payload identities and final completion,
not only counts or a warning. Never accept truncation plus a completed cursor as bounded collection;
test designed retention or poison-record drops separately from work-budget resumption.

## Docker-backed integration setup

Use ddev_test for unit and Docker-backed integration tests. Select the tier explicitly with a test
path or pytest marker so results are unambiguous; do not call a bare mixed suite "offline." A
Docker-backed test uses one session-scoped `dd_environment` that always calls
`docker_run(..., wait_for_health=True)`, supplies every compose variable Hatch does not, uses the
actual/free published port consistently, yields real instance configuration, and owns setup and
teardown. Give every long-running compose service a `healthcheck`. A one-shot setup or seed
service must be a `depends_on` target with `condition: service_completed_successfully`, or stay
running with a healthcheck that passes only after seeding; never disable `wait_for_health` to
tolerate it. Add `conditions` for API readiness and queryable seeded data. Seed deterministic
activity so every designed metric group is produced. Use repository Docker fixtures in generated
tests.

Compose variables that select a product or runtime version come from the Hatch matrix, not test
code: map a `hatch.toml` axis to them through `[envs.default.overrides]` (see existing Docker-based
integrations), set to the version the prepared assets use, and read it from the environment where
tests need it, with no hard-coded fallback. Set this up before the first ddev_env_show, because it
renames the environment.

Two harness details commonly break these tests. E2E sessions skip the body of `dd_environment`, so
an instance built inside it (for example one with a free port) must be stored with `dd_save_state`
and read back with `dd_get_state` in the fixtures E2E tests use. `RequestsWrapper` defines
`__slots__`, so `mock.patch.object(check.http, 'get')` fails; patch the product client, or patch at
the wrapper class or session level.

When the prepared compose mounts `{DD_LOG_<N>}` or the design collects log files, pass
`mount_logs=True` to `docker_run`. It creates one file per spec `logs` example entry (entry N is
`DD_LOG_<N>`), mounts it into the Agent, and injects that entry as the Agent's logs configuration;
the service must append to the mounted file. Never set `DD_LOG_<N>` or create those files yourself:
a log bind-mount failure usually means `mount_logs` is missing.

Put the shared metric assertion helper in a test module so the E2E task can reuse it from files.

Run ddev_lint with fmt=true before the Docker-backed integration selection, so formatting cannot
invalidate a slow run. Then run explicit unit and integration selections with ddev_test, config,
models, and metadata validation, and a final lint without formatting. Repair scoped defects under
the standing repair policy; regenerate only through validation tools. Finish with test paths,
client/check boundaries, fixture provenance, exact command outcomes and counts, repairs, failures, unrun work, and the
specific environment information that the E2E task must inspect. Do not run ddev_env tools here.
For every external failure, state the exact command, observed error, and the files/environment
condition that would make a retry meaningful.
