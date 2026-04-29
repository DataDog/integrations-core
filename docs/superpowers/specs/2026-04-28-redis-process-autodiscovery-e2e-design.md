# Redis Process Autodiscovery E2E Test — Design

## Goal

Add an end-to-end test that verifies the Datadog Agent's **process**
autodiscovery correctly schedules and runs the `redisdb` check against a
`redis-server` process running in a host-networking container, using the
integration's shipped `auto_conf.yaml`.

This complements the container-autodiscovery e2e test added earlier on this
branch ([2026-04-17 spec][redis-spec]). Both modes are exercised side-by-side
in CI in their own Hatch envs.

The chosen approach is the [second solution from DSCVR/6631130024][subpage]:
ship a separate `auto_conf_process.yaml` whose `ad_identifiers` and
`cel_selector` are process-only, and leave the existing `auto_conf.yaml`
unchanged. The original spec proposed the subpage's *first* solution
(single file with both `redis` and `cel://process` in `ad_identifiers`); we
discovered during implementation that this regresses container
autodiscovery — the agent runs the config's CEL `matchingProgram` against
every candidate (`comp/core/autodiscovery/listeners/common_filter.go:24`),
and a process-only CEL returns false against a container entity
(`comp/core/autodiscovery/integration/matching_program.go:38`), so the
redis container template is filtered out. Two files keep the two listeners
fully independent and avoid that regression. If the agent later treats CEL
filters as additive-when-present, a follow-up can collapse both files
into one.

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
of container short-image names matched by the docker listener). For process
matching the file needs `cel_selector.processes` with the CEL expression(s).
A new `auto_conf_process.yaml` ships alongside the existing `auto_conf.yaml`;
the agent loads every `*.yaml` in `conf.d/<integration>.d/` as a separate
template, so the two files become independent autodiscovery candidates. The
agent [auto-injects][autoconfig] `cel://process` into `ad_identifiers` when
the file's `ad_identifiers` block is empty, but we list it explicitly so a
reader of the shipped file can see what listener is involved.

The wiki's "Redis process autodiscovery" experiment also disables the docker
feature (`DD_AUTOCONFIG_EXCLUDE_FEATURES=docker`). Without that, processes
running inside containers are tagged with a container-id and excluded by the
process listener, defeating the test.

The agent's `system-probe-lite` (which feeds workloadmeta for the process
listener) needs `CAP_SYS_PTRACE` and `CAP_DAC_READ_SEARCH` to read /proc
entries of other processes. The default ddev e2e docker invocation grants
no extra capabilities, so we extend ddev with a `cap_add` metadata key and
request both caps from `dd_environment`.

