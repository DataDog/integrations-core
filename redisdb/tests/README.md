# redisdb test fixtures

This folder holds the pytest suite plus the Compose environments used by the
tests and by the evalya fixtures published from `evalya.yaml`.

## Compose environments

| File | What it is |
|---|---|
| `compose/standalone.compose` | Single authenticated Redis instance. |
| `compose/1m-2s.compose` | Master with two slaves (one deliberately unhealthy). |
| `compose/1m-2s-cloud.compose` | Same topology, master loads a mounted `config/redis.conf`. |
| `compose/full-coverage.compose` | Full metric-coverage environment (see below). |

`evalya.yaml` publishes two of these as reusable fixtures: `redis-standalone`
(the standalone Compose file) and `redis-full` (the full-coverage environment).

## The `redis-full` fixture and the INFO-rewrite proxy

`redis-full` exists to make a single fixture emit the **entire** `INFO` surface
that the redisdb check and the OpenTelemetry redisreceiver can parse, including
fields a plain OSS Redis instance can never produce.

It runs four services:

- **redis-master**: a real Redis server (AOF on, small `maxmemory` under LRU,
  full slowlog). No config file is mounted, so `CONFIG`/`CLIENT`/`CLUSTER` stay
  un-renamed and the check's side-channel collections work.
- **redis-replica**: `replicaof` the master, so `INFO replication` reports a
  connected slave and the check's with-replica path is exercised. It is not
  proxied; the check sees its state through the master's INFO.
- **seed**: a one-shot job that populates typed keys, TTLs, keyspace
  hits/misses, an eviction-inducing overfill, benchmark traffic, and forced key
  expiry, so the naturally derived counters are non-zero before the first scrape.
- **info-proxy**: the fixture entrypoint, a transparent RESP proxy fronting the
  master on 6379.

### How it sits in front of Redis

The proxy is the entrypoint; the real Redis runs behind it and is the source of
truth for almost everything. A scraper connects to the proxy on 6379 exactly as
it would to a standalone, and each request flows through:

```
scraper (redisdb check / OTel receiver)
   │  RESP request
   ▼
info-proxy  ──(forwards byte-for-byte)──►  redis-master
   │  ◄──────────── real reply ────────────┘
   │
   ├─ INFO all      → real reply + appended inject.conf lines (length re-framed)
   ├─ CLUSTER INFO  → canned reply from cluster_info.txt (master not contacted)
   └─ everything else → returned unchanged
```

This is a transparent forward, not a fallback: the master is always the primary
path, and the proxy only augments one reply and short-circuits one command.

### What the proxy does

The proxy speaks Redis (RESP) only. It has no knowledge of Datadog metrics or
metric formats; it fakes raw Redis server output, and the downstream check maps
that to `redis.*` metrics. Because both scrapers read the same `INFO`, one
injection point feeds both.

Its default path is forward-everything to the master, with two exceptions:

- `INFO all` (and bare `INFO` / `INFO everything`): the real reply is forwarded,
  then the `key:value` lines from `proxy/inject.conf` are appended and the RESP
  length is re-framed. These are the fields OSS Redis cannot emit on its own:
  managed-service (Azure Cache), cluster, sentinel, and RediSearch fields, each
  matching a key the check parses in `constants.py`.
- `CLUSTER INFO`: answered from `proxy/cluster_info.txt` without contacting the
  master, since a standalone master would reply that cluster support is disabled.

Everything else, including section-scoped requests such as `INFO commandstats`,
is forwarded and returned byte-for-byte. The proxy dials one backend connection
per client to preserve per-connection AUTH and the negotiated RESP protocol
version, and it handles both RESP2 (the redisdb check) and RESP3 (the OTel
receiver).

If you drop the proxy and point the check straight at redis-master, everything
still works; you only lose the faked managed-service/cluster/sentinel/RediSearch
fields.

### Port and access

The proxy listens on 6379, the standard Redis port, and presents exactly like a
standalone. The Compose file publishes no host port on purpose (to avoid
clashing with a local Redis or a concurrent run); consumers reach it over the
Compose network. To inspect the fixture by hand, add `--publish 6379:6379` or a
Compose override.

The proxy source lives in `proxy/`; see `proxy/main.go` for the request loop and
`proxy/resp.go` for the RESP framing.

### Driving full coverage: the `activity-gen` task

The `seed` service primes the fixture once, but most rate and counter metrics
report zero on an idle instance, and an assertion that compares 0 to 0 proves
nothing. The `activity-gen` task (`activity-gen.sh`) is an opt-in workload
generator that loops over keyspace hits/misses, command variety, eviction,
expiry, net bytes, blocked clients, forks/RDB, slowlog, and client-side caching,
so both scrapers see the full metric surface with non-zero values across scrape
intervals.

It is deliberately separate from `redis-full` so the fixture stays quiescent by
default. Add it alongside the fixture when you want sustained activity:

```
with:
  - redis-full
  - activity-gen
```

It reads only `DB_HOST`/`DB_PORT`/`REDIS_PASSWORD` (plus optional `ACTIVITY_DB`
and `ACTIVITY_DURATION`), so it has no dependency on any scraper and is reusable
by any consumer of the fixture.
