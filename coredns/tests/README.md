# coredns test fixtures

The pytest suite plus the Compose environment used by the evalya fixture in `evalya.yaml`.

## The `coredns-full` fixture

Published as the `coredns-full` evalya task (`compose/full-coverage.compose`). It makes a
single fixture emit every emittable metric referenced by the coredns dashboards and monitors, in both
the legacy (`prometheus_url`) and OpenMetrics V2 (`openmetrics_endpoint`) check configurations.
Two services:

- **`coredns`** — a plain CoreDNS instance built from `compose/coredns/Dockerfile`, which
  repackages the real `coredns/coredns` binary (unmodified) onto an Alpine base. The upstream
  image ships on `scratch` with no shell or HTTP client, so the compose healthcheck (which
  probes the `health` plugin's `:8080/health` endpoint) needs a base image that has `wget`. It
  runs the existing pytest Corefile (`docker/coredns/Corefile-v1.8`): `forward`, `cache`,
  `health`, `prometheus`.
- **`activity-gen`** — continuous DNS query workload (`activity-gen.sh`). Every target metric
  here is emittable by a live, unmodified CoreDNS: process/go metrics and the request/response
  counters appear as soon as any query flows, and cache hits appear once the same name is
  looked up twice inside the cache TTL. No metric needs data an OSS CoreDNS can't produce, so
  there is no seed step and no metric-injection layer, unlike the redisdb exemplar.

`activity-gen` sends three queries per iteration, about one iteration per second:

- `example.com`, forwarded to the host resolver by the `forward` plugin and then cached for 30s.
  The first lookup per window is a cache miss plus a forward request/response/rcode; repeats are
  cache hits.
- `fwd-<n>.example.com`, a unique name inside the forward zone. It always misses the cache and
  reaches `forward`, so `forward_response_rcode_count` and `forward_request_duration` move between
  any two scrapes, not just once per cache window.
- `miss-<n>.invalid`, outside the forward zone and answered locally as `SERVFAIL`, which adds
  cache misses and response-code variety without touching `forward`.

`coredns` depends on `activity-gen` in the compose file (not the reverse, to avoid a dependency
cycle on the entrypoint service), so requesting the `coredns-full` task also starts the workload.
`activity-gen` polls for CoreDNS to answer instead of using a compose health condition. It tries
each name in `DNS_HOSTS` (`coredns coredns-full`): plain `docker compose` exposes the server by
its service name, while evalya aliases the entrypoint only by its task id.

## Inputs

Each input has a working default, so the task runs unattended. All of them can be overridden from
the host environment.

| Variable | Default | Effect |
|---|---|---|
| `COREDNS_VERSION` | `1.8.5` | `coredns/coredns` image tag whose binary is repackaged into the `coredns` service. |
| `ACTIVITY_GEN` | `1` | Set to `0` for a quiescent fixture: `activity-gen` stays up but sends no queries. |
| `ACTIVITY_DURATION` | `0` | Seconds before `activity-gen` stops querying; `0` runs forever. |

CoreDNS has no authentication, so the fixture has no credential inputs. The task publishes
`DNS_HOST`, `DNS_PORT` (`53`) and `METRICS_PORT` (`9153`); the check's endpoint is
`http://<DNS_HOST>:<METRICS_PORT>/metrics`.

## Coverage

The target is every metric referenced by the coredns dashboards and recommended monitors (19
names). Coverage was measured with a Datadog Agent 7 container, with this repository's coredns check
mounted over the bundled one. It ran on the `coredns-full` network with two instances, one
`prometheus_url` (legacy) and one `openmetrics_endpoint` (OpenMetrics V2), both pointed at
`http://coredns-full:9153/metrics`:

```shell
agent check coredns -t 2 --pause 5000 --json
```

The 5s pause matters: back-to-back runs (the default) report a zero delta for every monotonic
counter.

Result: **18/18 achievable target metrics non-zero**, all live, 0 fixture-backed, 0
zero-by-nature. The result held over three consecutive runs.

- Legacy (`prometheus_url`): `cache_hits_count`, `cache_misses_count`, `cache_size.count`,
  `forward_request_duration.seconds.{count,sum}`, `forward_response_rcode_count`,
  `go.memstats.{alloc_bytes,heap_alloc_bytes}`, `process.{cpu_seconds_total,max_fds,open_fds}`,
  `request_duration.seconds.{count,sum}`, `response_code_count`.
- OpenMetrics V2 (`openmetrics_endpoint`): the same set with the `.count` counter suffix
  (`cache_hits_count.count`, `cache_misses_count.count`, `forward_response_rcode_count.count`,
  `response_code_count.count`). `process.cpu_seconds_total` is legacy-only.

Excluded: `coredns.request_duration.seconds` (no suffix). The `coredns_request_duration_high`
monitor queries it, but it is not in `metadata.csv` and the check never emits it in either mode.
It is the histogram's base name, and only its `.count`/`.sum`/`.bucket` series exist. The monitor
query, not the fixture, would have to change to cover it.
