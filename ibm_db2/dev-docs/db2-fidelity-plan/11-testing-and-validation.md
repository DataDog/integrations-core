# 11 — Testing & Validation

> **Audience.** An engineer (and an implementing AI agent) who knows the Datadog Postgres / MySQL /
> SQL Server integrations and their test suites well — `pg_stat_statements`, `DBMAsyncJob`, the
> `dbm-*` event-platform tracks, `aggregator.assert_metric`, `get_event_platform_events` — but knows
> **little about IBM Db2** and has never run the `ibm_db2` test suite. Every Db2-specific wrinkle is
> spelled out inline. This is the testing companion to
> [`10-implementation-phases.md`](10-implementation-phases.md): each implementation phase (P0–P5)
> there has a matching test section here.
>
> **Where this fits.** [`00-README.md`](00-README.md) is the index;
> [`02-current-integration-audit.md`](02-current-integration-audit.md) is the baseline check audit;
> [`10-implementation-phases.md`](10-implementation-phases.md) is the ordered execution plan;
> [`12-risks-open-questions.md`](12-risks-open-questions.md) tracks the blockers. The deep,
> line-cited raw reference is `_research/code-testing-harness.md` — when this doc summarizes, that
> file has the exact file:line citations.

> **Two contract decisions this doc follows (resolved in [`99-review-and-gaps.md`](99-review-and-gaps.md)
> — they override any contradicting research note):**
>
> 1. **`ddsource` / `dbms` / the vendor-row key are `"db2"`, NOT `"ibm_db2"`.** The backend routes
>    DBM payloads off these strings. So `event['ddsource'] == "db2"`, the rows arrays are
>    `event['db2_rows']` / `event['db2_activity']` / `event['db2_connections']`, and the check sets
>    `dbms = "db2"` explicitly (a bare `DatabaseCheck` subclass would otherwise default `dbms` to
>    `self.__class__.__name__.lower()` → `"ibmdb2check"`). **Note:** the metric *prefix*, integration
>    name, hatch env, and `ddev` target are still `ibm_db2` — only the DBM payload routing strings are
>    `db2`. `_research/code-testing-harness.md` §4 still says `"ibm_db2"` in places; trust `"db2"`.
> 2. **`execution_indicators=['num_exec_with_metrics']`** (not `num_executions`) for the statement
>    delta engine, and **`database_instance_collection_interval` defaults to 300s** (not 1800s).

---

## 0. TL;DR — the commands you will run most

```bash
# all paths/commands assume the integrations-core checkout:
cd /home/bits/dd/integrations-core

# --- regenerate config after editing assets/configuration/spec.yaml (ALWAYS this order) ---
ddev validate config ibm_db2 --sync      # rewrites data/conf.yaml.example
ddev validate models ibm_db2 --sync      # rewrites config_models/{instance,shared,defaults}.py
# (equivalently, from inside ibm_db2/:  ddev -x validate config -s  ;  ddev -x validate models -s)

# --- validate the metric catalog + assets ---
ddev validate metadata ibm_db2           # metadata.csv columns/types/units/orientation
ddev validate service-checks ibm_db2
ddev validate readmes ibm_db2
ddev validate all ibm_db2                # full CI-equivalent suite (manifest, deps, style, ...)

# --- unit / integration tests (hatch spins the Db2 container per env) ---
ddev test ibm_db2 -- -m unit             # pure-mock, no container
ddev test ibm_db2:py3.13-12.1 -- -m integration   # against the Db2 12.1.4 container
ddev test ibm_db2 --cov                  # with coverage
ddev test ibm_db2 -l                     # list available hatch envs

# --- fast local DBM dev: reuse a manually-started container (see §3.4) ---
docker compose -f ibm_db2/tests/docker/docker-compose.yaml up -d
ddev test ibm_db2 -- --skip-env -m integration

# --- e2e against a LIVE agent (only @pytest.mark.e2e tests run) ---
ddev env start ibm_db2 py3.13-12.1 --dev
ddev env test  ibm_db2 py3.13-12.1
ddev env agent ibm_db2 py3.13-12.1 check --log-level debug
ddev env stop  ibm_db2 py3.13-12.1
```

---

## 1. The test pyramid for integrations-core

Three test *types*, registered as pytest markers by the ddev plugin
(`datadog_checks_dev/datadog_checks/dev/plugin/pytest.py`); each maps to a filename convention:

| Marker | File convention | Needs a DB? | What runs the check | Run with |
|---|---|---|---|---|
| `unit` | `test_unit.py` | no — pure mocks | the check class in-process, `ibm_db` mocked | `ddev test ibm_db2 -- -m unit` |
| `integration` | `test_integration*.py` | **yes** — `dd_environment` container | `dd_run_check(check)` in-process against the real Db2 | `ddev test ibm_db2:py3.13-12.1 -- -m integration` |
| `e2e` | `test_*` with `@pytest.mark.e2e` | yes — DB **and** a live Agent container | the real Agent, via `dd_agent_check` (shells out to `ddev env agent ... check --json`) | `ddev env test ibm_db2 py3.13-12.1` |

How the markers are applied today in `ibm_db2/tests/`:

- **unit** — module-level `pytestmark = pytest.mark.unit` (`test_unit.py:11`). No fixtures touch
  Docker; `ibm_db.connect`/`ibm_db.exec_immediate` are `mock.patch`-ed.
- **integration** — module-level `pytestmark = pytest.mark.integration` (`test_integration.py:13`),
  and **every** test adds `@pytest.mark.usefixtures('dd_environment')` so the session-scoped Db2
  container is up. Postgres/mysql combine both into one module-level list:
  `pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]`.
- **e2e** — `@pytest.mark.e2e` on the function (`test_integration_e2e.py::test_e2e`). It uses the
  `dd_agent_check` fixture, which **skips automatically unless** running under `ddev env test`
  (the fixture short-circuits when `e2e_testing()` is false). A single file can mix integration +
  e2e — `test_integration_e2e.py` does exactly that today.

**Practical split for the fidelity work** (mirrors postgres/mysql):

