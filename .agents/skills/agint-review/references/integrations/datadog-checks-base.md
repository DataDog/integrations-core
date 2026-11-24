# datadog_checks_base

Read this when the PR changes `datadog_checks_base/`, together with `lifecycle.md`.

## Which rules apply

`datadog_checks_base` isn't an integration root (`.ddev/config.toml` marks it `is-integration = false`), so the registry sends it to this agent, `security` and `conventions` explicitly. Rules that apply: this file, the lifecycle context, safe defaults, the deprecation path, "what the PR adds is covered" and the unit test rules (`tests.md`). Not the product-specific ones: real environment, product fixtures, version matrix, metrics against product docs.

## Context

- About 263 integrations depend on it, plus other repos (extras, marketplace).
- `pr-all.yml` runs every integration's tests on a base change, which only catches what those tests cover.
- The minimum-pin test (`--minimum-base-package`) installs the released base for the integrations the PR changes, so it doesn't cover base changes.
- 16 packages export their public names lazily through `lazy_loader.attach_stub` and `.pyi` files.

## Rules

All PR scope.

- Public API stays backward compatible: no removed or renamed public names, changed signatures, defaults or return types without a deprecation path. Grep the callers across the integrations; extras, marketplace and internal-core use the released base too, so an empty local grep isn't proof (**Request**).
- Behaviour changes in shared paths (`AgentCheck.run`, metric submission, the HTTP wrapper, the OpenMetrics scraper, config models) are checked against the integrations that use or override them (**Request**).
- In the 16 packages with an `__init__.pyi`, a new public name is added there, or `lazy_loader` doesn't export it (an integration importing it in the same PR already fails in CI) (**Suggestion**).
- No heavy top-level imports in modules every check loads (the `AgentCheck` import path); follow the README's "Performance Optimizations": lazy loading and imports inside functions (**Request**).
- Changes to how the base talks to the Agent (`datadog_agent`, `aggregator`) update `base/stubs/`, so integration tests keep matching the real Agent (**Request**). Tests use the stubs, so a call to a new Agent function passes everywhere: ask for the datadog-agent PR that adds it (**Question**).
- Changes to `AgentCheck.run`, metric submission or logging also work when the check runs in a separate process (`utils/replay/execute.py` proxies the calls; four fixes there in 2026) (**Question**).
- Significant changes to code that runs for every metric (submission, the OpenMetrics scraper), such as new work per metric or a new data structure, come with before/after numbers from the benchmark environment; small fixes don't (`datadog_checks_base/hatch.toml`, `test_bench.py`) (**Suggestion**).
