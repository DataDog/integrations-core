# Integration tests

Read this when the PR changes tests, fixtures, `hatch.toml` or `conftest.py`, or adds an integration. Scope tags are defined in the agent file. How tests are written in general (testing through the check's output, `parametrize`, what not to test) is in `AGENTS.md` › Writing Tests, which `conventions` reviews: don't restate it here.

## What must be tested

- New integrations ship a working E2E environment: a real `dd_environment`, an E2E env in `hatch.toml`, at least one `dd_agent_check` test (**Request**, new only).
- What the PR adds is covered: new metrics asserted, new options tested, the failure path still tested.

## Test types

- Unit: `dd_run_check(check)`, not `check.check()`, which skips `check_initializations`: `self.config` is `None` and the cache prefix is never set, so the test can pass for the wrong reason (159 test files still do it) (PR scope). How HTTP is mocked is in `AGENTS.md` › HTTP Requests, which `conventions` reviews.
- Integration: `dd_run_check(check)` against `dd_environment`. Files named `test_integration*` get the mark automatically; elsewhere a missing mark is only a **Suggestion**.
- E2E: `dd_agent_check(config)`, `rate=True` when the check sends rates or counters (the real Agent drops the first value), `dd_agent_check_discovery` for autodiscovery.
- E2E mark: a test outside `test_e2e*` files without `pytest.mark.e2e` never runs, since E2E runs select `-m e2e` (**Request**).

## Assertions

- `assert_metrics_using_metadata` with `check_symmetric_inclusion` (`exclude=` for conditional metrics) and `check_submission_type=True` in unit and integration tests, off in E2E. One `dd_run_check` is enough: the test aggregator records the first scrape (new or PR-added tests).
- Aggregator assert methods preferred over reading `aggregator.metrics()` by hand (a public API, fine for comparing values across runs) (**Suggestion**).
- Unit or integration: product version checked with `datadog_agent.assert_metadata` when the check calls `set_metadata` (**Suggestion**).

## Test environment and fixtures

- Tests run against a real environment, or at least a mock app (**Request**, PR scope).
- A mock app needs a reason why a real environment isn't possible. Look for one first: a public image for the supported version (vendor, Docker Hub), whether the product can run locally at all (SaaS only, appliance, paid license; opt-in lab envs with `e2e-env=false` are a valid answer), how sibling integrations test, and whether the PR or README already explains it. Public image found → **Request** with the link; clearly can't run locally → no comment; unclear → **Question** saying what you checked (PR scope).
- Most metrics come from the environment (a judgement call, not a percentage) (**Question**, **Request** when clearly not, PR scope).
- Fixtures captured from the real product, not invented (**Question**, PR scope).
- Test matrix covers the product versions the integration claims (**Question**).
- Instance builders in `conftest.py`; shared test helpers in `tests/common.py`, not `helpers.py` (**Suggestion**).
