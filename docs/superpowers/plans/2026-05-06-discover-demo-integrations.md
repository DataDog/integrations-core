# Plan C: Demo Integrations for Python `discover()` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Demonstrate the Python `discover()` advanced auto-config path against three real integrations covering distinct discovery patterns: airflow (HTTP multi-step version detection), twemproxy (TCP banner JSON), hdfs_namenode (HTTP JSON-shape verification). Each ships a working `discover()` classmethod, a presence-marker `auto_conf_discovery.yaml`, and an `@pytest.mark.e2e` test that exercises end-to-end discovery against the integration's existing docker-compose fixture.

**Architecture:** Each integration adds a small `discover(service)` classmethod on its existing check class that uses Plan A helpers (`candidate_ports`, `http_probe`/`tcp_probe`, verifier predicates). The `auto_conf_discovery.yaml` carries `ad_identifiers` + `discovery: {}` + `instances: []` (the parser change in Plan B Task 11 accepts the empty-instances form when `discovery` is set). E2e tests use `dd_agent_check(..., discovery_min_instances=1, discovery_timeout=30)` against the existing `tests/compose/docker-compose.yaml` fixture, mirroring the krakend e2e (`krakend/tests/test_e2e.py:test_e2e_discovery`).

**Tech Stack:** Python 3.13, `datadog_checks_base.utils.discovery` (Plan A helpers), pytest + ddev e2e harness (`@pytest.mark.e2e` + `dd_agent_check`).

**Spec / context:**
- Design spec: [`docs/superpowers/specs/2026-05-06-advanced-autoconfig-discover-design.md`](../specs/2026-05-06-advanced-autoconfig-discover-design.md).
- Plan A (Python helpers) shipped: `vitkyrka/disco-autoconfig` branch on this repo.
- Plan B (agent-side bridge + lazy-init) shipped on `datadog-agent` branch `vitkyrka/advanced-autoconfig-krakend`.
- Krakend reference e2e: `krakend/tests/test_e2e.py:test_e2e_discovery`.

**Working directory:** `/home/vagrant/go/src/github.com/DataDog/integrations-core`. Branch: `vitkyrka/disco-autoconfig`.

## File Structure

For each integration `<I>`:
- Modify: `<I>/datadog_checks/<I>/<I>.py` — add `discover(cls, service)` classmethod on the existing check class.
- Create: `<I>/datadog_checks/<I>/data/auto_conf_discovery.yaml` — `ad_identifiers`, `discovery: {}`, empty `instances: []`.
- Modify: `<I>/tests/test_e2e.py` (or create if absent) — add `test_e2e_discovery`.
- Create: `<I>/changelog.d/<PR>.added` — one-line entry via `ddev release changelog new added <I>`.

Plus one shared change:
- `datadog_checks_base/datadog_checks/base/utils/discovery/verifiers.py` — add `response_json_keys(required_keys)` TCP verifier (twemproxy needs it; mirrors HTTP `json_has`). Plus tests.

## Test Command

The user's invocation pattern:

```bash
DDEV_E2E_AGENT=datadog/agent-dev:discovery-local DDEV_E2E_DOCKER_NO_PULL=1 \
  ddev env test --dev <integration> <env>
```

Where `<env>` is one of the integration's hatch envs (e.g. `py3.13-2.10` for krakend). Use `ddev env show <integration>` to list envs.

The custom image `datadog/agent-dev:discovery-local` is a local agent build with the Plan B changes; the user has already produced this image. The plan assumes it remains available across plan execution.

For unit-only tests during development, use the Plan A test workflow:
```bash
hatch -e datadog-harbor run pytest <integration>/tests/test_unit.py -v
```

---

### Task 1: Add `response_json_keys` TCP verifier to datadog_checks_base

twemproxy's stats port emits a JSON document on TCP connect; we need a TCP-side equivalent of the HTTP `json_has` predicate.

**Files:**
- Modify: `datadog_checks_base/datadog_checks/base/utils/discovery/verifiers.py`
- Modify: `datadog_checks_base/tests/base/utils/discovery/test_verifiers.py`
- Modify: `datadog_checks_base/datadog_checks/base/utils/discovery/__init__.pyi`

- [ ] **Step 1: Write failing tests**

Add to `test_verifiers.py`:

