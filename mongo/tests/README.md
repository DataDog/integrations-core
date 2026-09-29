# mongo test fixtures

The pytest suite plus the Compose environments used by the tests and by the evalya
fixture in `evalya.yaml`.

## Compose environments

| File | What it is |
|---|---|
| `compose/mongo-{standalone,auth,tls,shard}.yaml` | Environments used by the pytest suite (`hatch.toml` flavors). |
| `compose/full-coverage.compose` | Full metric-coverage environment (see below). |

`full-coverage.compose` is published as the reusable evalya fixture `mongo-full`.

## The full-coverage fixture

`mongo-full` drives the mongo check (and the OpenTelemetry `mongodbreceiver`) to emit the
metrics users are shown: everything referenced by the OOTB dashboard (`assets/dashboards/`)
and the recommended monitors (`assets/monitors/`), 29 metrics in total.

Those metrics need two node roles that no single endpoint exposes: `chunks.*` and
`sessions.count` come only from a mongos, while `replset.*` and `oplog.*` come only from a
replica-set member. The fixture is therefore the smallest sharded cluster that has both:

- **config** — single-member config server replica set.
- **shard-a** — primary of the one shard, `shard01`.
- **shard-b** — a delayed secondary of `shard01` (hidden, priority 0, no vote,
  `secondaryDelaySecs: 5`). The delay keeps `replset.optime_lag` at a steady non-zero
  value, and replication keeps the `opcountersrepl.*` and `repl.*` counters moving. With no
  vote, majority writes never wait on it.
- **mongos** — the router.
- **rs-init** — one-shot: initiates both replica sets.
- **seed** — one-shot: adds the shard, creates the monitoring user on mongos and on the
  shard, and seeds `activity.orders` (sharded on `cust_id`, pre-split into 5 chunks,
  indexed) and `activity.events` (`seed.sh`).
