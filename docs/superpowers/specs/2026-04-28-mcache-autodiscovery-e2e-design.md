# Memcached Agent Autodiscovery E2E Test — Design

## Goal

Add an end-to-end test that verifies the Datadog Agent's container
autodiscovery correctly schedules and runs the `mcache` check against a
Memcached container using the integration's shipped `auto_conf.yaml`.

This is the second integration to gain autodiscovery e2e coverage, after
[redisdb][redis-spec]. The motivation is twofold: extend coverage to a second
real check, and surface what duplicates between the two so we know what to
extract into shared helpers in the next phase.

This spec covers **mcache only**. Helper extraction and a third integration
(apache) are tracked in their own subsequent specs.

[redis-spec]: 2026-04-17-redis-autodiscovery-e2e-design.md

## Background

`mcache/datadog_checks/mcache/data/auto_conf.yaml` declares
`ad_identifiers: [memcached]` with a hardcoded instance of
`url: %%host%%`, `port: 11211`. When the Agent runs with the Docker listener
enabled and observes a container whose short image matches `memcached`, it
substitutes the container's IP for `%%host%%` and schedules the check.

The existing e2e test (`mcache/tests/test_integration_e2e.py::test_e2e`) runs
the check with an explicit instance pointing at port 11211 of a SASL-enabled
custom image (`datadog/docker-library:memcached_SASL`); it does not exercise
autodiscovery at all, and its image's short name (`docker-library`) would not
match `ad_identifiers: [memcached]` anyway.

The redisdb autodiscovery work landed a generic ddev fix in
`ddev/src/ddev/e2e/agent/docker.py` that file-bind-mounts the integration's
shipped `auto_conf.yaml` over the agent image's bundled copy when no static
config is provided. mcache benefits from that fix automatically.

## Approach

Mirror the redisdb pattern with the minimal mcache-specific deltas. Add a
dedicated Hatch environment `py3.13-ad-1.6` that toggles a new
`MCACHE_AUTODISCOVERY=true` env var. `conftest.py` branches on that var:

- When set, start a single vanilla `memcached:1.6` container on the Docker
  bridge network, mount `/var/run/docker.sock` read-only into the Agent
  container, and yield `(None, e2e_metadata)` so no static `conf.yaml` is
  mounted. The Agent falls back purely to `auto_conf.yaml` + the Docker
  listener.
- When unset, the existing SASL/IPv6/socket multi-container path is preserved.

A new test file `tests/test_e2e_autodiscovery.py` is skipped in every
environment except `py3.13-ad-1.6`. It waits for the Agent to discover the
Memcached container, runs the check, and asserts a minimal proof of
autodiscovery success.

The version pin (`memcached:1.6`) is hardcoded in the new compose. The
existing `docker-compose.yaml` pins a different image
(`datadog/docker-library:memcached_SASL`) that is not interchangeable —
autodiscovery requires a vanilla image whose short name is `memcached` so the
Docker listener matches `ad_identifiers: [memcached]`.

## Changes

### 1. `mcache/hatch.toml`

mcache currently has no `version` axis — its matrix is just
`python = ["3.13"]`, producing a single env named `py3.13`. Adding
`version = ["ad-1.6"]` to that single matrix block would *replace* the
version-less env with `py3.13-ad-1.6`, breaking every existing call to
`ddev env start mcache py3.13` and `ddev test mcache`. Instead, add a second
matrix block so both envs coexist:

```toml
[env.collectors.datadog-checks]

[[envs.default.matrix]]
python = ["3.13"]

[[envs.default.matrix]]
python = ["3.13"]
version = ["ad-1.6"]

[envs.default.env-vars]
DDEV_SKIP_GENERIC_TAGS_CHECK = "true"

[envs.default.overrides]
matrix.version.env-vars = [
  { key = "MCACHE_VERSION", value = "1.6", if = ["ad-1.6"] },
  { key = "MCACHE_AUTODISCOVERY", value = "true", if = ["ad-1.6"] },
]
```

Resulting envs: `py3.13` (existing, unchanged) and `py3.13-ad-1.6` (new).
Invoke the new one with the standard `ddev env start|test|stop --dev mcache
py3.13-ad-1.6`. Verify after the change that `ddev env show mcache` lists
both envs and that `ddev test mcache` still resolves to `py3.13`.

