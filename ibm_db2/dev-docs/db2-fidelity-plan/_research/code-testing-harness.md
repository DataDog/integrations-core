# Code Research: DBM Integration Testing Harness (integrations-core)

Scope: how `ibm_db2`, `postgres`, `mysql`, `sqlserver` integrations are TESTED, so the
implementing agent can WRITE and RUN tests for the Db2 fidelity work (target Db2 12.1, live
container `icr.io/db2_community/db2:12.1.4.0`). All file paths are absolute. Code citations are
to `/home/bits/dd/integrations-core/...`. This is raw input, not a summary.

> Key takeaway for the implementer: there is NO `assert_event_platform_event` helper. DBM payloads
> (samples/metrics/activity/metadata) are validated by pulling raw JSON via
> `aggregator.get_event_platform_events("<track>")` and asserting on the parsed dicts. Classic
> metrics use `aggregator.assert_metric(...)` + `aggregator.assert_metrics_using_metadata(...)`.
> The existing `ibm_db2` suite is metrics-only and has none of the DBM scaffolding yet.

---

## 1. Directory layout of a check's `tests/`

### 1.1 Current `ibm_db2/tests/` (metrics-only baseline — what exists today)
`/home/bits/dd/integrations-core/ibm_db2/tests/`
- `__init__.py` — license header only.
- `common.py` — constants + `CONFIG` instance dict + `E2E_METADATA`.
- `conftest.py` — `dd_environment` (session) + `instance` fixtures, `DbManager` class.
- `docker/docker-compose.yaml` — the container harness (one service).
- `metrics.py` — plain Python lists of metric-name strings (`STANDARD`, `BUFFERPOOL`, `TABLESPACE`).
- `test_unit.py` — `pytestmark = pytest.mark.unit`; pure-mock tests, no container.
- `test_integration.py` — `pytestmark = pytest.mark.integration`; uses `dd_environment`.
- `test_integration_e2e.py` — mixes `@pytest.mark.integration` and `@pytest.mark.e2e`.
- `test_bench.py` — benchmark (`benchmark` fixture) under `envs.bench`.
- `README.md` — macOS clidriver note only.

### 1.2 Reference DBM suites (the model to expand toward)
`postgres/tests/`, `mysql/tests/`, `sqlserver/tests/` add files such as:
`test_statements.py` (dbm-metrics + dbm-samples), `test_query_activity.py` /
`test_activity.py` (dbm-activity), `test_metadata.py` / `test_schemas.py` (dbm-metadata),
`utils.py` (connection + thread helpers), and `compose/` dirs with multiple compose files +
SQL/shell init resources. Postgres splits classic metrics into `test_pg_integration.py` and DBM
into the above; mysql splits `test_mysql.py` (classic) from `test_statements.py`,
`test_query_activity.py`, `test_metadata.py`.

---

## 2. The docker harness (`tests/docker/docker-compose.yaml` + conftest)

### 2.1 Existing `ibm_db2` harness
`/home/bits/dd/integrations-core/ibm_db2/tests/docker/docker-compose.yaml`:
```yaml
services:
  ibm_db2:
    # Official image does not yet support 11.1
    image: taskana/db2:${DB2_VERSION}
    container_name: ibm_db2
    ports:
      - "50000:50000"
    environment:
      - LICENSE=accept
```
Notes for the implementer:
- Image is the community `taskana/db2`, NOT the IBM `icr.io/db2_community/db2` image our live
  stack uses (`local-dev/db2/docker-compose.yaml:3`). For Db2 12.1 fidelity tests you will likely
  switch this to `icr.io/db2_community/db2:${DB2_VERSION}` (12.1.4.0), and that image needs
  `privileged: true`, `ipc: host`, `LICENSE=accept`, `DB2INSTANCE=db2inst1`,
  `DB2INST1_PASSWORD=...`, `DBNAME=...` (see live compose lines 6-16). The current
  `taskana/db2` image does not require those.
- `container_name: ibm_db2` is hard-referenced by `conftest.py` `docker exec ibm_db2 ...`.
- Port 50000 maps to host 50000; `common.py` `PORT='50000'`.

### 2.2 `common.py` constants (`/home/bits/dd/integrations-core/ibm_db2/tests/common.py`)
```python
from datadog_checks.dev import get_docker_hostname, get_here
HERE = get_here()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')
HOST = get_docker_hostname()      # 'localhost' on CI/local
PORT = '50000'
DB = 'datadog'
USERNAME = 'db2inst1'
PASSWORD = 'db2inst1-pwd'
DB2_VERSION = os.getenv('DB2_VERSION')
CONFIG = {'db': DB, 'username': USERNAME, 'password': PASSWORD,
          'host': HOST, 'port': PORT, 'tags': ['foo:bar']}
E2E_METADATA = {
    'env_vars': {'IBM_DB_INSTALLER_URL': 'https://ddintegrations.blob.core.windows.net/ibm-db2/'},
    'docker_volumes': ['{}/requirements.txt:/dev/requirements.txt'.format(os.path.join(HERE,'docker'))],
    'start_commands': ['apt-get update',
                       'apt-get install -y build-essential libxslt-dev',
                       'pip install ibm_db==3.2.6'],
}
```
- `E2E_METADATA` injects the `ibm_db` driver build/install into the live Agent container for e2e
  (the stock Agent lacks it — same problem the live stack solves with `Dockerfile.agent`).
