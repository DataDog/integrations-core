# Integrations Advanced Auto-Config — Results

Final summary of the analysis driven by [DSCVR/6650004331](https://datadoghq.atlassian.net/wiki/spaces/DSCVR/pages/6650004331/Integrations+advanced+auto+config+exploration). The Confluence page is updated; this file is the local hand-off summary for anyone reading the branch.

## Stats

- **Total analysed:** 260 integrations (every `assets/configuration/spec.yaml` in `integrations-core` as of 2026-04-30, ordered by org count from `analysis/inputs/integrations_by_org_count.csv`).
- **Discovery-bucket distribution** (the primary classification — see [`procedure.md`](procedure.md) for definitions):

| Section | Bucket | Count |
|---|---|---|
| Fully generic | generic-openmetrics-scan | 51 |
| Fully generic | generic-incluster-bearer-token | 10 |
| Fully generic | generic-windows-perf | 6 |
| Fully generic | generic-linux-procfs | 7 |
| HTTP probe (specific verification) | http-text-format | 4 |
| HTTP probe (specific verification) | http-json-shape | 10 |
| HTTP probe (specific verification) | http-multi-path | 21 |
| TCP probe (specific protocol) | tcp-banner-server-greets | 1 |
| TCP probe (specific protocol) | tcp-protocol-handshake | 5 |
| Local detection | local-cli-binary | 10 |
| Local detection | local-scm-enumeration | 1 |
| Local detection | cloud-task-metadata | 1 |
| Local detection | local-config-file | 2 |
| Credentials required | creds-spec-mandated | 24 |
| Credentials required | creds-jmx-rmi | 14 |
| Credentials required | creds-api-token | 24 |
| Credentials required | creds-proprietary-client | 9 |
| Credentials required | creds-auth-optional-practical | 4 |
| No probe surface | logs-only | 38 |
| No probe surface | dogstatsd-only | 1 |
| No probe surface | user-schema-template | 6 |
| No probe surface | user-intent-synthetic | 6 |
| No probe surface | per-process-discovery | 5 |

- The legacy 3-way classification (`generic` / `custom` / `impossible`) is also kept on every per-integration JSON for backward reference: 96 generic, 40 custom, 124 impossible.
- **Confidence:** 227 high, 33 medium, 0 low.
- **Flagged for human review:** 2 (`ibm_i`, `oracle`).
- **Skipped (no `spec.yaml`):** 270 entries from the CSV (logs/incidents/audit-trail/SaaS-only/marketplace tiles). See `analysis/skipped.md`.

## Headline conclusion

After the bucket refinement, **74 of 260 integrations (28%) are fully generic** — the discovery layer needs no integration-specific verification code at all, just a per-integration port + path table. These break down as:

- **51** — `generic-openmetrics-scan` (Prometheus exposition format on a known port)
- **10** — `generic-incluster-bearer-token` (same as above, with the Agent's pod ServiceAccount token auto-injected)
- **6** — `generic-windows-perf` (PDH counter set presence on the local Windows host)
- **7** — `generic-linux-procfs` (`/proc` and `/sys` reads on the local Linux host)

The next ~35 integrations have a fixed URL/port but need integration-specific *verification* (text/JSON shape, multi-path probing). These are real custom-logic territory — the user's stricter definition of "not generic":

- `http-text-format` (3, e.g. apache mod_status, squid)
- `http-json-shape` (10, e.g. mesos `id`+`frameworks`, fluentd `plugins`, yarn `clusterMetrics`)
- `http-multi-path` (21, e.g. nginx 3-paths, rabbitmq Prometheus+Management, envoy stats vs Prometheus)

Plus 6 with TCP-protocol-specific handshakes (redis, memcached, zookeeper 4LW, gearmand, statsd, twemproxy).

The "no probe surface" bucket — logs-only tiles, DogStatsD-only, user-supplied templates, synthetic probes, per-process discovery — accounts for **56 integrations (22%)**.

Credentials-required buckets (124 total, 48%) split into 5 sub-categories: spec-mandated DB creds (24), JMX/RMI (14), API token / OAuth (24), proprietary client library (9), auth-optional-but-practically-required (4), plus `local-cli-binary` (10) and `local-config-file` (2) which need host-local state.

## Patterns surfaced (named in `procedure.md`)

19 named patterns A–S were extracted during the bootstrap and waves. Highest leverage for engineering follow-up:

- **A. OpenMetrics on a known port** — single canonical port + `/metrics`. Generic. ~58 integrations.
- **H. Local Windows host detection** — perf counters, no network probe.
- **L. Local CLI subprocess** — varnish, ceph, nodetool, slurm, glusterfs, lustre, lparstats, postfix.
- **O. In-cluster bearer-token auth** — k8s control-plane integrations don't get downgraded to "impossible" just because they need a token.
- **P. JMX-over-HTTP servlet** — looks JMX-shaped but is actually `/jmx` HTTP (hdfs_datanode, hdfs_namenode); generic.
- **Q. Hard-coded URL fallback list** — strong generic signal (etcd, kube_controller_manager, kube_scheduler).
- **R. Two-path single-spec dual API** — envoy, airflow, traefik_mesh, torchserve.

## Items flagged for human review

| Integration | Why flagged |
|---|---|
| [`ibm_i`](integrations/ibm_i.json) | Proprietary ODBC driver must be installed on the Agent host. Sits between pattern D (DB credentials) and pattern L (local CLI) — could merit a new "Pattern T: proprietary client library prerequisite". |
| [`oracle`](integrations/oracle.json) | Same shape as `ibm_i`: needs Oracle Instant Client / native client / JDBC driver on the Agent host. No `datadog_checks/oracle/` Python package in `integrations-core` (it's Agent-core/DBM-managed) — flagged for confirmation that the analysis correctly captures the integration's true shape. |

## Surprises that overrode hints

A few sub-agents had to correct their starting hypotheses against the code. Worth noting because they're plausibly recurrent in future analyses:

- `ping_federate` is logs-only despite PingFederate's Prometheus support — the in-repo tile carries no Prometheus configuration.
- `microsoft_dns` and `keycloak` are also logs-only despite both upstream systems having Prometheus modes.
- `tibco_ems` shells out to the local `tibemsadmin` CLI; it is **not** a JMX integration despite the family name.
- `ibm_was` uses the WebSphere PerfServlet over HTTP, **not** JMX.
- `nfsstat` shells out to `nfsiostat`; it does not read `/proc/net/rpc/nfsd` directly.
- `statsd` is the **Etsy StatsD admin protocol** integration (TCP banner probe on 8126), not DogStatsD.
- `celery` ships an OpenMetrics endpoint via Celery Flower; it is **not** DogStatsD-only.

## Layout on this branch (`analysis/auto-config-exploration`)

```
analysis/
├── README.md                               # Pointer to design / plan / procedure
├── procedure.md                            # 19-pattern rubric used by every wave
├── schema.json                             # JSON schema for per-integration output
├── queue.txt                               # 260 integrations (CSV order ∩ has spec.yaml)
├── skipped.md                              # 270 CSV entries with no Agent spec.yaml
├── state.json                              # Final orchestrator state
├── summary.md                              # Verbose tables (one paragraph per row)
├── summary_brief.md                        # Brief tables (the form pushed to Confluence)
├── integrations/<name>.json (×260)         # Per-integration analysis (canonical data)
├── inputs/integrations_by_org_count.csv    # Source CSV
└── scripts/
    ├── build_queue.py                      # CSV → queue.txt + skipped.md
    ├── validate.py                         # Stdlib JSON schema validator
    ├── render_summary.py                   # *.json → summary.md, summary_brief.md
    ├── render_html.py                      # markdown subset → Confluence HTML
    ├── build_confluence_body.py            # Intro + summary, links rewritten
    └── tests/                              # pytest tests for the three Python utilities
```

The design spec and implementation plan live under `docs/superpowers/specs/` and `docs/superpowers/plans/` respectively.

## Re-running

```bash
python3 analysis/scripts/build_queue.py
python3 -m pytest analysis/scripts/tests -v
python3 analysis/scripts/render_summary.py
python3 analysis/scripts/build_confluence_body.py brief    # for incremental pushes
python3 analysis/scripts/build_confluence_body.py verbose  # full per-integration prose
```

## Source artifacts on Confluence

The source ticket was updated through six page versions during the run:

- v2 — Bootstrap (15 integrations).
- v3 — Wave 1 (+50 → 65).
- v4 — Wave 2 (+50 → 115).
- v5 — Wave 3 (+50 → 165).
- v6 — **Final (+95 → 260)**, currently displayed on the page.

The verbose per-integration details (the `summary.md` form) are kept on this branch rather than on Confluence, because the tables are large enough that the brief form is a better fit for the source ticket's request that "if many integrations just use an OpenMetrics endpoint no need to be verbose about it".
