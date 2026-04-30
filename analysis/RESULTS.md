# Integrations Advanced Auto-Config — Results

Final summary of the analysis driven by [DSCVR/6650004331](https://datadoghq.atlassian.net/wiki/spaces/DSCVR/pages/6650004331/Integrations+advanced+auto+config+exploration). The Confluence page is updated; this file is the local hand-off summary for anyone reading the branch.

## Stats

- **Total analysed:** 260 integrations (every `assets/configuration/spec.yaml` in `integrations-core` as of 2026-04-30, ordered by org count from `analysis/inputs/integrations_by_org_count.csv`).
- **Generic auto-config possible:** 96 (36.9%). Method breakdown: 58 `openmetrics-port-scan`, 18 `other` (host-local), 14 `http-path-probe`, 6 `tcp-banner-probe`.
- **Custom auto-config possible:** 40 (15.4%).
- **Auto-config impossible:** 124 (47.7%).
- **Confidence:** 227 high, 33 medium, 0 low.
- **Flagged for human review:** 2 (`ibm_i`, `oracle`).
- **Skipped (no `spec.yaml`):** 270 entries from the CSV (logs/incidents/audit-trail/SaaS-only/marketplace tiles). See `analysis/skipped.md`.

## Headline conclusion

About **a third of integrations could be picked up by a generic "scan ports until something looks like OpenMetrics"** mechanism with no integration-specific code at all — that is, the source ticket's lightest-weight option would deliver real coverage.

The next-largest generic sub-cluster is **host-local kernel/perf-counter integrations** (iis, btrfs, network, disk, system_core, system_swap, infiniband, dotnetclr, aspdotnet, …). For these the auto-config trigger is "is the relevant subsystem present on this host?", not a network probe, and the discovery primitive looks more like Windows SCM enumeration (Windows side) or `/sys|/proc` filesystem checks (Linux side).

The "impossible" bucket is dominated by:

1. **Spec-required credentials** (DBs, JMX, vendor APIs) — credentials cannot come from the wire.
2. **Logs-only / DogStatsD-only / vendor security tiles** — there is no probe surface; the "integration" is just a logs config or a metric-name mapping.
3. **User-supplied generic templates** (openmetrics, prometheus, windows_performance_counters, wmi_check, pdh_check, http_check, tcp_check, dns_check, process, etc.) — the integration *is* the configuration template; nothing for the discovery layer to fingerprint.

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