- `DB2_VERSION` is set via hatch env-vars (see §6). Tests that need version-conditional behavior
  read this (e.g. `test_metadata` in `test_integration.py`).

### 2.3 `conftest.py` fixtures (`/home/bits/dd/integrations-core/ibm_db2/tests/conftest.py`)
```python
@pytest.fixture(scope='session')
def dd_environment():
    db = DbManager(CONFIG)
    with docker_run(COMPOSE_FILE, conditions=[db.initialize, WaitFor(db.connect)], attempts=2):
        yield CONFIG, E2E_METADATA

@pytest.fixture
def instance():
    return deepcopy(CONFIG)
```
`DbManager.initialize()` runs a sequence of `run_command('docker exec ibm_db2 su - db2inst1 -c "db2 -c ..."')`:
1. `create db datadog using codeset utf-8 territory us`
2. enable monitoring: `update dbm cfg using HEALTH_MON on`; `DFT_MON_STMT on`; `DFT_MON_LOCK on`;
   `DFT_MON_TABLE on`; `DFT_MON_BUFPOOL on`
3. trigger a backup (so `ibm_db2.backup.latest` has data): `quiesce instance db2inst1 restricted
   access immediate force connections`; `deactivate db datadog`; `backup db datadog`;
   `activate db datadog`; `unquiesce instance db2inst1`

`DbManager.connect()` opens+closes an `ibm_db.connect(target, user, pwd)` using
`IbmDb2Check.get_connection_data(...)`. This is the `WaitFor` readiness condition.

> IMPORTANT for Db2 12.1 / DBM: to test DBM features you'll need extra init in `DbManager.initialize`
> (or a new compose resource script) to: create the monitoring user/grants, ensure the WLM/event
> monitor or `MON_GET_*` table functions used by the DBM collector are available, and seed schema +
> workload tables. The live stack does this via `local-dev/db2/primary/custom/` scripts (root-run
> post-setup) — mirror that pattern. The `attempts=2` + `start_period`/healthcheck timing matters:
> the IBM image first-boot can take minutes (live healthcheck uses `start_period: 480s`).

### 2.4 `docker_run` / `WaitFor` helpers (the harness primitives)
- `datadog_checks.dev.docker_run` — `/home/bits/dd/integrations-core/datadog_checks_dev/datadog_checks/dev/docker.py:108`.
  Signature (key kwargs): `docker_run(compose_file=None, wait_for_health=True, build=False,
  service_name=None, conditions=None, env_vars=None, attempts=None, attempts_wait=1, sleep=None,
  endpoints=None, log_patterns=None, mount_logs=False, ...)`. It `up`s the compose file, waits for
  `conditions` (each a callable or `LazyFunction`), `yield`s, then tears down.
- `WaitFor` — `/home/bits/dd/integrations-core/datadog_checks_dev/datadog_checks/dev/conditions.py:17`
  (`class WaitFor(LazyFunction)`; `WaitForPortListening` at :219). `WaitFor(fn, attempts=..., wait=...)`
  retries `fn` until it stops raising.
- `run_command` — `/home/bits/dd/integrations-core/datadog_checks_dev/datadog_checks/dev/subprocess.py:17`:
  `run_command(command, capture=None, check=False, encoding='utf-8', shell=False, env=None)`.
- `env_vars=` pattern: postgres passes `POSTGRES_IMAGE`, `POSTGRES_LOCALE`, `PGDATA` into compose
  (`postgres/tests/conftest.py:73-81`). For Db2 you'd pass `DB2_VERSION` (already via hatch env-var,
  but can also pass through `docker_run(env_vars=...)`).

### 2.5 `--skip-env` pattern (fast local DBM dev — copy this for Db2)
Postgres lets you reuse a manually-started compose so you don't re-spin the slow container each run
(`postgres/tests/conftest.py:62-99`):
```python
@pytest.fixture(scope='session')
def dd_environment(e2e_instance, skip_env):
    if skip_env:
        yield e2e_instance, E2E_METADATA
        return
    ...docker_run(...)...

def pytest_addoption(parser):
    parser.addoption("--skip-env", action="store_true", default=False, help="skip environment setup")

@pytest.fixture(scope='session')
def skip_env(request):
    return request.config.getoption("--skip-env")
```
This is HIGHLY recommended for Db2 because container startup is multi-minute. Then:
`docker compose -f tests/docker/docker-compose.yaml up -d` once, then
`ddev test ibm_db2 -- --skip-env`.

---

## 3. Classic metric-assertion pattern

