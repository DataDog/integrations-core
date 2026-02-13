# Migrate HTTP layer from requests to httpx

- Authors: Morgan Wang
- Date: 2025-02-05
- Status: draft
- [Discussion][1]

**Implementation branches (as of 2026-02):**
- **`mwdd146980/ai-6576`** – Base httpx implementation: `HTTPXWrapper`, `HTTPXResponseAdapter`, shared `http_exceptions`/`http_protocol`, `use_httpx` on AgentCheck, Kerberos via httpx-gssapi.
- **`mwdd146980/base-httpx-migration`** – Application in datadog_checks_base: `OpenMetricsBaseCheckV2.get_http_handler(config)`, scraper uses it, `mock_http_response(CheckClass, ...)` fixture, OpenMetrics legacy tests migrated to implementation-independent mocks.

## Overview

The Datadog Agent check base currently uses the `requests` library for all HTTP traffic via a shared wrapper (`RequestsWrapper`) in `datadog_checks_base`. The `requests` project is in maintenance mode (no new features; security and bug fixes only) and does not support async or HTTP/2. This RFC proposes migrating to `httpx`: we introduce an httpx-based wrapper that preserves the current public API, switch the base check to use it first, then migrate Prometheus/OpenMetrics and remaining code paths incrementally. Integrations will not need to change how they call `self.http.get(url)` or consume responses; only the implementation behind those calls changes.

## Problem

- **Maintenance and roadmap**: `requests` is effectively in maintenance mode. There is no path to async support or HTTP/2, which limits future options for concurrent checks or HTTP/2-only endpoints.
- **Single point of coupling**: All checks that perform HTTP through the base use `RequestsWrapper` in [`datadog_checks_base/datadog_checks/base/utils/http.py`](datadog_checks_base/datadog_checks/base/utils/http.py), which is built on `requests.Session`, custom adapters (TLS, Host header, Unix sockets), and a set of auth helpers (basic, digest, Kerberos, NTLM, AWS, OAuth). Any change or replacement touches this central module and every code path that creates or uses the wrapper.
- **Blast radius**: The wrapper is used in multiple places:
  - **Base check**: `AgentCheck.http` (property) returns a `RequestsWrapper` used by many integrations for ad-hoc HTTP (e.g. REST APIs).
  - **Prometheus mixin**: `get_http_handler()` in [`datadog_checks_base/datadog_checks/base/checks/prometheus/mixins.py`](datadog_checks_base/datadog_checks/base/checks/prometheus/mixins.py) creates and caches a `RequestsWrapper` per endpoint.
  - **OpenMetrics mixin and v2 scraper**: Same pattern in [`datadog_checks_base/datadog_checks/base/checks/openmetrics/mixins.py`](datadog_checks_base/datadog_checks/base/checks/openmetrics/mixins.py) and [`datadog_checks_base/datadog_checks/base/checks/openmetrics/v2/scraper/base_scraper.py`](datadog_checks_base/datadog_checks/base/checks/openmetrics/v2/scraper/base_scraper.py).
  - **Direct instantiation**: A few integrations (e.g. vsphere, kube_controller_manager, kube_scheduler, kube_proxy, kube_metrics_server, kube_dns) construct `RequestsWrapper` directly.
- **Testing**: Many tests mock `requests.Session.get` or similar. The migration uses a single, implementation-independent mock design: (1) **Check mode** – `mock_http_response(CheckClass, ...)` patches the check’s `get_http_handler` with a `RequestWrapperMock` and response queue. (2) **General mode** – `mock_http_response(...)` with no check class returns `(client, enqueue)` for use in tests without a check (e.g. inject `client` where the HTTP wrapper is created). Both use `HTTPResponseMock` / `RequestWrapperMock` from `datadog_checks.dev.http` so tests work with either requests or httpx. See `.cursor/rfc-requests-to-httpx-migration.md` and `docs/developer/base/http.md`.

A big-bang replacement would be risky and hard to roll back. An incremental migration by code path (base check first, then Prometheus, then OpenMetrics, then remaining direct usage) keeps rollback options and allows validation at each step.

## Constraints

1. **API stability**: The public API of the HTTP wrapper must remain the same so that integrations do not need code changes. Call sites use `self.http.get(url)`, `response.content`, `response.iter_lines(...)`, `response.raise_for_status()`, `response.close()`, and sometimes `handler.options['headers']`. All of these must continue to work.
2. **Feature parity**: The new implementation must support the same configuration and behavior: TLS (custom CA, client cert, protocol restrictions, host-header TLS), auth (basic, digest, Kerberos, NTLM, AWS, OAuth), auth_token (file/OAuth/DC/OS readers and header writer), proxy and no_proxy, timeouts (connect/read), Unix domain sockets, and connection persistence where applicable.
3. **Compatibility**: Must work with existing Agent config (instance, init_config, agent proxy), ddtrace (HTTP tracing), and all supported Python versions for the Agent.
4. **Incremental rollout**: Migration must be phased so that we can switch one code path at a time (base check, then Prometheus, then OpenMetrics, then direct instantiations) and roll back without reverting the entire change.

## Recommended Solution

Introduce an **httpx-based wrapper** alongside the existing `RequestsWrapper`, then migrate call sites phase by phase.

### 1. Response adapter

Add a class that wraps `httpx.Response` and exposes the same surface as the current response object:

- Attributes: `content`, `headers`, `encoding` (settable for OpenMetrics v2), `status_code`
- Methods: `iter_lines(chunk_size=None, decode_unicode=False, delimiter=None)`, `iter_content(chunk_size=None, decode_unicode=False)`, `raise_for_status()`, `close()`

