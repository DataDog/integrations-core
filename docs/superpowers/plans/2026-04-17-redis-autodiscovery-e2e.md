# Redis Agent Autodiscovery E2E Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an end-to-end test under a new `py3.13-ad-7.0` Hatch environment that verifies the Datadog Agent autodiscovers a default-port Redis container via `auto_conf.yaml` and runs the `redisdb` check successfully.

**Architecture:** New Hatch matrix row toggles `REDIS_AUTODISCOVERY=true`. `conftest.py` branches on that env var: under autodiscovery it starts a single vanilla `redis:7.0` container (no published ports, Docker bridge network), mounts `/var/run/docker.sock` read-only into the Agent, and yields `(None, e2e_metadata)` so no static `conf.yaml` is mounted. A dedicated test file waits for the Agent to discover the container via `agent configcheck`, then invokes `dd_agent_check` with `discovery_min_instances=1` and asserts `redis.can_connect` OK with `redis_port:6379`.

**Tech Stack:** Hatch, Docker Compose, pytest, `datadog_checks.dev` (docker_run, WaitFor, run_command), the `dd_agent_check` pytest fixture.

**Spec:** `docs/superpowers/specs/2026-04-17-redis-autodiscovery-e2e-design.md`.

---

## File Structure

Files this plan creates or modifies:

- **Create** `redisdb/tests/compose/autodiscovery-default.compose` — Compose file running a single `redis:${REDIS_VERSION}` container on a user-defined bridge network, no published ports.
- **Create** `redisdb/tests/test_e2e_autodiscovery.py` — Marked `@pytest.mark.e2e`, skipped unless `REDIS_AUTODISCOVERY=true`. Holds the `autodiscovery_ready` fixture and the single test function.
- **Modify** `redisdb/hatch.toml` — Adds a `version = ["ad-7.0"]` matrix row and env-var overrides.
- **Modify** `redisdb/tests/common.py` — Adds `AUTODISCOVERY` constant read from env.
- **Modify** `redisdb/tests/conftest.py` — Branches `dd_environment` on `AUTODISCOVERY`.
- **Modify** `redisdb/DEVELOPMENT.md` — Documents the new env under "E2E Tests".

Each file has one responsibility; nothing else in the repo changes.

---

## Task 1: Add the Hatch env row

**Files:**
- Modify: `redisdb/hatch.toml`

- [ ] **Step 1: Read the current file**

Current content of `redisdb/hatch.toml`:

```toml
[env.collectors.datadog-checks]

[[envs.default.matrix]]
python = ["3.13"]
version = ["5.0", "6.0", "7.0", "8.0", "cloud"]

[envs.default.overrides]
matrix.version.env-vars = [
  { key = "REDIS_VERSION", if = ["5.0", "6.0", "7.0", "8.0"] },
  { key = "CLOUD_ENV", value = "false", if = ["5.0", "6.0", "7.0", "8.0"] },
  { key = "REDIS_VERSION", value="7.0", if = ["cloud"] },
  { key = "CLOUD_ENV", value = "true", if = ["cloud"] },
]

[envs.latest.env-vars]
CLOUD_ENV = "false"
REDIS_VERSION = "latest"
```

- [ ] **Step 2: Add the `ad-7.0` version**

Edit the existing `version` line in `[[envs.default.matrix]]` to append `"ad-7.0"`, and add three env-var override entries for the new version. The resulting file must be:

```toml
[env.collectors.datadog-checks]

[[envs.default.matrix]]
python = ["3.13"]
version = ["5.0", "6.0", "7.0", "8.0", "cloud", "ad-7.0"]

[envs.default.overrides]
matrix.version.env-vars = [
  { key = "REDIS_VERSION", if = ["5.0", "6.0", "7.0", "8.0"] },
  { key = "CLOUD_ENV", value = "false", if = ["5.0", "6.0", "7.0", "8.0"] },
  { key = "REDIS_VERSION", value="7.0", if = ["cloud"] },
  { key = "CLOUD_ENV", value = "true", if = ["cloud"] },
  { key = "REDIS_VERSION", value = "7.0", if = ["ad-7.0"] },
  { key = "CLOUD_ENV", value = "false", if = ["ad-7.0"] },
  { key = "REDIS_AUTODISCOVERY", value = "true", if = ["ad-7.0"] },
]

[envs.latest.env-vars]
CLOUD_ENV = "false"
REDIS_VERSION = "latest"
```

