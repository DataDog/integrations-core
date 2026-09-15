# Async GitHub Client Test Guidelines

These rules govern the tests in this package. They supplement the repository root
`AGENTS.md`; where they overlap, the root file still applies. They exist because this suite
had grown with tests that could not fail for a reason living in the client code.

## The one question before adding a test

Can this test fail for a reason that lives in the client code? If the only way it fails is
Pydantic, `httpx`, or `ddev.utils.rate_limiting` breaking, it belongs in that layer's suite,
or nowhere. The client suite covers exactly: request construction (method, path, body,
headers), response wiring (parsing into the right model, forwarding headers), error
propagation, retry behavior, and the limiter/governor integration points.

## Layer ownership

- Model parsing contracts belong in `test_models.py`, exercised with `Model.model_validate(payload)`
  and no transport or client. If a test only checks that a payload parses, it is a model test.
- Limiter and governor semantics belong in the rate-limiting suite (`tests/utils/test_rate_limiting.py`).
  Here we test only that the client wires them in and reacts (`test_rate_limiting.py`).
- Enum exhaustiveness is never tested here. The client-owned boundary is "one valid member parses,
  one invalid string raises." A request-constant, response-varying matrix over a `StrEnum` field
  tests Pydantic, not the client.
- Helper modules obey the same layer boundaries as tests. Pure payload factories
  live in `payloads.py` and import nothing beyond the stdlib; client-layer
  helpers (transports, client factories, the endpoint registry) live in
  `helpers.py` and may import payloads, never the reverse. `test_models.py`
  imports only from `payloads.py` — if a model test needs something from
  `helpers.py`, either the helper is misplaced or the test is not a model test.

## Cross-cutting behavior goes through the registry

Every public endpoint method must be registered in `ENDPOINT_CALLS` (in `helpers.py`) with minimal
valid arguments and a valid response factory. The registry drives error-propagation and
header-forwarding coverage for all endpoints at once. Never write a per-endpoint
`*_http_error_raises` or `*_headers_forwarded` test; register the method instead.

## Per-endpoint tests

Write exactly one success test per endpoint, asserting the request sent (method, path, body) and
the parsed model, plus tests for behavior unique to that endpoint (for example the workflow-dispatch
overloads, `update_check_run` conclusion validation, or the review-comment position/line-side
exclusivity). If a second endpoint test asserts the same things with different literals, it is a
duplicate.

## Determinism

- No `time.time()` in assertions. Governor-driven waits use `FakeClock` and `advance_clock_on_sleep`
  from `tests/helpers/clock.py`.
- No explicit `@pytest.mark.asyncio`; asyncio auto mode is the convention.
- Signed-URL download flows route through `patch_signed_download`.

## Assertions must be able to fail

A test whose handler ignores the property named in the test is worse than no test: it reads as
coverage that isn't there. When adding a test, break the code mentally and confirm the assertion
would catch it.
