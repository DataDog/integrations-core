# istio test fixtures

This directory holds the pytest suite (`conftest.py` runs it against a kind cluster
through `ddev env`) and the evalya fixture declared in `evalya.yaml`.

## The istio-full fixture

The `istio-full` task makes one environment emit the metrics used by the integration's OOTB
dashboards and recommended monitors. Istio needs Kubernetes, so the fixture runs a
single-node k3s cluster inside the Compose environment (`compose/full-coverage.compose`):

- **k3s**: privileged single-node cluster.
- **tools-init**, **istioctl-bin**: one-shot steps that copy `istioctl` out of the
  official image into a shared volume.
- **seed**: one-shot `seed.sh`. Installs istiod (`minimal` profile, 1s push debounce),
  deploys the sidecar-injected `client` and `web` workload (`compose/full-coverage/mesh.yaml`),
  applies routing and a WasmPlugin (`istio-config.yaml`), and applies the drills in
  `drills.yaml`: deliberate misconfigurations that move istiod's conflict and duplicate
  gauges off 0 without changing how `client` reaches `web`.
- **activity-gen**: continuous `activity-gen.sh`. Each iteration sends HTTP and TCP
  traffic from `client`, injects, skips, and rejects sidecar injections, submits valid
  and invalid Istio config, makes istiod reconcile its validating webhook (with a
  `ValidatingAdmissionPolicy` drill that denies the first attempts), and applies
  `churn.yaml` so the drill gauges are recorded in istiod's latest push. The `client`
  sidecar uses a 20s workload certificate, so CSR counters move as well.
- **gateway**: the entrypoint (nginx on port 15014). It routes the live endpoints out of
  the cluster and serves this directory's recorded payloads, both as recorded and
  replayed:

  | Path | Serves |
  |---|---|
  | `/istiod/metrics` | Live istiod |
  | `/mesh/stats/prometheus` | Live `client` sidecar (merged Envoy and pilot-agent stats) |
  | `/fixtures/<version>/<file>` | `fixtures/` recordings as recorded, for Istio <= 1.5 components |
  | `/replay/<version>/<file>` | The same recordings, replayed with increasing counters (see below) |

### Inputs

Every input has a working default, and each one can be overridden from the host environment.

| Variable | Default | Effect |
|---|---|---|
| `ISTIO_VERSION` | `1.29.2` | Tag of the `istio/istioctl` image, and therefore the installed Istio release. |
| `K3S_VERSION` | `v1.31.6-k3s1` | Tag of the `rancher/k3s` image used by the cluster, seed, and activity-gen. |
| `ACTIVITY_GEN` | `1` | Set to `0` to keep activity-gen alive but idle. |
| `ACTIVITY_DURATION` | `0` | Seconds before activity-gen stops; `0` runs forever. |

Istio's metrics endpoints are unauthenticated, so the fixture has no credentials.

### Provided values

The task publishes `ISTIO_HOST`, `ISTIO_PORT`, `ISTIOD_ENDPOINT`, `ISTIO_MESH_ENDPOINT`,
`ISTIO_FIXTURES_URL` (the `/fixtures` base URL), and `ISTIO_REPLAY_URL` (the `/replay`
base URL).

### Check configuration for full coverage

The dashboards span three check implementations (OpenMetrics V2, the legacy istiod
check, and the Istio <= 1.4 check), so coverage needs one instance per implementation
and endpoint:

