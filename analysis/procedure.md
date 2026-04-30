# Procedure: per-integration auto-config feasibility analysis

Output goes to `analysis/integrations/<name>.json` and must validate against
`analysis/schema.json` (run `python3 analysis/scripts/validate.py <file>`).

## Steps

1. **Read** `<name>/assets/configuration/spec.yaml`.
   - Find the `instances` block (or whichever block defines the per-instance
     options for an Agent check).
   - For every option, capture `name`, whether it's `required`, and its
     `default`. Put them in `all_relevant_fields`.
   - A field is "required" if it has `required: true` AND no `default`. Some
     specs use `value.example` as the default for the user-facing template;
     don't confuse that with an actual default — it's a placeholder.
   - Don't bother listing options that are clearly orthogonal to discovery
     (`tags`, `min_collection_interval`, `service`, `empty_default_hostname`,
     etc.). Stick to fields that actually drive endpoint resolution / auth.

2. **Check** `<name>/datadog_checks/<name>/data/auto_conf.yaml`. Set
   `has_existing_auto_conf` and `auto_conf_path` accordingly. Its presence
   proves Autodiscovery templating already works for the integration. Its
   contents tell you what the project assumes the user will know.

3. **Read** the check implementation (`<name>/datadog_checks/<name>/<name>.py`
   or equivalent). Find what each required field actually drives:
   - TCP socket connect → candidate for `tcp-banner-probe`.
   - HTTP request to a fixed URL → candidate for `http-path-probe` (generic
     if the URL is well-known and singular; custom if multiple plausible
     URLs).
   - OpenMetrics endpoint → candidate for `openmetrics-port-scan`.
   - Reads the server's own config files → `config-file-parse` (custom).
   - Binds username / password / token / API key / certificate →
     `credentials-required` (impossible).

4. **Skim** `<name>/README.md` for sanity checks: identify the upstream
   system, its conventional default port, and whether the integration is
   one of multiple modes (e.g. `apache` Apache + mod_status + ExtendedStatus).

5. **WebFetch** upstream docs only when the spec or README is ambiguous about
   a default port / endpoint. Cite the URL in `references`.

6. **Classify** the integration:
   - **generic** — host + a well-known port (or a single well-known URL) is
     enough; everything else has defaults or is easily probable from the
     wire. The probe is integration-agnostic.
     - Methods: `openmetrics-port-scan`, `tcp-banner-probe`, `http-path-probe`
       (when there is *one* canonical path).
   - **custom** — needs integration-specific logic: trying multiple URL
     paths, parsing the server's config file, multi-endpoint discovery,
     plugin variants.
     - Methods: `http-path-probe` (when there are multiple plausible paths),
       `config-file-parse`, `other`.
   - **impossible** — needs credentials, API keys, tenant / account / region
     IDs, OAuth tokens, certificates, or any other state that doesn't
     come over the wire.
     - Method: `credentials-required`.

7. **Confidence** is your honest read on the JSON:
   - `high` — spec is clear, code matches, port/endpoint is universal.
   - `medium` — minor ambiguity (one optional that may be required in
     practice, or upstream supports multiple deployment modes).
   - `low` → set `needs_human_review: true`. Use when the spec is unusual
     enough that you wouldn't bet on the classification.

8. **Emit** the JSON. Use stable enum values matching `schema.json`. Cite
   every source in `references` (file path or url).

## Confidence shortcuts

- `auto_conf.yaml` exists, contains only `host` / `port` / a fixed URL with
  no `%%env_…%%` template → likely **generic**, **high** confidence.
- `auto_conf.yaml` contains `password: "%%env_…%%"`, `apikey:`, or
  `<API_KEY>` placeholders → **impossible**, **high** confidence.
- spec.yaml has `username` / `password` / `auth_type` as required → almost
  always **impossible** (some exceptions: optional auth, where the integration
  works without credentials in the default deployment).
- Check imports `OpenMetricsBaseCheck` / `OpenMetricsBaseCheckV2` /
  `OpenMetricsCompatibilityCheck` and the user passes a single URL → strong
  signal of **generic** with `openmetrics-port-scan`. If the URL has a
  variable path, then **custom** with `http-path-probe`.
- Integrations whose check inherits `JMXFetch` always need
  `host` + `port` + `user` + `password` → **impossible**.

## Worked example: redisdb

```json
{
  "name": "redisdb",
  "display_name": "Redis",
  "spec_path": "redisdb/assets/configuration/spec.yaml",
  "required_fields": ["host", "port"],
  "all_relevant_fields": [
    {"name": "host",     "required": true,  "default": "localhost"},
    {"name": "port",     "required": true,  "default": 6379},
    {"name": "password", "required": false, "default": null},
    {"name": "ssl",      "required": false, "default": false}
  ],
  "classification": "generic",
  "auto_config_method": "tcp-banner-probe",
  "has_existing_auto_conf": true,
  "auto_conf_path": "redisdb/datadog_checks/redisdb/data/auto_conf.yaml",
  "explanation": "Redis answers a banner over TCP; default port 6379 is universal. Auth-only deployments need a password (out of scope for generic discovery), but the existing autodiscovery template handles the rest.",
  "references": [
    {"kind": "spec",     "path": "redisdb/assets/configuration/spec.yaml"},
    {"kind": "auto_conf","path": "redisdb/datadog_checks/redisdb/data/auto_conf.yaml"}
  ],
  "confidence": "high",
  "needs_human_review": false,
  "notes": ""
}
```

