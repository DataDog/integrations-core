# Redis Process Autodiscovery E2E Test — Design

## Goal

Add an end-to-end test that verifies the Datadog Agent's **process**
autodiscovery correctly schedules and runs the `redisdb` check against a
`redis-server` process running in a host-networking container, using the
integration's shipped `auto_conf.yaml`.

This complements the container-autodiscovery e2e test added earlier on this
branch ([2026-04-17 spec][redis-spec]). Both modes are exercised side-by-side
in CI in their own Hatch envs.

The chosen approach is the [first solution from DSCVR/6631130024][subpage]:
keep `ad_identifiers: [redis]`, add `cel://process` to it, and add a
`cel_selector.processes` block with the CEL rule. One shipped file serves
both container and process autodiscovery.

[redis-spec]: 2026-04-17-redis-autodiscovery-e2e-design.md
[parent]: https://datadoghq.atlassian.net/wiki/spaces/DSCVR/pages/6568739159/Integrations+autodiscovery+exploration
[subpage]: https://datadoghq.atlassian.net/wiki/spaces/DSCVR/pages/6631130024/Adding+process+support+to+auto+configurations

## Background

The agent's **process listener** discovers integrations by reading host
`/proc/*/cmdline` and matching against CEL expressions in
`cel_selector.processes`. The listener is enabled via
`DD_DISCOVERY_ENABLED=true` and `DD_EXTRA_LISTENERS=process`. The match URL
scheme is `cel://process`.

`auto_conf.yaml` files have historically used only `ad_identifiers` (a list
of container short-image names matched by the docker listener). To support
process matching, the file needs:

- `cel_selector.processes` with the CEL expression(s); and
- `cel://process` explicitly listed in `ad_identifiers`. The agent
  [auto-injects][autoconfig] `cel://process` only when `ad_identifiers` is
  empty; if other identifiers are already present (as is the case for
  `redisdb`), it must be added explicitly.

The wiki's "Redis process autodiscovery" experiment also disables the docker
feature (`DD_AUTOCONFIG_EXCLUDE_FEATURES=docker`). Without that, processes
running inside containers are tagged with a container-id and excluded by the
process listener, defeating the test.

[autoconfig]: https://github.com/DataDog/datadog-agent/blob/eed01b7ea1dbaff02cb31fc4e1c0287665e91ede/comp/core/autodiscovery/autodiscoveryimpl/autoconfig.go#L475-L481

## Approach

Add a dedicated Hatch environment `py3.13-adproc-7.0` that toggles a new
`REDIS_AUTODISCOVERY_PROCESS=true` env var. `conftest.py` grows a third
branch on that var, parallel to the existing `AUTODISCOVERY` branch:

- When `REDIS_AUTODISCOVERY_PROCESS=true`: start a single `redis:7.0`
  container with `network_mode: host`, and pass the agent the env vars
  needed to enable the process listener and disable the docker feature. Yield
  `(None, e2e_metadata)` so no static `conf.yaml` is mounted — the agent runs
  purely off the integration's `auto_conf.yaml` (already bind-mounted by the
  ddev harness when no static config is present).
- When `REDIS_AUTODISCOVERY=true`: existing container-autodiscovery branch,
  unchanged.
- Otherwise: existing 1m-2s cluster path, unchanged.

A new test file `tests/test_e2e_autodiscovery_process.py` is skipped in
every environment except `py3.13-adproc-7.0`. It waits for the agent to
discover the redis process, runs the check, and asserts a minimal proof of
process-autodiscovery success.

The agent container is already started with `--network=host` on Linux by the
ddev harness (`ddev/src/ddev/e2e/agent/docker.py:275-276`) and the host
`/proc` is bind-mounted to `/host/proc` (`docker.py:215-216`), so the agent
can both reach `127.0.0.1:6379` and see the host's process table.

## Changes

### 1. `redisdb/datadog_checks/redisdb/data/auto_conf.yaml`

```yaml
## @param ad_identifiers - list of strings - required
## A list of container identifiers that are used by Autodiscovery to identify
## which container the check should be run against. For more information, see:
## https://docs.datadoghq.com/agent/guide/ad_identifiers/
##
## `cel://process` is required (in addition to `redis`) so the process
## listener picks up the `cel_selector.processes` CEL rule below. Without an
## explicit `cel://process` entry the agent only auto-injects it when
## `ad_identifiers` is empty.
#
ad_identifiers:
  - redis
  - cel://process

## @param cel_selector - mapping - optional
## CEL rules used by the agent's `process` and (future) container CEL
## listeners. The `processes` rule below matches any process whose cmdline
## contains `redis-server`.
#
cel_selector:
  processes:
    - process.cmdline.contains("redis-server")

## All options defined here are available to all instances.
#
init_config:

## Every instance is scheduled independently of the others.
#
instances:

    ## @param host - string - required
    ## Enter the host to connect to.
    #
  - host: '%%host%%'

    ## @param port - integer - required
    ## Enter the port of the host to connect to.
    #
    port: 6379
