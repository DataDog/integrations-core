# coredns test fixtures

The pytest suite (`docker/`, `fixtures/`) plus the evalya fixture in `evalya.yaml`.

## The `coredns-full` fixture

Published as the `coredns-full` evalya task (`compose/full-coverage.compose`). One unmodified
CoreDNS 1.8.5 serves several zones, each wired to a plugin state the coredns check reports on, and a
fixed-rate workload keeps every counter moving and changes each state-like value once. Every metric
is emitted live by CoreDNS itself: nothing is recorded, replayed or injected. Nothing reaches the
internet: every upstream runs in the same CoreDNS process on loopback.

Three services, all upstream or mirror images pinned by digest, none built locally:

- **`seed`** (one-shot): copies `full-coverage/Corefile` and `full-coverage/hosts` into a shared,
  writable config volume, then exits.
- **`coredns`** (the entrypoint): `coredns/coredns:1.8.5`. DNS on `:53`, health on `:8080`, metrics
  on `:9153`. The image is a static binary on `scratch` with no shell, so readiness is an HTTP probe
  on the health plugin (`evalya.yaml`), not a shell healthcheck.
- **`workload`**: `full-coverage/workload.py` (stdlib Python) on `python:3.12-alpine`. It sends UDP
  queries at fixed rates without waiting for answers, so a slow or dead upstream never changes the
  send rate. Its Corefile rewrites are the seed `Corefile` with `Corefile.broken` or
  `Corefile.extra` appended, so the base config is defined once.

`coredns` depends on `seed` (completed) and `workload` (started), so requesting `coredns-full` starts
the whole fixture. `workload` waits for one of `DNS_HOSTS` (`coredns coredns-full`) to resolve:
plain `docker compose` exposes the server by its service name, evalya by its task id.

### Zones

| Zone | Plugins | What it exercises |
|---|---|---|
| `.:1053` | `template` | test upstream: answers `hot.example.test` with a 60s TTL, `miss.example.test` with a 1s TTL |
| `.:1054` | `erratic` | slow upstream: delays every answer by 4s |
| `example.test:53` | `cache 30`, `forward` to `:1053` | cache hits and misses, forward requests and responses |
| `dead.test:53` | `cache 30`, `forward` to `:5399` (nothing listens), `health_check 1s` | SERVFAIL answers, failed health checks, all upstreams down |
| `slow.test:53` | `forward` to `:1054`, `max_concurrent 2` | queries rejected once 2 are in flight |
| `hosts.test:53` | `hosts`, `reload 5s` | hosts entries and reload timestamp |
| `.:53` | `health`, `reload 5s 2s`, `whoami` | Corefile reloads, health endpoint |

## Workload plan

Rates are per second, from the workload start. `workload.py` logs `t=<s> epoch=<unix>` at each state
change, so it can be matched against a scrape window.

| Metric (OpenMetrics V2 name) | Moved by | Rate or change |
|---|---|---|
| `coredns.request_count.count`, `coredns.response_code_count.count` | every query below | ~14/s |
| `coredns.cache_hits_count.count` | `h<n>.hot.example.test` | ~5/s |
| `coredns.cache_misses_count.count` | `m<n>.miss.example.test` (30 names, 1s TTL) and `d<n>.dead.test` | ~2.5/s |
| `coredns.forward_request_count.count`, `coredns.forward_response_rcode_count.count` | forwarded misses, accepted `slow.test` queries | ~2.5/s |
| `coredns.forward_healthcheck_failure_count.count` | health checks of the dead and slow upstreams | ~1-2/s |
| `coredns.forward_healthcheck_broken_count.count` | a `dead.test` query while its only upstream is down | ~0.5/s |
| `coredns.forward_max_concurrent_rejects.count` | `s<n>.slow.test` at 2/s against a 4s upstream behind `max_concurrent 2` | ~1.5/s |
| `coredns.cache_size.count` | the hot set grows from 10 to 40 names | at `T_HOT_GROW` (450s) |
| `coredns.reload.failed_count.count` | `Corefile.broken` (unknown directive) | +1 at `T_RELOAD_BROKEN` (500s) |
| `coredns.plugin_enabled` | `Corefile.extra` (one more server block) | +2 series at `T_RELOAD_OK` (530s) |
| `coredns.hosts.entries_count`, `coredns.hosts.reload_timestamp` | the hosts file grows from 3 to 6 names | at `T_HOSTS_GROW` (600s) |

The Go runtime and process metrics (`go.memstats.*`, `process.*`) move with the query load.

## Inputs

Each input has a working default, so the task runs unattended. Override any of them from the host
environment: `evalya.yaml` declares each one as `${VAR:-default}`.

| Variable | Default | Effect |
|---|---|---|
| `ACTIVITY_GEN` | `1` | Set to `0` for a quiescent fixture: `workload` stays up but sends no queries. |
| `T_HOT_GROW` | `450` | Seconds before the hot set grows from 10 to 40 names. |
| `T_RELOAD_BROKEN` | `500` | Seconds before the invalid Corefile is written. |
| `T_RELOAD_OK` | `530` | Seconds before the valid, extended Corefile is written. Must be at least 10s after `T_RELOAD_BROKEN`, or `workload` exits at startup. |
| `T_HOSTS_GROW` | `600` | Seconds before the hosts file grows from 3 to 6 names. |

CoreDNS has no authentication, so the fixture has no credential inputs. The task publishes
`DNS_HOST`, `DNS_PORT` (`53`) and `METRICS_PORT` (`9153`). The check's endpoint is
`http://<DNS_HOST>:<METRICS_PORT>/metrics`.

## Coverage

Measured by scraping `:9153/metrics` at about 2 minutes and 12 minutes after start, against the
Prometheus names in the check's `METRIC_MAP`: 24 families exposed, 23 non-zero, 22 changing between
the two scrapes. That covers every family CoreDNS 1.8.5 emits for these plugins. The others in the map
are names from older CoreDNS versions or plugins this fixture doesn't load (acl, autopath, dnssec,
grpc, kubernetes, proxy).

Not covered:

- `coredns.panic_count.count`: no CoreDNS 1.8.5 plugin panics on demand.
- `coredns.build_info` is emitted but constant, as expected.
- `coredns.request_duration.seconds` (no suffix): `assets/monitors/coredns_request_duration_high.json`
  queries it, but the check never emits it in either mode and it is not in `metadata.csv`. Only the
  histogram's `.count`, `.sum` and `.bucket` series exist, so that monitor has no data. Fixing it means
  changing the monitor query, which is out of scope for this fixture.