- `test_unit.py` — keep growing the mock-only tests (connection-string building, version parse,
  obfuscation strip, delta-engine math, payload-shape unit tests that don't need a DB).
- `test_integration.py` — classic metrics (`MON_GET_*` → `aggregator.assert_metric`).
- **New DBM files** (net-new, P1+): `test_statements.py` (dbm-metrics + FQT), `test_activity.py`
  (dbm-activity), `test_metadata.py` / `test_schemas.py` (dbm-metadata), and (P3) plan-sample tests.
- `test_integration_e2e.py` — the `assert_all_metrics_covered` gate + a live-agent smoke.

### 1.1 The ddev / hatch env layout

`ibm_db2/hatch.toml` defines the test environments. Today (metrics-only):

```toml
[env.collectors.datadog-checks]

[[envs.default.matrix]]
python = ["3.13"]
version = ["11.1"]                  # <-- only 11.1 today

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

The matrix `(python, version)` produces hatch env **names** of the form `py3.13-11.1`; the
`version` axis flows into the `DB2_VERSION` env-var, which the docker-compose interpolates as the
image tag and which `tests/common.py` reads (`DB2_VERSION = os.getenv('DB2_VERSION')`).

**What the fidelity work changes in `hatch.toml`** (P0 + P5):

1. Add `"12.1"` to the matrix: `version = ["11.1", "12.1"]` (env name becomes `py3.13-12.1`).
2. Because the IBM image tag is the full `12.1.4.0` (not `12.1`), map matrix → tag with an
   overrides block:
   ```toml
   [[envs.default.matrix]]
   python = ["3.13"]
   version = ["11.1", "12.1"]

   [envs.default.overrides]
   matrix.version.env-vars = [
     { key = "DB2_VERSION", value = "11.5.9.0", if = ["11.1"] },   # see §3 note on the 11.1 image
     { key = "DB2_VERSION", value = "12.1.4.0", if = ["12.1"] },
   ]
   ```
   (postgres/mysql/sqlserver use this exact `matrix.version.env-vars` mechanism to map a friendly
   matrix value to an image tag / compose file.)
3. **DBM dependency (P1+):** once the check uses `DBMAsyncJob`/obfuscation/payload helpers, add
   ```toml
   [env.collectors.datadog-checks]
   base-package-features = ["deps", "db", "json"]
   ```
   This pulls the DBM extras of `datadog-checks-base` into the test env (postgres/mysql/sqlserver all
   set this). Without it the DBM imports fail at collection time. May also need bumping
   `datadog-checks-base>=…` in `pyproject.toml` if you use newer base helpers.

---

## 2. ddev validation commands (config models, metadata, etc.)

All run from the repo root with the integration name, or from inside `ibm_db2/` with `-x`.

### 2.1 Regenerate config_models from spec.yaml

**Source of truth is `assets/configuration/spec.yaml`.** The files
`config_models/{instance,shared,defaults}.py` and `data/conf.yaml.example` are **generated — never
hand-edit them**. (`config_models/validators.py` and `config_models/__init__.py` *are* hand-editable.)
After editing the spec — e.g. adding the P1 `dbm`, `query_metrics`, `query_activity`,
`collect_settings`, `collect_schemas`, `obfuscator_options` blocks:

```bash
ddev validate config ibm_db2 --sync     # FIRST: rewrites data/conf.yaml.example
ddev validate models ibm_db2 --sync     # THEN:  rewrites config_models/*.py
```

Order matters (config before models). Without `--sync` the commands only **check for drift** and
fail CI if the generated files are stale — which is exactly what CI does, so always re-run both with
`--sync` and commit the regenerated files alongside the spec change. Sanity-check the diff: nested
DBM option blocks in the spec should produce nested pydantic models in `instance.py` and default
functions in `defaults.py` (e.g. `instance_database_instance_collection_interval() -> 300`).

### 2.2 Validate metadata.csv

```bash
ddev validate metadata ibm_db2
```

Enforces the exact header/column order
`metric_name,metric_type,interval,unit_name,per_unit_name,description,orientation,integration,short_name,curated_metric`
and the value rules (validator: `ddev/src/ddev/cli/validate/metadata_utils.py`):

- `metric_type` ∈ **`{count, gauge, rate}`** only. **Db2 gotcha:** the check submits via
  `self.monotonic_count(...)` for cumulative `MON_GET_*` counters, but metadata.csv catalogs those as
  **`count`** (there is no `monotonic_count` metadata type). Gauges/ratios → `gauge`.
- `orientation` ∈ `{0, 1, -1}` (0 neutral, 1 higher-better, -1 lower-better).
- `unit_name` / `per_unit_name` ∈ the fixed `VALID_UNIT_NAMES` allow-list. Units already used:
  `connection, second, percent, get, lock, page, millisecond, block, read, write, row, byte`. For
  new P0 metrics: BP reads use **`get`**, writes use `write`/`page`, times use `millisecond`,
  direct I/O uses `sector`, FS space uses `byte`. **`sort` is NOT a valid unit** — verify every new
  unit against the allow-list before using it (the map docs flag this).
- `integration` must be `ibm_db2` on every row. Descriptions ≤ 400 chars; quote any description
  containing a comma.

**DBM data is NOT in metadata.csv.** Query metrics/samples/activity/plans/schemas are
event-platform payloads, not Agent metrics — they have no metadata.csv rows. Only summary health
gauges/counts the check emits via `self.gauge`/`self.count` (and the self-telemetry
`dd.ibm_db2.*` metrics) belong there.

### 2.3 Other asset validations

```bash
ddev validate service-checks ibm_db2     # if you add e.g. ibm_db2.hadr.status (P0) or a DBM check
ddev validate readmes ibm_db2            # README anchors/links (DBM setup section, P5)
ddev validate dep ibm_db2                # dependency pins
ddev validate license-headers ibm_db2    # every new .py needs the BSD header
ddev validate all ibm_db2                # run everything CI runs for this integration
ddev validate ci ibm_db2                 # CI config / labeler / codeowners
```

---

## 3. The Docker harness: extend it to Db2 12.1.4 with a seeded workload

### 3.1 What exists today (the baseline you are replacing)

`tests/docker/docker-compose.yaml` (one service):
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
- `container_name: ibm_db2` is **hard-referenced** by `conftest.py` (`docker exec ibm_db2 ...`) —
  keep the name `ibm_db2` even when you switch the image.
- `taskana/db2` is a *community* image and does **not** publish a `12.1` tag. The live DBM stack
  uses the IBM image `icr.io/db2_community/db2:12.1.4.0`.

`tests/common.py` constants: `PORT='50000'`, `DB='datadog'`, `USERNAME='db2inst1'`,
`PASSWORD='db2inst1-pwd'`, `CONFIG={db,username,password,host,port,tags:['foo:bar']}`,
`E2E_METADATA` (installs `ibm_db==3.2.6` into the live Agent for e2e).

`tests/conftest.py`:
```python
@pytest.fixture(scope='session')
def dd_environment():
    db = DbManager(CONFIG)
    with docker_run(COMPOSE_FILE, conditions=[db.initialize, WaitFor(db.connect)], attempts=2):
        yield CONFIG, E2E_METADATA
```
`DbManager.initialize()` runs a sequence of `docker exec ibm_db2 su - db2inst1 -c "db2 -c ..."`:
`create db datadog ...` → enable monitor switches (`HEALTH_MON`, `DFT_MON_STMT`, `DFT_MON_LOCK`,
`DFT_MON_TABLE`, `DFT_MON_BUFPOOL`) → quiesce/deactivate/**backup**/activate/unquiesce (so
`ibm_db2.backup.latest` has data). `DbManager.connect()` opens+closes one `ibm_db.connect` and is
the `WaitFor` readiness probe.

### 3.2 Target compose for Db2 12.1.4 (P0)

Switch the image and add the flags the IBM image needs (mirror
`/home/bits/go/src/github.com/DataDog/dbm/local-dev/db2/docker-compose.yaml`):

```yaml
services:
  ibm_db2:
    image: icr.io/db2_community/db2:${DB2_VERSION}   # 12.1.4.0 via hatch override
    container_name: ibm_db2                          # KEEP this name (conftest uses it)
    platform: linux/amd64        # Db2 community image is x86_64-only
    privileged: true             # Db2 tunes kernel IPC / shared-memory at startup
    ipc: host                    # Db2 uses host System V IPC
    ports:
      - "50000:50000"
    environment:
      - LICENSE=accept
      - DB2INSTANCE=db2inst1
      - DB2INST1_PASSWORD=db2inst1-pwd     # must match tests/common.py PASSWORD
      - DBNAME=datadog                     # creates the DB on first boot -> can drop the
                                           #   `create db` step from DbManager.initialize
      - ARCHIVE_LOGS=false                 # faster first boot for CI
      - PERSISTENT_HOME=true
    healthcheck:
      test: ["CMD-SHELL", "su - db2inst1 -c 'db2 connect to datadog' >/dev/null 2>&1 || exit 1"]
      interval: 15s
      timeout: 10s
      retries: 40
      start_period: 480s          # IBM first-boot (instance+db create) takes minutes
```

> **Why `start_period: 480s` matters for the harness.** `docker_run(..., wait_for_health=True)`
> waits on the compose healthcheck; the IBM image's first boot is multi-minute. Keep `attempts=2`
> in `docker_run` and the long `start_period`, or integration runs will flake on a slow cold start.
> Locally, prefer the `--skip-env` path (§3.4) so you pay this cost once, not per test run.

**Note on keeping 11.1 green:** the original comment said the *official* image lacked 11.1; if you
want CI to keep an 11.x lane, map the `11.1` matrix value to a real IBM tag (e.g. `11.5.9.0`) in the
hatch override, or drop 11.1 from the matrix and document that 12.1.4 is the supported floor. Either
way, version-gate any 12.1-only `MON_GET_*` columns so the 11.x lane (if kept) does not fail on
missing columns.

### 3.3 conftest fixtures + seeding the monitoring grants and workload (P0 base, extended per phase)

Extend `DbManager.initialize()` (or, cleaner, add a SQL/shell resource under `tests/docker/` and
`docker cp`/exec it) to do three new things beyond the existing switches+backup. **Mirror the live
stack's `local-dev/db2/primary/custom/01_datadog_setup.sh`** — it is the canonical least-privilege
recipe:

1. **Monitor switches + the EXTENDED config the DBM features need.** The existing five switches stay.
   Statement/query-metrics fidelity additionally depends on the database `MON_*` config; confirm
   (and set if needed) `mon_act_metrics <> 'NONE'` and `mon_req_metrics`/`mon_obj_metrics` are not
   `NONE` — these gate the timing-derived columns in `MON_GET_PKG_CACHE_STMT` / `MON_GET_ACTIVITY`
   (the live default is `mon_act_metrics=BASE`, `mon_obj_metrics=EXTENDED`, `mon_req_metrics=BASE`;
   the tests should assert that and/or set it). If a test must verify the "metrics off" degradation
   path, set `mon_act_metrics=NONE` in a dedicated fixture.

2. **Create the least-privilege monitoring user + grants** (so tests run as a *non-owner*, matching
   real deployments and the README grant list). Per phase, grant `EXECUTE` on the functions that
   phase reads:
   ```sql
   -- existing (metrics)
   GRANT EXECUTE ON FUNCTION SYSPROC.MON_GET_INSTANCE        TO USER datadog;
   GRANT EXECUTE ON FUNCTION SYSPROC.MON_GET_DATABASE        TO USER datadog;
   GRANT EXECUTE ON FUNCTION SYSPROC.MON_GET_BUFFERPOOL      TO USER datadog;
   GRANT EXECUTE ON FUNCTION SYSPROC.MON_GET_TABLESPACE      TO USER datadog;
   GRANT EXECUTE ON FUNCTION SYSPROC.MON_GET_TRANSACTION_LOG TO USER datadog;
   -- P0
   GRANT EXECUTE ON FUNCTION SYSPROC.MON_GET_HADR            TO USER datadog;
   GRANT EXECUTE ON FUNCTION SYSPROC.MON_GET_CONTAINER       TO USER datadog;
   -- P1 (query metrics)
   GRANT EXECUTE ON FUNCTION SYSPROC.MON_GET_PKG_CACHE_STMT  TO USER datadog;
   -- P2 (activity) — MON_CURRENT_SQL view + the underlying functions
   GRANT EXECUTE ON FUNCTION SYSPROC.MON_GET_ACTIVITY        TO USER datadog;
   GRANT EXECUTE ON FUNCTION SYSPROC.MON_GET_CONNECTION      TO USER datadog;
   GRANT EXECUTE ON FUNCTION SYSPROC.MON_GET_UNIT_OF_WORK    TO USER datadog;
   -- P4 (settings/schemas) — config + catalog read
   GRANT EXECUTE ON FUNCTION SYSPROC.DBM_GET_CFG             TO USER datadog;
   GRANT EXECUTE ON FUNCTION SYSPROC.DB_GET_CFG              TO USER datadog;
   -- simplest alternative covering all MON_GET_*: GRANT SYSMON
   ```
   You can either keep using the all-powerful `db2inst1` in the default `CONFIG` (simplest) and add a
   *second* least-privilege instance/fixture for a "grants are sufficient" test, or switch `CONFIG`
   to the `datadog` user outright. The live stack creates an OS `datadog` user (Db2 uses OS auth) and
   grants exactly the above — replicate that for a faithful privilege test.

3. **Seed a schema + workload** so the DBM sources have data to return:
   - **Schema** (gives P4 `SYSCAT.*` real objects, and P0 per-table/index metrics rows): create a
     couple of tables with an index/FK. The live stack's inventory schema is a good minimal model
     (`orders/workloads/inventory_schema.db2.sql`): `inventory_items` and `shipments` with PK
     identity columns. Add an index and a foreign key so `SYSCAT.INDEXES`/`SYSCAT.REFERENCES` are
     exercised.
   - **Package-cache entries** (P1): run a few representative statements (incl. one with a literal
     and one parameter-marker variant) before the check so `MON_GET_PKG_CACHE_STMT` is populated.
     For *delta* tests, run them again between two `dd_run_check` calls.
   - **In-flight activity** (P2): the orders OLTP inventory workload is **sub-millisecond and is
     systematically missed by activity sampling** — this is expected (document it). To get a
     catchable long-running statement, drive a deliberate slow statement from a *separate* thread,
     e.g. a self-cartesian join or `CALL DBMS_LOCK.SLEEP(N)`, while the activity job samples (see
     §5.3). `_research/db2-live-activity.md` covers the negative result and the workaround.

4. **Add the `--skip-env` option** (next section) and the `dbm_instance` fixture (§5.1).

> **Driver note (e2e only).** `E2E_METADATA` in `common.py` installs `ibm_db==3.2.6` into the live
> Agent container via `start_commands` (the stock Agent lacks the `ibm_db` C-extension — the same
> reason the live stack ships `Dockerfile.agent`). Integration (in-process) tests use the `ibm_db`
> already installed in the hatch env (`hatch.toml` `dependencies`), so they need no such injection.

### 3.4 The `--skip-env` fast-dev path (strongly recommended for Db2)

Because the IBM container's first boot is multi-minute, copy postgres's `--skip-env` pattern so you
can start the container **once** and re-run tests against it instantly:

```python
# conftest.py
def pytest_addoption(parser):
    parser.addoption("--skip-env", action="store_true", default=False,
                     help="skip environment setup (reuse an already-running container)")

@pytest.fixture(scope='session')
def skip_env(request):
    return request.config.getoption("--skip-env")

@pytest.fixture(scope='session')
def dd_environment(skip_env):
    if skip_env:
        yield CONFIG, E2E_METADATA
        return
    db = DbManager(CONFIG)
    with docker_run(COMPOSE_FILE, conditions=[db.initialize, WaitFor(db.connect)], attempts=2):
        yield CONFIG, E2E_METADATA
```
Then:
```bash
docker compose -f ibm_db2/tests/docker/docker-compose.yaml up -d   # once; wait ~5 min for health
# ...run DbManager.initialize() steps manually once (or a one-shot seed script)...
ddev test ibm_db2 -- --skip-env -m integration -k test_statements   # instant re-runs
```

---

## 4. Classic metric-assertion pattern (P0 metric breadth)

### 4.1 `tests/metrics.py` is plain lists of metric-name strings

Today it defines `STANDARD` (44 asserted), `BUFFERPOOL` (20), `TABLESPACE` (4). **Every metric the
check can emit must be listed**, because the e2e gate `aggregator.assert_all_metrics_covered()`
fails if *any* submitted metric was never asserted. So for P0: add every new
buffer-pool-writes / I/O-timing / direct-I/O / sort / hash / HADR / container metric name to the
appropriate list, and add matching rows to `metadata.csv`.

### 4.2 The "all metrics present + correctly tagged" gate

`test_integration_e2e.py::_assert_standard` is the model:
```python
def _assert_standard(aggregator):
    aggregator.assert_service_check('ibm_db2.can_connect', AgentCheck.OK)
    for metric in metrics.STANDARD:
        aggregator.assert_metric_has_tag(metric, 'db:datadog')
        aggregator.assert_metric_has_tag(metric, 'foo:bar')
    aggregator.assert_all_metrics_covered()
```
Key aggregator helpers (`datadog_checks_base/.../stubs/aggregator.py`):
- `assert_metric(name, value=None, tags=None, count=None, at_least=1, metric_type=None, ...)`.
  `metric_type` is an **int enum**: `gauge=0, rate=1, count=2, monotonic_count=3, counter=4,
  histogram=5`. `tags=` requires the **exact full** sorted tag set; `count=` pins the number of
  submissions. Example (existing custom-query test): `metric_type=3` (monotonic_count) with
  `tags=['db:datadog','foo:bar','test:ibm_db2','tablespace:USERSPACE1']`.
- `assert_metric_has_tag(name, tag)` — metric present **and** carries `tag` (loose; preferred for
  the per-bufferpool/tablespace metrics).
- `assert_metric_has_tag_prefix(name, prefix)` — used today for `bufferpool:` / `tablespace:`
  prefixes; use the same for new `container:` / per-`member:` tags.
- `assert_service_check(name, status=None, count=None, ...)` — statuses via `check.OK/WARNING/...`.
- `assert_event(msg_text, ...)` — the *Agent* event bus (tablespace state-change event), **not** a
  DBM track.

### 4.3 Add metadata-driven assertion (a fidelity improvement)

The `ibm_db2` suite does **not** currently call `assert_metrics_using_metadata` — add it (P0 task 8).
It fails if a submitted metric is missing from `metadata.csv` or its type mismatches:
```python
from datadog_checks.dev.utils import get_metadata_metrics
...
aggregator.assert_metrics_using_metadata(get_metadata_metrics())
```
This catches "added a metric but forgot the metadata.csv row" and type drift — exactly the mistakes
P0's wide metric expansion invites.

### 4.4 HADR zero-row test (P0)

On the default STANDARD (non-HADR) database, `MON_GET_HADR(-1)` returns **0 rows**. The test must
assert `query_hadr` emits **no** `ibm_db2.hadr.*` metrics (or only `hadr.role{role:standard}=1`) and
does **not** raise — i.e. graceful "not configured". Don't try to stand up an HADR pair in CI.

---

## 5. DBM payload assertions (P1–P4)

**There is no `assert_event_platform_event` helper.** DBM payloads are captured by the aggregator
stub and pulled back as parsed dicts:
```python
events = aggregator.get_event_platform_events("dbm-metrics")   # or dbm-samples / dbm-activity / dbm-metadata
```
You then assert on the dicts. The four track strings are `"dbm-metrics"`, `"dbm-samples"`,
`"dbm-activity"`, `"dbm-metadata"`. **For every Db2 payload: `event['ddsource'] == "db2"`** and the
vendor rows live under a **`db2_*`** key (decided: §0). Compute expected signatures in-test with
`from datadog_checks.base.utils.db.sql import compute_sql_signature`.

### 5.1 The `dbm_instance` fixture + thread hygiene (shared by all DBM tests)

```python
import pytest
from concurrent.futures.thread import ThreadPoolExecutor
from datadog_checks.base.utils.db.utils import DBMAsyncJob

CLOSE_TO_ZERO_INTERVAL = 1e-7

@pytest.fixture
def dbm_instance(instance):
    instance['dbm'] = True
    instance['min_collection_interval'] = 0.2
    instance['query_metrics']  = {'enabled': True, 'run_sync': True,
                                  'collection_interval': CLOSE_TO_ZERO_INTERVAL}
    instance['query_activity'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}
    instance['collect_settings'] = {'enabled': False}
    instance['collect_schemas']  = {'enabled': False}
    return instance

@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    # reset the shared executor so async DBM jobs don't leak between tests (mysql pattern)
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()
```
Critical knobs (deterministic tests): **`run_sync: True`** runs the async job inline so the payload
exists immediately after `dd_run_check`; a near-zero `collection_interval` stops `DBMAsyncJob` from
skipping back-to-back runs. Alternatively (postgres style) use `run_one_check(check, cancel=True)`
which runs then `check.cancel()` to join threads. **Always** ensure jobs are cancelled at teardown
or threads leak across the suite.

### 5.2 dbm-metrics (query metrics) — `test_statements.py` (P1)

Model (adapted from postgres `test_statements.py`):
```python
from datadog_checks.base.utils.db.sql import compute_sql_signature

def test_statement_metrics(aggregator, dbm_instance, dd_run_check, datadog_agent):
    check = IbmDb2Check('ibm_db2', {}, [dbm_instance])
    # first run primes the snapshot; second run produces deltas
    dd_run_check(check)
    run_some_statements()          # see §3.3 seeding
    dd_run_check(check)

    events = aggregator.get_event_platform_events("dbm-metrics")
    assert events, "no dbm-metrics payload emitted"
    event = events[-1]
    assert event['host'] == 'stubbed.hostname'
    assert event['ddsource'] == 'db2'
    assert event['timestamp'] > 0
    assert event['ddagentversion'] == datadog_agent.get_version()
    assert event['min_collection_interval'] == dbm_instance['query_metrics']['collection_interval']
    assert set(event['tags']) == expected_dbm_tags(check, dbm_instance)   # see §5.6

    expected_sig = compute_sql_signature(expected_obfuscated_query)
    rows = [r for r in event['db2_rows'] if r['query_signature'] == expected_sig]   # <-- db2_rows
    assert len(rows) == 1
    row = rows[0]
    assert row['query'] == expected_obfuscated_query
    # numeric counter columns are float/int after the delta engine:
    for col in ('num_executions', 'total_act_time', 'total_cpu_time', 'rows_read'):
        if col in row:
            assert isinstance(row[col], (int, float))
```
Assert, additionally:
- **Delta correctness:** with two runs and N statements between them, the row's `num_executions`
  delta equals N; the delta key is `HEX(EXECUTABLE_ID)`+member+db while the *emit* key is
  `query_signature` (so literal variants / `EXECUTABLE_ID` churn re-aggregate to one signature).
- **Unit normalization:** `TOTAL_CPU_TIME` is microseconds, `STMT_EXEC_TIME`/`TOTAL_ACT_TIME`/
  `PREP_TIME` are milliseconds — assert the converted values, and that averages divide by
  **`num_exec_with_metrics`** (guard 0), not `num_executions`.
- **Graceful degradation:** a separate test with `mon_act_metrics=NONE` asserts timing-derived
  columns are absent and the check does not crash.

### 5.3 dbm-samples — FQT + plan events (`test_statements.py` / P3)

FQT (full query text) events ride the **`dbm-samples`** track with `dbm_type == 'fqt'`:
```python
samples = aggregator.get_event_platform_events("dbm-samples")
fqt = [e for e in samples if e.get('dbm_type') == 'fqt']
m = [e for e in fqt if e['db']['query_signature'] == expected_sig][0]
assert m['ddsource'] == 'db2'
assert m['ddagentversion'] == datadog_agent.get_version()
assert m['db']['statement'] == expected_obfuscated_query
assert m['db2']['...'] == ...          # vendor block keyed by 'db2'
assert m['timestamp'] > 0
```
Plan events (P3) — `dbm_type == 'plan'`:
```python
plans = [e for e in samples if e['dbm_type'] == 'plan'
         and e['db']['statement'].encode('utf-8') in expected_query.encode('utf-8')]
event = plans[0]
assert event['db']['plan']['definition'] is not None, "missing execution plan"
assert 'Plan' in json.loads(event['db']['plan']['definition']), "plan JSON invalid"
assert event['db']['plan']['signature']         # compute_exec_plan_signature(normalized)
# error path emits self-telemetry:
aggregator.assert_metric("dd.ibm_db2.statement_samples.error", at_least=0)
```
Db2 has no inline plan column — the test only runs after the P3 spike proves EXPLAIN-table assembly
to JSON works. The assertion contract is the same as postgres's plan-sample test, just keyed `db2`.

### 5.4 dbm-activity — `test_activity.py` (P2)

```python
def test_activity(aggregator, dbm_instance, dd_run_check, datadog_agent):
    # start a deliberately slow statement on a background thread (orders OLTP is too fast to catch)
    fut = run_slow_statement_async()        # e.g. self-cartesian join / DBMS_LOCK.SLEEP
    check = IbmDb2Check('ibm_db2', {}, [dbm_instance])
    dd_run_check(check)
    fut.cancel_or_join()

    activity = aggregator.get_event_platform_events("dbm-activity")
    assert activity
    a = activity[0]
    assert a['host'] == 'stubbed.hostname'
    assert a['dbm_type'] == 'activity'
    assert a['ddsource'] == 'db2'
    assert a['ddagentversion']
    assert isinstance(a['ddtags'], list)        # NOTE: activity ddtags is a LIST, not comma-joined
    assert isinstance(a['collection_interval'], (int, float))
    assert a['db2_activity']                     # active-session rows
    # blocked/long-running row:
    row = next(r for ev in activity for r in ev['db2_activity']
               if r.get('query_signature') == expected_sig)
    assert row['statement'] == expected_obfuscated_sql   # obfuscated
    assert 'db2_connections' in a                # connection counts
    # self-exclusion: the agent's own monitoring session must NOT appear
    assert all(r.get('application_name') != AGENT_APP_NAME for r in a['db2_activity'])
```
Document the expected negative result: sub-millisecond OLTP statements are routinely missed by
sampling — the cumulative P1 metrics are the complete per-statement source.

### 5.5 dbm-metadata — `test_metadata.py` / `test_schemas.py` (P4)

Same retrieval; assert on `kind`:
```python
md = aggregator.get_event_platform_events("dbm-metadata")
# settings (DBMCFG ∪ DBCFG):
settings = [e for e in md if e['kind'] == 'db2_settings'][0]
rows = settings['metadata']
assert any(r['config_scope'] == 'dbm' for r in rows)
assert any(r['config_scope'] == 'db'  for r in rows)
assert any('pending_change' in r for r in rows)
# schemas (SYSCAT.*), chunked:
schemas = [e for e in md if e['kind'] == 'db2_databases']
assert schemas
assert schemas[-1].get('collection_payloads_count')   # completion marker on last chunk
```
Also assert the **`database_instance`** registration (the single must-have DBM payload) lands with
`metadata.dbm == True`:
```python
inst = [e for e in md if e.get('kind') == 'database_instance']
assert inst and inst[0]['metadata']['dbm'] is True
```

### 5.6 Canonical DBM tag set helper

postgres/mysql build the expected DBM tag set once and reuse it. Add a Db2 equivalent in
`tests/common.py` reflecting the Db2 tag scheme (instance tags + `port:` + `database_hostname:` +
`database_instance:` + any version/db tags), e.g.:
```python
def expected_dbm_tags(check, instance, with_host=False):
    tags = list(instance.get('tags', [])) + [
        'port:{}'.format(instance['port']),
        'database_hostname:{}'.format(check.database_hostname),
        'database_instance:{}'.format(check.database_identifier),
        'db:{}'.format(instance['db']),
    ]
    if with_host:
        tags.append('dd.internal.resource:database_instance:{}'.format(check.database_identifier))
    return set(tags)
```
Adjust to whatever the check's `TagManager` actually emits — derive it from the check, don't
hard-code, so the test tracks the implementation.

### 5.7 Obfuscation in tests

Inject deterministic obfuscation (postgres/mysql do this) so signatures are stable regardless of the
real Go obfuscator:
```python
import mock
from datadog_checks.base.stubs import datadog_agent
with mock.patch.object(datadog_agent, 'obfuscate_sql',
                       side_effect=lambda q, options=None: q.strip()):
    ...
```
(Resolve the real obfuscator `dbms:'db2'` question in P1 task 0 — it is an Agent-side decision, not
testable from this repo; see [`12-risks-open-questions.md`](12-risks-open-questions.md).)

---

## 6. Live manual validation with the dbm repo's `local-dev/db2` stack

The dbm repo ships a **live Db2 12.1.4 + Agent (with `ibm_db`) + orders-app** stack that is the best
manual end-to-end environment — more realistic than the CI container (real workload, real Agent,
optional mitmproxy to inspect the actual `dbm-*` payloads on the wire).

Location: `/home/bits/go/src/github.com/DataDog/dbm/local-dev/db2/`.

```bash
cd /home/bits/go/src/github.com/DataDog/dbm/local-dev    # the Makefile lives one level up
make up/db2                 # db2-primary + agent + orders-app (inventory workload)
make up/db2 NOAPP=1         # db + agent only (no workload)
make up/db2-db              # database only

make logs/db2-agent         # tail agent logs
make exec/db2               # shell into Db2 as db2inst1 (run db2 CLI / DESCRIBE here)
make down/db2               # tear down
```
Stack facts you'll need:
- **DB** `testdb`, **host** `db2-primary`, **port** `50000`, monitoring user **`datadog`**
  (OS user, password `Password12!`), created + granted by
  `primary/custom/01_datadog_setup.sh` (runs as root after first boot). The check config the agent
  mounts is `local-dev/db2/conf.d/ibm_db2.yaml`.
- The agent image is built from `Dockerfile.agent` (stock agent + `pip install ibm_db==3.2.6`).
- **Today the stack is metrics-only** — `conf.d/ibm_db2.yaml` has **no** `dbm:` block, and the
  README/targets explicitly say "metrics-only, no DBM." The `01_datadog_setup.sh` grants cover only
  the five metrics functions. **To exercise the new DBM features you must extend this stack** (see
  below) — that work is the still-owed "phase 2" in the project memory.

### 6.1 Point a dev agent at your in-development check code

Use the dbm Makefile's `DEV` integration-mount path so the live agent runs your local
`integrations-core/ibm_db2` working tree:
```bash
make up/db2 DEV=1     # mounts DEV_CHECKS = datadog_checks_base,ibm_db2 into the agent
```
(`targets.mk` sets `up/db2: DEV_CHECKS = datadog_checks_base,ibm_db2` and the `$(DEV)` path requires
`_check_dev_env`.) Then iterate:
```bash
make restart/db2-agent                                   # after editing check code
make logs/db2-agent                                      # watch for errors
docker exec datadog-agent-db2-$USER agent check ibm_db2 -t 0   # run the check once, see raw output
```
To **manually enable DBM** against the live stack while developing P1+:
1. Add a `dbm: true` + per-collector block to `local-dev/db2/conf.d/ibm_db2.yaml`.
2. Extend `01_datadog_setup.sh` with the P1–P4 grants from §3.3 (or `GRANT SYSMON`), then
   `make restart/db2-db` (or recreate so the custom script re-runs) and `make restart/db2-agent`.
3. Drive load with the orders-app inventory workload (`make up/db2`, `DB_LOAD_TYPE=inventory`) and,
   for catchable activity, a deliberate slow statement via `make exec/db2`.
4. Verify payloads either in the Datadog DBM UI (the host should appear once the
   `database_instance` event lands) or, offline, by enabling the stack's **mitmproxy** layer
   (`MITM=1` / `restart/db2-mitm`) and inspecting the intercepted `dbm-metrics`/`dbm-samples`/
   `dbm-activity`/`dbm-metadata` POST bodies.

### 6.2 Use the live container to validate columns (a P0/P1 prerequisite)

Several P0 columns are `[DOC]`-flagged (doc-sourced, not yet live-verified on 12.1.4), and
`MON_GET_PKG_CACHE_STMT` has ~327 columns that vary by fixpack. **Before writing any SELECT**, prove
the columns exist on the live image:
```bash
make exec/db2     # then, inside the db2inst1 shell:
db2 connect to testdb
db2 "DESCRIBE SELECT * FROM TABLE(MON_GET_BUFFERPOOL(NULL,-1))"
db2 "DESCRIBE SELECT * FROM TABLE(MON_GET_CONTAINER(NULL,-1))"
db2 "DESCRIBE SELECT * FROM TABLE(MON_GET_PKG_CACHE_STMT(NULL,NULL,NULL,-1)) FETCH FIRST 0 ROWS ONLY"
```
This is the same mechanism the check should use at runtime (`WHERE 1=0` / `FETCH FIRST 0 ROWS ONLY`
column probe) — don't hard-code the column list. The raw captures in `_research/_raw/` were produced
exactly this way.

---

## 7. CI considerations

- **What CI runs.** With no explicit integration name, ddev tests only checks **changed vs `master`**
  (Markdown-only diffs test nothing). CI runs `ddev validate all` + `ddev test` across the
  `hatch.toml` matrix. So a metric/DBM change must keep `ddev validate all ibm_db2`, `ddev test
  ibm_db2 -- -m unit`, and `ddev test ibm_db2:py3.13-12.1 -- -m integration` green.
- **Config-model drift is a hard CI failure.** If you edit `spec.yaml` without committing the
  regenerated `config_models/*` + `conf.yaml.example`, `ddev validate config/models` (no `--sync`)
  fails CI. Always commit the regenerated files.
- **metadata drift is a hard CI failure.** A submitted metric missing from `metadata.csv` fails
  `assert_metrics_using_metadata` (once adopted) and `ddev validate metadata`. Keep `metrics.py`,
  `metadata.csv`, and the emission code in lockstep.
- **The Db2 12.1.4 image is heavy + slow.** First boot is multi-minute; the image is x86_64-only
  (`platform: linux/amd64`) and needs `privileged`/`ipc: host`. Confirm the CI runners allow
  `privileged` containers and have the disk/RAM headroom, and keep the long `start_period` +
  `attempts=2`. This image swap is **asserted but unproven** — running the existing suite against
  `icr.io/db2_community/db2:12.1.4.0` for the first time is itself a P0 deliverable
  ([`12`](12-risks-open-questions.md) / `99` gap #7).
- **`ibm_db` driver build.** The hatch env installs `ibm_db==3.2.6` (PyPI wheel bundles the
  clidriver). If a runner lacks a manylinux wheel and must compile, it needs `build-essential` /
  `libxslt-dev` (mirrors the live `Dockerfile.agent` fallback). `IBM_DB_INSTALLER_URL` points the
  build at the internal blob.
- **DBM extras must be wired** (`base-package-features = ["deps","db","json"]`) or DBM imports fail at
  test collection (§1.1). Land this with P1, not later.
- **Thread leakage** between DBM tests will cause flakiness — the `stop_orphaned_threads` autouse
  fixture (or `run_one_check(cancel=True)`) is not optional in CI.
- **e2e is not part of the default unit/integration CI lane** — e2e (`ddev env test`) runs the live
  Agent and is typically gated separately. Treat the `assert_all_metrics_covered` gate in
  `test_integration_e2e.py::test_standard` (an `@integration` test) as the always-on coverage gate;
  `test_e2e` (the `@e2e` one) is the opt-in live-agent smoke.

---

## 8. Per-phase validation checklists (copy-paste, runnable)

Each phase: code → regenerate config (if spec changed) → validate assets → unit → integration →
(optionally) live-stack manual check. Cross-reference the matching section of
[`10-implementation-phases.md`](10-implementation-phases.md).

### P0 — Foundation metrics (buffer-pool writes, I/O timing, sort/hash, HADR, container FS)

```bash
# 0. live-verify every [DOC] column exists on 12.1.4 (prerequisite — see §6.2)
make -C /home/bits/go/src/github.com/DataDog/dbm/local-dev exec/db2
#    db2 "DESCRIBE SELECT * FROM TABLE(MON_GET_BUFFERPOOL(NULL,-1))"   (+ DATABASE/CONTAINER/LOG)

# 1. hatch + compose: add 12.1 matrix + icr.io image (§1.1, §3.2)
# 2. extend queries.py + emit metrics; add HADR collector with 0-row handling (§4.4)
# 3. add every new metric to tests/metrics.py + rows to metadata.csv (§4.1, §4.3)

ddev validate metadata ibm_db2
ddev validate service-checks ibm_db2          # if ibm_db2.hadr.status added
ddev test ibm_db2 -- -m unit
ddev test ibm_db2:py3.13-12.1 -- -m integration
ddev test ibm_db2:py3.13-12.1 -- -m integration -k "standard or buffer_pool or table_space"
```
Gate: new metrics typed/tagged correctly, in metadata.csv; `assert_metrics_using_metadata` +
`assert_all_metrics_covered` pass; HADR emits nothing on STANDARD DB; **no regression** to the 49
existing metrics or the tablespace state-change event; CI green on 12.1.4.

### P1 — DBM scaffold + query metrics (`dbm-metrics`, FQT, `database_instance`)

```bash
# 0. resolve obfuscator dialect ('db2' vs generic) — Agent-side, document in 12-risks (§5.7)
# 1. edit assets/configuration/spec.yaml: dbm, query_metrics, obfuscator_options, reported_hostname,
#    database_identifier, database_instance_collection_interval (default 300), cloud blocks
ddev validate config ibm_db2 --sync
ddev validate models ibm_db2 --sync
# 2. add base-package-features = ["deps","db","json"] to hatch.toml (§1.1)
# 3. implement DatabaseCheck conversion (dbms="db2"), per-job ibm_db connection layer (UR isolation),
#    _send_database_instance_metadata, Db2StatementMetrics(DBMAsyncJob) over MON_GET_PKG_CACHE_STMT

ddev test ibm_db2 -- -m unit          # delta-engine math, unit normalization, payload shape
docker compose -f ibm_db2/tests/docker/docker-compose.yaml up -d   # then --skip-env for fast iter
ddev test ibm_db2 -- --skip-env -m integration -k test_statements
```
Gate: `dbm-metrics` payload has `ddsource=="db2"`, a `db2_rows` array with correct **deltas**,
obfuscated `query`, and `query_signature` (== `compute_sql_signature`) that survives
`EXECUTABLE_ID` churn; averages divide by `num_exec_with_metrics`; FQT events on `dbm-samples`;
`database_instance` event with `metadata.dbm==True` on `dbm-metadata`; `mon_act_metrics=NONE`
degrades gracefully; **no leaked threads** (jobs cancelled at teardown).

### P2 — Samples + activity (`dbm-activity`)

```bash
# spec: query_activity block; regenerate
ddev validate config ibm_db2 --sync && ddev validate models ibm_db2 --sync
ddev test ibm_db2 -- --skip-env -m integration -k test_activity
```
Gate: `dbm-activity` payload `dbm_type=="activity"`, `ddsource=="db2"`, `ddtags` is a **list**,
`db2_activity` rows carry obfuscated `statement` + `query_signature`, `db2_connections` present, the
agent's own session is excluded, a deliberately slow statement is captured with correct
`elapsed_time_msec`; sub-ms OLTP absence documented as expected.

### P3 — Execution plans (`dbm-samples`, `dbm_type:"plan"`) — spike-gated

```bash
# spike first (timeboxed): prove EXPLAIN-tables -> JSON tree on the live 12.1.4 container (§6.2)
ddev test ibm_db2 -- --skip-env -m integration -k test_plan
```
Gate: plan events on `dbm-samples` with non-null `db.plan.definition` parseable as JSON, a
`db.plan.signature`, per-`(query_signature, plan_signature)` rate limiting, and the error path
emitting `dd.ibm_db2.*` telemetry — **OR** a documented deferral decision in
[`12-risks-open-questions.md`](12-risks-open-questions.md) (P1/P2/P4 still ship).

### P4 — Schemas + settings (`dbm-metadata`)

```bash
# spec: collect_settings, collect_schemas blocks; regenerate
ddev validate config ibm_db2 --sync && ddev validate models ibm_db2 --sync
ddev test ibm_db2 -- --skip-env -m integration -k "metadata or schemas"
```
Gate: `dbm-metadata` carries `db2_settings` (DBMCFG ∪ DBCFG with `config_scope` + `pending_change`,
schema-agnostic — no hard-coded parameter list) and, when enabled, chunked `db2_databases` schema
payloads with `collection_payloads_count` on the last chunk.

### P5 — Dashboards, docs, packaging, CI hardening

```bash
ddev validate readmes ibm_db2            # DBM setup section, least-privilege grants, driver install
ddev validate dashboards ibm_db2
ddev validate all ibm_db2                # full suite
# add changelog fragment per shipped phase:
#   ibm_db2/changelog.d/<PR_NUMBER>.<added|changed|fixed>
```
Gate: dashboards render new metrics; README documents `dbm:true` enablement + grants
(consolidate on `SYSMON`) + `ibm_db` driver install; `base-package-features` + `--skip-env` +
`dbm_instance` fixtures + thread hygiene in place; CI green on 12.1 with DBM tests; manifest /
service_checks updated; one `changelog.d/<PR>.<type>` fragment per phase.

---

## 9. File / command reference index

- **This integration's tests:**
  `/home/bits/dd/integrations-core/ibm_db2/tests/{conftest.py,common.py,metrics.py,test_unit.py,test_integration.py,test_integration_e2e.py,docker/docker-compose.yaml}`
- **Add (P1+):** `tests/test_statements.py`, `tests/test_activity.py`, `tests/test_metadata.py`,
  `tests/test_schemas.py`, `tests/utils.py` (thread/blocking helpers).
- **Config source of truth:** `/home/bits/dd/integrations-core/ibm_db2/assets/configuration/spec.yaml`
  (generated: `config_models/*.py`, `data/conf.yaml.example`).
- **Metric catalog:** `/home/bits/dd/integrations-core/ibm_db2/metadata.csv`
  (validator: `ddev/src/ddev/cli/validate/metadata_utils.py`).
- **hatch matrix:** `/home/bits/dd/integrations-core/ibm_db2/hatch.toml`.
- **Aggregator stub (assert helpers):**
  `/home/bits/dd/integrations-core/datadog_checks_base/datadog_checks/base/stubs/aggregator.py`.
- **Harness primitives:**
  `/home/bits/dd/integrations-core/datadog_checks_dev/datadog_checks/dev/{docker.py,conditions.py,subprocess.py}`,
  pytest plugin `.../dev/plugin/pytest.py`.
- **DBM test references to copy:**
  `postgres/tests/{test_statements.py,test_schemas.py,utils.py,common.py,conftest.py}`,
  `mysql/tests/{test_statements.py,test_query_activity.py,test_metadata.py}`,
  `sqlserver/tests/{test_metrics.py,test_e2e.py}`.
- **Live manual stack:** `/home/bits/go/src/github.com/DataDog/dbm/local-dev/db2/`
  (`docker-compose.yaml`, `Dockerfile.agent`, `conf.d/ibm_db2.yaml`,
  `primary/custom/01_datadog_setup.sh`, `targets.mk`) + the `Makefile` one level up.
- **Deep reference (file:line citations):**
  `_research/code-testing-harness.md`, `_research/code-integration-scaffolding.md`,
  `_research/db2-live-pkgcache.md`, `_research/db2-live-activity.md`,
  `_research/db2-config-settings.md`, `_research/code-dbm-payload-contract.md`,
  `_research/code-base-framework.md`, `_research/_raw/{01-version-and-monget-functions.txt,04-monitor-config.txt}`.
- **Sibling plan docs:** [`00-README.md`](00-README.md),
  [`02-current-integration-audit.md`](02-current-integration-audit.md),
  [`10-implementation-phases.md`](10-implementation-phases.md),
  [`12-risks-open-questions.md`](12-risks-open-questions.md),
  [`99-review-and-gaps.md`](99-review-and-gaps.md).