```

The two added comments document the not-obvious "must be added explicitly
when `ad_identifiers` is non-empty" caveat. Container autodiscovery (the
existing `py3.13-ad-7.0` env) keeps working unchanged: the docker listener
matches `redis` and substitutes `%%host%%` to the bridge IP. Process
autodiscovery: the `cel://process` listener evaluates the `processes` CEL
rule against host processes, and substitutes `%%host%%` to `127.0.0.1` when
matched.

### 2. `redisdb/hatch.toml`

Add `adproc-7.0` to the existing version axis:

```toml
[[envs.default.matrix]]
python = ["3.13"]
version = ["5.0", "6.0", "7.0", "8.0", "cloud", "ad-7.0", "adproc-7.0"]

[envs.default.overrides]
matrix.version.env-vars = [
  # ... existing entries unchanged ...
  { key = "REDIS_VERSION", value = "7.0", if = ["adproc-7.0"] },
  { key = "CLOUD_ENV", value = "false", if = ["adproc-7.0"] },
  { key = "REDIS_AUTODISCOVERY_PROCESS", value = "true", if = ["adproc-7.0"] },
]
```

Resulting env: `py3.13-adproc-7.0`. Invoked with the standard
`ddev env start|test|stop --dev redisdb py3.13-adproc-7.0`.

### 3. `redisdb/tests/compose/autodiscovery-process.compose` (new)

```yaml
services:
  redis-process:
    image: "redis:${REDIS_VERSION}"
    network_mode: host
```

`network_mode: host` makes `redis-server` visible in the host process table,
where the agent's process listener (also on the host network namespace,
reading host `/proc` via the existing `/proc:/host/proc` mount) can see it.

### 4. `redisdb/tests/common.py`

```python
AUTODISCOVERY_PROCESS = is_affirmative(os.environ.get('REDIS_AUTODISCOVERY_PROCESS', 'false'))
AUTODISCOVERY_PROCESS_COMPOSE_PATH = os.path.join(HERE, 'compose', 'autodiscovery-process.compose')
```

### 5. `redisdb/tests/conftest.py`

Add a third branch to `dd_environment` (above the existing `AUTODISCOVERY`
branch, since both should match before falling through to the cluster path):

```python
if AUTODISCOVERY_PROCESS:
    e2e_metadata = {
        'env_vars': {
            'DD_DISCOVERY_ENABLED': 'true',
            'DD_EXTRA_LISTENERS': 'process',
            'DD_AUTOCONFIG_EXCLUDE_FEATURES': 'docker',
        },
    }
    with docker_run(
        AUTODISCOVERY_PROCESS_COMPOSE_PATH,
        conditions=[
            CheckDockerLogs(AUTODISCOVERY_PROCESS_COMPOSE_PATH, 'Ready to accept connections', wait=5)
        ],
    ):
        yield None, e2e_metadata
    return
```

`env_vars` in `e2e_metadata` is read by ddev at agent-start time
(`ddev/src/ddev/cli/env/start.py:190`) and forwarded as `-e` flags. The
docker socket is intentionally NOT mounted: process autodiscovery doesn't
need it, and `DD_AUTOCONFIG_EXCLUDE_FEATURES=docker` disables the docker
feature so processes inside containers don't get container-IDs (which would
cause the process listener to skip them — per the wiki experiment).

### 6. `redisdb/tests/test_e2e_autodiscovery_process.py` (new)

```python
import os

import pytest

from datadog_checks.dev import WaitFor, run_command
from datadog_checks.redisdb import Redis

from . import common

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not common.AUTODISCOVERY_PROCESS, reason='Requires REDIS_AUTODISCOVERY_PROCESS=true'
    ),
]


def _agent_container_name():
    env = os.environ['HATCH_ENV_ACTIVE']
    return f'dd_redisdb_{env}'


def _autodiscovery_ready():
    result = run_command(
        ['docker', 'exec', _agent_container_name(), 'agent', 'configcheck'],
        capture=True,
        check=True,
    )
    assert 'redisdb' in result.stdout, result.stdout


@pytest.fixture
def autodiscovery_ready():
    WaitFor(_autodiscovery_ready, attempts=30, wait=2)()


def test_e2e_autodiscovery_process(dd_agent_check, autodiscovery_ready):
    aggregator = dd_agent_check(
        {'init_config': {}, 'instances': []},
        rate=True,
        discovery_min_instances=1,
        discovery_timeout=30,
    )
    service_checks = aggregator.service_checks('redis.can_connect')
    assert any(
        sc.status == Redis.OK and 'redis_port:6379' in sc.tags for sc in service_checks
    ), service_checks
```

Structurally identical to `test_e2e_autodiscovery.py`. The assertion is
deliberately minimal: one `redis.can_connect` OK with `redis_port:6379`.
Process-discovered submissions emit `host:127.0.0.1` (per the wiki) and no
docker tags, but those specifics are confirmed empirically on first run
rather than baked into the spec.