- [ ] **Step 3: Verify the env is discoverable**

Run: `ddev env show redisdb`
Expected: the output lists `py3.13-ad-7.0` alongside the existing `py3.13-5.0`, `py3.13-6.0`, `py3.13-7.0`, `py3.13-8.0`, `py3.13-cloud`.

- [ ] **Step 4: Commit**

```bash
git add redisdb/hatch.toml
git commit -m "[redisdb] Add ad-7.0 hatch env for autodiscovery e2e"
```

---

## Task 2: Add the compose file for the autodiscovery target

**Files:**
- Create: `redisdb/tests/compose/autodiscovery-default.compose`

- [ ] **Step 1: Create the compose file**

Write `redisdb/tests/compose/autodiscovery-default.compose` with exactly this content:

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

Notes:
- No `ports:` mapping — the Agent reaches Redis on its bridge IP + container port 6379. This matches the known-working autodiscovery case from the DSCVR Confluence exploration.
- No `command:` override — the image's default entrypoint binds port 6379.
- The `networks.network1.name` mirrors the pattern used by `1m-2s.compose`, which sets an explicit external name for the project's default network.

- [ ] **Step 2: Sanity-check the compose syntax**

Run (from repo root):

```bash
REDIS_VERSION=7.0 docker compose -f redisdb/tests/compose/autodiscovery-default.compose config
```

Expected: the command prints a resolved compose config without errors and references `image: redis:7.0`.

- [ ] **Step 3: Commit**

```bash
git add redisdb/tests/compose/autodiscovery-default.compose
git commit -m "[redisdb] Add autodiscovery-default compose for e2e"
```

---

## Task 3: Add the `AUTODISCOVERY` flag to `common.py`

**Files:**
- Modify: `redisdb/tests/common.py`

- [ ] **Step 1: Read the current file**

Current content is:

```python
# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.base import is_affirmative
from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))

PORT = '6379'
PASSWORD = 'devops-best-friend'
MASTER_PORT = '6382'
REPLICA_PORT = '6380'
UNHEALTHY_REPLICA_PORT = '6381'
HOST = get_docker_hostname()
REDIS_VERSION = os.getenv('REDIS_VERSION', 'latest')
CLOUD_ENV = is_affirmative(os.environ['CLOUD_ENV'])

if CLOUD_ENV:
    DOCKER_COMPOSE_PATH = os.path.join(HERE, 'compose', '1m-2s-cloud.compose')
else:
    DOCKER_COMPOSE_PATH = os.path.join(HERE, 'compose', '1m-2s.compose')
```

- [ ] **Step 2: Add the `AUTODISCOVERY` constant**

Insert a new line after the `CLOUD_ENV` definition. The final file must be:

```python
# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.base import is_affirmative
from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))

PORT = '6379'
PASSWORD = 'devops-best-friend'
MASTER_PORT = '6382'
REPLICA_PORT = '6380'
UNHEALTHY_REPLICA_PORT = '6381'
HOST = get_docker_hostname()
REDIS_VERSION = os.getenv('REDIS_VERSION', 'latest')
CLOUD_ENV = is_affirmative(os.environ['CLOUD_ENV'])
AUTODISCOVERY = is_affirmative(os.environ.get('REDIS_AUTODISCOVERY', 'false'))

if CLOUD_ENV:
    DOCKER_COMPOSE_PATH = os.path.join(HERE, 'compose', '1m-2s-cloud.compose')
else:
    DOCKER_COMPOSE_PATH = os.path.join(HERE, 'compose', '1m-2s.compose')

AUTODISCOVERY_COMPOSE_PATH = os.path.join(HERE, 'compose', 'autodiscovery-default.compose')
```

Rationale for both constants: `AUTODISCOVERY` is the branch toggle; `AUTODISCOVERY_COMPOSE_PATH` keeps the path in one place consistent with how `DOCKER_COMPOSE_PATH` is defined.

- [ ] **Step 3: Run the existing unit tests to confirm nothing breaks**

Run: `ddev --no-interactive test redisdb -- -k "not e2e" tests/test_unit.py -x`
Expected: tests pass (the new constants are not imported anywhere yet but must not break existing imports of `common.py`).