```python
def test_response_json_keys_pass():
    from datadog_checks.base.utils.discovery.verifiers import response_json_keys
    body = b'{"service":"nutcracker","source":"x","version":"0.5","total_connections":12}'
    assert response_json_keys(["service", "source", "version"])(body)


def test_response_json_keys_missing_key():
    from datadog_checks.base.utils.discovery.verifiers import response_json_keys
    body = b'{"service":"nutcracker"}'
    assert not response_json_keys(["service", "source", "version"])(body)


def test_response_json_keys_not_json():
    from datadog_checks.base.utils.discovery.verifiers import response_json_keys
    assert not response_json_keys(["x"])(b"not json")
```

Update the imports at the top of the file:

```python
from datadog_checks.base.utils.discovery.verifiers import (
    body_contains,
    body_matches,
    is_prometheus_exposition,
    json_has,
    response_equals,
    response_json_keys,
    response_starts_with,
    status_2xx,
)
```

```bash
hatch -e datadog-harbor run pytest datadog_checks_base/tests/base/utils/discovery/test_verifiers.py::test_response_json_keys_pass -v
```

Expected: ImportError on `response_json_keys`.

- [ ] **Step 2: Implement**

Append to `verifiers.py`:

```python
def response_json_keys(required_keys: Iterable[str]) -> TCPPredicate:
    """Verify the TCP response decodes as a JSON object containing all the
    required top-level keys. Mirror of ``json_has`` for raw bytes.
    """
    keys = tuple(required_keys)

    def predicate(buf: bytes) -> bool:
        try:
            doc = json.loads(buf.decode("utf-8", errors="strict"))
        except (ValueError, UnicodeDecodeError):
            return False
        if not isinstance(doc, dict):
            return False
        return all(k in doc for k in keys)

    return predicate
```

Add `import json` to the top of the file (next to `import re`).

- [ ] **Step 3: Update __init__.pyi**

Add `response_json_keys` to the verifiers re-export block and to `__all__` (alphabetical):

```python
from .verifiers import (
    body_contains,
    body_matches,
    is_prometheus_exposition,
    json_has,
    response_equals,
    response_json_keys,
    response_starts_with,
    status_2xx,
)

__all__ = [
    'Discovery',
    'Port',
    'Service',
    'body_contains',
    'body_matches',
    'candidate_ports',
    'http_probe',
    'is_prometheus_exposition',
    'json_has',
    'response_equals',
    'response_json_keys',
    'response_starts_with',
    'status_2xx',
    'tcp_probe',
    '_run_discover',
]
```

- [ ] **Step 4: Run tests**

```bash
hatch -e datadog-harbor run pytest datadog_checks_base/tests/base/utils/discovery/ -v
```

Expected: all existing tests + 3 new tests pass.

- [ ] **Step 5: Add changelog entry**

```bash
ddev release changelog new added datadog_checks_base \
  -m "Add response_json_keys TCP verifier under datadog_checks.base.utils.discovery for advanced auto-config of integrations whose stats port emits JSON on connect (e.g. twemproxy)."
```

- [ ] **Step 6: Commit**

```bash
git add datadog_checks_base/datadog_checks/base/utils/discovery/verifiers.py \
        datadog_checks_base/datadog_checks/base/utils/discovery/__init__.pyi \
        datadog_checks_base/tests/base/utils/discovery/test_verifiers.py \
        datadog_checks_base/changelog.d/*.added
git commit -m "datadog_checks_base: add response_json_keys TCP verifier"
```

---

### Task 2: Airflow `discover()` — HTTP multi-step version detection

**Pattern:** `http-multi-path`. Probes `/api/v1/version` first; if 2xx, the integration is Airflow 2.x. Otherwise probes `/api/experimental/test`; if 2xx, it's 1.x. Returns a single instance with `url` set to the base URL.

**Files:**
- Modify: `airflow/datadog_checks/airflow/airflow.py` — add `discover` classmethod to `AirflowCheck`.
- Create: `airflow/datadog_checks/airflow/data/auto_conf_discovery.yaml`.
- Modify: `airflow/tests/test_e2e.py` — add `test_e2e_discovery`.
- Create: `airflow/changelog.d/<PR>.added`.

- [ ] **Step 1: Add the `discover` classmethod**

In `airflow/datadog_checks/airflow/airflow.py`, find `class AirflowCheck(AgentCheck):` and add this method to the class body (anywhere; top of class is conventional):

```python
    @classmethod
    def discover(cls, service):
        from datadog_checks.base.utils.discovery import (
            candidate_ports,
            http_probe,
            status_2xx,
        )

        for port in candidate_ports(service, [8080]):
            url = f"http://{service.host}:{port.number}"
            # Airflow 2.x: stable REST API at /api/v1.
            if http_probe(service.host, port.number, "/api/v1/version",
                          verifier=status_2xx()):
                return [{"url": url}]
            # Airflow 1.x: experimental API.
            if http_probe(service.host, port.number, "/api/experimental/test",
                          verifier=status_2xx()):
                return [{"url": url}]
        return None
```