- **activity-gen** — a continuous workload through mongos (`activity-gen.sh`): inserts,
  indexed and unindexed queries, small-batch reads for getMores, updates, deletes,
  aggregations, `listIndexes`, periodic DDL (replicated as commands), and one long-lived
  session so `sessions.count` is non-zero. It also runs bounded lock contention in the
  `lockdrill` database, described under [Lock metrics](#lock-metrics).
- **mongo-full** — the entrypoint the evalya task targets: a `socat` forwarder that
  exposes mongos on 27017, shard-a on 27018, and shard-b on 27019. It depends on every
  long-lived node and on the workload, since evalya only starts a task's `depends_on`
  chain and stops services nothing running depends on.

No ports are published to the host, so the fixture cannot clash with a local mongod or a
concurrent run.

### Inputs

| Variable | Default | Purpose |
|---|---|---|
| `MONGO_VERSION` | `8.0` | Image tag for every mongo service. Needs 6.0+ (`mongosh`). |
| `DB_USERNAME` / `DB_PASSWORD` | `datadog` / `datadog` | The monitoring user created by `seed`. |
| `ACTIVITY_GEN` | `1` | Set to `0` to keep `activity-gen` running but idle. |

All three are read from the host environment (Compose interpolation). Access control is
not enforced, because `--auth` on a sharded cluster needs a keyFile for internal auth; the
user still exists, so a wrong credential fails to authenticate.

### Check configuration

Run one instance per role, all against the entrypoint host:

```yaml
instances:
  # mongos: chunks.*, sessions.count, sharded data distribution
  - hosts: [<DB_HOST>:27017]
    username: datadog
    password: datadog
    options: {authSource: admin}
    database: activity
    additional_metrics: [metrics.commands, tcmalloc, collection, jumbo_chunks, sharded_data_distribution]
    collections: [orders, events]
    collections_indexes_stats: true
  # shard primary (27018) and delayed secondary (27019): replset.*, oplog.*, top
  - hosts: [<DB_HOST>:27018]
    username: datadog
    password: datadog
    options: {authSource: admin}
    database: activity
    additional_metrics: [metrics.commands, tcmalloc, top, collection]
    collections: [orders, events]
    collections_indexes_stats: true
  - hosts: [<DB_HOST>:27019]
    # same options as 27018
```

Collection, index, and sharded-distribution stats are collected every 300s by default,
so the `*.opsps` rates need a second sample that far apart. For short runs, lower
`metrics_collection_interval` (`collection`, `collections_indexes_stats`,
`sharded_data_distribution`) to 15.

### Verifying coverage

```shell
agent check mongo -t 2 --pause 15000 --json
```

The pause matters: rates (`opcounters.*ps` and the like) are computed between the two runs
and read `0` when the runs are back to back.

Measured on MongoDB 8.0.32 with the three instances above: all 29 target metrics emitted,
25 non-zero. The four at `0` are zero-by-nature on a healthy fixture:

- `mongodb.chunks.jumbo` — a jumbo chunk is one the balancer failed to split, which does
  not happen here.
- `mongodb.globallock.currentqueue.readers` / `.writers` — operations queued on lock
  contention; the monitors alert when these exceed 100, and a healthy node sits at 0.
  These are point-in-time gauges: the lock contention below queues operations only in
  bursts of about 100 ms, so a scrape still reads 0.
- `mongodb.extra_info.page_faultsps` — major page faults; the data set fits in memory.

### Lock metrics

The `mongodb.locks.*` metrics (OTel: `mongodb.lock.acquire.{count,wait_count,time}`) read
serverStatus `locks.<type>.{acquireCount,acquireWaitCount,timeAcquiringMicros}.<mode>`.
MongoDB only reports a field once it is non-zero: `acquireWaitCount` and
`timeAcquiringMicros` need an acquisition that waited on a conflicting mode, which
one-at-a-time traffic never causes. So `activity-gen` also runs lock contention in the
`lockdrill` database (seeded through mongos):

- a slow writer, directly on shard-a: an update whose `$where` sleeps 100 ms, so it holds
  its intent locks (IX on Global, Database, and Collection) almost continuously;
- two fast writers and `dbStats`, directly on shard-a, which queue behind the holders
  (IS/IX waits);
- a holder on shard-a, every 3 s: `createIndexes` (S for the drain, X to commit) and
  `dropIndexes` (X) on `lockdrill.hot`, `dbHash` (Database S), a cross-database
  `renameCollection` from `lockdrill_aux` (Database X on the target), and `fsync` with
  `lock: true` (Global S), unlocked in a `finally`;
- a holder through mongos, every 3 s: an insert into the capped `lockdrill.capped` (Metadata
  X) and `setUserWriteBlockMode` on then off (Global X on the shard), turned off in a
  `finally`. Writes that land in that window fail with `UserWritesBlocked`, which the lock
  writers ignore.

Each lock held past its command is released in a `finally`, and each holder first clears
one a killed predecessor left behind. `ACTIVITY_GEN=0` disables it with the rest of the
workload. The waits are counted on shard-a (the `27018` instance); mongos reports only its
`Mutex` lock.

Measured on MongoDB 8.0.32 over three 15 s windows: every wait count and wait time for
Global, Database, and Collection in all four modes, plus `Metadata` `acquireCount` in X
mode, was non-zero in every window, both from the mongo check and from the OTel
`mongodbreceiver`. Six fields stay absent, because MongoDB 8.0 never acquires those modes
in steady state:

- `locks.Metadata.acquireCount.R`: 8.0 takes the Metadata resource only in X mode, for
  writes to capped collections.
- `locks.oplog.{acquireCount,acquireWaitCount,timeAcquiringMicros}.R`: nothing in 8.0
  takes the oplog collection lock in S mode.
- `locks.oplog.{acquireWaitCount,timeAcquiringMicros}.w`: 8.0 writes and reads the oplog
  without its collection lock (`AutoGetOplogFastPath` takes only the Global lock). Only
  startup, repair, and oplog creation take IX on it, so no workload makes it wait.