The test's verification doesn't use the standard `dd_agent_check` fixture:
that fixture spawns a short-lived `agent check` subprocess whose
workloadmeta never finishes initialising before the deadline ("Workloadmeta
collectors are not ready after 17 retries"), so the in-subprocess process
listener has nothing to match. Instead, the test queries the long-running
agent's `status --json` output, which already runs the discovery check and
the process listener.

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

Unchanged. Container autodiscovery keeps using the existing
`ad_identifiers: [redis]` template.

### 1b. `redisdb/datadog_checks/redisdb/data/auto_conf_process.yaml` (new)

Generated by `ddev validate config -s redisdb` from a new file block in
`redisdb/assets/configuration/spec.yaml` (with `example_name:
auto_conf_process.yaml` because the example consumer otherwise defaults to
`conf.yaml.example`, colliding with `redisdb.yaml`'s example):

```yaml
## @param ad_identifiers - list of strings - required
## A list of container identifiers that are used by Autodiscovery to identify
## which container the check should be run against. For more information, see:
## https://docs.datadoghq.com/agent/guide/ad_identifiers/
##
## `cel://process` selects the agent's process listener; the
## `cel_selector.processes` CEL rule below is what actually matches
## the redis-server process. The container listener is unaffected
## and continues to use `auto_conf.yaml`.
#
ad_identifiers:
  - cel://process

## @param cel_selector - mapping - required
## CEL rules used by the agent's process listener. The `processes` rule
## below matches any process whose cmdline contains `redis-server`.
#
cel_selector:
  processes:
  - process.cmdline.contains("redis-server")

init_config:

instances:
  - host: '%%host%%'
    port: 6379
```

The agent loads every `*.yaml` in `conf.d/redisdb.d/` as an independent
template, so the docker listener uses `auto_conf.yaml` (matching `redis`)
and the cel://process listener uses `auto_conf_process.yaml` (matching the
CEL rule against process entities). The two paths never interfere.

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
        'cap_add': ['SYS_PTRACE', 'DAC_READ_SEARCH'],
    }
    with docker_run(
        AUTODISCOVERY_PROCESS_COMPOSE_PATH,
        conditions=[CheckDockerLogs(AUTODISCOVERY_PROCESS_COMPOSE_PATH, 'Ready to accept connections', wait=5)],
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

`cap_add` is read by a small ddev change in `ddev/src/ddev/e2e/agent/docker.py`
(mirrors the existing `docker_volumes` / `custom_hosts` keys) and forwarded
as `--cap-add` flags. `SYS_PTRACE` and `DAC_READ_SEARCH` are required by
the agent's `system-probe-lite` to read /proc entries of other processes;
without them service discovery is impaired and the cel://process listener
has nothing to match.

### 6. `redisdb/tests/test_e2e_autodiscovery_process.py` (new)

The test does not use `dd_agent_check`. That fixture spawns a short-lived
`agent check` subprocess whose workloadmeta never finishes initialising
before the deadline ("Workloadmeta collectors are not ready after 17
retries"), so the in-subprocess process listener has nothing to match.
Instead, the test queries the long-running agent's `status --json` output:

```python
def _redisdb_scheduled_and_running():
    container = _agent_container_name()
    configcheck = run_command(
        ['docker', 'exec', container, 'agent', 'configcheck'],
        capture=True, check=True,
    )
    assert 'redisdb' in configcheck.stdout
    assert 'host: 127.0.0.1' in configcheck.stdout
    assert 'port: 6379' in configcheck.stdout

    status = run_command(
        ['docker', 'exec', container, 'agent', 'status', '--json'],
        capture=True, check=True,
    )
    checks = json.loads(status.stdout).get('runnerStats', {}).get('Checks', {}).get('redisdb', {})
    assert checks
    info = next(iter(checks.values()))
    assert info['TotalRuns'] >= 1
    assert info['TotalErrors'] == 0
    assert info['TotalServiceChecks'] >= 1
```

The fixture polls this assertion (60 attempts × 2s) before the test runs.
The `redisdb` config being scheduled with `host: 127.0.0.1, port: 6379`
proves cel://process matched and substituted `%%host%%`. The non-zero
TotalRuns/TotalServiceChecks with no errors prove the running agent
actually ran the check successfully.

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

Add a paragraph next to the existing autodiscovery section describing the
`py3.13-adproc-7.0` env, the agent env vars used, and the host-port +
bind-mount caveats developers will hit.

### 9. `ddev/src/ddev/e2e/agent/docker.py`

Two small extensions:

- Mount any `auto_conf*.yaml` from the integration's `data/` directory (not
  just `auto_conf.yaml`) so the new `auto_conf_process.yaml` reaches the
  agent container.
- Honour a `cap_add` metadata key from `dd_environment` so integrations can
  request Linux capabilities at agent start.

## Verification

Two independent signals both must pass:

1. The fixture's configcheck assertion: the running agent's
   `agent configcheck` output contains `redisdb` with `host: 127.0.0.1` and
   `port: 6379` within ~120s.
2. The fixture's status-JSON assertion: the running agent has at least one
   successful run of redisdb (`TotalRuns >= 1`, `TotalErrors == 0`,
   `TotalServiceChecks >= 1`).

Two-direction sanity check on first implementation:

1. With the new `auto_conf_process.yaml` (process.cmdline.contains
   ("redis-server")), the test passes.
2. With `process.cmdline.contains("redis-foo")` substituted in
   `auto_conf_process.yaml`, the fixture times out and the test fails. This
   confirms the test exercises the source-tree file, not the agent image's
   bundled copy. Restore via `git checkout` + `ddev env stop` +
   `ddev env start` (the bind-mount inode caveat applies).

Plus a third pass: the existing `py3.13-ad-7.0` container e2e
(`test_e2e_autodiscovery_default_port`) must still pass, proving the file
split keeps container autodiscovery unchanged.

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
- `system-probe-lite` doesn't get `CAP_SYS_PTRACE` / `CAP_DAC_READ_SEARCH`
  → the discovery check can't read other processes' /proc entries, no
  service is detected, the cel://process listener has nothing to match.
  The agent logs `WARN | Not all required capabilities were available;
  service discovery may be impaired`.

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
  with containers > processes — and a CEL-typed config that doesn't match
  the candidate's type drops the candidate from the match list
  (`comp/core/autodiscovery/listeners/common_filter.go:24`). This is what
  forced the file split: putting `cel_selector.processes` in the same file
  as `ad_identifiers: [redis]` made the docker listener's redis-container
  match fail the CEL filter and disappear. Two files keep the listeners'
  match paths fully independent. If the agent later treats CEL filters as
  additive-when-present, a follow-up can collapse both files into one.
- `DD_AUTOCONFIG_EXCLUDE_FEATURES=docker` and `DD_EXTRA_LISTENERS=process`
  require an agent build that supports CEL process autodiscovery. The wiki
  experiment used `datadog/agent:7.78.0`. ddev's default agent image
  (`registry.datadoghq.com/agent-dev:master-py3`) is newer and should include
  the feature; if not, the test fails at `autodiscovery_ready` and we'd need
  to pin a specific `--agent-build`.

[priority]: https://github.com/DataDog/datadog-agent/blob/03f5a8be52a0dc3adb9d7abbef04150fe1ae5f4e/comp/core/autodiscovery/integration/matching_program.go#L56-L60
