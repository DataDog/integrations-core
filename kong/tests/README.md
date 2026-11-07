# Kong test fixtures

## `kong-full` evalya task

The `kong-full` task in `evalya.yaml` stands up an environment in which the kong check emits 31 of the 34 metrics
in `metadata.csv`, plus `kong.http.status.count`, with non-zero values (see [Coverage](#coverage)). Run it with:

```shell
evalya run --path kong/tests/evalya.yaml --task kong-full
```

The check covers three metric families that no single Kong node emits, so the environment
(`compose/full-coverage.compose`) runs two DB-less Kong nodes:

| Service | Role |
|---|---|
| `upstream` | `nginx` backend that both Kong nodes proxy to. |
| `kong` | Kong 3.x. Emits the 3.0 Prometheus names (`bandwidth.bytes`, `http.requests`, `kong.latency.ms`, `nginx.connections.total`), plus stream session series through a TCP route on `:9000`. |
| `kong-legacy` | Kong 2.x. Emits the pre-3.0 names that Kong 3.0 renamed (`bandwidth`, `http.status`, `http.consumer.status`, `latency`, `nginx.http.current_connections`). |
| `seed` | One-shot. Sends one request per labelled series (authenticated 200, unauthenticated 401, authenticated 404) and one TCP session, so every series exists before the first scrape. |
| `activity-gen` | Runs `activity-gen.sh`: continuous proxied HTTP and TCP traffic for the request, bandwidth, latency, and session counters, plus per node one idle keep-alive connection (`connections_waiting`) and one slow-header connection (`connections_reading`). |
| `gateway` | Entrypoint. Publishes both nodes on one hostname and serves the recorded `fixtures/prometheus.txt` on `:8200` (see `compose/gateway.conf`). |

Each node routes `/` to `upstream` behind `key-auth`, with one consumer and the Prometheus plugin enabled per
consumer (on Kong 3.x, with the status code, latency, bandwidth, and upstream health flags on). Both nodes also
serve the legacy `/status` endpoint.

### Published connection details

| Label | Value |
|---|---|
| `provides.DB_HOST` | Entrypoint hostname. |
| `provides.KONG_PROXY_PORT` / `provides.KONG_ADMIN_PORT` | `8000` / `8001` (Kong 3.x). |
| `provides.KONG_LEGACY_PROXY_PORT` / `provides.KONG_LEGACY_ADMIN_PORT` | `8100` / `8101` (Kong 2.x). |
| `provides.KONG_FIXTURE_METRICS_PORT` | `8200` (recorded Kong 2.x `/metrics`). |
| `provides.KONG_CONSUMER_KEY` | The `key-auth` credential of `consumer1`. |

The Kong OSS Admin API is unauthenticated, so the consumer key is the only credential.

### Configurable inputs

Every input has a working default and accepts a host-env override.

| Variable | Default | Effect |
|---|---|---|
| `KONG_VERSION` | `3.9.4` | Image tag of the Kong 3.x node. |
| `KONG_LEGACY_VERSION` | `2.7.2` | Image tag of the Kong 2.x node. It must stay below 3.0 to emit the pre-3.0 names. 2.7 is the newest 2.x line published for arm64. |
| `KONG_CONSUMER_KEY` | `devops-best-friend` | `key-auth` credential, read by both nodes, `seed`, and `activity-gen`. |
| `ACTIVITY_GEN` | `1` | `0` keeps `activity-gen` running but idle, which leaves the counters at `0`. |

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
  - openmetrics_endpoint: http://<DB_HOST>:8200/metrics
```

Counters need two scrapes with traffic between them, for example `agent check kong -t 2 --pause 5000`. Back-to-back
scrapes report a zero delta.

### Coverage

Target: the 34 metrics in `metadata.csv`, plus `kong.http.status.count`, which the check emits (from
`kong_http_status`) but `metadata.csv` lists without the `.count` suffix. Measured with
`agent check kong -t 2 --pause 5000 --json` against the five instances above:

- 31 covered live with non-zero values, including `kong.http.status.count` and all 20 OOTB dashboard metrics. The kong assets define no
  recommended monitors.
- 1 fixture-backed: `kong.nginx.stream.current_connections`, from the recorded `fixtures/prometheus.txt`. Its values
  are frozen.
- 1 at zero: `kong.stream.status.count`. It is emitted only from the recorded fixture, and a frozen counter reports a
  zero delta between scrapes.
- 2 not emitted under their `metadata.csv` names: `kong.http.status` (the check emits `kong.http.status.count`) and
  `kong.session.duration.ms` (the check emits `.bucket`, `.count`, and `.sum`, all covered live).

The Kong 2.x stream series cannot be produced live. Kong 2.x relays stream metrics to the Admin API through a
`stream_api` capped at 8000 bytes (also in 2.8). One proxied TCP session grows the payload past that cap
permanently, after which Kong drops every stream series. Kong 3.9 exports its stream series without this
failure, so the live stream coverage comes from the `kong` node.