## Time budget

5 minutes per integration. If you're stuck, set `needs_human_review: true`,
write what you know, and move on. The summary will surface the entry with a
warning marker.

## Patterns observed (after Phase 1 bootstrap, 15 integrations)

The bootstrap surfaced a few recurring shapes worth naming. Use these as
shortcuts but verify them against the actual `spec.yaml` and check code.

### A. "OpenMetrics on a known port" — `generic` / `openmetrics-port-scan`

Hallmarks:
- Spec uses `template: instances/openmetrics` or
  `template: instances/openmetrics_legacy`.
- `auto_conf.yaml` (in spec or on disk) sets `openmetrics_endpoint` /
  `prometheus_url` to `http://%%host%%:PORT/metrics` (port and path are fixed).
- No `username` / `password` in the required path.

Examples: coredns, etcd. Classification: **generic**, **high** confidence.

### B. "Single canonical HTTP path" — `generic` / `http-path-probe`

Hallmarks:
- Required field is a single URL with one universal path (e.g.
  `/server-status?auto`).
- Upstream documents that exact path as the monitoring endpoint.

Examples: apache. Classification: **generic**, **high** confidence.

### C. "TCP banner / known protocol" — `generic` / `tcp-banner-probe`

Hallmarks:
- Required fields are `host` + `port` only.
- The server speaks first (Redis: server greeting; SSH: banner) or responds
  to a fixed protocol-specific request (Memcached: `version`).

Examples: redisdb. Classification: **generic**, **high** confidence.

### D. "Spec-required credentials" — `impossible` / `credentials-required`

Hallmarks:
- `username` and/or `password` (or API key, certificate, OAuth) is
  `required: true` in the spec.
- The DB / management API can't be queried without them.

Examples: postgres, mysql, sqlserver. Classification: **impossible**,
**high** confidence.

### E. "Auth-optional in spec but practically required" — `custom` / `credentials-required`

Hallmarks:
- Spec marks `username` / `password` as optional, but every production
  deployment of the upstream system enables authentication (e.g. xpack
  security, Mongo auth, SASL/SSL on Kafka).
- The localhost-no-auth case works for development.

Examples: elastic, mongo, kafka_consumer. Classification: **custom**,
**medium** confidence. Add a note that real deployments will fall through
to credential discovery.

### F. "Dual-mode: Prometheus plus legacy" — `custom` / `http-path-probe`

Hallmarks:
- Spec defines two distinct collection paths (typically a Prometheus /
  OpenMetrics plugin and a management API or stats page).
- The Prometheus path is unauthenticated and easy; the legacy path needs
  basic auth.
- A discovery layer must probe the Prometheus port first and fall back.

Examples: rabbitmq, haproxy. Classification: **custom**, **high** to
**medium** confidence depending on default-port stability.

### G. "Multiple plausible URL paths" — `custom` / `http-path-probe`

Hallmarks:
- One URL field, but the path varies by upstream module/version (e.g.
  nginx stub_status, Plus `/api`, vts JSON).
- The discovery layer must try paths in order and inspect response shape.

Examples: nginx. Classification: **custom**, **high** confidence.

### H. "Local Windows host detection" — `generic` / `other`

Hallmarks:
- Spec inherits `template: instances/perf_counters`.
- No remote host/port in the default mode (the Agent runs on the same
  Windows host that exposes the counters).
- Optional `pdh_legacy` mode adds remote host + credentials.

Examples: iis. Classification: **generic**, **medium** confidence. Method
is `other` because there's no network probe — discovery is "is this
service installed on this machine?". Likely also applies to
`active_directory`, `dns_check`, `exchange_server`, `windows_service`.

### I. "Credential-gated network discovery" — `impossible` / `credentials-required`

Hallmarks:
- The integration includes its own network-sweep autodiscovery (e.g. SNMP
  `network_address` + profiles).
- Sweep still requires a credential to authenticate against discovered
  devices.

Examples: snmp. Classification: **impossible**, **high** confidence —
auto-config feasibility is about credential discovery, not device discovery.

### J. "User-supplied generic check template" — `impossible` / `other`

Hallmarks:
- The integration is a *framework*, not a service binding: the user
  provides the URL, counter list, metric mapping, JMX MBean list, etc.
- Required spec fields name *what to collect*, not *where to probe*.
- The check class is a base class (`OpenMetricsBaseCheckV2`,
  `PerfCountersBaseCheck`, plain `AgentCheck` with subprocess), not a
  service-specific implementation.

