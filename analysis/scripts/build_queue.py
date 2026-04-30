"""Build queue.txt (CSV order intersected with has-spec.yaml) and skipped.md."""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "analysis" / "inputs" / "integrations_by_org_count.csv"
QUEUE_PATH = ROOT / "analysis" / "queue.txt"
SKIPPED_PATH = ROOT / "analysis" / "skipped.md"

ALIASES = {
    "redis": "redisdb",
    "elasticsearch": "elastic",
    "memcached": "mcache",
    "kafka": "kafka_consumer",
    "kubernetes_controller_manager": "kube_controller_manager",
    "zookeeper": "zk",
    "mongodb": "mongo",
    "mongodb_atlas": "mongo",
    "ssh": "ssh_check",
    "event_viewer": "win_event_log",
    "datadog_cluster_agent": "datadog_cluster_agent",
    "sql_server": "sqlserver",
    "kube_dns": "kube_dns",
    "kube_scheduler": "kube_scheduler",
    "wmi": "wmi_check",
    "iis": "iis",
    "container": "containerd",
    "cri": "cri",
    "containerd": "containerd",
    "datadog_cluster_agent_admission": "datadog_cluster_agent",
    "knative_for_anthos": "knative",
    "synthetics_data": "",
    "logs": "",
    "incidents": "",
    "feed": "",
    "audit_trail": "",
    "push_notifications": "",
    "security_monitoring": "",
    "network_performance_monitoring": "",
    "tls": "tls",
    "github": "github",
    "snmp": "snmp",
    "vault": "vault",
}


def normalize(name):
    s = name.strip().strip('"').lower()
    s = re.sub(r"[\s\-./]+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    return s.strip("_")


def resolve_directory(name):
    aliased = ALIASES.get(name, name)
    if aliased == "":
        return None
    p = Path(aliased) / "assets" / "configuration" / "spec.yaml"
    if p.exists():
        return aliased
    p = Path(name) / "assets" / "configuration" / "spec.yaml"
    if p.exists():
        return name
    return None


def read_csv_names(path):
    with path.open() as f:
        reader = csv.reader(f)
        next(reader)  # header
        for row in reader:
            if row:
                yield row[0]


def all_integration_dirs():
    """Every integration directory with a spec.yaml, for back-fill."""
    out = []
    for p in sorted(ROOT.iterdir()):
        if (p / "assets" / "configuration" / "spec.yaml").exists():
            out.append(p.name)
    return out


def main():
    seen = set()
    queue = []
    skipped = []
    for raw in read_csv_names(CSV_PATH):
        norm = normalize(raw)
        if norm in seen:
            continue
        seen.add(norm)
        directory = resolve_directory(norm)
        if directory and directory not in queue:
            queue.append(directory)
        elif not directory:
            skipped.append((raw, "no spec.yaml in repo"))

    in_queue = set(queue)
    appended = 0
    for d in all_integration_dirs():
        if d not in in_queue:
            queue.append(d)
            appended += 1

    QUEUE_PATH.write_text("\n".join(queue) + "\n")
    lines = ["# Skipped integrations (no Agent spec.yaml)\n",
             "These appear in the org-count CSV but have no `assets/configuration/spec.yaml`",
             "in `integrations-core` — typically platform features (logs, incidents, audit trail),",
             "SaaS-only integrations, or marketplace tiles.\n"]
    for name, reason in skipped:
        lines.append(f"- `{name}` — {reason}")
    SKIPPED_PATH.write_text("\n".join(lines) + "\n")
    print(f"queue: {len(queue)} (CSV-ordered: {len(queue) - appended}, "
          f"appended at tail: {appended}); skipped: {len(skipped)}")


if __name__ == "__main__":
    main()
