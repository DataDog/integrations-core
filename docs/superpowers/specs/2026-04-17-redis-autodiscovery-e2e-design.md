# Redis Agent Autodiscovery E2E Test — Design

## Goal

Add an end-to-end test that verifies the Datadog Agent's container
autodiscovery correctly schedules and runs the `redisdb` check against a Redis
container using the integration's shipped `auto_conf.yaml`.

This is the first step of a broader effort to cover the autodiscovery cases
explored in the [Integrations autodiscovery exploration][confluence] page. This
spec targets only the known-working "default-port, bridge network" case. The
broken cases (port-forwarded, non-default in-container port, `--network=host`
double-reporting, process autodiscovery) are explicitly out of scope and will
be addressed in follow-ups after the upstream fixes land.

[confluence]: https://datadoghq.atlassian.net/wiki/spaces/DSCVR/pages/6568739159/Integrations+autodiscovery+exploration

## Background

`redisdb/datadog_checks/redisdb/data/auto_conf.yaml` declares
`ad_identifiers: [redis]` with a hardcoded instance of
`host: %%host%%`, `port: 6379`. When the Agent runs with the Docker listener
enabled and observes a container whose short image matches `redis`, it
substitutes the container's IP for `%%host%%` and schedules the check.

The existing E2E test (`redisdb/tests/test_e2e.py`) runs the check with an
explicit instance pointing at port 6382 in a 1-master/2-slave compose; it does
not exercise autodiscovery at all.

## Approach

Add a dedicated Hatch environment `py3.13-ad-7.0` that toggles a new
`REDIS_AUTODISCOVERY=true` env var. `conftest.py` branches on that var:

- When set, start a single vanilla `redis:7.0` container on the Docker bridge
  network, mount `/var/run/docker.sock` read-only into the Agent container,
  and yield `(None, e2e_metadata)` so no static `conf.yaml` is mounted. The
  Agent falls back purely to `auto_conf.yaml` + the Docker listener.
- When unset, the existing 1m-2s cluster behavior is preserved.

A new test file `tests/test_e2e_autodiscovery.py` is skipped in every
environment except `py3.13-ad-7.0`. It waits for the Agent to discover the
Redis container, runs the check, and asserts a minimal proof of autodiscovery
success.

This mirrors the SNMP integration's autodiscovery pattern
(`snmp/tests/conftest.py`, `snmp/tests/test_e2e_snmp_listener.py`).

## Changes

### 1. `redisdb/hatch.toml`

Add one matrix row + env-var overrides:

```toml
[[envs.default.matrix]]
python = ["3.13"]
version = ["ad-7.0"]

[envs.default.overrides]
matrix.version.env-vars = [
  # existing entries preserved …
  { key = "REDIS_VERSION", value = "7.0", if = ["ad-7.0"] },
  { key = "CLOUD_ENV", value = "false", if = ["ad-7.0"] },
  { key = "REDIS_AUTODISCOVERY", value = "true", if = ["ad-7.0"] },
]
```

Resulting env: `py3.13-ad-7.0`, invoked with the standard `ddev env
start|test|stop --dev redisdb py3.13-ad-7.0`.

### 2. `redisdb/tests/compose/autodiscovery-default.compose` (new)

```yaml
services:
  redis-default:
    image: "redis:${REDIS_VERSION}"
    networks:
      - network1
networks:
  network1:
    name: autodiscovery-default_default
```

No published ports: the Agent reaches Redis on its bridge IP and default port
`6379`. This matches the "working" case documented on the confluence page.

### 3. `redisdb/tests/common.py`

Add one constant:

```python
AUTODISCOVERY = is_affirmative(os.environ.get('REDIS_AUTODISCOVERY', 'false'))
```

### 4. `redisdb/tests/conftest.py`

`dd_environment` grows an autodiscovery branch. Sketch:

```python
@pytest.fixture(scope='session')
def dd_environment(master_instance):
    if AUTODISCOVERY:
        compose_file = os.path.join(HERE, 'compose', 'autodiscovery-default.compose')
        e2e_metadata = {
            'docker_volumes': ['/var/run/docker.sock:/var/run/docker.sock:ro'],
        }
        with docker_run(
            compose_file,
            conditions=[CheckDockerLogs(compose_file, 'Ready to accept connections')],
        ):
            yield None, e2e_metadata
        return

    # existing 1m-2s cluster path, unchanged
    with docker_run(DOCKER_COMPOSE_PATH, conditions=[CheckCluster(...)]):
        yield master_instance
```