### 3.1 `tests/metrics.py` — plain lists of metric-name strings
`/home/bits/dd/integrations-core/ibm_db2/tests/metrics.py` defines three module-level lists:
`STANDARD` (49 metrics), `BUFFERPOOL` (20), `TABLESPACE` (4). Excerpt:
```python
STANDARD = [
    'ibm_db2.application.active', 'ibm_db2.application.executing',
    'ibm_db2.connection.active', 'ibm_db2.connection.max', 'ibm_db2.connection.total',
    'ibm_db2.lock.dead', 'ibm_db2.lock.waiting', 'ibm_db2.lock.active', 'ibm_db2.lock.wait',
    'ibm_db2.lock.pages', 'ibm_db2.lock.timeouts', 'ibm_db2.backup.latest',
    'ibm_db2.row.modified.total', 'ibm_db2.row.reads.total', 'ibm_db2.row.returned.total',
    'ibm_db2.bufferpool.column.reads.physical', ... 'ibm_db2.bufferpool.hit_percent',
    'ibm_db2.tablespace.size','ibm_db2.tablespace.usable','ibm_db2.tablespace.used',
    'ibm_db2.tablespace.utilized',
    'ibm_db2.log.used','ibm_db2.log.available','ibm_db2.log.utilized',
    'ibm_db2.log.reads','ibm_db2.log.writes',
]
BUFFERPOOL = [ ... 20 bufferpool.* names ... ]
TABLESPACE = [ 'ibm_db2.tablespace.size','...usable','...used','...utilized' ]
```
sqlserver instead imports named tuples of metric definitions from
`datadog_checks.sqlserver.const` (`sqlserver/tests/test_metrics.py:9-31`,
e.g. `INSTANCE_METRICS`, `DATABASE_STATS_METRICS`). Both patterns are acceptable; the `ibm_db2`
plain-list style is what to extend for new Db2 12.1 metrics.

### 3.2 The standard "all metrics present + tagged" test
`/home/bits/dd/integrations-core/ibm_db2/tests/test_integration_e2e.py`:
```python
def _assert_standard(aggregator):
    aggregator.assert_service_check('ibm_db2.can_connect', AgentCheck.OK)
    for metric in metrics.STANDARD:
        aggregator.assert_metric_has_tag(metric, 'db:datadog')
        aggregator.assert_metric_has_tag(metric, 'foo:bar')
    aggregator.assert_all_metrics_covered()
```
- `assert_metric_has_tag(name, tag, count=None, at_least=1)` — metric present AND carries `tag`
  (`stubs/aggregator.py:218`).
- `assert_all_metrics_covered()` — FAILS if any submitted metric was never asserted
  (`stubs/aggregator.py:417`). This is the gate that forces you to list every new metric in
  `metrics.py`. Implication: when you add Db2 12.1 metrics to the check, you MUST add them to
  `metrics.STANDARD` (or the test fails on "metrics not asserted").

### 3.3 `assert_metric` full signature & semantics
`/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/stubs/aggregator.py:318`:
```python
def assert_metric(self, name, value=None, tags=None, count=None, at_least=1,
                  hostname=None, metric_type=None, device=None, flush_first_value=None)
```
- `metric_type` is an INT enum (`stubs/aggregator.py:70-82`):
  `gauge=0, rate=1, count=2, monotonic_count=3, counter=4, histogram=5, historate=6`.
  Constants: `AggregatorStub.GAUGE/RATE/COUNT/MONOTONIC_COUNT/...`. Example usage in
  `ibm_db2/tests/test_integration.py:78` uses `metric_type=3` (monotonic_count).
- `tags=` requires an EXACT, full tag set match (sorted comparison) — see
  `test_custom_queries` (`test_integration.py:77-81`) asserting
  `tags=['db:datadog','foo:bar','test:ibm_db2','tablespace:USERSPACE1']`.
- Other helpers: `assert_metric_has_tag_prefix(name, prefix)` (`:620`) — used for per-bufferpool /
  per-tablespace tags (`test_integration.py:31-33`, `:41-43`); `assert_metric_has_tags(name, [tags])`
  (`:214`).

### 3.4 `assert_service_check`
`stubs/aggregator.py:375`: `assert_service_check(name, status=None, tags=None, count=None,
at_least=1, hostname=None, message=None)`. Status constants are on the check class:
`IbmDb2Check.OK / WARNING / CRITICAL / UNKNOWN` and `IbmDb2Check.SERVICE_CHECK_CONNECT`
(value `'ibm_db2.can_connect'`). Example: `aggregator.assert_service_check(check.SERVICE_CHECK_CONNECT,
count=1, status=check.OK)` (`test_integration.py:33`).

### 3.5 Events (Agent events, not DBM event-platform)
`assert_event(msg_text, count=None, at_least=1, exact_match=True, tags=None, **kwargs)`
(`stubs/aggregator.py:251`). Used for the tablespace state-change event:
`aggregator.assert_event('State of \`USERSPACE1\` changed from \`test\` to \`NORMAL\`.')`
(`test_integration.py:52`). This is the Agent event bus, NOT a DBM event-platform track.

