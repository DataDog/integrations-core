# oracle test fixtures

The Oracle Database check is the Agent's `oracle` core check (Go, in
`datadog-agent/pkg/collector/corechecks/oracle`), so this directory holds no pytest
suite. It holds the evalya fixture declared in `evalya.yaml`.

## The `oracle-full` fixture

`oracle-full` stands up an Oracle Database Free instance with a workload, so the check
emits the metrics plotted on the OOTB dashboards (`assets/dashboards/*.json`) with
non-zero values. Point the check at it with `dbm: true`, because most of the
dashboard sysmetrics are only collected in DBM mode:

```yaml
instances:
  - server: <DB_HOST>:<DB_PORT>
    service_name: <DB_SERVICE_NAME>   # FREE, the CDB root
    username: <DB_USERNAME>
    password: <DB_PASSWORD>
    dbm: true
```

Run it with `evalya run --path oracle/tests/evalya.yaml --task oracle-full`.

### Services (`compose/full-coverage.compose`)

| Service | Role |
|---|---|
| `oracle` | Oracle Database Free (CDB `FREE`, PDB `FREEPDB1`). `startdb/01-direct-io.sh` sets `filesystemio_options=SETALL` on first start, bouncing the instance once, so datafile reads bypass the host page cache. Reads served from the page cache take a few microseconds, which leaves the whole-millisecond `oracle.avg_synchronous_single_block_read_latency` at 0. |
| `seed` | One-shot (`seed.sh`). Creates the Datadog user with the Agent's grants and the `dd_session` view, then creates the `ddapp` workload schema in `FREEPDB1`. It finishes by verifying that the Datadog user can log in. |
| `activity-gen` | Continuous workload (`activity-gen.sh`). It keeps a long-lived session holding temp space and a row lock, then loops commits, rollbacks, hard and soft parses, parse failures, wide-key index inserts, NOCACHE LOB I/O, full scans of a large table, a sort that spills to disk, a lock-wait timeout, a two-session deadlock, checkpoints, and periodic buffer cache flushes. |
| `oracle-full` | Entrypoint: a plain TCP forwarder (socat) to `oracle:1521`, gated on `seed` and `activity-gen`, so requesting it pulls up the whole environment. Compose only starts the dependencies of the requested service, so the database itself cannot be the entrypoint. The forwarder injects nothing. |

No host port is published; reach the fixture over the managed network through the
`DB_HOST` label, or add `--publish 1521:1521` to inspect it by hand.

### Inputs

Each input has a working default and can be overridden from the host environment.

| Variable | Default | Purpose |
|---|---|---|
| `ORACLE_VERSION` | `23.26.3` | `gvenzl/oracle-free:<version>-slim-faststart` tag, shared by `oracle`, `seed`, and `activity-gen`. |
| `ORACLE_PASSWORD` | `datad0g` | `SYS`/`SYSTEM` password, also used for the `ddapp` workload user. |
| `DB_USERNAME` | `c##datadog` | Datadog monitoring user (a common user in the CDB). |
| `DB_PASSWORD` | `datadog` | Password of `DB_USERNAME`. |
| `ACTIVITY_GEN` | `1` | Set to `0` for a quiescent fixture: the workload container stays up but generates no traffic. |
| `ACTIVITY_DURATION` | `0` | Stop the workload after this many seconds (`0` runs forever). |

The task publishes `DB_HOST`, `DB_PORT` (`1521`), `DB_SERVICE_NAME` (`FREE`),
`DB_USERNAME`, and `DB_PASSWORD`. These labels carry the defaults: if you override
the credentials, override the consumer's values as well.

### Coverage

The fixture emits 67 of the 73 dashboard metrics with non-zero values, all from the
live instance. The other six are:

| Metric | Why it is not covered |
|---|---|
| `oracle.gc_average_cr_get_time`, `oracle.gc_average_current_get_time`, `oracle.gc_cr_block_received`, `oracle.gc_current_block_received` | RAC global cache (interconnect) metrics. They are 0 on a single instance, and Oracle Database Free cannot run RAC. |
| `oracle.cache_blocks_corrupt` | Zero by nature: corrupted global cache blocks are a failure counter. |
| `oracle.cursor_cachehit_ratio` | Unreachable: plotted by `oracle_overview.json` but never emitted by the Agent check (it has no `V$SYSMETRIC` mapping and is not in `metadata.csv`). |
