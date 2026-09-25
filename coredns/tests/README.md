# coredns test fixtures

The pytest suite plus the Compose environment used by the evalya fixture in `evalya.yaml`.

## The `coredns-full` fixture

Published as the `coredns-full` evalya task (`compose/full-coverage.compose`). It makes a
single fixture emit every metric referenced by the coredns dashboards and monitors, in both
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

`activity-gen` repeatedly queries `example.com` (forwarded to the host resolver by the `forward`
plugin, then cached for 30s -- the first lookup per window is a cache miss plus a forward
request/response/rcode, repeats are cache hits) and a unique unresolvable name per iteration
(answered locally as `SERVFAIL`, adding cache misses and response-code variety without touching
`forward`). `coredns` depends on `activity-gen` in the compose file (not the reverse, to avoid a
dependency cycle on the entrypoint service) so requesting the `coredns-full` task also starts the
workload; `activity-gen` polls for `coredns` to answer on its own instead of using a compose
health condition.

For a quiescent `coredns-full` (no generated traffic), set `ACTIVITY_GEN=0` in the host
environment before starting the fixture; the container stays up but does nothing.

## Coverage

Verified live against a running `coredns-full` fixture by instantiating the check directly
(`CoreDNSCheck`/`CoreDNS`) against the container's `/metrics` endpoint and diffing the emitted
metric names against the dashboard+monitor target set: **17/17** target metric names emitted,
all live, 0 fixture-backed, 0 unreachable, split across both check versions:

- `prometheus_url` (legacy): `cache_hits_count`, `cache_misses_count`, `cache_size.count`,
  `forward_request_duration.seconds.{count,sum}`, `forward_response_rcode_count`,
  `go.memstats.{alloc_bytes,heap_alloc_bytes}`, `process.{cpu_seconds_total,max_fds,open_fds}`,
  `request_duration.seconds.{count,sum}`, `response_code_count`.
- `openmetrics_endpoint` (V2): the same set with the OMv2 `.count` counter suffix
  (`cache_hits_count.count`, `response_code_count.count`, etc).

One target entry from the metric extractor, `coredns.request_duration.seconds` (no suffix), is
not a real emitted metric name in `metadata.csv` or on the wire in either mode -- it is the
histogram's base name, already covered by its `.count`/`.sum`/`.bucket` series above.