### 3.6 metadata.csv-driven assertion
`assert_metrics_using_metadata(metadata_metrics, check_metric_type=True,
check_submission_type=False, exclude=None, check_symmetric_inclusion=False)`
(`stubs/aggregator.py:428`). Fails if a submitted metric is absent from `metadata.csv`, and (with
`check_metric_type`) that the in-app type matches. Load the CSV with
`from datadog_checks.dev.utils import get_metadata_metrics`. Usage:
`sqlserver/tests/test_e2e.py:55`, `mysql/tests/test_mysql.py:95`, `postgres/tests/common.py:536`.
`ibm_db2`'s `metadata.csv` header is:
`metric_name,metric_type,interval,unit_name,per_unit_name,description,orientation,integration,short_name,curated_metric`
(`/home/bits/dd/integrations-core/ibm_db2/metadata.csv:1`). Example rows establish the type/unit
contract you must keep consistent when adding metrics, e.g.:
- `ibm_db2.application.active,gauge,,connection,,...`
- `ibm_db2.bufferpool.column.reads.logical,count,,get,,...`
- `ibm_db2.backup.latest,gauge,,second,,...`
The `ibm_db2` suite does NOT currently call `assert_metrics_using_metadata` — adding it is a good
fidelity improvement (catches metrics-without-metadata and type mismatches).

---

## 4. DBM payload assertions (dbm-samples / dbm-metrics / dbm-activity / dbm-metadata)

There is **no** `assert_event_platform_event` stub method. DBM payloads are submitted by the check
via `database_monitoring_query_sample/metrics/activity/metadata(...)` (base framework) and captured
by the aggregator stub:
- `submit_event_platform_event(check, check_id, raw_event, event_type)` →
  `self._event_platform_events[event_type].append(raw_event)` (`stubs/aggregator.py:129`).
- Retrieval: `get_event_platform_events(event_type, parse_json=True)` →
  `[json.loads(e) ... for e in self._event_platform_events[event_type]]` (`stubs/aggregator.py:190`).

The four track names (strings passed to `get_event_platform_events`): `"dbm-samples"`,
`"dbm-metrics"`, `"dbm-activity"`, `"dbm-metadata"`. (Db2's check should pick `ddsource:"ibm_db2"`
to match its integration name, mirroring postgres `"postgres"` / mysql `"mysql"`.)

### 4.1 dbm-metrics (query metrics / pg_stat_statements-style) — postgres model
`/home/bits/dd/integrations-core/postgres/tests/test_statements.py:273-336`:
```python
events = aggregator.get_event_platform_events("dbm-metrics")
assert len(events) == 2
event = events[1]                       # events[0] is the initial settings-load run
assert event['host'] == 'stubbed.hostname'
assert event['timestamp'] > 0
assert event['ddagentversion'] == datadog_agent.get_version()
assert event['min_collection_interval'] == dbm_instance['query_metrics']['collection_interval']
expected_dbm_metrics_tags = set(_get_expected_tags(check, dbm_instance, with_host=False))
assert set(event['tags']) == expected_dbm_metrics_tags
# rows live under a vendor-namespaced key:
matching_rows = [r for r in event['postgres_rows'] if r['query_signature'] == query_signature]
assert len(matching_rows) == 1
row = matching_rows[0]
assert row['calls'] == 1
assert row['datname'] == dbname
assert row['rolname'] == username
assert row['query'] == expected_query
for col in (set(row.keys()) & PG_STAT_STATEMENTS_METRICS_COLUMNS):
    assert type(row[col]) in (float, int)
```
Vendor-namespaced rows key: postgres uses `event['postgres_rows']`; mysql uses
`event['mysql_rows']`. **Db2 should choose an analogous key (e.g. `event['db2_rows']` or
`ibm_db2_rows`) — decide and keep consistent across check + tests.**
`query_signature` is computed in-test with
`from datadog_checks.base.utils.db.sql import compute_sql_signature` (`test_statements.py:17`,
`:291`). Also asserts classic counters exist:
`assert len(aggregator.metrics("postgresql.pg_stat_statements.max")) != 0` (`:285`).

