# redisdb test fixtures

The pytest suite plus the Compose environments used by the tests and by the
evalya fixtures in `evalya.yaml`.

## Compose environments

| File | What it is |
|---|---|
| `compose/standalone.compose` | Single authenticated Redis instance. |
| `compose/1m-2s.compose` | Master with two slaves (one deliberately unhealthy). |
| `compose/1m-2s-cloud.compose` | Same topology, master loads a mounted `config/redis.conf`. |
| `compose/full-coverage.compose` | Full metric-coverage environment (see below). |

Two of these are published as reusable evalya fixtures: `redis-standalone` (the
standalone file) and `redis-full` (the full-coverage environment).

## The full-coverage fixture and its proxy

`redis-full` makes a single fixture emit the **entire** `INFO` surface the redisdb
check and the OTel redisreceiver can parse, including fields a plain OSS Redis can
never produce. Four services:

- **redis-master** — real Redis (AOF, small `maxmemory` under LRU, full slowlog).
  No config file is mounted, so `CONFIG`/`CLIENT`/`CLUSTER` stay un-renamed for the
  check's side-channel collections.
- **redis-replica** — `replicaof` the master, so `INFO replication` shows a
  connected slave. Not proxied; the check sees it through the master's INFO.
- **seed** — one-shot: primes typed keys, TTLs, hits/misses, an eviction overfill,
  and expiry so the natural counters are non-zero before the first scrape.
- **info-proxy** — the entrypoint, a transparent RESP proxy on 6379.

### The proxy

It speaks RESP only, with no knowledge of Datadog metrics: it fakes raw Redis
`INFO` output and the check maps that to `redis.*`. One injection point feeds both
scrapers, since they read the same `INFO`. The master is the source of truth; the
proxy forwards everything byte-for-byte except two cases:

```
scraper ──RESP──► info-proxy ──forwards──► redis-master
                     │  ◄──── real reply ────┘
                     ├─ INFO all      → real reply + inject.conf lines (re-framed)
                     ├─ CLUSTER INFO  → canned cluster_info.txt (master not hit)
                     └─ everything else → unchanged
```

The injected lines (`proxy/inject.conf`) are the fields OSS Redis can't emit
(managed-service, cluster, sentinel, RediSearch), each matching a key the check
parses in `constants.py`. The canned `CLUSTER INFO` exists because a standalone
master reports cluster support disabled. The proxy dials one backend connection
per client (preserving AUTH and the negotiated protocol) and handles both RESP2
(the redisdb check) and RESP3 (the OTel receiver).

No host port is published, to avoid clashing with a local Redis; reach it over the
Compose network, or add `--publish 6379:6379` to inspect by hand. Source in
`proxy/` (`main.go` request loop, `resp.go` framing).

## Driving full coverage: the activity-gen service

The `seed` service primes the fixture once, but most rate/counter metrics stay
zero on an idle instance. The `activity-gen` service (`activity-gen.sh`) runs
continuously inside `full-coverage.compose`, looping over keyspace, command
variety, eviction, expiry, net bytes, blocked clients, forks/RDB, slowlog, and
client-side caching so both scrapers see non-zero values across scrapes. It is
part of the fixture, so any consumer of `redis-full` gets it automatically with no
extra wiring. Tunable via `ACTIVITY_DB` / `ACTIVITY_DURATION`.