If `ddev` is unavailable in the execution environment, skip this step and rely on Task 6's full run. Do not continue past Task 5 without running the real test once.

---

## Task 4: Branch `dd_environment` in `conftest.py`

**Files:**
- Modify: `redisdb/tests/conftest.py`

- [ ] **Step 1: Read the current file**

Current content of `redisdb/tests/conftest.py`:

```python
# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import time

import pytest
import redis

from datadog_checks.dev import LazyFunction, RetryError, docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.redisdb import Redis

from .common import DOCKER_COMPOSE_PATH, HERE, HOST, MASTER_PORT, PASSWORD, PORT, REPLICA_PORT


class CheckCluster(LazyFunction):
    ...  # existing class body — unchanged


@pytest.fixture(scope='session')
def redis_auth():
    ...  # existing body — unchanged


@pytest.fixture(scope='session')
def dd_environment(master_instance):
    """
    Start a cluster with one master, one replica, and one unhealthy replica.
    """
    with docker_run(
        DOCKER_COMPOSE_PATH,
        conditions=[
            CheckCluster({'port': MASTER_PORT, 'db': 14, 'host': HOST}, {'port': REPLICA_PORT, 'db': 14, 'host': HOST})
        ],
    ):
        yield master_instance


@pytest.fixture
def redis_instance():
    ...  # existing body — unchanged


@pytest.fixture
def replica_instance():
    ...  # existing body — unchanged


@pytest.fixture(scope='session')
def master_instance():
    ...  # existing body — unchanged


@pytest.fixture(scope='session')
def check():
    ...  # existing body — unchanged
```

- [ ] **Step 2: Add the autodiscovery branch**

Two edits are needed:

**Edit A** — extend the import line for `common` to pull in the new constants. Replace the existing import:

```python
from .common import DOCKER_COMPOSE_PATH, HERE, HOST, MASTER_PORT, PASSWORD, PORT, REPLICA_PORT
```

with:

```python
from .common import (
    AUTODISCOVERY,
    AUTODISCOVERY_COMPOSE_PATH,
    DOCKER_COMPOSE_PATH,
    HERE,
    HOST,
    MASTER_PORT,
    PASSWORD,
    PORT,
    REPLICA_PORT,
)
```

**Edit B** — replace the existing `dd_environment` fixture body with the branched version. The final fixture must be:

```python
@pytest.fixture(scope='session')
def dd_environment(master_instance):
    """
    Start the Redis test environment.

    In autodiscovery mode (`REDIS_AUTODISCOVERY=true`) run a single default-port
    Redis container on the Docker bridge network and hand the Agent the Docker
    socket so it can discover the container via the Docker listener. No static
    instance config is yielded so the Agent relies purely on `auto_conf.yaml`.

    Otherwise run the 1-master/2-replica cluster used by the existing e2e
    tests.
    """
    if AUTODISCOVERY:
        e2e_metadata = {
            'docker_volumes': ['/var/run/docker.sock:/var/run/docker.sock:ro'],
        }
        with docker_run(
            AUTODISCOVERY_COMPOSE_PATH,
            conditions=[CheckDockerLogs(AUTODISCOVERY_COMPOSE_PATH, 'Ready to accept connections', wait=5)],
        ):
            yield None, e2e_metadata
        return

    with docker_run(
        DOCKER_COMPOSE_PATH,
        conditions=[
            CheckCluster({'port': MASTER_PORT, 'db': 14, 'host': HOST}, {'port': REPLICA_PORT, 'db': 14, 'host': HOST})
        ],
    ):
        yield master_instance
```

Notes on this fixture body:
- The autodiscovery branch `yield None, e2e_metadata` is a tuple; the `dd_environment_runner` in `datadog_checks.dev`'s pytest plugin already handles the tuple form (see SNMP precedent at `snmp/tests/conftest.py:50-78`). `None` as the instance config means no `conf.yaml` file is mounted into the Agent container.
- `/var/run/docker.sock:/var/run/docker.sock:ro` mounts the host Docker socket read-only; the Agent's Docker listener uses it to enumerate running containers.
- The `return` after the `yield None, e2e_metadata` block is important — without it execution would fall through to the cluster setup.
- `CheckDockerLogs(AUTODISCOVERY_COMPOSE_PATH, ...)` matches the pattern already used by `redis_auth` (`conftest.py:59-65`).