```yaml
instances:
  # Live: OpenMetrics V2, the legacy istiod check, and the Istio <= 1.4 mesh check.
  - use_openmetrics: true
    istiod_endpoint: <ISTIOD_ENDPOINT>
    istio_mesh_endpoint: <ISTIO_MESH_ENDPOINT>
  - use_openmetrics: false
    istiod_endpoint: <ISTIOD_ENDPOINT>
  - istio_mesh_endpoint: <ISTIO_MESH_ENDPOINT>
  # Recorded: components that current Istio no longer runs.
  - mixer_endpoint: <ISTIO_FIXTURES_URL>/1.1/mixer.txt
    galley_endpoint: <ISTIO_FIXTURES_URL>/1.1/galley.txt
    citadel_endpoint: <ISTIO_FIXTURES_URL>/1.1/citadel.txt
    pilot_endpoint: <ISTIO_REPLAY_URL>/1.1/pilot.txt
  - istio_mesh_endpoint: <ISTIO_FIXTURES_URL>/1.1/mesh.txt
  - istio_mesh_endpoint: <ISTIO_REPLAY_URL>/1.5/istio-merged.txt
  - mixer_endpoint: <ISTIO_FIXTURES_URL>/0.5/mixer.txt
  - use_openmetrics: true
    istiod_endpoint: <ISTIO_FIXTURES_URL>/1.5/istiod.txt
  - use_openmetrics: true
    istiod_endpoint: <ISTIO_REPLAY_URL>/1.1/galley.txt
```

Run the check at least twice (`agent check istio -t 2 --pause 15000`): counters are
submitted as the difference between two scrapes.

### Replayed recordings

A recording served as is never changes between scrapes, so every counter in it reports a
delta of 0. The following 8 counters have data only in a recording, because Galley, the
Istio 1.1 Pilot, and the Istio 1.5 pilot-agent's xDS client no longer exist in a current
Istio. To report them non-zero, the gateway serves them from `/replay/`
(`compose/full-coverage/replay.js`, run by nginx's njs module). On the Nth request for a
file, it multiplies every counter, histogram bucket, and histogram or summary count and sum
by N. Gauges and summary quantiles are served as recorded. Each file has one request count
shared by every client, so values only grow.

These 8 metrics are covered by synthetically incremented recordings, not by live scrapes.
Their non-zero values show that the check parses and maps the recorded series. They say
nothing about a live deployment, and the replayed rates are artificial:

- Galley: `istio.galley.runtime_processor.events_processed.count` and
  `istio.galley.runtime_processor.snapshots_published.count`.
- Istio 1.5 pilot-agent: `istio.mesh.agent.pilot.xds.config_size_bytes.count.total`,
  `istio.mesh.agent.pilot.xds.config_size_bytes.sum.total`,
  `istio.mesh.agent.pilot.xds.push_time.count.total`,
  `istio.mesh.agent.pilot.xds.push_time.sum.total`, and
  `istio.mesh.agent.pilot.xds.pushes.total`.
- Istio 1.1 Pilot: `istio.pilot.rds_expired_nonce`.

### Metrics that stay at 0 or are missing

The istiod drill gauges (`pilot_*` conflicts and duplicates, `endpoint_no_pod`) report
istiod's latest push, so they can briefly drop to 0 between activity-gen iterations.

The following are 0 by nature:

- The Istio 1.5 pilot-agent's pilot gauges: `istio.mesh.agent.conflict.inbound_listener`,
  `istio.mesh.agent.conflict.outbound_listener.tcp_over_current_tcp`,
  `istio.mesh.agent.endpoint_no_pod`, and the `istio.mesh.agent.pilot.` gauges
  `destrule_subsets`, `duplicate_envoy_clusters`, `eds_no_instances`, `endpoint_not_ready`,
  `no_ip`, and `virt_services`. The agent registered these but never set them; the
  recording shows 0, and current pilot-agent no longer exports them.
- Pilot no-IP gauge, `istio.pilot.no_ip`: istiod registers `pilot_no_ip` but never
  records it.
- Pilot HTTP-over-TCP conflicts, `istio.pilot.conflict.outbound_listener.http_over_current_tcp`:
  current istiod no longer exports it, and the recordings show 0.

The dashboard metric `istio.citadel.server.success_cert_issuance_count.sum` is never
emitted: `citadel_server_success_cert_issuance_count` is a counter, and no check
implementation submits a `.sum` for a counter.