- [ ] **Step 2: Create auto_conf_discovery.yaml**

`airflow/datadog_checks/airflow/data/auto_conf_discovery.yaml`:

```yaml
ad_identifiers:
  - airflow
discovery: {}
init_config:
instances: []
```

- [ ] **Step 3: Add the e2e test**

Read the existing `airflow/tests/test_e2e.py` first to understand the integration's current e2e shape and metadata-metrics pattern. Then add a sibling test, mirroring `krakend/tests/test_e2e.py:test_e2e_discovery`:

```python
@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check):
    aggregator = dd_agent_check(
        {"init_config": {}, "instances": []},
        check_rate=True,
        discovery_min_instances=1,
        discovery_timeout=30,
    )
    # Airflow's metric set varies by version and the StatsD plugin path;
    # at minimum, assert the check ran and submitted *something*.
    assert aggregator.metric_names, "expected at least one metric submitted"
```

(Use `assert_metrics_using_metadata` if the existing tests in this file already use it and the metadata file is reliable across Airflow versions; otherwise the looser metric-name presence check above is sufficient for proving the discovery path works.)

- [ ] **Step 4: Run unit tests**

```bash
hatch -e datadog-harbor run pytest airflow/tests/test_unit.py -v
```

Expected: existing tests still pass; the `discover` classmethod doesn't affect the existing check.

- [ ] **Step 5: Run the e2e test**

```bash
ddev env show airflow
# pick an env name, e.g. py3.13-2.10
DDEV_E2E_AGENT=datadog/agent-dev:discovery-local DDEV_E2E_DOCKER_NO_PULL=1 \
  ddev env test --dev airflow <env>
```

Expected: `test_e2e_discovery` passes; aggregator received at least one metric.

If the discovery probe fails, troubleshoot by inspecting the agent container's logs:

```bash
docker logs $(docker ps --filter ancestor=datadog/agent-dev:discovery-local -q | head -1) 2>&1 | grep -iE "airflow|discoverer|run python check"
```

- [ ] **Step 6: Add changelog entry**

```bash
ddev release changelog new added airflow \
  -m "Support advanced auto-config discovery: discover() probes the webserver REST API to detect Airflow 1.x vs 2.x and returns a resolved instance config without a static auto_conf.yaml template."
```

- [ ] **Step 7: Commit**

```bash
git add airflow/
git commit -m "airflow: add Python discover() for advanced auto-config"
```

---

### Task 3: Twemproxy `discover()` — TCP banner with JSON shape

**Pattern:** `tcp-banner-server-greets`. Twemproxy's stats port (default 22222 per upstream; 2222 in the agent's example/code default) emits a JSON document on TCP connect, no client send needed. The verifier checks the well-known top-level keys `service`, `source`, `version`, `total_connections`.

**Files:**
- Modify: `twemproxy/datadog_checks/twemproxy/twemproxy.py` — add `discover` classmethod to `Twemproxy`.
- Create: `twemproxy/datadog_checks/twemproxy/data/auto_conf_discovery.yaml`.
- Modify: `twemproxy/tests/test_twemproxy.py` (or create `test_e2e.py` if e2e tests live separately).
- Create: `twemproxy/changelog.d/<PR>.added`.

- [ ] **Step 1: Add the `discover` classmethod**

In `twemproxy/datadog_checks/twemproxy/twemproxy.py`, find `class Twemproxy(AgentCheck):` and add:

```python
    @classmethod
    def discover(cls, service):
        from datadog_checks.base.utils.discovery import (
            candidate_ports,
            response_json_keys,
            tcp_probe,
        )

        for port in candidate_ports(service, [22222, 2222]):
            verifier = response_json_keys(
                ["service", "source", "version", "total_connections"]
            )
            if tcp_probe(service.host, port.number, verifier=verifier, timeout=1.0):
                return [{"host": service.host, "port": port.number}]
        return None
```

(`timeout=1.0` is generous because some twemproxy builds buffer the JSON briefly.)

- [ ] **Step 2: Create auto_conf_discovery.yaml**

`twemproxy/datadog_checks/twemproxy/data/auto_conf_discovery.yaml`:

```yaml
ad_identifiers:
  - twemproxy
  - nutcracker
discovery: {}
init_config:
instances: []
```

