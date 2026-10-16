# envoy test fixtures

The pytest suite runs against the Compose environments under `docker/` (`api_v2` and `api_v3`, selected by the
`FLAVOR` Hatch variable). This directory also holds the `envoy-full` evalya fixture declared in `evalya.yaml`.

## The envoy-full fixture

`envoy-full` is a full metric-coverage environment: the running envoy check emits every metric that the OOTB
dashboards (`assets/dashboards/*.json`) and the recommended monitor (`assets/monitors/connected_state.json`) use,
with non-zero values. The dashboards chart both check modes, so point two check instances at the same admin port:

```yaml
instances:
  - openmetrics_endpoint: http://<ENVOY_HOST>:8001/stats/prometheus   # *.count names (OpenMetrics overview)
  - stats_url: http://<ENVOY_HOST>:8001/stats                          # legacy names (Envoy overview)
```

The task publishes `ENVOY_HOST`, `ENVOY_PORT` (the admin port, `8001`), `ENVOY_OPENMETRICS_ENDPOINT`, and
`ENVOY_STATS_URL`. The Envoy admin interface has no authentication, so the fixture has no credentials.

Run it with:

```shell
evalya run --path envoy/tests/evalya.yaml --task envoy-full
```

### Services

All defined in `compose/full-coverage.compose`:

- **envoy-full**: the entrypoint, a front proxy configured by `compose/full-coverage/front-envoy.yaml`. It depends on
  every other service, so requesting it brings up the whole environment.
- **xds**, **service1**, **service2**: reused from `docker/api_v3`. The xds control plane serves LDS over ADS
  (`control_plane.connected_state`), and the sidecar services answer the 2xx traffic.
- **backend**: `compose/full-coverage/backend.py`, a small HTTP server that returns the responses the shipped
  services cannot: chosen status codes, slow responses, a WebSocket `101`, and a failing health check.
- **seed**: one-shot. Writes the file-based CDS, the overload pressure file, and a runtime directory nested past
  Envoy's walk limit to a volume shared with `envoy-full`.
- **activity-gen**: continuous workload (`activity-gen.sh`). It waits for the proxy to be ready, then loops traffic
  through every route.

### How each non-obvious metric is driven

| Metric | Mechanism |
|---|---|
| `cluster.upstream_rq_{3,4,5}xx`, `listener.http.downstream_rq_*` | `/status/<code>` on the backend |
| `listener.http.downstream_rq_1xx` | WebSocket upgrade to `/ws` (`101 Switching Protocols`) |
| `cluster.upstream_rq_timeout` | `/timeout`: 0.25s route timeout in front of a 1s response |
| `cluster.upstream_cx_connect_timeout` | `blackhole` cluster pointing at a non-routable address |
| `cluster.lb_healthy_panic` | `panic` cluster whose only host always fails its health check |
| `cluster.internal.upstream_rq_xx` | `use_remote_address` marks compose-network clients as internal |
| `cluster.version` | `file_eds` cluster fed by a file-based EDS assignment |
| `http.no_route`, `http.no_cluster` | an unmatched path, and a `cluster_header` route naming an unknown cluster |
| `http.downstream_cx_protocol_error` | a malformed request line sent with `nc` |
| `http.downstream_rq_timeout` | a body uploaded slower than the 2s `request_timeout` |
| `http.downstream_cx_http{1,2}_active`, `*_rq_active` | long-held HTTP/1.1 and HTTP/2 requests to `/slow` |
| `listener.downstream_cx_overflow` | the `limited` listener allows one connection (runtime `connection_limit`) |
| `listener.downstream_cx_overload_reject` | the workload briefly trips the overload manager's injected resource |
| `runtime.load_success`, `runtime.load_error` | `/runtime_modify` reloads, with the too-deep disk layer parked on alternate reloads |
| `runtime.admin_overrides_active` | a key set in the admin runtime layer |
| `runtime.deprecated_feature_use` | the file CDS uses the deprecated `http2_protocol_options` and is re-published |

### Inputs

| Variable | Default | Effect |
|---|---|---|
| `ENVOY_VERSION` | `1.31.0` | Image tag (`envoyproxy/envoy:v<version>`) for the front proxy and the seed. |
| `ACTIVITY_GEN` | `1` | Set to `0` for a quiescent fixture: `activity-gen` stays up but sends no traffic. |
| `ACTIVITY_DURATION` | `0` | Stop the workload after this many seconds (`0` runs forever). |

All three accept a host-environment override. The `service1`/`service2` sidecars are built from
`docker/api_v3/Dockerfile-service`, which pins its own Envoy version; `ENVOY_VERSION` does not change them, and the
check does not scrape them.

### Coverage

All 66 envoy metrics in the dashboards and monitor are emitted non-zero, from the live fixture, with no
fixture-backed data. The dashboards also chart five `kubernetes.*` metrics; those come from the Kubernetes
integration, not the envoy check, and are out of scope.