### 4.2 dbm-samples — FQT (full query text) + plan events
`/home/bits/dd/integrations-core/postgres/tests/test_statements.py:287-333` (FQT) and `:782-844` (plan):
```python
dbm_samples = aggregator.get_event_platform_events("dbm-samples")
fqt_events = [e for e in dbm_samples if e.get('dbm_type') == 'fqt']
matching = [e for e in fqt_events if e['db']['query_signature'] == query_signature]
fqt_event = matching[0]
assert fqt_event['ddagentversion'] == datadog_agent.get_version()
assert fqt_event['ddsource'] == "postgres"
assert fqt_event['db']['statement'] == expected_query
assert fqt_event['postgres']['datname'] == dbname     # vendor block keyed by 'postgres'
assert fqt_event['postgres']['rolname'] == username
assert fqt_event['timestamp'] > 0
assert fqt_event['host'] == 'stubbed.hostname'
assert set(fqt_event['ddtags'].split(',')) == expected_dbm_metrics_tags | {
    "db:" + fqt_event['postgres']['datname'], "rolname:" + fqt_event['postgres']['rolname']}
```
Plan-sample assertions (`:782-826`):
```python
matching = [e for e in dbm_samples
            if e['db']['statement'].encode("utf-8") in expected_query.encode("utf-8")
            and e['dbm_type'] == 'plan']
event = matching[0]
assert event['db']['query_truncated'] == expected_statement_truncated
assert set(event['ddtags'].split(',')) == set(tags)
assert event['db']['plan']['definition'] is not None, "missing execution plan"
assert 'Plan' in json.loads(event['db']['plan']['definition']), "invalid json execution plan"
assert event['duration']
# error path -> a stat counter is emitted:
aggregator.assert_metric("dd.postgres.statement_samples.error",
    tags=tags + [expected_error_tag, 'agent_hostname:stubbed.hostname'], hostname='stubbed.hostname')
```
`dbm_type` discriminators seen in postgres: `'fqt'` (full query text), `'plan'` (obfuscated plan
sample), `'rqp'` (raw query plan, when `collect_raw_query_statement` enabled), `'rqt'` (raw query
text). **For Db2, decide the analogous `dbm_type` values + the vendor block key.**

### 4.3 dbm-activity — connection / blocking activity
mysql model (closest to a separate-binary DB), `mysql/tests/test_query_activity.py:113-165`:
```python
dbm_activity = aggregator.get_event_platform_events("dbm-activity")
assert len(dbm_activity) == 1
activity = dbm_activity[0]
assert activity['host'] == 'stubbed.hostname'
assert activity['dbm_type'] == 'activity'
assert activity['ddsource'] == 'mysql'
assert activity['ddagentversion']
assert sorted(activity['ddtags']) == sorted(expected_tags)
assert type(activity['collection_interval']) in (float, int)
assert activity['mysql_activity']                       # vendor rows key
blocked_row = next(r for a in dbm_activity for r in a['mysql_activity']
                   if r.get('query_signature') == query_signature)
assert blocked_row['processlist_user'] == 'fred'
assert blocked_row['sql_text'] == expected_sql_text
assert blocked_row['query_truncated'] == expected_query_truncated
```
postgres activity adds `event['postgres_activity']` + `event['postgres_connections']`, blocking-pid
assertions, ISO timestamp check, and `assert 'query' not in bobs_query` (obfuscation guarantee) —
`postgres/tests/test_statements.py:1101-1188`. Db2 activity rows key e.g. `event['db2_activity']`.

### 4.4 dbm-metadata (schema collection)
Same retrieval pattern: `aggregator.get_event_platform_events("dbm-metadata")`. See
`postgres/tests/test_schemas.py` and `mysql/tests/test_metadata.py` (kind `"pg_databases"` /
schema payloads under vendor keys). Not detailed here; follow the same dict-assertion approach.

### 4.5 The `dbm_instance` fixture pattern (run DBM synchronously in tests)
postgres `dbm_instance` (`/home/bits/dd/integrations-core/postgres/tests/test_statements.py:458-471`):
```python
@pytest.fixture
def dbm_instance(pg_instance):
    pg_instance['dbm'] = True
    pg_instance['min_collection_interval'] = 0.2
    pg_instance['query_samples'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.2}
    pg_instance['query_activity'] = {'enabled': True, 'collection_interval': 0.2}
    pg_instance['query_metrics'] = {'enabled': True, 'run_sync': True,
                                    'collection_interval': CLOSE_TO_ZERO_INTERVAL}  # 1e-7
    pg_instance['collect_settings'] = {'enabled': False}
    return pg_instance
```
mysql `dbm_instance` (`mysql/tests/test_query_activity.py:37-49`) sets `instance['dbm']=True`,
`query_activity={'enabled':True,'run_sync':True,'collection_interval':0.1}`, disables the others.
Critical knobs for deterministic tests:
- `'run_sync': True` — runs the async DBM job inline so the payload exists right after the check run.
- tiny `collection_interval` (postgres uses `CLOSE_TO_ZERO_INTERVAL = 0.0000001`,
  `test_statements.py:51`) — prevents `DBMAsyncJob` from skipping back-to-back runs.
- `'dbm': True` at the instance level enables DBM.

### 4.6 Thread / orphaned-job management for DBM tests
mysql resets the shared executor between tests (`mysql/tests/test_query_activity.py:30-34`):
```python
@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()
```
(`from datadog_checks.base.utils.db.utils import DBMAsyncJob`, `:20`.) postgres instead uses
`run_one_check(check, cancel=True)` (`postgres/tests/utils.py:137-144`) which calls
`check.run()` then `check.cancel()` (joins threads / nulls futures), and the
`integration_check` fixture cancels all created checks at teardown
(`postgres/tests/conftest.py:109-123`). Adopt one of these patterns for Db2 so async jobs don't
leak between tests.

