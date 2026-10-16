# Kong test fixtures

## `kong-full` evalya task

The `kong-full` task in `evalya.yaml` stands up a live environment in which the kong check emits every metric
plotted on the kong OOTB dashboards, with non-zero values. Run it with:

```shell
evalya run --path kong/tests/evalya.yaml --task kong-full
```

The dashboards plot three metric families that no single Kong node emits, so the environment
(`compose/full-coverage.compose`) runs two DB-less Kong nodes:

| Service | Role |
|---|---|
| `upstream` | `nginx:alpine` backend that both Kong nodes proxy to. |
| `kong` | Kong 3.x. Emits the 3.0 Prometheus names (`bandwidth.bytes`, `http.requests`, `kong.latency.ms`, `nginx.connections.total`). |
| `kong-legacy` | Kong 2.x. Emits the pre-3.0 names that Kong 3.0 renamed (`bandwidth`, `http.status`, `http.consumer.status`, `latency`, `nginx.http.current_connections`). |
| `seed` | One-shot. Sends one request per labelled series (authenticated 200, unauthenticated 401, authenticated 404) so every series exists before the first scrape. |
| `activity-gen` | Runs `activity-gen.sh`: continuous proxied traffic for the request, bandwidth, and latency counters, plus one idle keep-alive connection per node for `connections_waiting`. |
| `gateway` | Entrypoint. Publishes both nodes on one hostname (see `compose/gateway.conf`). |

Each node routes `/` to `upstream` behind `key-auth`, with one consumer and the Prometheus plugin enabled per
consumer (on Kong 3.x, with the status code, latency, bandwidth, and upstream health flags on). Both nodes also
serve the legacy `/status` endpoint.

### Published connection details

| Label | Value |
|---|---|
| `provides.DB_HOST` | Entrypoint hostname. |
| `provides.KONG_PROXY_PORT` / `provides.KONG_ADMIN_PORT` | `8000` / `8001` (Kong 3.x). |
| `provides.KONG_LEGACY_PROXY_PORT` / `provides.KONG_LEGACY_ADMIN_PORT` | `8100` / `8101` (Kong 2.x). |
| `provides.KONG_CONSUMER_KEY` | The `key-auth` credential of `consumer1`. |

The Kong OSS Admin API is unauthenticated, so the consumer key is the only credential.

### Configurable inputs

Every input has a working default and accepts a host-env override.

| Variable | Default | Effect |
|---|---|---|
| `KONG_VERSION` | `3.9` | Image tag of the Kong 3.x node. |
| `KONG_LEGACY_VERSION` | `2.7` | Image tag of the Kong 2.x node. It must stay below 3.0 to emit the pre-3.0 names. `2.7` is the newest 2.x tag published for arm64. |
| `KONG_CONSUMER_KEY` | `devops-best-friend` | `key-auth` credential, read by both nodes, `seed`, and `activity-gen`. |
| `ACTIVITY_GEN` | `1` | `0` keeps `activity-gen` running but idle, which leaves the counters at `0`. |
| `ACTIVITY_DURATION` | `0` | Seconds of traffic before `activity-gen` exits with a `PASS:` line. `0` runs forever. |

The two nodes intentionally read different version variables: Kong 3.0 renamed the Prometheus metrics, so the
pre-3.0 and 3.0 names can only be produced by two different Kong versions.

### Check configuration

Run one check instance per node and endpoint. `memory.workers.lua.vms.bytes` is not in the default metric map, so
add it with `extra_metrics`:

```yaml
instances:
  - openmetrics_endpoint: http://<DB_HOST>:8001/metrics
    extra_metrics:
      - kong_memory_workers_lua_vms_bytes: memory.workers.lua.vms.bytes
  - openmetrics_endpoint: http://<DB_HOST>:8101/metrics
    extra_metrics:
      - kong_memory_workers_lua_vms_bytes: memory.workers.lua.vms.bytes
  - kong_status_url: http://<DB_HOST>:8001/status/
  - kong_status_url: http://<DB_HOST>:8101/status/
```

Counters need two scrapes with traffic between them, for example `agent check kong -t 2 --pause 5000`. Back-to-back
scrapes report a zero delta.

### Coverage

All 20 dashboard metrics are covered live with non-zero values. None are fixture-backed or zero-by-nature. The kong
assets define no recommended monitors. `kong.http.status.count` is emitted by the check (from `kong_http_status`)
but is missing from `metadata.csv`.