### 2. `mcache/tests/compose/autodiscovery-default.compose` (new)

```yaml
services:
  memcached-default:
    image: "memcached:${MCACHE_VERSION}"
    networks:
      - network1
networks:
  network1:
    name: autodiscovery-default_default
```

No published ports: the Agent reaches Memcached on its bridge IP and default
port `11211`. This matches the working "default-port, bridge network" case
documented on the [Integrations autodiscovery exploration][confluence] page.

[confluence]: https://datadoghq.atlassian.net/wiki/spaces/DSCVR/pages/6568739159/Integrations+autodiscovery+exploration

### 3. `mcache/tests/common.py`

Add one constant alongside the existing ones:

```python
from datadog_checks.dev.utils import is_affirmative

AUTODISCOVERY = is_affirmative(os.environ.get('MCACHE_AUTODISCOVERY', 'false'))
```

### 4. `mcache/tests/conftest.py`

`dd_environment` grows an autodiscovery branch at the top. Sketch:

```python
@pytest.fixture(scope='session')
def dd_environment(e2e_instance):
    if AUTODISCOVERY:
        compose_file = os.path.join(HERE, 'compose', 'autodiscovery-default.compose')
        e2e_metadata = {
            'docker_volumes': ['/var/run/docker.sock:/var/run/docker.sock:ro'],
        }
        with docker_run(
            compose_file,
            conditions=[CheckDockerLogs(compose_file, 'server listening')],
        ):
            yield None, e2e_metadata
        return

    # existing SASL + IPv6 + socket path, unchanged
    with docker_run(...):
        ...
```

The `yield None, e2e_metadata` tuple form means no static config file is
written, so the Agent is driven purely by `auto_conf.yaml` + the Docker
listener. The `e2e_instance` fixture is still passed in (pytest needs the
parameter resolved) but unused on the autodiscovery branch.

The `CheckDockerLogs` line `'server listening'` is what `memcached:1.6`
emits at startup. Verify empirically when implementing; if the version is
silent, fall back to a TCP probe via `WaitFor` connecting to the bridge IP
on port 11211.

### 5. `mcache/tests/test_integration_e2e.py`

Add a skipif to the existing `test_e2e`:

```python
@pytest.mark.e2e
@pytest.mark.skipif(common.AUTODISCOVERY, reason='Existing e2e is not run in the autodiscovery env')
def test_e2e(client, dd_agent_check, instance):
    ...
```

Required because the existing `test_e2e` depends on SASL credentials and a
published-port memcached on the host, both of which are absent under the
autodiscovery env.

### 6. `mcache/tests/test_e2e_autodiscovery.py` (new)

```python
import os

import pytest

from datadog_checks.dev import WaitFor, run_command
from datadog_checks.mcache import Memcache

from . import common

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not common.AUTODISCOVERY, reason='Requires MCACHE_AUTODISCOVERY=true'),
]


def _agent_container_name():
    env = os.environ['HATCH_ENV_ACTIVE']
    return f'dd_mcache_{env}'


def _autodiscovery_ready():
    result = run_command(
        ['docker', 'exec', _agent_container_name(), 'agent', 'configcheck'],
        capture=True,
        check=True,
    )
    assert 'mcache' in result.stdout, result.stdout


@pytest.fixture
def autodiscovery_ready():
    WaitFor(_autodiscovery_ready, attempts=30, wait=2)()


def test_e2e_autodiscovery_default_port(dd_agent_check, autodiscovery_ready):
    aggregator = dd_agent_check(
        {'init_config': {}, 'instances': []},
        rate=True,
        discovery_min_instances=1,
        discovery_timeout=30,
    )
    service_checks = aggregator.service_checks('memcache.can_connect')
    assert any(sc.status == Memcache.OK and 'port:11211' in sc.tags for sc in service_checks), service_checks
```

Assertion is deliberately minimal: one service check with `port:11211` and
`status=OK`. The Docker listener also emits `docker_image`, `image_id`,
`image_name`, `image_tag`, and `short_image` tags, plus the check's own
`host:` tag resolved to the container's bridge IP. `assert_service_check`
requires the `tags` argument to match the emitted tag list exactly, so we
scan `service_checks()` and assert any submission with status OK contains
`port:11211`.