- [ ] **Step 3: Run the existing non-autodiscovery e2e once to confirm no regression**

Run:

```bash
ddev env start --dev redisdb py3.13-7.0
ddev env test --dev redisdb py3.13-7.0
ddev env stop redisdb py3.13-7.0
```

Expected: existing e2e passes as before. This proves the refactored `dd_environment` still works when `REDIS_AUTODISCOVERY` is unset.

If Docker or `ddev env` isn't available in the current execution environment, skip this step; Task 6 will exercise the autodiscovery path, which is the new behavior under test. Mention the skipped verification when handing the plan back to the user.

- [ ] **Step 4: Commit**

```bash
git add redisdb/tests/common.py redisdb/tests/conftest.py redisdb/tests/compose/autodiscovery-default.compose
git commit -m "[redisdb] Branch dd_environment for autodiscovery"
```

Note: this commit bundles Task 2 (compose) + Task 3 (common.py) + Task 4 (conftest.py) because they are a single cohesive change — the compose file is unused until `conftest.py` references it, and the `AUTODISCOVERY` constant is unused until `conftest.py` reads it. If Task 2 and Task 3 were already committed per their own `git commit` steps, skip them here and only commit `redisdb/tests/conftest.py`.

---

## Task 5: Add the autodiscovery test file

**Files:**
- Create: `redisdb/tests/test_e2e_autodiscovery.py`

- [ ] **Step 1: Write the test file**

Write `redisdb/tests/test_e2e_autodiscovery.py` with exactly this content:

```python
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import pytest

from datadog_checks.dev import WaitFor, run_command
from datadog_checks.redisdb import Redis

from . import common

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not common.AUTODISCOVERY, reason='Requires REDIS_AUTODISCOVERY=true'),
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


def test_e2e_autodiscovery_default_port(dd_agent_check, autodiscovery_ready):
    aggregator = dd_agent_check(
        {'init_config': {}, 'instances': []},
        rate=True,
        discovery_min_instances=1,
        discovery_timeout=30,
    )
    aggregator.assert_service_check(
        'redis.can_connect',
        status=Redis.OK,
        tags=['redis_port:6379'],
        at_least=1,
    )
```

Notes:
- `pytestmark` applies both `e2e` (so unit runs exclude it) and `skipif` (so non-autodiscovery envs skip it cleanly).
- `HATCH_ENV_ACTIVE` is exported by Hatch/`ddev env` to the pytest process; its value is the env name without the `py3.13-` prefix (e.g. `ad-7.0`). The Agent container that `DockerAgent` starts is named `dd_<check>_<env>` (`ddev/src/ddev/e2e/agent/docker.py:97-98`), so `dd_redisdb_ad-7.0` is the right name.
- `WaitFor(attempts=30, wait=2)` gives up to 60 seconds for the Agent to discover the container.
- `dd_agent_check({'init_config': {}, 'instances': []}, ...)` provides an empty instance config; combined with `discovery_min_instances=1` and `discovery_timeout=30` the Agent waits for one autodiscovered instance before running. This mirrors `snmp/tests/test_e2e_snmp_listener.py:46-52`.
- `at_least=1` on the service-check assertion avoids asserting on the exact count (two sampling ticks are typical under `rate=True`, but we don't pin that number because the bridge-IP-derived `redis_host` tag already introduces variance the test doesn't care about).

- [ ] **Step 2: Commit**

```bash
git add redisdb/tests/test_e2e_autodiscovery.py
git commit -m "[redisdb] Add autodiscovery e2e test"
```

---

## Task 6: Run the autodiscovery e2e end-to-end

**Files:** none modified; this task verifies the pieces work together.

- [ ] **Step 1: Start the environment**

Run: `ddev env start --dev redisdb py3.13-ad-7.0`

Expected: `ddev` starts the `redis-default` compose container, pulls the Agent image if needed, starts `dd_redisdb_ad-7.0` with the docker socket mounted. The command completes without errors.

If it fails, inspect:
- `docker ps -a` for the container states,
- `docker logs dd_redisdb_ad-7.0` for Agent startup errors,
- `docker logs autodiscovery-default_default_redis-default_1` (or similar) for Redis startup errors.

