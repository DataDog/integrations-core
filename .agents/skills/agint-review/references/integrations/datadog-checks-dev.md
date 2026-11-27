# datadog_checks_dev

Read this when the PR changes `datadog_checks_dev/`.

## Which rules apply

`datadog_checks_dev` is also `is-integration = false`, so the registry routes it explicitly, like the base. It isn't shipped in the Agent: no Agent-compatibility or import-cost rules.

## Context

- Every integration's tests use its pytest plugin (`plugin/pytest.py`: `dd_run_check`, `dd_agent_check`, `mock_http_response`…) and helpers (`docker_run`, conditions, `get_metadata_metrics`).
- `tooling/` holds the config spec templates and generators, and ddev imports much of it.
- For `plugin/` changes the Dispatcher runs every integration's tests, but non-blocking ("Dispatcher / tests (beta, non-blocking)"); spec template changes only run the dev package's own tests.
- Outside integrations-core, tests install the latest `datadog-checks-dev` from PyPI, unpinned, so a released break reaches extras and marketplace immediately.

## Rules

All PR scope.

- Fixtures and helpers stay backward compatible (names, arguments, defaults, what they assert). Grep their use across integrations' tests; other repos use them too (e.g. #23628 changed the `docker_run` default) (**Request**).
- For a `plugin/` change, the Dispatcher's all-integrations result is green; raise it when it's red, and say so when it's still running (**Request**).
- Spec template changes (`tooling/templates/configuration/`) change the config of every integration that uses them: defaults and descriptions reviewed as customer-facing, and the regenerated `conf.yaml.example`/`config_models` included. On a PR, `validate config`/`models` only run for changed integrations (**Question**).
- Changes to modules ddev imports (`utils`, `tooling.utils`, `tooling.commands.validate.*`, `tooling.commands.release.*`, `meta.*`, `ci.setup`, `run`…) are checked against their ddev callers: ddev's tests don't run for a dev `tooling/` change (**Request**).