### 7. Skipif update on `redisdb/tests/test_e2e.py`

Currently:

```python
pytest.mark.skipif(common.AUTODISCOVERY, reason='Cluster e2e is not run in the autodiscovery env'),
```

Becomes:

```python
pytest.mark.skipif(
    common.AUTODISCOVERY or common.AUTODISCOVERY_PROCESS,
    reason='Cluster e2e is not run in the autodiscovery envs',
),
```

`test_e2e_autodiscovery.py` doesn't need changes — its `not common.AUTODISCOVERY`
condition is already false in the process env, so it skips correctly.

### 8. `redisdb/DEVELOPMENT.md`

Add a paragraph next to the existing autodiscovery section:

> The `py3.13-adproc-7.0` environment exercises the agent's **process**
> autodiscovery using the `cel_selector.processes` rule in `auto_conf.yaml`.
> It starts a single `redis:7.0` container with `network_mode: host` and
> runs the agent with `DD_DISCOVERY_ENABLED=true`, `DD_EXTRA_LISTENERS=process`,
> and `DD_AUTOCONFIG_EXCLUDE_FEATURES=docker`. The same bind-mount inode
> caveat as `py3.13-ad-7.0` applies. Port 6379 must be free on the host.

## Verification

Two independent signals both must pass:

1. `autodiscovery_ready` fixture: `docker exec dd_redisdb_py3.13-adproc-7.0
   agent configcheck` output contains `redisdb` within 60s.
2. `dd_agent_check(..., discovery_min_instances=1, discovery_timeout=30)` runs
   the check, and the resulting aggregator shows `redis.can_connect` OK with
   `redis_port:6379`.

Two-direction sanity check on first implementation:

1. With the new `auto_conf.yaml` (both `redis` and `cel://process` in
   `ad_identifiers`, `cel_selector.processes` present), the test passes.
2. With `process.cmdline.contains("redis-foo")` substituted in
   `auto_conf.yaml`, `autodiscovery_ready` times out and the test fails. This
   confirms the test exercises the source-tree `auto_conf.yaml`, not the
   agent image's bundled copy. Restore via `git checkout` + `ddev env stop` +
   `ddev env start` (the bind-mount inode caveat applies).

## Failure Modes

- Redis can't bind 6379 because something's already listening on the host
  → compose startup fails fast with a port conflict; documented in
  `DEVELOPMENT.md`.
- `process` listener doesn't see the redis process → likely PID-namespace or
  `/proc` mount issue. Check `agent configcheck` output, then inspect the
  agent's view of host processes via
  `docker exec <agent> sh -c 'for p in /host/proc/[0-9]*/cmdline; do tr "\0" " " <"$p"; echo; done | grep redis-server'`.
- `DD_AUTOCONFIG_EXCLUDE_FEATURES=docker` not honoured (e.g., agent version
  mismatch) → the docker feature stays on, the redis process gets a
  container-id, and the process listener excludes it; the test fails at
  `autodiscovery_ready`.
- Agent reaches the wrong host for the process → `discovery_min_instances=1`
  succeeds (config was discovered) but `redis.can_connect` comes back
  CRITICAL. Distinguishable from a pure discovery failure.
- `cel://process` not added to `ad_identifiers` (regression) → the agent's
  auto-injection logic skips it because `ad_identifiers` is non-empty; the
  process rule is loaded but never triggers. Caught by the negative-direction
  sanity check.

## Out of Scope (Follow-Ups)

Tracked against the [parent confluence][parent], to be addressed in
subsequent specs:

- mcache process autodiscovery (next branch step, separate spec).
- Two-instance double-reporting case from the wiki (no error reported, both
  redis processes get identical configs because the port is hardcoded).
- Asserting the absence of `docker_image` / `image_id` / etc tags on the
  process-discovered submission.
- Multi-version coverage (5.0 / 6.0 / 8.0).

## Risks

- The agent's CEL handling [applies one selector type at a time][priority],
  with containers > processes. Our config only has `cel_selector.processes`,
  so we're fine. If a `cel_selector.containers` is added later (in the same
  block), the process rule would silently stop working. The shipped file's
  comment block flags `cel://process` as load-bearing; reviewers of any
  future selector-block edit need to keep this in mind.
- `DD_AUTOCONFIG_EXCLUDE_FEATURES=docker` and `DD_EXTRA_LISTENERS=process`
  require an agent build that supports CEL process autodiscovery. The wiki
  experiment used `datadog/agent:7.78.0`. ddev's default agent image
  (`registry.datadoghq.com/agent-dev:master-py3`) is newer and should include
  the feature; if not, the test fails at `autodiscovery_ready` and we'd need
  to pin a specific `--agent-build`.

[priority]: https://github.com/DataDog/datadog-agent/blob/03f5a8be52a0dc3adb9d7abbef04150fe1ae5f4e/comp/core/autodiscovery/integration/matching_program.go#L56-L60
