"""Render analysis/integrations/*.json into analysis/summary*.md.

Output structure:

    ## Section title
    ### bucket-name (count)
    _One-sentence bucket description._
    | table rows |

A trailing summary file (summary.md) keeps the verbose Method/detail column;
summary_compact.md trims explanations to ~240 chars; summary_brief.md drops
explanations entirely and shows only Integration | Required fields | Method |
Confidence.
"""
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INT_DIR = ROOT / "analysis" / "integrations"
OUT_VERBOSE = ROOT / "analysis" / "summary.md"
OUT_BRIEF = ROOT / "analysis" / "summary_brief.md"
OUT_COMPACT = ROOT / "analysis" / "summary_compact.md"


SECTIONS = [
    ("Fully generic", "No integration-specific verification code; the discovery layer carries at most a per-integration port + path table.", [
        ("generic-openmetrics-scan",
         "Probe a port for `/metrics`, validate Prometheus exposition format. Per-integration data is just port + path."),
        ("generic-incluster-bearer-token",
         "Same as openmetrics-scan but the Agent's pod ServiceAccount token is auto-injected for HTTPS+auth endpoints. Per-integration data is just port + path."),
        ("generic-windows-perf",
         "Detect a PDH counter set on the local Windows host (e.g. `IIS`, `MSExchange*`). Per-integration data is the counter set name + counter list."),
        ("generic-linux-procfs",
         "Read host-local files under `/proc` or `/sys`. Per-integration data is just the file paths."),
    ]),
    ("HTTP probe with integration-specific verification", "Fixed URL on a known port, but the discovery layer needs integration-specific verification code (more than just \"is this Prometheus exposition format?\") to confirm the target.", [
        ("http-text-format",
         "Fixed URL, integration-specific text/HTML format (e.g. apache mod_status, squid Cache Manager `key = value`)."),
        ("http-json-shape",
         "Fixed URL, JSON shape verification with integration-specific keys (e.g. `version`+`cluster` for mesos master, `id`+`frameworks` for mesos slave)."),
        ("http-multi-path",
         "Try several plausible paths or modes per integration (e.g. nginx stub_status / Plus API / VTS; rabbitmq Prometheus + management plugin)."),
    ]),
    ("TCP probe with integration-specific protocol", "Open a TCP socket, exchange integration-specific bytes to confirm the target.", [
        ("tcp-banner-server-greets",
         "Server speaks first with an integration-specific reply (e.g. twemproxy emits its stats JSON on connect)."),
        ("tcp-protocol-handshake",
         "Client sends fixed bytes, integration-specific reply (memcached `version`, redis `PING`/`+PONG`, zookeeper `ruok`/`imok`, gearmand admin protocol, statsd `health`)."),
    ]),
    ("Local detection (no network, no credentials)", "The integration runs against host-local state; discovery is \"is this thing present on the Agent host?\".", [
        ("local-cli-binary",
         "Shell out to a local CLI binary (`varnishstat`, `ceph`, `gstatus`, `nodetool`, `lctl`, `slurm`, `lparstat`, `tibemsadmin`, `nfsiostat`, `postqueue`)."),
        ("local-scm-enumeration",
         "Enumerate the Windows Service Control Manager."),
        ("cloud-task-metadata",
         "Hit the link-local task metadata endpoint of the cloud platform (`ECS_CONTAINER_METADATA_URI_V4`)."),
        ("local-config-file",
         "Read a user-supplied local config or DB file (`duckdb` `.db` file, nagios `nagios.cfg`)."),
    ]),
    ("Credentials required", "The check needs credentials that cannot be discovered from the wire. Sub-bucketed by what kind of credential.", [
        ("creds-spec-mandated",
         "Spec marks `username`/`password` (or equivalent) as required with no default. Typical for traditional databases."),
        ("creds-jmx-rmi",
         "JMX/RMI integrations (`is_jmx: true`, `template: instances/jmx`). Production deployments enable JMX authentication; ports are not standardized."),
        ("creds-api-token",
         "Vendor REST API behind an API key, OAuth client credentials, or bearer token."),
        ("creds-proprietary-client",
         "Needs a proprietary client library installed on the Agent host (Oracle Instant Client, IBM `ibm_db`, `pymqi`, `hdbcli`, FoundationDB cluster file, …) plus credentials."),
        ("creds-auth-optional-practical",
         "Spec marks auth as optional but production deployments invariably need it (xpack-secured Elasticsearch, MongoDB with auth enabled, Vault token-gated metrics, etc.)."),
    ]),
    ("No probe surface", "No reachable upstream service to probe at all. The integration is a logs sink, a DogStatsD listener, a generic configuration template, or a synthetic check.", [
        ("logs-only",
         "Vendor security tile or log-only integration. The Agent ingests logs; there is no metric check to schedule."),
        ("dogstatsd-only",
         "Application instruments via DogStatsD; the Agent only listens — no probe."),
        ("user-schema-template",
         "The integration is a configuration framework: the user supplies the URL / counter list / metric mapping that defines what to collect."),
        ("user-intent-synthetic",
         "User nominates an arbitrary target to probe (`http_check`, `tcp_check`, `dns_check`, `tls`, `directory`, `win32_event_log`)."),
        ("per-process-discovery",
         "User picks which application to monitor by name; the check enumerates host processes."),
    ]),
]


