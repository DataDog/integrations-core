# Memcached Autodiscovery E2E Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an end-to-end test that verifies the Datadog Agent's container autodiscovery correctly schedules and runs the `mcache` check against a vanilla `memcached:1.6` container using the integration's shipped `auto_conf.yaml`.

**Architecture:** Mirror the redisdb autodiscovery e2e pattern (spec: `docs/superpowers/specs/2026-04-17-redis-autodiscovery-e2e-design.md`). Add a dedicated Hatch env `py3.13-ad-1.6` toggled by `MCACHE_AUTODISCOVERY=true`. `dd_environment` branches on that var: when set, runs a single vanilla `memcached:1.6` container on the Docker bridge network, mounts the host Docker socket into the agent, and yields `(None, e2e_metadata)` so the agent runs purely off `auto_conf.yaml` + the Docker listener. A new test file waits for `agent configcheck` to surface the integration, runs the check via `dd_agent_check(..., discovery_min_instances=1)`, and asserts a `memcache.can_connect` service check with `port:11211` came back OK.

**Tech Stack:** Python 3.13, pytest, Hatch, Docker, ddev, datadog-checks-base, bmemcached.

**Spec:** `docs/superpowers/specs/2026-04-28-mcache-autodiscovery-e2e-design.md`.

---

## Pre-Flight: Environment Setup

Before starting Task 1, verify the following are in place. The redisdb autodiscovery work already landed all of them:

- [ ] **Step P1: Verify ddev is installed editable from the local repo**

Run: `pip show ddev | grep -E '^(Version|Location):'`

Expected: `Location: /home/bits/go/src/github.com/DataDog/integrations-core/ddev/src` (or similar editable install pointing at this repo). Version should end with `.devN`.

If not, install editable: `pip install -e /home/bits/go/src/github.com/DataDog/integrations-core/ddev`.

- [ ] **Step P2: Verify ddev points at this repo**

Run: `ddev config show | grep -A1 'repos'`

Expected: `core = "/home/bits/go/src/github.com/DataDog/integrations-core"` (or whatever the absolute repo path is).

If not: `ddev config set repos.core /home/bits/go/src/github.com/DataDog/integrations-core`.

- [ ] **Step P3: Verify pyenv has Python 3.13**

Run: `pyenv versions | grep 3.13`

Expected: a line containing `3.13`.

If not: `curl https://pyenv.run | bash` (one-time), then `pyenv install 3.13`.

- [ ] **Step P4: Verify the ddev autodiscovery fix is in place**

Run: `grep -n "auto_conf.yaml" /home/bits/go/src/github.com/DataDog/integrations-core/ddev/src/ddev/e2e/agent/docker.py`

