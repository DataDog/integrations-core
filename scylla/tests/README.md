# scylla test fixtures

The pytest suite plus the Compose environments used by the tests and by the
evalya fixture in `evalya.yaml`.

## Compose environments

| File | What it is |
|---|---|
| `compose/docker-compose.yaml` | Single unauthenticated Scylla node used by the pytest suite and `ddev env`. |
| `compose/full-coverage.compose` | Full metric-coverage environment, published as the evalya `scylla-full` task. |

## The scylla-full fixture

`scylla-full` makes the check emit every metric used by the OOTB dashboard
(`assets/dashboards/overview.json`) and the recommended monitor
(`assets/monitors/instance_down.json`) with non-zero values. Four services:

- **scylla**: a single-shard Scylla node with `PasswordAuthenticator`, sized
  for a shared host (`--smp 1 --memory 750M`). The REST API listens on all
  interfaces so the workload can flush and drop caches.
- **seed**: one-shot. Ensures the `DB_USERNAME`/`DB_PASSWORD` role can log in
  (bootstrapping it from the built-in `cassandra` superuser when they differ),
  then creates and primes the `activity.kv` table.
- **activity-gen**: continuous workload (`activity-gen.sh`), described below.
- **scylla-proxy**: the entrypoint. A plain nginx TCP pass-through for 9180
  (metrics) and 9042 (CQL) that modifies nothing. It exists only so a single
  dependency on it pulls up the node, the seeded schema, and the workload,
  because the scraped node cannot depend on its own seed.

No host port is published, to avoid clashing with a local Scylla; reach the
fixture over the Compose network through the published `DB_HOST`.

### Configuring the check

The dashboard and monitor use the legacy metric names (for example
`scylla.cache.row_hits`), which only the `prometheus_url` mode emits. The
`openmetrics_endpoint` mode reports counters with a `.count` suffix instead.
Point the check at the fixture with:

```yaml
instances:
  - prometheus_url: http://<DB_HOST>:<DB_PORT>/metrics
```

### Inputs

Every input has a working default, so the task runs unattended. Each one can
be overridden from the host environment when starting the fixture.

| Variable | Default | Purpose |
|---|---|---|
| `SCYLLA_VERSION` | `5.2.6` | Scylla image tag, shared by every Scylla-based service. |
| `DB_USERNAME` | `cassandra` | CQL role used by `seed` and `activity-gen`, published as `provides.DB_USERNAME`. |
| `DB_PASSWORD` | `cassandra` | Password for `DB_USERNAME`, published as `provides.DB_PASSWORD`. |
| `ACTIVITY_GEN` | `1` | Set to `0` for a quiescent fixture: the container stays up but generates no traffic. |

The task also publishes `provides.DB_PORT` (`9180`, the metrics endpoint) and
`provides.CQL_PORT` (`9042`).

### The activity-gen service

An idle node reports zero for the coordinator, cache, and transport counters.
`activity-gen.sh` streams CQL into a single long-lived `cqlsh` session, so
traffic is continuous rather than bursty. Each iteration:

- inserts and reads small partitions (coordinator write attempts, reads, and
  latency histograms, `cache.row_hits`, `transport.requests_served`);
- reads large partitions and writes a ~900 KB unlogged batch with Scylla's
  `USING TIMEOUT 1ms`, which deliberately trips
  `storage.proxy.coordinator_read_timeouts` and
  `storage.proxy.coordinator_write_timeouts`;
- every fifth iteration, flushes the keyspace and drops the sstable caches
  through the REST API, so the following reads produce `cache.row_misses`.

Because of the deliberate timeouts, the dashboard's timeout widgets show
activity and the node logs batch-size warnings; this is expected for this
fixture. `ACTIVITY_DURATION` (seconds, `0` = forever) bounds the run.

All 14 target metrics are produced live; none rely on recorded fixtures, and
none are expected to stay at zero.