### 4.7 Helpers worth copying
- `compute_sql_signature` — `from datadog_checks.base.utils.db.sql import compute_sql_signature`
  (compute expected `query_signature` in-test).
- `_get_expected_tags(check, instance, with_host=False, **kwargs)` — postgres builds the canonical
  DBM tag set (`postgres/tests/common.py:155-184`): instance tags + `port:` +
  `database_hostname:` + `database_instance:` + `replication_role:` (+ optional version/cluster/db).
  mysql inlines the equivalent tuple (`test_query_activity.py:121-133`). Db2 needs its own
  `_get_expected_tags` reflecting the Db2 tag scheme.
- thread helpers in `postgres/tests/utils.py`: `run_query_thread`, `lock_table`, `kill_session`,
  `_wait_for_value`, `WaitGroup` (go-style sync) — used to create blocking sessions for activity
  tests. mysql uses `concurrent.futures.thread.ThreadPoolExecutor` + a blocking `FOR UPDATE` txn
  (`test_query_activity.py:97-111`).
- `datadog_agent.get_version()` (the `datadog_agent` stub fixture) for `ddagentversion` asserts.
- `mock.patch.object(datadog_agent, 'obfuscate_sql', ...)` to inject deterministic obfuscation +
  metadata into samples/metrics tests (`postgres/tests/test_statements.py:898-899`).

---

## 5. unit vs integration vs e2e markers

Markers are registered by the dev pytest plugin
(`/home/bits/dd/integrations-core/datadog_checks_dev/datadog_checks/dev/plugin/pytest.py:456-467`):
```python
TestType = namedtuple('TestType', 'name description filepath_match')
TEST_TYPES = (
    TestType('unit', 'marker for unit tests', 'test_unit'),
    TestType('integration', 'marker for integration tests', 'test_integration'),
    TestType('e2e', 'marker for end-to-end tests', 'test_e2e'),
)
# also registered: 'latest_metrics' (run with --run-latest-metrics), pytest.py:469,472-479
```
How each check applies them:
- **unit** (no container; pure mock): `pytestmark = pytest.mark.unit` at module top
  (`ibm_db2/tests/test_unit.py:11`). Run with `ddev test ibm_db2 -- -m unit`.
- **integration** (needs `dd_environment` container; runs the check in-process against the DB):
  `pytestmark = pytest.mark.integration` (`ibm_db2/tests/test_integration.py:13`), and each test
  uses `@pytest.mark.usefixtures('dd_environment')`. Postgres/mysql apply both via a module-level
  list: `pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]`
  (`postgres/tests/test_statements.py:49`).
- **e2e** (runs against a LIVE Agent in a container; only these run under `ddev env test`):
  `@pytest.mark.e2e` on the function (`ibm_db2/tests/test_integration_e2e.py:21`,
  `postgres/tests/test_e2e.py:11`). Uses the `dd_agent_check` fixture (skips if not in e2e mode,
  `plugin/pytest.py:166-167`).
- A single file can mix integration + e2e (`ibm_db2/tests/test_integration_e2e.py`):
  `test_standard` is `@pytest.mark.integration`+`usefixtures('dd_environment')`; `test_e2e` is
  `@pytest.mark.e2e` and calls `dd_agent_check(instance, rate=True)`.

Per-check pytest config: `datadog_checks_dev/setup.cfg` has
`[tool:pytest] addopts = "--ignore=tests/tooling"; testpaths = tests`. `ibm_db2` has none of its own
beyond what hatch/ddev inject.

---

## 6. hatch test environments (`hatch.toml`)

### 6.1 Existing `ibm_db2/hatch.toml` (`/home/bits/dd/integrations-core/ibm_db2/hatch.toml`)
```toml
[env.collectors.datadog-checks]

[[envs.default.matrix]]
python = ["3.13"]
version = ["11.1"]                 # <-- only 11.1 today; ADD "12.1" for the fidelity work

[envs.default.env-vars]
DB2_VERSION = "{matrix:version:11.1}"
IBM_DB_INSTALLER_URL = "https://ddintegrations.blob.core.windows.net/ibm-db2/"

[envs.default]
dependencies = [
  "ibm_db==3.0.1; python_version < '3.0'",
  "ibm_db==3.2.6; python_version > '3.0'",
]

[envs.bench]
```
To test Db2 12.1 you must add a matrix `version` entry (and ensure the compose image tag resolves):
e.g. `version = ["11.1", "12.1"]`. `{matrix:version}` flows into the `DB2_VERSION` env-var which the
compose file interpolates (`image: ...:${DB2_VERSION}`) and `common.py` reads
(`DB2_VERSION = os.getenv('DB2_VERSION')`). Note: the `taskana/db2` image may not publish a `12.1`
tag — switching to `icr.io/db2_community/db2:12.1.4.0` likely also requires the env-var to carry the
full tag, OR an `[envs.default.overrides] matrix.version.env-vars` block (see §6.2) to map
`12.1` → `12.1.4.0`.