The `yield None, e2e_metadata` tuple form means no static config file is
written, so the Agent is driven purely by `auto_conf.yaml` + the Docker
listener.

### 5. `redisdb/tests/test_e2e_autodiscovery.py` (new)

```python
import os

import pytest

from datadog_checks.dev import WaitFor, run_command
from datadog_checks.redisdb import Redis

from . import common

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not common.AUTODISCOVERY, reason='Requires REDIS_AUTODISCOVERY=true'),
]


@pytest.fixture
def autodiscovery_ready():
    WaitFor(_autodiscovery_ready, attempts=30, wait=2)()


def _autodiscovery_ready():
    env = os.environ['HATCH_ENV_ACTIVE']
    result = run_command(
        ['docker', 'exec', f'dd_redisdb_{env}', 'agent', 'configcheck'],
        capture=True, check=True,
    )
    assert 'redisdb' in result.stdout, result.stdout


def test_e2e_autodiscovery_default_port(dd_agent_check, autodiscovery_ready):
    aggregator = dd_agent_check(
        {'init_config': {}, 'instances': []},
        rate=True,
        discovery_min_instances=1,
        discovery_timeout=30,
    )
    service_checks = aggregator.service_checks('redis.can_connect')
    assert any(sc.status == Redis.OK and 'redis_port:6379' in sc.tags for sc in service_checks), service_checks
```

Assertion is deliberately minimal: one service check with `redis_port:6379`
and `status=OK`. `redis_host` resolves to the container's bridge IP, and the
Docker listener also emits `docker_image`, `image_id`, `image_name`,
`image_tag`, and `short_image` tags. `assert_service_check` requires the
`tags` argument to match the emitted tag list exactly, so we scan
`service_checks()` and assert that any submission with status OK contains
the `redis_port:6379` tag.

### 6. `redisdb/DEVELOPMENT.md`

Add a short note under "E2E Tests":

> The `py3.13-ad-7.0` environment exercises the Agent's container
> autodiscovery using the integration's `auto_conf.yaml`. It starts a single
> default-port Redis container and verifies the Agent discovers it via the
> Docker listener.

## Verification

Two independent signals both must pass:

1. `autodiscovery_ready` fixture: `docker exec dd_redisdb_<env> agent
   configcheck` output contains `redisdb` within 60s.
2. `dd_agent_check(..., discovery_min_instances=1, discovery_timeout=30)` runs
   the check, and the resulting aggregator shows `redis.can_connect` OK with
   `redis_port:6379`.

## Failure Modes

- Docker socket not mounted or wrong permissions → `autodiscovery_ready`
  times out; `agent configcheck` output is printed in the assertion message
  for diagnosis.
- Redis container unhealthy → `CheckDockerLogs` fails at compose startup
  before the Agent runs.
- Agent reaches the wrong IP for the container → `discovery_min_instances=1`
  succeeds (config was discovered) but `redis.can_connect` comes back
  CRITICAL, making the failure distinguishable from a pure discovery failure.

## Out of Scope (Follow-Ups)

Tracked against the [confluence page][confluence], to be addressed as separate
specs once upstream fixes land:

- Port-forwarded redis (host port ≠ container port) — tag-level assertions.
- Non-default in-container port — requires fixing `auto_conf.yaml` first (port
  is currently hardcoded to 6379).
- `--network=host` double-reporting case — same fix required.
- Process autodiscovery via `cel_selector`.
- Validating `docker_image` / `short_image` / `image_id` tags (confluence
  flagged an `image_id` inconsistency vs. the Containers product).
- Extending autodiscovery coverage to Redis 5.0 / 6.0 / 8.0.

## Risks

- `dd_agent_check` with empty `instances` + `discovery_min_instances` is used
  by SNMP and should behave identically for `redisdb`. Fallback if not: assert
  via `agent status --json` parsed through `docker exec`, matching the
  mechanism already used by `autodiscovery_ready`.
