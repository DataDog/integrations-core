# Advanced auto-config — Python `discover()` callback

Status: design, not yet implemented. Successor to the krakend experiment ([`2026-05-05-advanced-autoconfig-experiment-design.md`](2026-05-05-advanced-autoconfig-experiment-design.md)). Tracks Confluence ticket [DSCVR/6650004331](https://datadoghq.atlassian.net/wiki/spaces/DSCVR/pages/6650004331/Integrations+advanced+auto+config+exploration) and the per-integration analysis on the [`vitkykra/autoconfig-analysis` branch](https://github.com/DataDog/integrations-core/blob/vitkykra/autoconfig-analysis/analysis/RESULTS.md).

## Goal

Generalise the krakend experiment to cover the next two analysis buckets:

- **HTTP probe with integration-specific verification** (35 integrations) — `http-text-format`, `http-json-shape`, `http-multi-path`.
- **TCP probe with integration-specific protocol** (6 integrations) — `tcp-banner-server-greets`, `tcp-protocol-handshake`.

Combined with the existing `generic-openmetrics-scan` bucket (51), this experiment establishes a single mechanism that handles 92 of the 260 integrations (35%) — every bucket the analysis classified as "discoverable on the wire without credentials."

## Approach

Each integration's check class gains a `discover(service)` classmethod that the Agent invokes when a `Service` matches the integration's `ad_identifiers`. `discover` probes the service, performs integration-specific verification in Python, and returns the concrete list of instance configs to schedule. No template substitution for discovered values.

Common discovery primitives (HTTP probe, TCP probe, candidate-port iteration, response verifiers) live in `datadog_checks_base`. Per-pattern base classes (`OpenMetricsBaseCheckV2`, an `HTTPDiscoverable` mixin, a `TCPDiscoverable` mixin) carry the default `discover` implementation, so most integrations need zero per-integration discovery code.

## Non-goals

- Cluster-agent / `kube_service` / `kube_endpoints` flows. Container + process listener path only.
- Credentialled integrations (`creds-*` buckets). Out of scope for the on-the-wire approach.
- Local-detection integrations (`local-cli-binary`, `local-config-file`, `cloud-task-metadata`, `local-scm-enumeration`, `generic-windows-perf`, `generic-linux-procfs`). They have no network probe surface; a separate mechanism applies.
- Migrating existing `auto_conf.yaml` files. New discovery is opt-in per integration via `auto_conf_discovery.yaml`.
- Probe-result persistence across Agent restarts. In-memory cache only.
- Inferring `ad_identifiers` from check metadata. The discovery file is required and explicit. Revisit independently.

## Approaches considered

**A. Declarative verification DSL.** Widen `auto_conf_discovery.yaml` with verifier predicates (status, content-type, body regex, JSON-keys-present, fixed-bytes prefix) plus `%%discovered_path%%`/`%%discovered_scheme%%` template variables. Agent ships HTTP and TCP probers in Go.

**B. Pluggable Go `Verifier` interface with a registry.** Hybrid of A and integration-specific Go code. Per-integration Go in `datadog-agent` core for the awkward cases.

**C. Python `discover(service)` callback per integration (chosen).** Each integration's check class implements (or inherits) a `discover` classmethod. Common probe + verifier helpers in `datadog_checks_base`. Per-pattern base classes carry the defaults.

C was chosen because:

- It does not grow a DSL. Every messy integration in the analysis (multi-step version detection in airflow/gitlab, multi-component enumeration in druid/kubeflow/spark, JSON-shape depth in hdfs JMX servlets) would have pushed A toward JSONPath, conditional rules, multi-step probes, etc. Python doesn't grow.
- The integration-specific knowledge (response shape, version detection logic, port semantics) already lives in the integration's Python check. Reusing it for discovery puts the verifier next to the parser that consumes the same response.
- Per-integration cost is small. For the 51 OpenMetrics integrations, a base-class default with a `DISCOVERY_PORTS` class attribute is enough — zero per-integration code. For the 41 verification-bucket integrations, per-integration `discover` overrides are 5–15 lines using the shared helpers.
- The `discover` return value is the literal instance-config list. No template substitution layer for discovered values, no `%%discovered_*%%` template variable zoo.

The cluster-agent flow is the one place A would have been clearly easier — the cluster agent does not run Python checks today. The krakend experiment already excludes cluster-agent flow as a non-goal; this experiment inherits that exclusion. When cluster-agent autoconfig is taken on, options include: probe runs on a node agent and ships results, Python-in-cluster-agent, or a small declarative fallback for cluster-agent-only.

## Architecture

Pipeline with this change (compare to the krakend experiment design):

```
Listeners ─► Service (host, ports, id, ad_identifiers, ...)
                │
                ▼
File provider ─► Config from auto_conf_discovery.yaml
                │   { ad_identifiers, init_config, optional default instance template (unused for discovery) }
                ▼ match by ad_identifier
                ▼
[NEW] discoverer.Discover(integrationName, svc)
                │   - Cross svc into Python as a Service object (id, host, ports)
                │   - Invoke <Check>.discover(service) on the Python runner
                │   - Receive list[dict] | None
                │   - Bound by per-call timeout; cached per (service ID, integration)
                ▼
For each returned dict: build a concrete integration.Config and schedule it.
```

The change is local: a new file-format file (still `auto_conf_discovery.yaml`), a new rtloader entry point, a new `discoverer` package on the Agent side, the per-pattern Python base classes plus shared helpers in `datadog_checks_base`. Listeners and scheduler are unchanged. The existing `auto_conf.yaml` template path is unchanged for static-config integrations.

The Go-side prober from the krakend experiment (`comp/core/autodiscovery/discovery/openmetrics_prober.go`) is removed in favour of the Python entry point. The candidate-port ordering, cache, and time-budget logic are kept — they live in the new `discoverer` package and apply to all integrations regardless of which patterns their `discover` uses.

## Service surface crossed into Python

The Agent's `listeners.Service` interface is the existing abstraction over containers, processes, K8s services, K8s endpoints, SNMP, DBM cloud services, and others. `ProcessService` (`comp/core/autodiscovery/listeners/process.go`) implements the same interface for processes, so process autodiscovery is supported by this design without any extra plumbing.

The Python-facing surface is a deliberately narrow read-only projection. For this experiment only three accessors:

```python
class Service:
    @property
    def id(self) -> str:
        """Opaque service identifier; for log correlation only."""
    @property
    def host(self) -> str:
        """Eagerly resolved single host string; IPv6 is bracketed for URL use."""
    @property
    def ports(self) -> list[Port]:
        """Ordered list of (number, name) pairs. `name` is empty for non-K8s ports."""

class Port:
    number: int
    name: str
```

`host` is resolved Agent-side using the same fallback policy that `tmplvar.GetHost` uses today (single-network → bridge → error). The Python side never re-implements host resolution.

The interface name `Service` is kept for the experiment to match `listeners.Service` on the Go side. Renaming (`Workload`, `DiscoveryTarget`, etc.) is deferred — easy to revisit before GA.

Fields deliberately not exposed in this experiment: `pid`, `hostname`, `image_name`, `tags`, `ad_identifiers`, `extra_config`. None of the 92 targeted integrations need them for the discovery decision. They are the natural extension points for future experiments:

- `pid` for process-mode discovery (read `/proc/<pid>/...`, exec in process namespace).
- `image_name` for stricter pre-probe filtering than `ad_identifiers` provides.
- `extra_config(key)` for K8s-metadata-driven discovery (`kube_namespace`, etc.).
- `tags` rarely needed inside `discover` since the tagger merge happens after; included only when a concrete case requires it.

## File format

Path: `<integration>/datadog_checks/<integration>/data/auto_conf_discovery.yaml`. Same lookup logic as `auto_conf.yaml`. The file is required for discovery to apply — there is no inference from check metadata in this experiment.

```yaml
ad_identifiers:
  - krakend
init_config:
instances: []
```

The instance template is intentionally absent — `discover` returns concrete instance configs. `instances: []` (or omitted) is the correct shape. `init_config` may be set if the integration needs init-time configuration; it is passed through verbatim alongside each discovered instance.

If both `auto_conf.yaml` and `auto_conf_discovery.yaml` exist for the same integration the Agent logs a warning and prefers the discovery file.

## `discover` contract

```python
class MyCheck(AgentCheck):
    @classmethod
    def discover(cls, service: Service) -> list[dict] | None:
        ...
```

Return values:

- `list[dict]` — one instance config per dict. Each is the literal payload that would otherwise come from a resolved `instances:` template entry.
- `None` — probe ran but did not match. Don't schedule. Negative-cache for ~30 s.
- `[]` — probed and explicitly nothing applies (e.g. multi-component umbrella found no components on this host). Don't schedule. Negative-cache for ~30 s.
- Raised exception — discovery itself failed (network error other than verifier rejection, malformed response, bug). Don't schedule. Negative-cache for ~30 s. Log at error.

Tagger merge: the Agent merges AD/tagger-derived tags into each returned instance dict before scheduling, the same way it does for resolved templates today. `discover` returns integration-specific fields only; pod/container/cluster tags layer on after.

Determinism: `discover` must be a pure function of `service`. The Agent caches results per `(service ID, integration name)`; non-deterministic returns will thrash the scheduler.

Optional config-model validation: integrations with a generated `config_models/` (Pydantic from `spec.yaml`) can validate before returning:

```python
@classmethod
def discover(cls, service: Service) -> list[dict] | None:
    raw = cls._discover_raw(service)
    return [cls._instance_model(**i).model_dump() for i in raw] if raw else None
```

Opt-in at first; the base classes can adopt it once the helper proves stable.

## Shared helpers in `datadog_checks_base`

```
datadog_checks/base/utils/discovery/
  __init__.py
  http.py       # http_probe(host, port, path, *, verify, timeout=0.5) -> bool
  tcp.py        # tcp_probe(host, port, *, send=b"", verify, timeout=0.5) -> bool
  ports.py      # candidate_ports(service, hints) -> Iterator[Port]
  verifiers.py  # is_prometheus_exposition, status_2xx, body_contains, body_matches,
                # json_has, response_equals, response_starts_with, ...
```

All helpers are pure functions or thin wrappers around `requests` / `socket`. No global state. Each unit-tested in isolation.

## Per-pattern base classes

```
datadog_checks/base/checks/discovery/
  openmetrics.py      # mixin for OpenMetricsBaseCheckV2 — DISCOVERY_PORTS, DISCOVERY_PATH
  http_static.py      # one fixed (path, verifier) — apache, kyototycoon, lighttpd, squid,
                      # mesos_*, riak, traffic_server, fluentd, hdfs_*, yarn, mapreduce, consul
  http_multi.py       # list of (path, verifier) candidates — nginx, rabbitmq, envoy, ...
  tcp_handshake.py    # send + verifier — redis, memcached, zookeeper, gearmand, statsd
  tcp_banner.py       # server speaks first — twemproxy
```

Each base class implements `discover(cls, service)` using the shared helpers and class-level configuration. An integration that fits a pattern declares the configuration as class attributes and inherits the default `discover`. An integration that doesn't fit overrides `discover` directly.

Worked examples:

```python
# OpenMetrics — 51 integrations get this for free via OpenMetricsBaseCheckV2
class KrakenD(OpenMetricsBaseCheckV2):
    DISCOVERY_PORTS = [9090]

# http-text-format
class Apache(AgentCheck, HTTPStaticDiscoverable):
    DISCOVERY_PORTS = [80]
    DISCOVERY_PATH = "/server-status?auto"
    DISCOVERY_VERIFY = body_contains("Total Accesses:")
    DISCOVERY_FIELD = "apache_status_url"   # how to name the URL in the returned instance

# http-multi-path
class Nginx(AgentCheck):
    @classmethod
    def discover(cls, service: Service) -> list[dict] | None:
        for port in candidate_ports(service, [80, 8080]):
            for path, verifier in [
                ("/nginx_status", body_matches(r"^Active connections:")),
                ("/api/9",        json_has(["version", "processes"])),
                ("/status/format/json", json_has(["nginxVersion"])),
            ]:
                if http_probe(service.host, port.number, path, verify=verifier):
                    return [{"nginx_status_url": f"http://{service.host}:{port.number}{path}"}]
        return None

# tcp-protocol-handshake
class Redis(AgentCheck, TCPDiscoverable):
    DISCOVERY_PORTS = [6379]
    DISCOVERY_SEND = b"PING\r\n"
    DISCOVERY_VERIFY = starts_with(b"+PONG")
    DISCOVERY_INSTANCE = lambda host, port: {"host": host, "port": port}
```

## Probe semantics

Owned by the Agent (Go side, in the new `discoverer` package); the Python `discover` runs inside this envelope.

1. Resolve `host` from `svc.GetHosts()` using the existing fallback policy. If empty, log "no probe target," skip the integration for this service.
2. Build the Python `Service` object: `id = svc.GetServiceID()`, `host = resolved`, `ports = [Port(p.Port, p.Name) for p in svc.GetPorts()]`.
3. Cache lookup keyed by `(svc.GetServiceID(), integrationName)`. On hit: short-circuit.
4. Invoke `<Check>.discover(service)` via rtloader with a per-call deadline (default 2 s).
5. Bound the Python call: hard timeout, cancel on Agent shutdown.
6. On `list[dict]` result: for each dict, build a concrete `integration.Config` (name = integration, instances = [marshalled dict], init_config = from auto_conf_discovery.yaml) and schedule. Cache hit for the lifetime of the service.
7. On `None`/`[]`: cache as failure for ~30 s. Don't schedule.
8. On exception: log at error, cache as failure for ~30 s. Don't schedule. Don't crash.

The Python side is responsible for its own per-port and per-path timeouts inside `discover`. The shared `http_probe`/`tcp_probe` helpers carry sensible defaults (500 ms per attempt). The Agent-side total deadline is the outer bound.

## Demo plan

The same krakend container fixture as the previous experiment, plus one integration from each new bucket:

1. **OpenMetrics base-class default** — krakend. Confirms the migration from the krakend experiment's `%%discovered_port%%` template path to the new `discover` path produces an equivalent scheduled config.
2. **`http-text-format`** — apache with mod_status. Probe `/server-status?auto`, verify `body_contains("Total Accesses:")`, return one instance with `apache_status_url`.
3. **`http-multi-path`** — nginx with stub_status. Probe three (path, verifier) tuples in order, return the first match.
4. **`tcp-protocol-handshake`** — redis. TCP `PING` → `+PONG` verification, return `{host, port}`.

For each: golden path (default port), non-default port (server moved), negative case (wrong service labelled with the ad_identifier).

## File-level summary of the change

| Repo | Path | Change |
|------|------|--------|
| `integrations-core` | `<integration>/datadog_checks/<integration>/data/auto_conf_discovery.yaml` | New file per discovered integration. Contains `ad_identifiers` (and optional `init_config`). No template instance. |
| `integrations-core` | `datadog_checks_base/datadog_checks/base/utils/discovery/` | New package: `http`, `tcp`, `ports`, `verifiers`. |
| `integrations-core` | `datadog_checks_base/datadog_checks/base/checks/discovery/` | New per-pattern mixins/base classes. |
| `integrations-core` | `<integration>/datadog_checks/<integration>/check.py` | Adopt the matching base class or implement `discover` directly. ~5–15 lines per integration in the targeted buckets. |
| `datadog-agent` | `comp/core/autodiscovery/discovery/openmetrics_prober.go` | Delete (superseded by the Python path). |
| `datadog-agent` | `comp/core/autodiscovery/discoverer/` (new package) | Cross-into-Python bridge, candidate-port ordering, cache, time budget. |
| `datadog-agent` | `comp/core/autodiscovery/integration/config.go` | Keep `Discovery` field (or rename to a marker bool — discovery is now indicated by file presence and the integration's `discover` method). |
| `datadog-agent` | `comp/core/autodiscovery/autodiscoveryimpl/configmgr.go` | Replace the `prober.Probe` call with `discoverer.Discover` returning `[]integration.Config` directly. |
| `datadog-agent` | `pkg/util/tmplvar/resolver.go` | Remove `%%discovered_port%%` resolver and `GetDiscoveredPort`. No discovered-value templating. |
| `datadog-agent` | `comp/core/autodiscovery/discovery/service_wrapper.go` | Delete. |
| `datadog-agent` | rtloader bridge | New entry point: `discover(service_handle) -> instances|None`. Marshals `Service` projection to Python and the result back. |

## Risks to verify during implementation

- **Python execution latency.** Discovery runs on service-arrival events, not on the check schedule. Confirm rtloader can host a `discover` invocation with sub-second overhead. If the Python pool is busy with checks, queueing matters; the negative cache mitigates retry storms but the first call needs to be fast.
- **Process listener interaction.** `ProcessService` populates `host = 127.0.0.1` and `ports` from observed TCP listeners. Confirm the Python `Service` projection sees a usable port list for at least one targeted integration when the integration is run as a host-local process (not a container).
- **Digest stability across re-invocations.** Confirm `discover` results produce stable `integration.Config` digests when the underlying service state is unchanged. The cache is the primary defence; verify no codepath bypasses it.
- **Interaction with existing `auto_conf.yaml` for the same integration.** When both files exist (during an integration's migration), the prefer-discovery rule must avoid double-scheduling.
- **Host resolution parity.** The host string passed into Python must match exactly what `%%host%%` resolution produces today (same multi-network policy, same IPv6 bracketing). Existing `tmplvar.GetHost` is the reference implementation; reuse it rather than reimplement.

## Out of scope but worth noting for follow-up

- **Cluster-agent flow.** Service/Endpoints listeners on the cluster agent; potentially a node-agent-runs-discovery / cluster-agent-consumes-result split, or Python-in-cluster-agent.
- **Credentialled integrations.** `creds-*` buckets (75 integrations, 29%). A separate experiment would explore whether secret-store integration plus probe-shape detection can carry any of these.
- **`ad_identifiers` inference from check metadata.** Track separately from this experiment.
- **Renaming the Python `Service` type.** `Workload`, `DiscoveryTarget`, or `Target` — revisit before GA.
- **Exposing `pid`, `image_name`, `extra_config`, `tags`, `hostname` to Python.** Add when a concrete integration needs them, expected to be the trigger for a process-discovery experiment.