### 6.2 Reference hatch patterns (postgres / mysql / sqlserver)
- The `[env.collectors.datadog-checks]` line wires in the ddev/hatch test scaffolding.
  postgres/mysql/sqlserver add `base-package-features = ["deps","db","json"]` (pulls DBM extras of
  `datadog-checks-base`). **Db2 will need `["deps","db","json"]` once it uses the DBM framework**
  (currently `ibm_db2/hatch.toml` has none — fine for metrics-only, insufficient for DBM).
- Multi-axis matrices: postgres `version = ["9.6","10.0",...,"18.0"]` × `locale` with
  `[envs.default.overrides] matrix.version.env-vars` to map matrix value → `POSTGRES_VERSION`
  (`postgres/hatch.toml`). mysql maps `version` → `COMPOSE_FILE` selection
  (`mysql/hatch.toml` `[envs.default.overrides]`). sqlserver maps `version` (year) → multiple
  env-vars incl. `SQLSERVER_IMAGE_TAG` with platform/`if` guards. Use the
  `matrix.version.env-vars` override mechanism to map Db2 `12.1` → image tag `12.1.4.0`.
- `[envs.latest.env-vars]` defines a "latest" env (postgres `POSTGRES_VERSION=latest`, mysql
  `MYSQL_VERSION=latest`). Tests marked `latest_metrics` only run there + `--run-latest-metrics`.
- mypy: `check-types`/`mypy-files`/`mypy-deps` keys (postgres/mysql) — type-check selected files.

---

## 7. Exact `ddev test` / `ddev env` (e2e) commands

Source: `/home/bits/dd/integrations-core/docs/developer/testing.md`,
`/home/bits/dd/integrations-core/docs/developer/e2e.md`.

### 7.1 `ddev test` (unit + integration, env management via hatch)
- List available envs: `ddev test ibm_db2 -l` (or `--list`).
- Run ALL default-matrix envs (spins compose per env, runs unit+integration, tears down):
  `ddev test ibm_db2`
- Select specific env(s) by suffix after `:` (comma-sep):
  `ddev test ibm_db2:py3.13-12.1`  /  `ddev test ibm_db2:py3.13-11.1,py3.13-12.1`
- Coverage: `ddev test ibm_db2 -c` (`--cov`).
- Lint only: `ddev test ibm_db2 -s` (`--lint`); format: `ddev test ibm_db2 -fs` (`--fmt`).
- Forward args to pytest after `--`:
  - only unit (no container): `ddev test ibm_db2 -- -m unit`
  - only integration: `ddev test ibm_db2 -- -m integration`
  - reuse a manually-started container (if `--skip-env` is wired per §2.5):
    `ddev test ibm_db2 -- --skip-env`
  - single test / debug: `ddev test ibm_db2 -- tests/test_statements.py -k test_activity -x --pdb`
- If no integration name is given, ddev tests only checks changed vs `master` (CI behavior;
  Markdown-only diffs test nothing) — `docs/developer/testing.md:66-74`.

### 7.2 `ddev env` (e2e against a live Agent)
- Show envs: `ddev env show ibm_db2` (only envs that run tests appear).
- Start (spins compose + live Agent container, mounts config):
  `ddev env start ibm_db2 py3.13-12.1`
  - dev integration code (mount + live reload): add `--dev`
  - modified base package: add `--base` (implies `--dev`)
  - pick Agent build: `-a registry.datadoghq.com/agent:7.78.0` (`--agent`)
- Run e2e tests (ONLY `@pytest.mark.e2e`, against the live Agent):
  `ddev env test ibm_db2 py3.13-12.1`
- Invoke the Agent directly:
  - status: `ddev env agent ibm_db2 py3.13-12.1 status`
  - run check (integration arg may be omitted): `ddev env agent ibm_db2 py3.13-12.1 check`
  - debug: `ddev env agent ibm_db2 py3.13-12.1 check --log-level debug`
  - benchmark/raw output: `... check -b 0`
- Reload config after editing the mounted yaml: `ddev env reload ibm_db2 py3.13-12.1`
- Stop / clean up: `ddev env stop ibm_db2 py3.13-12.1` (un-stopped envs persist in `ddev env show`).

### 7.3 How fixtures behave under each mode
- `aggregator` fixture (`plugin/pytest.py:39-53`) returns the global `AggregatorStub`, `reset()` each
  test. `datadog_agent` fixture (`:56-67`) returns the datadog_agent stub.
- `dd_run_check(check, extract_message=False, cancel=True)` (`:240-261`) runs `check.run()`,
  re-raises check errors, and cancels created checks at teardown (good for DBM async jobs).
  `ibm_db2/tests/test_integration.py` uses it heavily.
- `dd_agent_check(config=None, **kwargs)` (`:164-237`) — e2e only; SKIPS unless `e2e_testing()`
  (`:166-167`). Shells out to `ddev env agent <check> <env> check --json`, parses JSON, replays into
  the aggregator. Legacy kwargs `rate=`/`times=` map to `--check-rate`/`--check-times`. Usage:
  `aggregator = dd_agent_check(instance, rate=True)` (`ibm_db2/tests/test_integration_e2e.py:23`).