Examples: openmetrics, prometheus (generic), windows_performance_counters,
wmi_check. Classification: **impossible**, **high** confidence — there
is no upstream system to autodiscover because the integration itself is
the configuration template.

### K. "Synthetic / user-intent probe" — `custom` or `impossible`

Hallmarks:
- The check actively probes a target the user nominates (`tls`,
  `http_check`, `tcp_check`, `ssh_check`).
- There is no upstream "service" running alongside the Agent — the user
  picks an arbitrary remote.

Classification: **custom** when no credentials are required (`tls`,
`http_check`, `tcp_check`); **impossible** when authentication is needed
(`ssh_check`). Method: `other` for unauthenticated, `credentials-required`
when creds are needed.

### L. "Local CLI subprocess" — `custom` / `other`

Hallmarks:
- The check executes a local binary (`varnishstat`, `ceph`, `postqueue`)
  and parses its output.
- May need group/sudo privileges or a keyring file the user must provision.
- Discovery on the Agent host: "is this binary installed and runnable?"

Examples: varnish, ceph, postfix. Classification: **custom**,
**medium** confidence; method: `other`. Linux analogue of pattern H.

### M. "Process-name local discovery" — `impossible` / `other`

Hallmarks:
- The check enumerates host processes (psutil) and matches a user-supplied
  name (`proc_name`).
- The choice of which application to monitor is user policy, not a
  discoverable property.

Examples: gunicorn. Classification: **impossible**, **high** confidence —
similar to pattern J in that the user's *intent* is the missing input.

### N. "DogStatsD / instrumentation-only" — `impossible` / `other`

Hallmarks:
- The "integration" is just a logs config + dogstatsd_mapper_profiles; no
  Agent check is dispatched against a live endpoint.
- The upstream emits metrics to the Agent via DogStatsD (or by tailing logs).

Examples: sidekiq. Classification: **impossible**, **high** confidence —
auto-config in the network-probe sense doesn't apply; the integration
exists as a metric-name mapping, not a probe.

### O. "In-cluster bearer-token auth" — does NOT downgrade to `impossible`

Many Kubernetes control-plane integrations (`kube_controller_manager`,
`kube_scheduler`, `kube_apiserver`, `kube_proxy`) reach Prometheus
endpoints behind authentication, but the credential is the pod's own
ServiceAccount bearer token mounted at
`/var/run/secrets/kubernetes.io/serviceaccount/token`. The Agent supplies
this automatically when running in-cluster. Treat these as **generic**
with `openmetrics-port-scan`, not impossible — the credential is
auto-injected, not user-supplied.

### P. "JMX-over-HTTP servlet" — `generic` / `http-path-probe`

Hallmarks:
- Looks JMX-shaped in the spec, but the check actually scrapes the
  Hadoop-style `/jmx` HTTP servlet on a fixed port.
- No JMXFetch / RMI involved.

Examples: hdfs_datanode. Classification: **generic**, **high** confidence.
Distinct from the JMXFetch-impossible rule — read the check code to
confirm whether it inherits `JMXFetch` or just GETs `/jmx`.

### Q. "Hard-coded URL fallback list" — strong `generic` signal

When the spec ships a built-in `possible_prometheus_urls` ordered list
(e.g. kube_controller_manager, etcd), the discovery layer effectively
already lives inside the integration. Classification: **generic**,
**high** confidence.

### R. "Two-path single-spec dual API" — `custom` / `http-path-probe`

Distinct from F (rabbitmq, haproxy, where the two modes live in *separate*
instance fields):

Hallmarks:
- One required URL field, but the check tries multiple paths or APIs in
  order under that single field (envoy: `/stats/prometheus` vs `/stats`;
  airflow: REST API v1 vs experimental).

Examples: envoy, airflow. Classification: **custom**, **medium** to
**high** confidence depending on how many fallback paths and how stable
the upstream version split is.

### S. "Topology multiplexer (mode enum)" — `custom` / `http-path-probe` or `other`

Hallmarks:
- Spec has an enum field (`spark_cluster_mode`, `istio_mode`, etc.) that
  selects between mutually-exclusive backend topologies (Standalone vs
  YARN vs Mesos for Spark; sidecar vs ambient for Istio).
- Different ports, different response shapes, different auth.

Examples: spark, istio. Classification: **custom**, **medium** confidence.

## Free-form instance labels are NOT discovery blockers

When a `required: true` field is just a freeform tag (`name` in squid,
`cluster_name` in spark), don't classify the integration as impossible
on that basis — the auto-config layer can synthesize it from container
or host metadata. Only classify as impossible if the field needs
*specific* user input (URL, credentials, metric list, etc.).

## Decision rule for "auth-optional in spec"

When the spec marks `username` / `password` (or token / cert) as optional:
- If the integration has *no* mode that works without authentication
  in production-shaped deployments → **impossible**.
- If there is *one* unauthenticated path that is realistic
  (e.g. RabbitMQ's Prometheus plugin) → **custom** (cover both modes).
- If localhost-no-auth is the typical case → **generic**, but flag the
  production caveat in `notes`.