- [ ] **Step 2: Manually confirm autodiscovery fired (one-off diagnostic)**

Run: `docker exec dd_redisdb_ad-7.0 agent configcheck | grep -A 5 redisdb`
Expected: the output shows a `redisdb` check source (`container` or `docker`) with an instance whose `host:` is a bridge IP (e.g. `172.17.0.x` or `172.18.0.x`) and `port: 6379`. If this is empty, the test cannot pass — debug the Docker listener before running tests.

- [ ] **Step 3: Run the autodiscovery test**

Run: `ddev env test --dev redisdb py3.13-ad-7.0`

Expected: `test_e2e_autodiscovery_default_port` passes. All other test files (`test_e2e.py`, `test_default.py`, `test_auth.py`, etc.) either skip under this env (because their fixtures don't apply) or pass.

If tests unrelated to autodiscovery fail because they expected the 1m-2s cluster, mark them with an explicit skip under `common.AUTODISCOVERY` (preferred) rather than changing their logic. Add that skip in a follow-up commit.

- [ ] **Step 4: Stop the environment**

Run: `ddev env stop redisdb py3.13-ad-7.0`
Expected: containers and network are removed.

- [ ] **Step 5: Commit any follow-up skips or fixture patches discovered during Step 3**

If Step 3 required additional skip markers, commit them now:

```bash
git add redisdb/tests/<file>
git commit -m "[redisdb] Skip non-autodiscovery e2e under ad-7.0 env"
```

If Step 3 passed without additional work, this step is a no-op.

---

## Task 7: Update `DEVELOPMENT.md`

**Files:**
- Modify: `redisdb/DEVELOPMENT.md`

- [ ] **Step 1: Append an autodiscovery subsection**

At the end of `redisdb/DEVELOPMENT.md` (after the existing "### Notes" block), append:

```markdown

### Agent Autodiscovery E2E

The `py3.13-ad-7.0` environment exercises the Agent's container autodiscovery using
the integration's `auto_conf.yaml`. It starts a single default-port Redis container on the
Docker bridge network, mounts the host Docker socket into the Agent container, and verifies
the Agent discovers the container via the Docker listener.

```shell
ddev env start --dev redisdb py3.13-ad-7.0
ddev env test  --dev redisdb py3.13-ad-7.0
ddev env stop  redisdb py3.13-ad-7.0
```

Only the default-port bridge-network case is covered today. Other cases (port-forwarded,
non-default in-container port, `--network=host`, process autodiscovery) are tracked in the
DSCVR "Integrations autodiscovery exploration" Confluence page and will be added as the
associated upstream issues are fixed.
```

- [ ] **Step 2: Commit**

```bash
git add redisdb/DEVELOPMENT.md
git commit -m "[redisdb] Document autodiscovery e2e env"
```

---

## Self-Review

- **Spec coverage:**
  - Hatch env `py3.13-ad-7.0` → Task 1.
  - Compose file `autodiscovery-default.compose` → Task 2.
  - `AUTODISCOVERY` flag in `common.py` → Task 3.
  - `dd_environment` branch → Task 4.
  - Test file with `autodiscovery_ready` + `discovery_min_instances` + `can_connect` assertion → Task 5.
  - `DEVELOPMENT.md` note → Task 7.
  - End-to-end verification → Task 6.
  - Failure-mode diagnostics (configcheck, logs) → Task 6 Step 1 and Step 2.
  - Out-of-scope items are named in Task 7's docs block, matching the spec.

- **Placeholder scan:** No TBD/TODO/placeholder prose; each code step contains the exact final code. The only `...` fragments are in Task 4 Step 1, where they mark *existing* fixture bodies that must be preserved verbatim (clearly called out as "existing body — unchanged").

- **Type consistency:** `AUTODISCOVERY` and `AUTODISCOVERY_COMPOSE_PATH` are defined in Task 3 and consumed in Task 4 with matching names. `_agent_container_name()`, `_autodiscovery_ready()`, and `autodiscovery_ready` in Task 5 are internally consistent. Fixture names `dd_agent_check` and `autodiscovery_ready` match how the test consumes them.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-17-redis-autodiscovery-e2e.md`.

Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