Implement by delegating to the underlying `httpx.Response`; map `iter_lines` to httpx’s `iter_lines()` and match existing semantics so Prometheus/OpenMetrics parsers work unchanged.

### 2. HTTPXWrapper

Add a new class in the same module as `RequestsWrapper` with:

- **Constructor**: Same signature as `RequestsWrapper(instance, init_config, remapper=None, logger=None, session=None)` and equivalent config parsing so that `STANDARD_FIELDS`, `HTTP_CONFIG_REMAPPER`, TLS, auth, proxy, UDS, and timeouts behave the same.
- **Public surface**: Same methods (`get`, `post`, `head`, `put`, `patch`, `delete`, `options_method`) and the same `options` dict (e.g. `options['headers']`) so code that inspects the handler (e.g. OpenMetrics) continues to work.
- **TLS**: Use `httpx.HTTPTransport` with `verify`, `cert`, and custom SSL context from the existing `create_ssl_context()`; implement or document Host-header TLS (custom transport or equivalent) where required.
- **Auth**: Basic (tuple), digest (httpx or auth class), Kerberos/NTLM via `httpx-kerberos` / `httpx-ntlm`, AWS (httpx-compatible auth), OAuth (same token flow, headers).
- **UDS**: Use `httpx.HTTPTransport(uds=path)` and existing `is_uds_url` / `quote_uds_url` logic to map `unix://` URLs.
- **Single direct requests call**: Replace `requests.post` in `DCOSAuthTokenReader` with a call through the same wrapper or a one-off httpx call with consistent TLS/auth options.
- **Exceptions**: Catch httpx exceptions and re-raise or expose a small compatibility layer so callers can be updated in one place (e.g. map `httpx.ConnectError` to a familiar name during transition).

### 3. Phased rollout

- **Phase 1**: Implement `HTTPXWrapper` and response adapter; switch only `AgentCheck.http` in the base check to use `HTTPXWrapper`. All other code paths (Prometheus mixin, OpenMetrics mixin, v2 scraper, direct instantiations) keep using `RequestsWrapper`.
- **Phase 2**: Switch Prometheus mixin `get_http_handler` to return `HTTPXWrapper`.
- **Phase 3**: Switch OpenMetrics mixin `get_http_handler` and OpenMetrics v2 scraper to use `HTTPXWrapper`.
- **Phase 4**: Migrate integrations that instantiate `RequestsWrapper` directly (vsphere, kube_* listed above) to use the shared wrapper or a factory.
- **Phase 5**: Deprecate and remove `RequestsWrapper`; remove `requests` and requests-specific optional deps; update ddtrace to patch httpx; update all tests to mock httpx.

### Strengths

- Same API for integrations; no call-site changes.
- Incremental migration with clear rollback at each phase.
- httpx is actively maintained, supports HTTP/2 and async for future use, and has built-in testing support (`MockTransport`).
- Single HTTP stack long-term reduces maintenance and dependency surface.

### Weaknesses

- Two implementations (requests and httpx) coexist for several phases; test matrix may need to cover both during transition.
- Auth and TLS edge cases (Kerberos, NTLM, Host header TLS) may require extra work to match current behavior; we will validate with existing tests and integrations.

### Performance and cost

- Connection pooling and timeouts are supported in httpx similarly to requests; we do not expect a meaningful performance regression. Optional HTTP/2 could improve performance for some endpoints later.
- Dependency size: httpx and httpcore replace requests and urllib3; net impact to be measured during implementation.

## Other Solutions

- **Stay on requests**: Avoids migration cost but leaves us on a maintenance-only library with no path to async or HTTP/2.
- **Big-bang replacement**: Replace all usages in one change. Higher risk and harder rollback; not recommended given blast radius.
- **New API only**: Expose a new httpx-based API and migrate integrations one by one. Would require many integration changes and a long deprecation period; the recommended approach (same API, swap implementation) is simpler for integrators.

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Auth (Kerberos/NTLM) behavior differs | Use existing Kerberos/NTLM tests and integration tests; document any gaps; consider feature flag to force requests path for affected customers during rollout. |
| Host-header TLS | requests_toolbelt’s HostHeaderSSLAdapter has no direct httpx equivalent; implement via custom transport or request hooks and test with integrations that use it. |
| Regression in production | Phased rollout; Phase 1 affects only checks using `self.http`; run integration test suites and optional canary before broadening. |
| ddtrace not patching httpx | Add httpx to ddtrace patch list when we switch; verify spans in staging. |

## Open Questions

1. Whether to add an explicit feature flag or agent config (e.g. `use_httpx: true`) to toggle the new implementation in Phase 1, or to switch the base check unconditionally once HTTPXWrapper is ready.
2. Where to track “validated” integrations (e.g. RFC appendix, tracking issue, or release notes).
3. Exact version pin for httpx and optional deps (httpx-kerberos, httpx-ntlm) to be decided during implementation.

## Appendix

### Key files

- [`datadog_checks_base/datadog_checks/base/utils/http.py`](datadog_checks_base/datadog_checks/base/utils/http.py): `RequestsWrapper`, auth helpers, TLS adapters, auth_token handlers.
- [`datadog_checks_base/datadog_checks/base/checks/base.py`](datadog_checks_base/datadog_checks/base/checks/base.py): `AgentCheck.http` property.

### Integrations that instantiate RequestsWrapper directly

- `vsphere/datadog_checks/vsphere/api_rest.py`
- `kube_controller_manager`, `kube_scheduler`, `kube_proxy`, `kube_metrics_server`, `kube_dns` (in their check modules, in a `get_http_handler`-like path)

### Documentation

- [HTTP (developer base)](docs/developer/base/http.md): Documents current `self.http` usage and options.

[1]: https://github.com/DataDog/integrations-core/pull/
