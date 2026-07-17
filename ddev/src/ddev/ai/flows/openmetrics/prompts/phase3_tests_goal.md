---
type: goal
name: phase3_tests_goal
---
Verify that the test suite for **${integration}** is sound **and actually passes**
end-to-end. The integration directory is `${integration}` in snake_case.

## 1 — Run the end-to-end environment (the decisive check)

Run the integration's end-to-end tests against the real environment with the
`ddev_env_test` tool for this integration (it runs every environment by default; use
`ddev_env_show` first if you need the environment names). This starts the Docker
environment, runs the integration inside a real Agent, and exercises the tests.

- If any environment **fails**, the goal is **not met**. Return `valid: false` and put
  the concrete failure (the failing test and the error/missing-metric output) in
  `reason`, so the worker can **fix the check or the spec** — not weaken the tests — and
  the run can be retried.
- If the tests cannot run for an environmental reason unrelated to the integration
  (Docker unavailable, image pull failure), say so explicitly in `reason`.

## 2 — Confirm the tests are necessary and honest

Read the test files and confirm they genuinely exercise the integration — a suite that
passes only because it asserts nothing is **not** valid. Check that:

- `test_unit.py` mocks every inspected endpoint from its fixture (`metrics.txt` for one endpoint,
  or every `<endpoint_name>_metrics.txt` for multiple endpoints), runs each endpoint instance
  twice, and then makes one union metadata cross-check with `assert_metrics_using_metadata`
  (submission-type and symmetric-inclusion enabled). That cross-check is the coverage —
  it must be present and must not have been narrowed or removed to force a pass.
  It must not demand that one endpoint alone emit the integration-wide union. Per-metric
  `assert_metric` calls are **not** required: their absence is fine, and a long
  list of them (or a hardcoded metric-name list) is a sign of a bloated test, not a better
  one. Explicit assertions are warranted only to pin custom behavior (a renamed label or
  an injected tag).
- `test_integration.py` is marked `@pytest.mark.integration`, uses the real environment,
  and makes the same metadata cross-check.
- `test_e2e.py` is marked `@pytest.mark.e2e` and asserts metrics via `dd_agent_check`.
- `conftest.py`'s `dd_environment` waits for every configured metrics endpoint to be healthy
  before yielding all endpoint instances.
- `conftest.py` supplies, via `docker_run(env_vars=...)`, **every** variable the copied
  compose references (image version tags, credentials, ports). An unset variable the
  compose needs is a likely cause of a startup failure — flag it specifically.
- `conftest.py`'s ports are consistent with the compose: it must not invent arbitrary
  "non-standard" port numbers that the compose does not read (they make the health check
  wait on a port nothing is listening on). Either the compose's ports come from env vars
  and the conftest chooses them with `find_free_port`, or the conftest uses the compose's
  actual published ports. Flag a mismatch between the URL ports and what the compose binds.
- There are no pointless or redundant tests.
- Any assertion that inspects the effective `metrics` config considers every mapping dict,
  not only `metrics[0]`.

## 3 — Confirm the product requirements are pinned

The team defined product requirements for this integration (verbatim below, and reflected in the
worker summary). Where a requirement is observable from telemetry, the suite must pin it — a
dropped metric asserted **absent**, a renamed label asserted present with the original absent. A
stated, observable requirement with no corresponding assertion is a fail. If the block below
states there are no requirements (e.g. "nothing to require"), there is nothing to check here.

Requirements, verbatim:

```
${prd}
```

## Verdict

Pass (`valid: true`) only if the end-to-end run is green, the suite is a genuine, necessary set
of tests with the metadata cross-check intact, **and** every observable product requirement is
pinned. Otherwise fail with the specific, actionable reason.