(Both `twemproxy` and `nutcracker` ad-identifiers are listed because the upstream image names vary.)

- [ ] **Step 3: Add the e2e test**

Read `twemproxy/tests/test_twemproxy.py` for the existing pattern. If the file has only unit tests (`@pytest.mark.unit`), append an `@pytest.mark.e2e` test at the bottom; if there's already an `@pytest.mark.e2e` test, append a `test_e2e_discovery` sibling.

```python
@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check):
    aggregator = dd_agent_check(
        {"init_config": {}, "instances": []},
        check_rate=True,
        discovery_min_instances=1,
        discovery_timeout=30,
    )
    # Twemproxy's most reliable metric is the per-pool client connection
    # count, which is non-zero whenever the test backends are connected.
    assert aggregator.metric_names, "expected at least one metric submitted"
```

The compose file maps the stats port `6222:22222`; the discoverer's hint `[22222, 2222]` will match the container's `22222` (internal port).

- [ ] **Step 4: Run the e2e test**

```bash
ddev env show twemproxy
# pick an env, e.g. py3.13-0.4.1
DDEV_E2E_AGENT=datadog/agent-dev:discovery-local DDEV_E2E_DOCKER_NO_PULL=1 \
  ddev env test --dev twemproxy <env>
```

If the test fails because the agent can't reach the twemproxy container's stats port, verify the docker network: the test fixture uses `docker_default` (or similar); the agent container needs to be on the same network. The `dd_agent_check` harness handles this by default.

- [ ] **Step 5: Add changelog entry + commit**

```bash
ddev release changelog new added twemproxy \
  -m "Support advanced auto-config discovery: discover() opens a TCP probe on the stats port and verifies the JSON banner emitted on connect."

git add twemproxy/
git commit -m "twemproxy: add Python discover() for advanced auto-config"
```

---

### Task 4: HDFS NameNode `discover()` — HTTP JSON-shape verification

**Pattern:** `http-json-shape`. The NameNode's HTTP servlet at `/jmx` (port 9870 in Hadoop 3) returns a JSON document `{"beans": [...]}` containing Hadoop MBeans. The verifier requires the top-level `beans` key.

**Files:**
- Modify: `hdfs_namenode/datadog_checks/hdfs_namenode/hdfs_namenode.py` — add `discover` to `HDFSNameNode`.
- Create: `hdfs_namenode/datadog_checks/hdfs_namenode/data/auto_conf_discovery.yaml`.
- Modify: `hdfs_namenode/tests/test_e2e.py`.
- Create: `hdfs_namenode/changelog.d/<PR>.added`.

- [ ] **Step 1: Add the `discover` classmethod**

In `hdfs_namenode/datadog_checks/hdfs_namenode/hdfs_namenode.py`, find `class HDFSNameNode(AgentCheck):` and add:

```python
    @classmethod
    def discover(cls, service):
        from datadog_checks.base.utils.discovery import (
            candidate_ports,
            http_probe,
            json_has,
        )

        # Hadoop 3 default; Hadoop 2 uses 50070 — listed second so a
        # mixed-version cluster prefers Hadoop 3 when both ports
        # respond.
        for port in candidate_ports(service, [9870, 50070]):
            if http_probe(service.host, port.number, "/jmx",
                          verifier=json_has(["beans"])):
                return [{
                    "hdfs_namenode_jmx_uri": f"http://{service.host}:{port.number}",
                }]
        return None
```

- [ ] **Step 2: Create auto_conf_discovery.yaml**

`hdfs_namenode/datadog_checks/hdfs_namenode/data/auto_conf_discovery.yaml`:

```yaml
ad_identifiers:
  - hadoop-namenode
  - hdfs-namenode
discovery: {}
init_config:
instances: []
```