- `dd_environment` is session-scoped and auto-run by `dd_environment_runner` (`:70-145`) which is how
  `ddev env start` extracts the config + `E2E_METADATA` (the `start_commands`/`env_vars`/
  `docker_volumes` that install `ibm_db` into the live Agent).

---

## 8. Concrete checklist to ADD DBM tests for Db2 12.1

1. **hatch**: add `version = "12.1"` to `[[envs.default.matrix]]` in `ibm_db2/hatch.toml`; add
   `[env.collectors.datadog-checks] base-package-features = ["deps","db","json"]`; map `12.1` →
   image tag via `[envs.default.overrides] matrix.version.env-vars` if using `icr.io` image.
2. **compose**: point `tests/docker/docker-compose.yaml` at `icr.io/db2_community/db2:${DB2_VERSION}`
   with `privileged: true`, `ipc: host`, `LICENSE=accept`, `DB2INSTANCE`, `DB2INST1_PASSWORD`,
   `DBNAME` (mirror `local-dev/db2/docker-compose.yaml:2-28`); raise healthcheck `start_period`.
3. **conftest**: extend `DbManager.initialize()` (or add compose resource scripts) to enable the
   Db2 monitor switches + create the DBM monitoring user/grants + seed schema/workload tables so
   `MON_GET_*`/event-monitor data exists; add the `--skip-env` option (§2.5) and a `dbm_instance`
   fixture with `dbm:True`, `run_sync:True`, tiny `collection_interval`.
4. **metrics.py**: add every new Db2 12.1 metric name (else `assert_all_metrics_covered` fails) and
   add matching rows to `metadata.csv`; consider adding `assert_metrics_using_metadata`.
5. **DBM tests**: new files `test_statements.py` (dbm-metrics + dbm-samples), `test_activity.py`
   (dbm-activity), `test_metadata.py` (dbm-metadata). Assert via
   `aggregator.get_event_platform_events("dbm-...")` + dict checks; verify `ddsource=="ibm_db2"`,
   `dbm_type`, `host=='stubbed.hostname'`, `ddagentversion`, `ddtags`, the vendor rows key
   (choose `db2_*`), and `query_signature` via `compute_sql_signature`.
6. **markers**: `pytest.mark.unit` for mock tests, `pytest.mark.integration` +
   `usefixtures('dd_environment')` for DB-backed, `pytest.mark.e2e` for live-Agent.
7. **thread hygiene**: reset `DBMAsyncJob.executor` (mysql style) or use `run_one_check(cancel=True)`
   (postgres style) to avoid leaking async DBM jobs across tests.
8. **run**: `ddev test ibm_db2:py3.13-12.1 -- -m integration` (or `--skip-env` for a pre-started
   container); `ddev env start ibm_db2 py3.13-12.1 --dev` then `ddev env test ibm_db2 py3.13-12.1`
   for e2e.

---

## 9. Source index (absolute paths)

- ibm_db2 tests: `/home/bits/dd/integrations-core/ibm_db2/tests/{common.py,conftest.py,metrics.py,test_unit.py,test_integration.py,test_integration_e2e.py,test_bench.py,docker/docker-compose.yaml,README.md}`
- ibm_db2 config: `/home/bits/dd/integrations-core/ibm_db2/{hatch.toml,pyproject.toml,metadata.csv}`
- ibm_db2 check: `/home/bits/dd/integrations-core/ibm_db2/datadog_checks/ibm_db2/{ibm_db2.py,queries.py,utils.py}`
- aggregator stub: `/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/stubs/aggregator.py`
- dev pytest plugin (fixtures+markers): `/home/bits/dd/integrations-core/datadog_checks_dev/datadog_checks/dev/plugin/pytest.py`
- harness helpers: `/home/bits/dd/integrations-core/datadog_checks_dev/datadog_checks/dev/{docker.py,conditions.py,subprocess.py}`
- postgres DBM refs: `/home/bits/dd/integrations-core/postgres/tests/{conftest.py,common.py,utils.py,test_statements.py,test_e2e.py}`
- mysql DBM refs: `/home/bits/dd/integrations-core/mysql/tests/{common.py,test_query_activity.py,test_statements.py,test_metadata.py}` ; `/home/bits/dd/integrations-core/mysql/hatch.toml`
- sqlserver refs: `/home/bits/dd/integrations-core/sqlserver/tests/{test_metrics.py,test_e2e.py}` ; `/home/bits/dd/integrations-core/sqlserver/hatch.toml`
- docs: `/home/bits/dd/integrations-core/docs/developer/{testing.md,e2e.md,ddev/plugins.md}`
- live Db2 12.1.4 stack (image/init reference): `/home/bits/go/src/github.com/DataDog/dbm/local-dev/db2/docker-compose.yaml`