Expected: at least one match showing the file-bind-mount of `auto_conf` from `self.integration.package_directory / 'data' / 'auto_conf.yaml'`. This was landed in commit `e16a94c72a` ([ddev] Mount integration's own auto_conf.yaml when no static config). Without it, the agent reads its bundled `auto_conf.yaml` instead of the source-tree one and the test would be a false positive.

If missing, the redisdb autodiscovery work was reverted and this plan cannot proceed.

---

## Task 1: Hatch Environment

**Files:**
- Modify: `mcache/hatch.toml`

The current file has only one matrix block (`python = ["3.13"]`, no version axis). Replacing that block to add `version = ["ad-1.6"]` would *replace* the existing version-less env. We need both: keep `py3.13` for existing tests, add `py3.13-ad-1.6` for autodiscovery. Two `[[envs.default.matrix]]` blocks coexist as separate cartesian products.

- [ ] **Step 1: Read current hatch.toml**

Run: `cat /home/bits/go/src/github.com/DataDog/integrations-core/mcache/hatch.toml`

Expected:
```toml
[env.collectors.datadog-checks]

[[envs.default.matrix]]
python = ["3.13"]

[envs.default.env-vars]
DDEV_SKIP_GENERIC_TAGS_CHECK = "true"
```

- [ ] **Step 2: Replace the file with the autodiscovery-aware version**

Write `mcache/hatch.toml`:

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

- [ ] **Step 3: Verify both envs are listed**

Run: `PATH="$HOME/.pyenv/shims:$HOME/.pyenv/bin:$PATH" ddev env show mcache`

Expected: output lists both `py3.13` and `py3.13-ad-1.6`. If only one appears, hatch did not honor the second matrix block — fall back to the alternative documented in the spec's Risks section (single matrix with `version = ["default", "ad-1.6"]`, accepting the rename of `py3.13` → `py3.13-default`).

- [ ] **Step 4: Commit**

```bash
cd /home/bits/go/src/github.com/DataDog/integrations-core
git add mcache/hatch.toml
git commit -m "[mcache] Add py3.13-ad-1.6 hatch env for autodiscovery e2e"
```

---

## Task 2: Compose File

**Files:**
- Create: `mcache/tests/compose/autodiscovery-default.compose`

A minimal compose file that runs vanilla `memcached:${MCACHE_VERSION}` on a named bridge network with no published ports. The agent will reach the container by its bridge IP on port 11211. The image's short name (`memcached`) matches the `ad_identifiers: [memcached]` in the integration's `auto_conf.yaml`.

- [ ] **Step 1: Create the compose file**

Write `mcache/tests/compose/autodiscovery-default.compose`:

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

- [ ] **Step 2: Verify the file parses**

Run: `MCACHE_VERSION=1.6 docker compose -f /home/bits/go/src/github.com/DataDog/integrations-core/mcache/tests/compose/autodiscovery-default.compose config`

Expected: docker compose echoes back the resolved config with `image: memcached:1.6`. No errors.

- [ ] **Step 3: Commit**

```bash
cd /home/bits/go/src/github.com/DataDog/integrations-core
git add mcache/tests/compose/autodiscovery-default.compose
git commit -m "[mcache] Add autodiscovery e2e compose"
```

---

## Task 3: Common Constants

**Files:**
- Modify: `mcache/tests/common.py`

Add an `AUTODISCOVERY` constant and an `AUTODISCOVERY_COMPOSE_PATH` constant alongside the existing module-level values. The redisdb pattern uses `is_affirmative` from `datadog_checks.base`; match that.

- [ ] **Step 1: Read the current file**

Run: `cat /home/bits/go/src/github.com/DataDog/integrations-core/mcache/tests/common.py`

- [ ] **Step 2: Add the imports and constants**

Edit `mcache/tests/common.py`:

Replace:
```python
import os

import pytest

from datadog_checks.dev import get_docker_hostname
from datadog_checks.dev.utils import ON_LINUX, ON_WINDOWS

HERE = os.path.dirname(os.path.abspath(__file__))

PORT = 11211
SERVICE_CHECK = 'memcache.can_connect'
HOST = get_docker_hostname()
USERNAME = 'testuser'
PASSWORD = 'testpass'

DOCKER_SOCKET_DIR = '/tmp'
DOCKER_SOCKET_PATH = '/tmp/memcached.sock'
```

With:
```python
import os

import pytest

from datadog_checks.base import is_affirmative
from datadog_checks.dev import get_docker_hostname
from datadog_checks.dev.utils import ON_LINUX, ON_WINDOWS

HERE = os.path.dirname(os.path.abspath(__file__))

PORT = 11211
SERVICE_CHECK = 'memcache.can_connect'
HOST = get_docker_hostname()
USERNAME = 'testuser'
PASSWORD = 'testpass'

DOCKER_SOCKET_DIR = '/tmp'
DOCKER_SOCKET_PATH = '/tmp/memcached.sock'

AUTODISCOVERY = is_affirmative(os.environ.get('MCACHE_AUTODISCOVERY', 'false'))
AUTODISCOVERY_COMPOSE_PATH = os.path.join(HERE, 'compose', 'autodiscovery-default.compose')
```

- [ ] **Step 3: Verify the module imports cleanly**

Run: `cd /home/bits/go/src/github.com/DataDog/integrations-core/mcache && python -c "from tests.common import AUTODISCOVERY, AUTODISCOVERY_COMPOSE_PATH; print(AUTODISCOVERY, AUTODISCOVERY_COMPOSE_PATH)"`

Expected: `False /home/bits/go/src/github.com/DataDog/integrations-core/mcache/tests/compose/autodiscovery-default.compose`. No `ImportError`.

If `datadog_checks.base` is not installed in the active environment, run inside the hatch env instead:
`PATH="$HOME/.pyenv/shims:$HOME/.pyenv/bin:$PATH" ddev test mcache --no-interactive -- --collect-only -q tests/test_check.py 2>&1 | tail -20`. Expected: collection succeeds with no `ImportError`.

- [ ] **Step 4: Commit**

```bash
cd /home/bits/go/src/github.com/DataDog/integrations-core
git add mcache/tests/common.py
git commit -m "[mcache] Add AUTODISCOVERY constants for e2e env"
```

---

## Task 4: Conftest Branch

**Files:**
- Modify: `mcache/tests/conftest.py`

`dd_environment` grows an autodiscovery branch at the top. When `AUTODISCOVERY` is true, run only the new compose, mount the Docker socket into the agent via `e2e_metadata`, and yield `(None, e2e_metadata)`. The `(None, metadata)` tuple form tells `dd_agent_check` not to write any static `conf.yaml`, so the agent is driven purely by `auto_conf.yaml` + Docker listener.

The `e2e_instance` fixture parameter is preserved (pytest needs to resolve it) but unused on the autodiscovery branch. The existing 3-container path (SASL + IPv6 + socket) is wrapped untouched in an `else`.

The compose readiness condition uses `CheckDockerLogs` looking for `'server listening'`, which is what `memcached:1.6` prints at startup. If empirically the version is silent, the failure mode is documented (compose readiness times out) and the fix is to switch to a `WaitFor` TCP probe.

- [ ] **Step 1: Read the current conftest**

Run: `cat /home/bits/go/src/github.com/DataDog/integrations-core/mcache/tests/conftest.py`

- [ ] **Step 2: Edit imports**

Replace:
```python
from datadog_checks.dev import TempDir, WaitFor, docker_run
from datadog_checks.mcache import Memcache

from .common import (
    DOCKER_SOCKET_DIR,
    DOCKER_SOCKET_PATH,
    HERE,
    HOST,
    PASSWORD,
    PORT,
    USERNAME,
    platform_supports_sockets,
)
```

With:
```python
from datadog_checks.dev import TempDir, WaitFor, docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.mcache import Memcache

from .common import (
    AUTODISCOVERY,
    AUTODISCOVERY_COMPOSE_PATH,
    DOCKER_SOCKET_DIR,
    DOCKER_SOCKET_PATH,
    HERE,
    HOST,
    PASSWORD,
    PORT,
    USERNAME,
    platform_supports_sockets,
)
```

- [ ] **Step 3: Replace the `dd_environment` body with the branched version**

Replace the existing `dd_environment` definition:

```python
@pytest.fixture(scope='session')
def dd_environment(e2e_instance):
    with docker_run(
        os.path.join(HERE, 'compose', 'docker-compose.yaml'),
        service_name='memcached',
        env_vars={'PWD': HERE},
        conditions=[WaitFor(connect_to_mcache, args=(['{}:{}'.format(HOST, PORT)], USERNAME, PASSWORD))],
    ):
        if platform_supports_sockets:
            with TempDir() as temp_dir:
                host_socket_path = os.path.join(temp_dir, 'memcached.sock')

                if not os.path.exists(host_socket_path):
                    os.chmod(temp_dir, 0o777)

                with docker_run(
                    os.path.join(HERE, 'compose', 'docker-compose.yaml'),
                    service_name='memcached_socket',
                    env_vars={
                        'DOCKER_SOCKET_DIR': DOCKER_SOCKET_DIR,
                        'DOCKER_SOCKET_PATH': DOCKER_SOCKET_PATH,
                        'HOST_SOCKET_DIR': temp_dir,
                        'HOST_SOCKET_PATH': host_socket_path,
                    },
                    conditions=[WaitFor(connect_to_mcache, args=(host_socket_path, USERNAME, PASSWORD))],
                    # Don't worry about spinning down since the outermost runner will already do that
                    down=lambda: None,
                ):
                    yield e2e_instance
        else:
            yield e2e_instance
```

With:

```python
@pytest.fixture(scope='session')
def dd_environment(e2e_instance):
    """
    Start the Memcached test environment.

    In autodiscovery mode (`MCACHE_AUTODISCOVERY=true`) run a single default-port
    Memcached container on the Docker bridge network and hand the Agent the Docker
    socket so it can discover the container via the Docker listener. No static
    instance config is yielded so the Agent relies purely on `auto_conf.yaml`.

    Otherwise run the existing SASL + IPv6 + socket multi-container setup used by
    the existing e2e and integration tests.
    """
    if AUTODISCOVERY:
        e2e_metadata = {
            'docker_volumes': ['/var/run/docker.sock:/var/run/docker.sock:ro'],
        }
        with docker_run(
            AUTODISCOVERY_COMPOSE_PATH,
            conditions=[CheckDockerLogs(AUTODISCOVERY_COMPOSE_PATH, 'server listening', wait=5)],
        ):
            yield None, e2e_metadata
        return

    with docker_run(
        os.path.join(HERE, 'compose', 'docker-compose.yaml'),
        service_name='memcached',
        env_vars={'PWD': HERE},
        conditions=[WaitFor(connect_to_mcache, args=(['{}:{}'.format(HOST, PORT)], USERNAME, PASSWORD))],
    ):
        if platform_supports_sockets:
            with TempDir() as temp_dir:
                host_socket_path = os.path.join(temp_dir, 'memcached.sock')

                if not os.path.exists(host_socket_path):
                    os.chmod(temp_dir, 0o777)

                with docker_run(
                    os.path.join(HERE, 'compose', 'docker-compose.yaml'),
                    service_name='memcached_socket',
                    env_vars={
                        'DOCKER_SOCKET_DIR': DOCKER_SOCKET_DIR,
                        'DOCKER_SOCKET_PATH': DOCKER_SOCKET_PATH,
                        'HOST_SOCKET_DIR': temp_dir,
                        'HOST_SOCKET_PATH': host_socket_path,
                    },
                    conditions=[WaitFor(connect_to_mcache, args=(host_socket_path, USERNAME, PASSWORD))],
                    # Don't worry about spinning down since the outermost runner will already do that
                    down=lambda: None,
                ):
                    yield e2e_instance
        else:
            yield e2e_instance
```

- [ ] **Step 4: Verify conftest still parses**

Run: `cd /home/bits/go/src/github.com/DataDog/integrations-core/mcache && python -c "import ast; ast.parse(open('tests/conftest.py').read()); print('ok')"`

Expected: `ok`. Catches Python syntax errors before launching docker.

- [ ] **Step 5: Commit**

```bash
cd /home/bits/go/src/github.com/DataDog/integrations-core
git add mcache/tests/conftest.py
git commit -m "[mcache] Branch dd_environment on MCACHE_AUTODISCOVERY"
```

---

## Task 5: Skip Existing E2E Under Autodiscovery

**Files:**
- Modify: `mcache/tests/test_integration_e2e.py`

The existing `test_e2e` depends on SASL credentials and a published-port memcached on the host, both of which are absent under the autodiscovery env. Skip it when `MCACHE_AUTODISCOVERY=true`.

- [ ] **Step 1: Read the current marker block**

Run: `head -45 /home/bits/go/src/github.com/DataDog/integrations-core/mcache/tests/test_integration_e2e.py`

Expected: `@pytest.mark.e2e` decorator on `test_e2e` around line 29.

- [ ] **Step 2: Add the import and skipif**

In `mcache/tests/test_integration_e2e.py`:

Replace:
```python
from .common import HOST, PORT, SERVICE_CHECK, requires_socket_support, requires_unix_utils
```

With:
```python
from . import common
from .common import HOST, PORT, SERVICE_CHECK, requires_socket_support, requires_unix_utils
```

Replace:
```python
@pytest.mark.e2e
def test_e2e(client, dd_agent_check, instance):
```

With:
```python
@pytest.mark.e2e
@pytest.mark.skipif(common.AUTODISCOVERY, reason='Existing e2e is not run in the autodiscovery env')
def test_e2e(client, dd_agent_check, instance):
```

- [ ] **Step 3: Verify file parses**

Run: `cd /home/bits/go/src/github.com/DataDog/integrations-core/mcache && python -c "import ast; ast.parse(open('tests/test_integration_e2e.py').read()); print('ok')"`

Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
cd /home/bits/go/src/github.com/DataDog/integrations-core
git add mcache/tests/test_integration_e2e.py
git commit -m "[mcache] Skip existing e2e under autodiscovery env"
```

---

## Task 6: Autodiscovery Test File

**Files:**
- Create: `mcache/tests/test_e2e_autodiscovery.py`

The test waits for `agent configcheck` output to contain `mcache` (proof the agent's autodiscovery picked up the container and scheduled a check), then runs `dd_agent_check(..., discovery_min_instances=1, discovery_timeout=30)` and asserts a `memcache.can_connect` service check came back OK with `port:11211` in its tags. We use a subset scan rather than `assert_service_check(tags=...)` because exact tag-list equality fails — the Docker listener emits `docker_image`, `image_id`, `image_name`, `image_tag`, `short_image` plus the check's resolved `host:` tag, all variable per run.

- [ ] **Step 1: Create the test file**

Write `mcache/tests/test_e2e_autodiscovery.py`:

```python
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
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

- [ ] **Step 2: Verify file parses**

Run: `cd /home/bits/go/src/github.com/DataDog/integrations-core/mcache && python -c "import ast; ast.parse(open('tests/test_e2e_autodiscovery.py').read()); print('ok')"`

Expected: `ok`.

- [ ] **Step 3: Verify the test file imports cleanly**

Run: `cd /home/bits/go/src/github.com/DataDog/integrations-core/mcache && python -c "import ast; ast.parse(open('tests/test_e2e_autodiscovery.py').read()); print('syntax ok')"`

Expected: `syntax ok`. (Full pytest collection happens in Task 7 Step 3 against the real autodiscovery env — no need to also do it here, since this file is skipped outside that env anyway.)

- [ ] **Step 4: Commit**

```bash
cd /home/bits/go/src/github.com/DataDog/integrations-core
git add mcache/tests/test_e2e_autodiscovery.py
git commit -m "[mcache] Add autodiscovery e2e test"
```

---

## Task 7: Run the Test End-to-End

This is the verification gate that Tasks 1–6 actually wired up correctly. It also empirically resolves three open questions documented in the spec: the `'server listening'` log line, the `'mcache'` configcheck identifier, and whether `dd_agent_check` with empty `instances` works for mcache.

- [ ] **Step 1: Start the autodiscovery env**

Run: `PATH="$HOME/.pyenv/shims:$HOME/.pyenv/bin:$PATH" ddev env start --dev mcache py3.13-ad-1.6`

Expected: env starts, compose readiness completes, agent container `dd_mcache_py3.13-ad-1.6` is running.

If startup fails on `'server listening'` → memcached:1.6 doesn't print that line. Switch the readiness condition in `mcache/tests/conftest.py` to a TCP probe:

```python
from datadog_checks.dev.conditions import WaitFor
from datadog_checks.dev import get_docker_hostname

def _memcached_listening():
    import socket
    with socket.create_connection((get_docker_hostname(), 11211), timeout=2):
        pass

# in dd_environment, replace conditions=[CheckDockerLogs(...)] with:
conditions=[WaitFor(_memcached_listening, attempts=30, wait=1)],
```

(Note: this only works if the compose publishes a port, which our autodiscovery compose deliberately does not. The cleaner fallback is to replace `'server listening'` with whatever memcached:1.6 actually emits — verify with `docker logs <container_id>` after `docker compose up`. Common alternatives: `'<accepting connections>'`, version banner, or omitting the condition entirely and relying on docker_run's default settle time.) Then re-run this step.

- [ ] **Step 2: Verify the agent sees memcached and scheduled the check**

Run: `docker exec dd_mcache_py3.13-ad-1.6 agent configcheck 2>&1 | head -50`

Expected: output includes a section like `=== mcache check ===` or `Provider: docker` listing the autodiscovered config.

If the output uses a different identifier (e.g. `memcache`), update `_autodiscovery_ready` in `mcache/tests/test_e2e_autodiscovery.py` to grep for that identifier instead of `'mcache'`, commit the fix, and re-run this step.

- [ ] **Step 3: Run the autodiscovery test**

Run: `PATH="$HOME/.pyenv/shims:$HOME/.pyenv/bin:$PATH" ddev env test --dev mcache py3.13-ad-1.6`

Expected: `tests/test_e2e_autodiscovery.py::test_e2e_autodiscovery_default_port PASSED`. The skipped existing `test_e2e` should also be reported as `SKIPPED` with reason `'Existing e2e is not run in the autodiscovery env'`.

If the test fails with `Needed at least 1 candidates ... got 0` or similar, the assertion logic is correct but no `memcache.can_connect` came back OK. Inspect:

```bash
docker exec dd_mcache_py3.13-ad-1.6 agent status 2>&1 | grep -A 20 'mcache\|memcache'
```

Common causes: agent reaches the wrong IP for the container (CRITICAL service check), or `MemCache.OK` is named differently (check `from datadog_checks.mcache import Memcache; Memcache.OK` — should be `0`).

- [ ] **Step 4: Two-direction sanity check (positive)**

After Step 3 passes, perturb the source-tree `auto_conf.yaml` to break autodiscovery and confirm the test correctly fails:

```bash
sed -i 's/- memcached/- memcachedfoo/' /home/bits/go/src/github.com/DataDog/integrations-core/mcache/datadog_checks/mcache/data/auto_conf.yaml
PATH="$HOME/.pyenv/shims:$HOME/.pyenv/bin:$PATH" ddev env stop mcache py3.13-ad-1.6
PATH="$HOME/.pyenv/shims:$HOME/.pyenv/bin:$PATH" ddev env start --dev mcache py3.13-ad-1.6
PATH="$HOME/.pyenv/shims:$HOME/.pyenv/bin:$PATH" ddev env test --dev mcache py3.13-ad-1.6
```

Expected: the test FAILS at `_autodiscovery_ready` (timeout waiting for `mcache` to appear in configcheck output). This proves the test is reading the source-tree `auto_conf.yaml`, not the agent image's bundled copy.

The `ddev env stop` + `ddev env start` between edits is required because file bind-mounts pin by inode and `sed -i` (like `git checkout`) replaces the inode, breaking the live mount.

- [ ] **Step 5: Restore the file and re-verify positive case**

```bash
cd /home/bits/go/src/github.com/DataDog/integrations-core
git checkout mcache/datadog_checks/mcache/data/auto_conf.yaml
PATH="$HOME/.pyenv/shims:$HOME/.pyenv/bin:$PATH" ddev env stop mcache py3.13-ad-1.6
PATH="$HOME/.pyenv/shims:$HOME/.pyenv/bin:$PATH" ddev env start --dev mcache py3.13-ad-1.6
PATH="$HOME/.pyenv/shims:$HOME/.pyenv/bin:$PATH" ddev env test --dev mcache py3.13-ad-1.6
```

Expected: test PASSES again.

- [ ] **Step 6: Stop the env**

Run: `PATH="$HOME/.pyenv/shims:$HOME/.pyenv/bin:$PATH" ddev env stop mcache py3.13-ad-1.6`

Expected: clean shutdown.

- [ ] **Step 7: Run formatter**

Run: `PATH="$HOME/.pyenv/shims:$HOME/.pyenv/bin:$PATH" ddev test -fs mcache`

Expected: ruff format and lint pass clean. Commit any auto-formatting fixes.

- [ ] **Step 8: Commit any fixes from the verification run**

If Step 1, Step 2, or Step 3 surfaced fixes (different log line, different configcheck identifier, etc.), commit them now:

```bash
cd /home/bits/go/src/github.com/DataDog/integrations-core
git add -A mcache/
git commit -m "[mcache] Fix autodiscovery e2e from end-to-end run"
```

If no fixes were needed, skip this step.

---

## Task 8: DEVELOPMENT.md

**Files:**
- Create: `mcache/DEVELOPMENT.md`

Mirror `redisdb/DEVELOPMENT.md` structure: prerequisites, unit/integration test commands, e2e env list, the autodiscovery section explaining the env and noting the bind-mount inode caveat. Each integration's DEVELOPMENT.md stands alone — no cross-link to redisdb's.

- [ ] **Step 1: Read the redisdb template for structure**

Run: `cat /home/bits/go/src/github.com/DataDog/integrations-core/redisdb/DEVELOPMENT.md`

(For reference only — copy structure, not content.)

- [ ] **Step 2: Create the file**

Write `mcache/DEVELOPMENT.md`:

````markdown
# Memcached Integration - Development

## Prerequisites

Install `ddev` and configure it to point at this repo:

```shell
pip install ddev
ddev config set repos.core /path/to/integrations-core
```

The test matrix requires Python 3.13. Install it via pyenv if needed:

```shell
curl https://pyenv.run | bash
# Add pyenv to your shell (follow the printed instructions), then:
pyenv install 3.13
pyenv global 3.13
```

## Unit and Integration Tests

Run all unit and integration tests:

```shell
ddev --no-interactive test mcache
```

Run a specific test:

```shell
ddev --no-interactive test mcache -- -k <PYTEST_FILTER_STRING>
```

Auto-format and lint:

```shell
ddev test -fs mcache
```

## E2E Tests

E2E tests spin up Docker containers running Memcached and a Datadog Agent.

1. List available environments:

   ```shell
   ddev env show mcache
   ```

2. Start an environment, run its E2E tests, then stop it:

   ```shell
   ddev env start --dev mcache py3.13
   ddev env test --dev mcache py3.13
   ddev env stop mcache py3.13
   ```

3. To recreate the environment from scratch (e.g. after dependency changes):

   ```shell
   ddev env test --dev --recreate mcache py3.13
   ```

### Agent Autodiscovery E2E

The `py3.13-ad-1.6` environment exercises the Agent's container autodiscovery using
the integration's `auto_conf.yaml`. It starts a single default-port Memcached container
on the Docker bridge network, mounts the host Docker socket into the Agent container,
and verifies the Agent discovers the container via the Docker listener.

```shell
ddev env start --dev mcache py3.13-ad-1.6
ddev env test  --dev mcache py3.13-ad-1.6
ddev env stop  mcache py3.13-ad-1.6
```

Only the default-port bridge-network case is covered today. Other cases (port-forwarded,
non-default in-container port, `--network=host`, SASL-authenticated autodiscovery,
process autodiscovery) are tracked in the DSCVR "Integrations autodiscovery exploration"
Confluence page and will be added as the associated upstream issues are fixed.

The Agent reads `auto_conf.yaml` via a file-level Docker bind-mount of the source-tree
copy at `mcache/datadog_checks/mcache/data/auto_conf.yaml`. Editing the file between
test runs requires restarting the environment (`ddev env stop` then `ddev env start`)
because tools like `git checkout` replace the file's inode and break the live mount.
````

- [ ] **Step 3: Commit**

```bash
cd /home/bits/go/src/github.com/DataDog/integrations-core
git add mcache/DEVELOPMENT.md
git commit -m "[mcache] Document e2e environments and autodiscovery caveat"
```

---

## Task 9: Final Verification

- [ ] **Step 1: Run the unit + integration suite to confirm no regressions in the default env**

Run: `PATH="$HOME/.pyenv/shims:$HOME/.pyenv/bin:$PATH" ddev --no-interactive test mcache 2>&1 | tail -30`

Expected: existing tests pass. The autodiscovery test should be skipped (`Requires MCACHE_AUTODISCOVERY=true`).

- [ ] **Step 2: Re-run the autodiscovery env one more time**

Run:
```bash
PATH="$HOME/.pyenv/shims:$HOME/.pyenv/bin:$PATH" ddev env start --dev mcache py3.13-ad-1.6 \
  && PATH="$HOME/.pyenv/shims:$HOME/.pyenv/bin:$PATH" ddev env test --dev mcache py3.13-ad-1.6 \
  ; PATH="$HOME/.pyenv/shims:$HOME/.pyenv/bin:$PATH" ddev env stop mcache py3.13-ad-1.6
```

Expected: `test_e2e_autodiscovery_default_port PASSED`, `test_e2e SKIPPED`, env stops cleanly.

- [ ] **Step 3: Confirm changelog is not required**

Per the project's `AGENTS.md`: "Changelog entries are not required for changes in tests or assets." This plan touches:
- `mcache/hatch.toml` — config, no changelog needed.
- `mcache/tests/*` — tests, no changelog needed.
- `mcache/DEVELOPMENT.md` — docs, no changelog needed.

No changelog entry required. Skip this step if the project's policy has changed since this plan was written.

- [ ] **Step 4: Final commit summary**

Run: `git log --oneline mcache/ | head -10`

Expected: a clean sequence of focused commits — one per task. No mixed concerns.

---

## Out of Scope (Tracked elsewhere)

Per the spec — do not address in this plan:

- Port-forwarded memcached coverage.
- Non-default in-container port (requires fixing `auto_conf.yaml` first; port is hardcoded to 11211).
- `--network=host` double-reporting case.
- SASL-authenticated autodiscovery.
- Multi-version coverage (1.5, 1.6, 1.7, latest).
- Process autodiscovery via `cel_selector`.
- Validating `docker_image` / `short_image` / `image_id` tags.
- **Helper extraction across redisdb and mcache** — this is the explicit subject of the next spec, brainstormed *after* this plan lands so the duplication is concrete.