The configcheck identifier (`mcache`) needs empirical confirmation when the
test first runs against a live agent — the integration's package name is
`mcache` but the check class is `Memcache`. If `agent configcheck` prints
the latter, update the assertion.

### 7. `mcache/DEVELOPMENT.md` (new)

Mirror `redisdb/DEVELOPMENT.md`: prerequisites (ddev install, Python 3.13 via
pyenv), unit/integration test commands, e2e environment listing, the
autodiscovery section explaining the `py3.13-ad-1.6` env and what it does,
and the bind-mount inode caveat (editing `auto_conf.yaml` between runs
requires `ddev env stop` + `ddev env start` because `git checkout` replaces
the file's inode).

The new file follows the same structure as the redis one. No cross-linking
between them — each integration's docs stand alone.

## Verification

Two independent signals both must pass:

1. `autodiscovery_ready` fixture: `docker exec dd_mcache_<env> agent
   configcheck` output contains `mcache` within 60s.
2. `dd_agent_check(..., discovery_min_instances=1, discovery_timeout=30)`
   runs the check, and the resulting aggregator shows `memcache.can_connect`
   OK with `port:11211`.

After implementation, repeat the redisdb two-direction sanity check:

1. With `ad_identifiers: [memcached]` in
   `mcache/datadog_checks/mcache/data/auto_conf.yaml`, the test passes.
2. With `ad_identifiers: [memcachedfoo]`, `autodiscovery_ready` times out
   and the test fails. This confirms the test exercises the source-tree
   `auto_conf.yaml`, not the agent image's bundled copy. Restore the file
   with `git checkout` and `ddev env stop` + `ddev env start` before any
   subsequent run.

## Failure Modes

- Docker socket not mounted or wrong permissions → `autodiscovery_ready`
  times out; `agent configcheck` output is printed in the assertion message
  for diagnosis.
- Memcached container unhealthy → `CheckDockerLogs` fails at compose startup
  before the Agent runs.
- Agent reaches the wrong IP for the container → `discovery_min_instances=1`
  succeeds (config was discovered) but `memcache.can_connect` comes back
  CRITICAL, making the failure distinguishable from a pure discovery failure.
- `memcached:1.6` does not emit `server listening` at startup → the compose
  startup probe times out; switch to a TCP-level `WaitFor` against port 11211
  on the bridge IP.
- `agent configcheck` prints `memcache` instead of `mcache` → update the
  assertion in `_autodiscovery_ready` to match. Empirically verify on first
  implementation.

## Out of Scope

Tracked against the [confluence page][confluence], to be addressed later:

- Port-forwarded memcached (host port ≠ container port).
- Non-default in-container port — requires fixing `auto_conf.yaml` first
  (port is currently hardcoded to 11211).
- `--network=host` double-reporting case.
- Process autodiscovery via `cel_selector`.
- Validating `docker_image` / `short_image` / `image_id` tags.
- Multi-version coverage (1.5, 1.6, 1.7, latest).
- SASL-authenticated autodiscovery (the shipped `auto_conf.yaml` has no
  `username`/`password` template variables, so SASL autodiscovery is its
  own design problem).

Helper extraction across redisdb and mcache is the subject of the next
spec, not this one.

## Risks

- `dd_agent_check` with empty `instances` + `discovery_min_instances` is
  used by SNMP and now redisdb and should behave identically for `mcache`.
  Fallback if not: assert via `agent status --json` parsed through `docker
  exec`, matching the mechanism already used by `autodiscovery_ready`.
- Two `[[envs.default.matrix]]` blocks is a less common Hatch pattern than
  a single block. Verify after the change that `ddev env show mcache` lists
  both `py3.13` (existing) and `py3.13-ad-1.6` (new), and that
  `MCACHE_AUTODISCOVERY` is set only on the latter. If the pattern doesn't
  produce the expected envs, fall back to a single matrix block with
  `version = ["default", "ad-1.6"]`, accepting the rename of the existing
  env from `py3.13` to `py3.13-default` and updating any callers.