(Common image names. The integration's analysis flags the bde2020 image used in tests/compose has `bde2020/hadoop-namenode`; the AD identifier-from-image mapping will match the `hadoop-namenode` slug.)

- [ ] **Step 3: Add the e2e test**

Read `hdfs_namenode/tests/test_e2e.py`. Add:

```python
@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check):
    aggregator = dd_agent_check(
        {"init_config": {}, "instances": []},
        check_rate=True,
        discovery_min_instances=1,
        discovery_timeout=30,
    )
    assert aggregator.metric_names, "expected at least one metric submitted"
```

- [ ] **Step 4: Run the e2e test**

```bash
ddev env show hdfs_namenode
DDEV_E2E_AGENT=datadog/agent-dev:discovery-local DDEV_E2E_DOCKER_NO_PULL=1 \
  ddev env test --dev hdfs_namenode <env>
```

The compose file exposes the NameNode at `9870:9870` and a separate datanode at `9864:9864`. The discoverer's `[9870, 50070]` hints will match port 9870 first.

A subtlety: the bde2020/hadoop image takes ~30 s to fully initialise. The compose's healthcheck/log-pattern handles that on the integration test side; the e2e test should set `discovery_timeout=30` (it does). If the test still fails on timing, bump to `60`.

- [ ] **Step 5: Add changelog entry + commit**

```bash
ddev release changelog new added hdfs_namenode \
  -m "Support advanced auto-config discovery: discover() probes the JMX HTTP servlet at /jmx and verifies the Hadoop-shaped JSON response."

git add hdfs_namenode/
git commit -m "hdfs_namenode: add Python discover() for advanced auto-config"
```

---

### Task 5: Whole-implementation review

A final pass before declaring Plan C done.

- [ ] **Step 1: Run the full discovery test suite to confirm no regression**

```bash
hatch -e datadog-harbor run pytest datadog_checks_base/tests/base/utils/discovery/ -v
```

Expected: all Plan A + Task 1 tests pass.

- [ ] **Step 2: Run all four e2e tests in sequence**

```bash
DDEV_E2E_AGENT=datadog/agent-dev:discovery-local DDEV_E2E_DOCKER_NO_PULL=1 ddev env test --dev krakend py3.13-2.10
DDEV_E2E_AGENT=datadog/agent-dev:discovery-local DDEV_E2E_DOCKER_NO_PULL=1 ddev env test --dev airflow <env>
DDEV_E2E_AGENT=datadog/agent-dev:discovery-local DDEV_E2E_DOCKER_NO_PULL=1 ddev env test --dev twemproxy <env>
DDEV_E2E_AGENT=datadog/agent-dev:discovery-local DDEV_E2E_DOCKER_NO_PULL=1 ddev env test --dev hdfs_namenode <env>
```

Expected: all four pass. Krakend is the regression sentinel; the new three are the demo expansion.

- [ ] **Step 3: Confirm no static `auto_conf.yaml` was introduced**

```bash
ls airflow/datadog_checks/airflow/data/ twemproxy/datadog_checks/twemproxy/data/ hdfs_namenode/datadog_checks/hdfs_namenode/data/
```

Each directory should have `auto_conf_discovery.yaml` and **not** `auto_conf.yaml`. The point of these demos is integrations that didn't already have a working auto-config.

- [ ] **Step 4: Confirm the four `discover()` methods exhibit four distinct shapes**

A quick read of each integration's `discover` method should show:

| Integration | Probe type | Verifier | Verifier source |
|---|---|---|---|
| krakend | HTTP single-path | `is_prometheus_exposition()` | (Plan A) |
| airflow | HTTP multi-path with version branching | `status_2xx()` x2 | (Plan A) |
| twemproxy | TCP banner (server speaks first) | `response_json_keys([...])` | (Task 1, new) |
| hdfs_namenode | HTTP single-path with JSON shape | `json_has(["beans"])` | (Plan A) |

Four patterns, four verifiers, three buckets covered. The point is to exercise the abstraction across its surface, not to maximise integration count.

## Self-Review

**Spec coverage:**
- Plan A's `Service`/`Port` types and helpers are exercised by all four integrations.
- Plan A's verifier predicates (`status_2xx`, `is_prometheus_exposition`, `json_has`) are each used at least once.
- Task 1's `response_json_keys` predicate fills the only verifier gap (JSON-shape over raw TCP bytes).
- Plan B's lazy-init bridge is exercised on every e2e run.

**Placeholder scan:** Each `discover()` body is concrete (5–15 lines). Each `auto_conf_discovery.yaml` is concrete. Each e2e test is concrete. The `<env>` placeholder in test commands is intentional — it's the per-integration hatch env name (`ddev env show <integration>` lists them).

**Type consistency:** `service.host`, `service.ports`, `port.number` used the same way in all four `discover` methods, matching the Plan A `Service`/`Port` dataclass shape.

**Scope:** Plan C is intentionally smaller than Plans A/B. It demonstrates the abstraction works for distinct discovery shapes; it is **not** an exhaustive rollout to all 92 integrations in the targeted analysis buckets. Bulk rollout is a separate effort once the experiment has been reviewed and approved.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-06-discover-demo-integrations.md`. Two execution options:

1. **Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks. Each task is self-contained and TDD-friendly.
2. **Inline Execution** — Execute tasks in this session via executing-plans.

Which approach?