def load_all():
    return [json.loads(p.read_text()) for p in sorted(INT_DIR.glob("*.json"))]


def _refs(rec):
    parts = []
    for r in rec.get("references", []):
        if "url" in r:
            parts.append(f"[{r['kind']}]({r['url']})")
        elif "path" in r:
            parts.append(f"[{r['kind']}](../{r['path']})")
    return ", ".join(parts) or "—"


def _fields(rec):
    return ", ".join(f"`{f}`" for f in rec.get("required_fields", [])) or "—"


def _flag(rec):
    return " ⚠" if rec.get("needs_human_review") else ""


def _verbose_row(rec):
    expl = rec.get("explanation", "").replace("|", "\\|")
    return (f"| {rec['display_name']}{_flag(rec)} (`{rec['name']}`) "
            f"| {_fields(rec)} "
            f"| {rec.get('auto_config_method', '')} — {expl} "
            f"| {_refs(rec)} |")


def _trim_explanation(text, limit=240):
    if len(text) <= limit:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out = ""
    for s in sentences:
        if len(out) + len(s) + 1 > limit and out:
            break
        out = (out + " " + s).strip() if out else s
    return out


def _compact_row(rec):
    expl = _trim_explanation(rec.get("explanation", "")).replace("|", "\\|")
    return (f"| {rec['display_name']}{_flag(rec)} (`{rec['name']}`) "
            f"| {_fields(rec)} "
            f"| {rec.get('auto_config_method', '')} — {expl} "
            f"| {_refs(rec)} |")


def _brief_row(rec):
    return (f"| {rec['display_name']}{_flag(rec)} (`{rec['name']}`) "
            f"| {_fields(rec)} "
            f"| {rec.get('auto_config_method', '')} "
            f"| {rec.get('confidence', '')} |")


VERBOSE_HEADER = "| Integration | Required fields | Method / detail | References |\n|---|---|---|---|"
BRIEF_HEADER = "| Integration | Required fields | Method | Conf. |\n|---|---|---|---|"


def _render(records, row_fn, table_header, generated_at=None):
    by_bucket = defaultdict(list)
    for r in records:
        by_bucket[r["discovery_bucket"]].append(r)

    section_counts = []
    for section_title, _, buckets in SECTIONS:
        n = sum(len(by_bucket.get(b, [])) for b, _ in buckets)
        section_counts.append((section_title, n))

    review = sum(1 for r in records if r.get("needs_human_review"))
    total = len(records)
    generated_at = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    out = []
    out.append(
        f"_Generated {generated_at}. {total} integrations classified across "
        f"23 discovery buckets in 6 sections; {review} need review (⚠)._\n"
    )
    out.append(
        "**Sections:** "
        + " · ".join(
            f"[{title} ({n})](#{_anchor(title)})"
            for title, n in section_counts
        )
        + "\n"
    )

    for (section_title, section_desc, buckets), (_, section_count) in zip(SECTIONS, section_counts):
        out.append(f"## {section_title} ({section_count})\n")
        out.append(f"_{section_desc}_\n")
        for bucket_name, bucket_desc in buckets:
            recs = sorted(by_bucket.get(bucket_name, []), key=lambda r: r["name"])
            out.append(f"### `{bucket_name}` ({len(recs)})\n")
            out.append(f"{bucket_desc}\n")
            if not recs:
                out.append("_(no integrations in this bucket)_\n")
                continue
            out.append(table_header)
            for rec in recs:
                out.append(row_fn(rec))
            out.append("")
    return "\n".join(out)


def _anchor(title):
    """Approximate GitHub-style heading anchor."""
    a = title.lower()
    a = re.sub(r"[^a-z0-9 -]", "", a)
    return a.replace(" ", "-")


def render(records, generated_at=None):
    return _render(records, _verbose_row, VERBOSE_HEADER, generated_at)


def render_compact(records, generated_at=None):
    return _render(records, _compact_row, VERBOSE_HEADER, generated_at)


def render_brief(records, generated_at=None):
    return _render(records, _brief_row, BRIEF_HEADER, generated_at)


def main():
    records = load_all()
    OUT_VERBOSE.write_text(render(records))
    print(f"wrote {OUT_VERBOSE} ({len(records)} integrations)")
    OUT_BRIEF.write_text(render_brief(records))
    print(f"wrote {OUT_BRIEF}")
    OUT_COMPACT.write_text(render_compact(records))
    print(f"wrote {OUT_COMPACT}")


if __name__ == "__main__":
    main()
