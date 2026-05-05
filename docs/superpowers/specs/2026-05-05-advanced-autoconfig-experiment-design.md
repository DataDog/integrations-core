# Advanced auto-config — KrakenD experiment

Status: design, not yet implemented.
Tracks Confluence ticket [DSCVR/6650004331](https://datadoghq.atlassian.net/wiki/spaces/DSCVR/pages/6650004331/Integrations+advanced+auto+config+exploration) and the per-integration analysis on the [`vitkykra/autoconfig-analysis` branch](https://github.com/DataDog/integrations-core/blob/vitkykra/autoconfig-analysis/analysis/RESULTS.md).

## Goal

Prove end-to-end, against a real Agent build and a real running container, that a declarative probe spec stored alongside an integration's static config files is enough to discover the integration's correct check config without any per-integration discovery code on the integration side.

The bucket targeted is `generic-openmetrics-scan` (51 of 260 integrations, 20%). The experiment carries one of those — `krakend` — through the full path. Other buckets (multi-path, JSON-shape, TCP handshake, credentialled) are explicit non-goals.

## Non-goals

- Cluster-agent / `kube_service` / `kube_endpoints` flows. Container listener path only.
- Probe types beyond `openmetrics`. No TCP, no `http-text-format`, no JSON-shape verification.
- Multi-path / multi-port logic. Single `path` and a port list, that's it. `http-multi-path` integrations are a follow-up experiment.
- Migrating any existing `auto_conf.yaml` to the new file. Only `krakend` gets the new file.
- Probe-result persistence across Agent restarts. In-memory cache only.
- Authenticated probes. No headers, no TLS. KrakenD's `/metrics` is unauthenticated.
- Concurrency tuning. Probes run sequentially per service.
- Telemetry / metrics about the prober itself. Logs only.
- Python `discover()` callback per integration. Out of scope by design — see "Approaches considered" below.

## Approaches considered

**A. Declarative probe spec + generic Go prober (chosen).** A new file `auto_conf_discovery.yaml` carries `ad_identifiers`, a `discovery:` block with `(type, ports, path)`, and the instance template. The Agent core has one prober that reads the block, probes the matched container, and substitutes a new `%%discovered_port%%` template variable. Per-integration data: a port/path table. Per-integration code: none.

**B. Python `discover(container) -> [Configs]` per integration.** Each integration ships a Python callable. The Agent invokes it via a new rtloader entry point. More flexible but is 51 near-identical files for the openmetrics bucket and requires new rtloader plumbing.

**C. Hybrid.** Declarative for the easy buckets, Python callback for the hard ones.

A was chosen because it is the smallest change that proves the concept end-to-end on a real OpenMetrics integration with dev-env support, and it exactly matches what the analysis says is achievable for the largest fully-generic bucket. C is the natural follow-up if a later experiment targets the harder buckets.

## Architecture

The current Agent autodiscovery pipeline (`comp/core/autodiscovery/` in `datadog-agent`):

```
Listeners ─► Service (host, ports, ad_identifiers, image)
                │
                ▼
File provider ─► Config{ ADIdentifiers, Instances=template } from auto_conf.yaml
                │
                ▼ match by ad_identifier
                ▼
configresolver.Resolve(tpl, svc) ──► substitutes %%host%%, %%port%%, ...
                │
                ▼
MetaScheduler ─► concrete config ─► check scheduler
```

With this change:

```
Listeners ─► Service
                │
                ▼
File provider ─► Config + Discovery{type, ports, path} from auto_conf_discovery.yaml
                │
                ▼ match by ad_identifier
                ▼
[NEW] discovery.Probe(tpl.Discovery, svc) ──► discoveredPort or "no match"
                │       (synchronous, bounded, per-port timeout)
                │       (cached per (service ID, probe spec) for some TTL)
                ▼
configresolver.Resolve(tpl, svc, probeResult) ──► substitutes %%discovered_port%% too
                │
                ▼
MetaScheduler ─► ...
```

The change is local: one file-format parser, one prober package, one template variable, one new branch in the matching loop. No listener change, no scheduler change, no rtloader change.

## File format

Path: `<integration>/datadog_checks/<integration>/data/auto_conf_discovery.yaml`. Same lookup logic as `auto_conf.yaml` today. If both files exist for an integration the Agent logs a warning and prefers the discovery file.

For the experiment, krakend has neither file today — the conflict path is hypothetical here but worth specifying so the failure mode is defined.

```yaml
ad_identifiers:
  - krakend
discovery:
  type: openmetrics       # only "openmetrics" supported in this experiment
  ports: [8090]           # optional. tried first, in order
  path: /metrics          # optional. default: /metrics
init_config:
instances:
  - openmetrics_endpoint: "http://%%host%%:%%discovered_port%%/metrics"
```

The shape is `auto_conf.yaml` plus a `discovery:` block. Existing fields (`init_config`, `instances`, `ad_identifiers`) keep their meaning.

## Probe semantics

For a matched (template, service) pair where `tpl.Discovery != nil`:

1. Resolve `host`: take the first IP from `svc.GetHosts()`. If empty, abort with "no probe target" and don't emit a config.
2. Build the candidate port list:
   - Start with `tpl.Discovery.Ports ∩ svc.GetPorts()`, in declared order. `Ports` are integer port numbers matched against the numeric `Port` field of `workloadmeta.ContainerPort`.
   - Append remaining `svc.GetPorts()` (the fallback scan).
   - Skip ports already in the negative cache for this service.
3. For each candidate, in order:
   - HTTP GET `http://<host>:<port><path>` with a 500 ms per-attempt timeout.
   - Verify response: status 200 AND `Content-Type` matches one of:
     - `text/plain` (Prometheus exposition; version parameter optional)
     - `application/openmetrics-text` (OpenMetrics 1.0)
   - AND the body's first non-comment line parses as a Prometheus exposition line (loose regex `^[a-zA-Z_:][a-zA-Z0-9_:]*(\{[^}]*\})?\s+\S+`). The regex is deliberately permissive — it's a probe, not a parser. The check itself does strict parsing once it owns the endpoint.
4. Bound the total budget: stop after 2 s of cumulative probing or 8 candidates, whichever comes first.
5. Cache results in-memory keyed by `(service ID, probe spec hash)`:
   - On success: cache the discovered port for the lifetime of the service.
   - On failure: cache for ~30 s, then expire.
6. On success the resolver gets `discovered_port` set and substitutes it into the instance template.
7. On failure no config is emitted. The service may match other templates; this template just doesn't apply.

## `%%discovered_port%%` template variable

New entry in `pkg/util/tmplvar`, sibling to `%%port%%`. Resolves only if the prober succeeded. If a template references it without a probe result available, substitution fails and the config is rejected with a clear log line. The existing `%%port%%` semantics are unchanged.

`configresolver.Resolve` gains an extended signature accepting an optional probe result (e.g. `Resolve(tpl, svc, probeResult)`). The probe result carries the discovered port; the resolver passes it to the template-variable substitution path so `%%discovered_port%%` resolves. Templates without a `Discovery` block don't go through the prober and don't see the new variable.

## Demo

1. Add `auto_conf_discovery.yaml` to `integrations-core/krakend/datadog_checks/krakend/data/` with `ports: [8090]` and `path: /metrics`.
2. Implement Agent-side changes in `datadog-agent`:
   - Parse `auto_conf_discovery.yaml` in `comp/core/autodiscovery/providers/config_reader.go`.
   - Add a `Discovery` field to `integration.Config`.
   - New `comp/core/autodiscovery/discovery/openmetrics_prober.go` (probe + verify + cache).
   - Hook into `AutoConfig` matching to call the prober before `configresolver.Resolve`.
   - Add `%%discovered_port%%` to `pkg/util/tmplvar`.
3. Build: `dda inv agent.build`.
4. Start KrakenD via its dev-env docker-compose (`integrations-core/krakend/tests/docker/`).
5. Run the Agent in the nightly Docker image with the locally built binary plus the local `krakend` integration source bind-mounted, per `integrations-core/reference_docker_integration_testing.md`.
6. Verify `agent status` shows the `krakend` check scheduled with `openmetrics_endpoint: http://<container-ip>:8090/metrics` and metrics flowing.

### Three success scenarios

- Default port: KrakenD exposes 8090. Hint port matches, one probe succeeds, check runs.
- Non-default port: restart KrakenD on port 9000. Hint port 8090 closed. Agent falls back to scanning exposed ports, finds 9000, check runs.
- Negative case: a non-KrakenD container labelled with the `krakend` ad_identifier but not serving OpenMetrics. Probes fail, no check is scheduled, only DEBUG-level log lines per probe failure.

## Risks to verify during implementation

- **Listener port visibility.** The container listener exposes `ContainerPort` entries from container metadata. If the docker-compose file does not expose 8090 explicitly the Agent may not see it. The realistic deployment shape exposes the port; verify at the start of implementation.
- **Container IP reachability.** The Agent container must reach the krakend container on the docker network. Standard nightly image plus krakend's compose network should suffice; confirm before claiming the demo works.
- **Probe timing vs container readiness.** A probe that fires before krakend is listening will fail. The 30 s negative cache means no re-probe for 30 s. The AD reconciliation loop runs frequently enough that the next service event (container becomes ready) re-triggers matching and bypasses the cache. Confirm during scenario 1.

## File-level summary of the change

| Repo | Path | Change |
|------|------|--------|
| `integrations-core` | `krakend/datadog_checks/krakend/data/auto_conf_discovery.yaml` | New file with the discovery block and instance template. |
| `datadog-agent` | `comp/core/autodiscovery/integration/config.go` | Add `Discovery` field on `Config`. |
| `datadog-agent` | `comp/core/autodiscovery/providers/config_reader.go` | Parse `auto_conf_discovery.yaml`; populate `Discovery`. |
| `datadog-agent` | `comp/core/autodiscovery/discovery/` (new package) | OpenMetrics prober, candidate-port ordering, cache. |
| `datadog-agent` | `comp/core/autodiscovery/autodiscoveryimpl/` | Call prober before `configresolver.Resolve`; pass result into resolver. |
| `datadog-agent` | `comp/core/autodiscovery/configresolver/configresolver.go` | Accept the probe result; substitute `%%discovered_port%%`. |
| `datadog-agent` | `pkg/util/tmplvar/` | Add `%%discovered_port%%` resolver. |

## Out of scope but worth noting for follow-up

- A second experiment targeting `http-multi-path` (nginx, rabbitmq, envoy) would add a list-of-paths form and verification that picks the first responsive path. The `Discovery` field shape leaves room for that without breaking the format.
- A third experiment targeting Python `discover()` callbacks would only matter if a real integration's discovery cannot be expressed declaratively. The analysis suggests this is a small set; better revisit after experiments 1 and 2.
- Cluster-agent integration (`kube_service` / `kube_endpoints` listeners) is the natural next plug-in point once the container case is solid. Probes from the cluster agent to a service IP work the same way; the listener change is the open question.
