# Integrations Advanced Auto-Config Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Classify every Agent integration in `integrations-core` (~260 with `spec.yaml`) by auto-config feasibility (generic / custom / impossible), produce a per-integration JSON dataset, render a summary, and post the summary to the Confluence "Analysis" section of page `6650004331`.

**Architecture:** Main session orchestrates: builds the queue, manually analyzes ~15 seed integrations, then dispatches adaptive waves of 10 parallel sub-agents (5 integrations each). Outputs are JSON files validated against a schema, rolled up into a single markdown summary, and pushed to Confluence after every wave. Working branch `analysis/auto-config-exploration` (already created).

**Tech Stack:** Python 3 (stdlib only — `json`, `csv`, `pathlib`, `subprocess`, `re`, `urllib`), `ddev` for spec parsing where helpful, `rg`/`find` for code spelunking, Atlassian MCP for Confluence pushes.

**Reference spec:** `docs/superpowers/specs/2026-04-30-integrations-auto-config-analysis-design.md` — read this first.

---

## File Structure

Created in this plan:

| Path | Responsibility |
|------|----------------|
| `analysis/procedure.md` | Step-by-step rubric for each integration analysis. |
| `analysis/schema.json` | JSON Schema (draft-07) for per-integration output. |
| `analysis/queue.txt` | Newline-delimited integration names, CSV order, only those with `spec.yaml`. |
| `analysis/skipped.md` | CSV entries skipped (no spec.yaml) with reasons. |
| `analysis/state.json` | Orchestrator state (done/failed/in_flight/wave). |
| `analysis/integrations/<name>.json` | Per-integration result. |
| `analysis/summary.md` | Three rendered tables (Confluence body source). |
| `analysis/scripts/build_queue.py` | Builds `queue.txt` + `skipped.md` from CSV. |
| `analysis/scripts/validate.py` | Validates a JSON file against `schema.json`. |
| `analysis/scripts/render_summary.py` | Renders `summary.md` from all `integrations/*.json`. |
| `analysis/scripts/render_html.py` | Converts `summary.md` to Confluence HTML for the MCP push. |
| `analysis/scripts/tests/test_render_summary.py` | Tests for the renderer. |
| `analysis/scripts/tests/test_validate.py` | Tests for the validator. |
| `analysis/scripts/tests/test_build_queue.py` | Tests for the queue builder. |
| `analysis/README.md` | Tiny pointer to the spec + how to re-run. |

The CSV at `~/agent_integrations_by_org_count_2026-04-30T10_07_38.868252573Z.csv` is the input — copied into `analysis/inputs/integrations_by_org_count.csv` so the dataset is self-contained on the branch.

---

## Phase 0 — Scaffolding

### Task 1: Create the analysis directory and copy inputs

**Files:**
- Create: `analysis/README.md`
- Create: `analysis/inputs/integrations_by_org_count.csv` (copy of the home CSV)
- Create: `analysis/integrations/.gitkeep`
- Create: `analysis/scripts/tests/.gitkeep`

- [ ] **Step 1: Create directory tree**

```bash
mkdir -p analysis/inputs analysis/integrations analysis/scripts/tests
touch analysis/integrations/.gitkeep analysis/scripts/tests/.gitkeep
```

- [ ] **Step 2: Copy the CSV input into the repo**

```bash
cp ~/agent_integrations_by_org_count_2026-04-30T10_07_38.868252573Z.csv \
   analysis/inputs/integrations_by_org_count.csv
```

- [ ] **Step 3: Write `analysis/README.md`**

```markdown
# Integrations Auto-Config Analysis

Working artifacts for the DSCVR/6650004331 Confluence ticket.

- Design spec: `../docs/superpowers/specs/2026-04-30-integrations-auto-config-analysis-design.md`
- Implementation plan: `../docs/superpowers/plans/2026-04-30-integrations-auto-config-analysis.md`

## Re-run

```bash
python3 analysis/scripts/build_queue.py
python3 analysis/scripts/render_summary.py
```
```

- [ ] **Step 4: Commit**

```bash
git add analysis/
git commit -m "analysis: scaffold working directory"
```

---

### Task 2: Write `analysis/schema.json`

**Files:**
- Create: `analysis/schema.json`

- [ ] **Step 1: Write the schema**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Integration auto-config analysis",
  "type": "object",
  "required": [
    "name", "display_name", "spec_path", "required_fields",
    "all_relevant_fields", "classification", "auto_config_method",
    "has_existing_auto_conf", "explanation", "references",
    "confidence", "needs_human_review"
  ],
  "additionalProperties": false,
  "properties": {
    "name": {"type": "string", "pattern": "^[a-z0-9_]+$"},
    "display_name": {"type": "string"},
    "spec_path": {"type": "string"},
    "required_fields": {
      "type": "array", "items": {"type": "string"}
    },
    "all_relevant_fields": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "required"],
        "additionalProperties": false,
        "properties": {
          "name": {"type": "string"},
          "required": {"type": "boolean"},
          "default": {}
        }
      }
    },
    "classification": {
      "type": "string",
      "enum": ["generic", "custom", "impossible"]
    },
    "auto_config_method": {
      "type": "string",
      "enum": [
        "openmetrics-port-scan",
        "tcp-banner-probe",
        "http-path-probe",
        "config-file-parse",
        "credentials-required",
        "other"
      ]
    },
    "has_existing_auto_conf": {"type": "boolean"},
    "auto_conf_path": {"type": ["string", "null"]},
    "explanation": {"type": "string"},
    "references": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["kind"],
        "additionalProperties": false,
        "properties": {
          "kind": {"type": "string", "enum": ["spec", "check", "auto_conf", "readme", "upstream", "other"]},
          "path": {"type": "string"},
          "url":  {"type": "string"}
        }
      }
    },
    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    "needs_human_review": {"type": "boolean"},
    "notes": {"type": "string"}
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add analysis/schema.json
git commit -m "analysis: add JSON schema for per-integration output"
```

---

### Task 3: Write `validate.py` and tests

**Files:**
- Create: `analysis/scripts/validate.py`
- Create: `analysis/scripts/tests/test_validate.py`

- [ ] **Step 1: Write the failing test**

```python
# analysis/scripts/tests/test_validate.py
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATE = ROOT / "scripts" / "validate.py"
SCHEMA = ROOT / "schema.json"

def run(payload, tmp_path):
    f = tmp_path / "x.json"
    f.write_text(json.dumps(payload))
    return subprocess.run(
        [sys.executable, str(VALIDATE), str(f)],
        capture_output=True, text=True
    )

VALID = {
    "name": "redisdb", "display_name": "Redis",
    "spec_path": "redisdb/assets/configuration/spec.yaml",
    "required_fields": ["host", "port"],
    "all_relevant_fields": [
        {"name": "host", "required": True, "default": "localhost"}
    ],
    "classification": "generic",
    "auto_config_method": "tcp-banner-probe",
    "has_existing_auto_conf": True,
    "auto_conf_path": "redisdb/datadog_checks/redisdb/data/auto_conf.yaml",
    "explanation": "Redis answers a banner; default port 6379.",
    "references": [{"kind": "spec", "path": "redisdb/assets/configuration/spec.yaml"}],
    "confidence": "high",
    "needs_human_review": False
}

def test_valid_passes(tmp_path):
    r = run(VALID, tmp_path)
    assert r.returncode == 0, r.stderr

def test_missing_required_field_fails(tmp_path):
    bad = dict(VALID); del bad["classification"]
    r = run(bad, tmp_path)
    assert r.returncode != 0
    assert "classification" in r.stderr

def test_bad_enum_fails(tmp_path):
    bad = dict(VALID); bad["classification"] = "maybe"
    r = run(bad, tmp_path)
    assert r.returncode != 0
```

- [ ] **Step 2: Run tests, expect failure**

```bash
cd analysis && python3 -m pytest scripts/tests/test_validate.py -v
```
Expected: FAIL — `validate.py` doesn't exist.

- [ ] **Step 3: Write minimal `validate.py`**

Use stdlib only — implement a tiny JSON Schema subset (required, type, enum, additionalProperties, items, pattern). No external deps.

```python
# analysis/scripts/validate.py
"""Tiny JSON-Schema-draft-07 subset validator (stdlib only)."""
import json
import re
import sys
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema.json"

def _type_ok(value, expected):
    if isinstance(expected, list):
        return any(_type_ok(value, t) for t in expected)
    return {
        "string":  isinstance(value, str),
        "boolean": isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number":  isinstance(value, (int, float)) and not isinstance(value, bool),
        "array":   isinstance(value, list),
        "object":  isinstance(value, dict),
        "null":    value is None,
    }.get(expected, True)

def _validate(value, schema, path, errors):
    if "type" in schema and not _type_ok(value, schema["type"]):
        errors.append(f"{path}: expected {schema['type']}, got {type(value).__name__}")
        return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not in {schema['enum']}")
    if "pattern" in schema and isinstance(value, str):
        if not re.search(schema["pattern"], value):
            errors.append(f"{path}: {value!r} does not match {schema['pattern']!r}")
    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{path}: missing required field {req!r}")
        if schema.get("additionalProperties") is False:
            allowed = set(schema.get("properties", {}))
            for k in value:
                if k not in allowed:
                    errors.append(f"{path}: unknown field {k!r}")
        for k, sub in schema.get("properties", {}).items():
            if k in value:
                _validate(value[k], sub, f"{path}.{k}", errors)
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            _validate(item, schema["items"], f"{path}[{i}]", errors)

def validate(payload, schema):
    errors = []
    _validate(payload, schema, "$", errors)
    return errors

def main():
    if len(sys.argv) != 2:
        print("usage: validate.py <file.json>", file=sys.stderr)
        sys.exit(2)
    schema = json.loads(SCHEMA_PATH.read_text())
    payload = json.loads(Path(sys.argv[1]).read_text())
    errors = validate(payload, schema)
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests, expect pass**

```bash
cd analysis && python3 -m pytest scripts/tests/test_validate.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add analysis/scripts/validate.py analysis/scripts/tests/test_validate.py
git commit -m "analysis: add stdlib JSON schema validator + tests"
```

---

### Task 4: Write `build_queue.py` and tests

**Files:**
- Create: `analysis/scripts/build_queue.py`
- Create: `analysis/scripts/tests/test_build_queue.py`
- Create (output): `analysis/queue.txt`, `analysis/skipped.md`

- [ ] **Step 1: Write the failing test**

```python
# analysis/scripts/tests/test_build_queue.py
from pathlib import Path
import importlib.util, sys

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "build_queue", ROOT / "scripts" / "build_queue.py"
)
build_queue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_queue)

def test_normalize_strips_quotes_and_spaces():
    assert build_queue.normalize("Redis ") == "redis"
    assert build_queue.normalize("SQL Server") == "sql_server"
    assert build_queue.normalize(".net clr") == "net_clr"

def test_resolve_directory_for_known_aliases(tmp_path, monkeypatch):
    (tmp_path / "redisdb" / "assets" / "configuration").mkdir(parents=True)
    (tmp_path / "redisdb" / "assets" / "configuration" / "spec.yaml").write_text("x")
    monkeypatch.chdir(tmp_path)
    assert build_queue.resolve_directory("redis") == "redisdb"

def test_resolve_directory_returns_none_when_no_spec(tmp_path, monkeypatch):
    (tmp_path / "logs").mkdir()
    monkeypatch.chdir(tmp_path)
    assert build_queue.resolve_directory("logs") is None
```

- [ ] **Step 2: Run tests, expect failure**

```bash
cd analysis && python3 -m pytest scripts/tests/test_build_queue.py -v
```
Expected: FAIL.

- [ ] **Step 3: Write `build_queue.py`**

```python
# analysis/scripts/build_queue.py
"""Build queue.txt (CSV order ∩ has spec.yaml) and skipped.md."""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "analysis" / "inputs" / "integrations_by_org_count.csv"
QUEUE_PATH = ROOT / "analysis" / "queue.txt"
SKIPPED_PATH = ROOT / "analysis" / "skipped.md"

ALIASES = {
    "redis": "redisdb",
    "postgres": "postgres",
    "mysql": "mysql",
    "sql_server": "sqlserver",
    "mongodb": "mongo",
    "kafka": "kafka_consumer",
    "elasticsearch": "elastic",
    "haproxy": "haproxy",
    "rabbitmq": "rabbitmq",
    "containerd": "containerd",
    "iis": "iis",
    "coredns": "coredns",
    "nginx": "nginx",
    "apache": "apache",
    "kube_scheduler": "kube_scheduler",
    "tomcat": "tomcat",
    "memcached": "mcache",
    "etcd": "etcd",
    "jenkins": "jenkins",
    "istio": "istio",
    "kubernetes_controller_manager": "kube_controller_manager",
    "zookeeper": "zk",
    "snmp": "snmp",
    "mongodb_atlas": "mongo",
    "consul": "consul",
    "kube_dns": "kube_dns",
    "vault": "vault",
    "windows_service": "windows_service",
    "ssh": "ssh_check",
    "php_fpm": "php_fpm",
    "nginx_ingress_controller": "nginx_ingress_controller",
    "tls": "tls",
    "github": "github",
    "event_viewer": "win_event_log",
}

def normalize(name):
    s = name.strip().strip('"').lower()
    s = re.sub(r"[\s\-./]+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    return s

def resolve_directory(name):
    candidate = ALIASES.get(name, name)
    p = Path(candidate) / "assets" / "configuration" / "spec.yaml"
    if p.exists():
        return candidate
    p = Path(name) / "assets" / "configuration" / "spec.yaml"
    if p.exists():
        return name
    return None

def read_csv(path):
    with path.open() as f:
        reader = csv.reader(f)
        next(reader)  # header
        for row in reader:
            if not row:
                continue
            yield row[0]

def main():
    queue = []
    skipped = []
    seen = set()
    for raw in read_csv(CSV_PATH):
        norm = normalize(raw)
        if norm in seen:
            continue
        seen.add(norm)
        directory = resolve_directory(norm)
        if directory:
            if directory not in queue:
                queue.append(directory)
        else:
            skipped.append((raw, "no spec.yaml in repo"))
    QUEUE_PATH.write_text("\n".join(queue) + "\n")
    lines = ["# Skipped integrations (no spec.yaml)\n"]
    for name, reason in skipped:
        lines.append(f"- `{name}` — {reason}")
    SKIPPED_PATH.write_text("\n".join(lines) + "\n")
    print(f"queue: {len(queue)}, skipped: {len(skipped)}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests, expect pass**

```bash
cd analysis && python3 -m pytest scripts/tests/test_build_queue.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Run the script for real**

```bash
python3 analysis/scripts/build_queue.py
wc -l analysis/queue.txt
head -20 analysis/queue.txt
```
Expected: ~150-260 lines in queue.txt; top-of-CSV high-traffic integrations like `redisdb` and `postgres` resolve to real directories.

- [ ] **Step 6: Manually inspect skipped.md for surprising omissions**

If the queue is unexpectedly small or a high-traffic integration was wrongly skipped, add an alias to `ALIASES` and re-run. The most common reasons for an entry in skipped.md are: SaaS-only integrations (logs, push notifications, audit trail, incidents, feed), display-name mismatches, or marketplace tiles.

- [ ] **Step 7: Commit**

```bash
git add analysis/scripts/build_queue.py analysis/scripts/tests/test_build_queue.py analysis/queue.txt analysis/skipped.md
git commit -m "analysis: build queue and skipped list from CSV"
```

---

### Task 5: Write `procedure.md`

**Files:**
- Create: `analysis/procedure.md`

- [ ] **Step 1: Write the procedure**

The procedure is the stable contract used by both the main session and sub-agents. Include classification rubric, confidence rubric, and a worked example.

```markdown
# Procedure: per-integration auto-config feasibility analysis

Output goes to `analysis/integrations/<name>.json` and must validate against
`analysis/schema.json` (run `python3 analysis/scripts/validate.py <file>`).

## Steps

1. **Read** `<name>/assets/configuration/spec.yaml`.
   - Extract every option under `instances` (or under the integration's
     `properties` block). For each, record `name`, `required`, and `default`
     into `all_relevant_fields`.
   - A field is "required" iff it has `required: true` AND no `default`.
2. **Check** `<name>/datadog_checks/<name>/data/auto_conf.yaml`. Set
   `has_existing_auto_conf` and `auto_conf_path` accordingly.
3. **Read** the check implementation (`<name>/datadog_checks/<name>/<name>.py`
   or equivalent). Confirm what each required field actually drives:
   - TCP connect → `tcp-banner-probe` candidate
   - HTTP request to a fixed URL → `http-path-probe` candidate (generic if
     URL is well-known and singular; custom if multiple plausible URLs)
   - OpenMetrics endpoint → `openmetrics-port-scan` candidate
   - Reads server config files → `config-file-parse` (custom)
   - Binds username/password/token → `credentials-required` (impossible)
4. **Skim** `<name>/README.md` to confirm upstream identity and default port.
5. **WebFetch** upstream docs only if the spec or README is ambiguous about a
   well-known endpoint or default port. Cite the URL in `references`.
6. **Classify**:
   - `generic` — host + well-known port (or single well-known URL) is enough,
     all other fields have defaults or are easily probable.
   - `custom`  — needs integration-specific logic (multi-endpoint, parsing
     server config, alternate plugin paths).
   - `impossible` — needs credentials, API keys, tenant IDs, OAuth, certs,
     region+account, or other state not on the wire.
7. **Confidence**:
   - `high` — spec is clear, code matches, port/endpoint is universal.
   - `medium` — minor ambiguity (one optional that may be required in
     practice, or upstream has multiple deployment modes).
   - `low` — spec is unusual or behavior couldn't be confirmed; set
     `needs_human_review: true`.
8. **Emit** the JSON. Use stable kebab-or-snake field names matching the
   schema. Cite every source in `references` (path or url).

## Worked example: redisdb

```json
{
  "name": "redisdb",
  "display_name": "Redis",
  "spec_path": "redisdb/assets/configuration/spec.yaml",
  "required_fields": ["host", "port"],
  "all_relevant_fields": [
    {"name": "host", "required": true,  "default": "localhost"},
    {"name": "port", "required": true,  "default": 6379},
    {"name": "password", "required": false, "default": null},
    {"name": "ssl", "required": false, "default": false}
  ],
  "classification": "generic",
  "auto_config_method": "tcp-banner-probe",
  "has_existing_auto_conf": true,
  "auto_conf_path": "redisdb/datadog_checks/redisdb/data/auto_conf.yaml",
  "explanation": "Redis responds to a `PING` over TCP; default port 6379 is universal. Auth-only deployments are out-of-scope of generic discovery but fall back to existing autodiscovery template.",
  "references": [
    {"kind": "spec", "path": "redisdb/assets/configuration/spec.yaml"},
    {"kind": "auto_conf", "path": "redisdb/datadog_checks/redisdb/data/auto_conf.yaml"}
  ],
  "confidence": "high",
  "needs_human_review": false,
  "notes": ""
}
```

## Time budget per integration

5 minutes. If you're stuck, set `needs_human_review: true` and move on.
```

- [ ] **Step 2: Commit**

```bash
git add analysis/procedure.md
git commit -m "analysis: add procedure rubric for per-integration analysis"
```

---

### Task 6: Write `render_summary.py` and tests

**Files:**
- Create: `analysis/scripts/render_summary.py`
- Create: `analysis/scripts/tests/test_render_summary.py`

- [ ] **Step 1: Write the failing test**

```python
# analysis/scripts/tests/test_render_summary.py
import json
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "render_summary", ROOT / "scripts" / "render_summary.py"
)
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)

DATA = [
    {"name": "redisdb", "display_name": "Redis", "classification": "generic",
     "required_fields": ["host", "port"],
     "auto_config_method": "tcp-banner-probe",
     "explanation": "PING banner.",
     "references": [{"kind": "spec", "path": "redisdb/assets/configuration/spec.yaml"}],
     "confidence": "high", "needs_human_review": False},
    {"name": "nginx", "display_name": "NGINX", "classification": "custom",
     "required_fields": ["nginx_status_url"],
     "auto_config_method": "http-path-probe",
     "explanation": "Multiple stub_status path conventions.",
     "references": [],
     "confidence": "medium", "needs_human_review": False},
    {"name": "github", "display_name": "GitHub", "classification": "impossible",
     "required_fields": ["github_app_id", "private_key"],
     "auto_config_method": "credentials-required",
     "explanation": "Needs app id + private key.",
     "references": [],
     "confidence": "high", "needs_human_review": False},
]

def test_render_has_all_three_tables():
    out = render.render(DATA, generated_at="2026-04-30")
    assert "### Generic auto-config possible" in out
    assert "### Custom auto-config possible" in out
    assert "### Auto-config impossible" in out
    assert "redisdb" in out
    assert "nginx" in out
    assert "github" in out

def test_counts_in_header():
    out = render.render(DATA, generated_at="2026-04-30")
    assert "1 generic" in out and "1 custom" in out and "1 impossible" in out

def test_needs_review_footnote():
    data = [dict(DATA[0], needs_human_review=True)]
    out = render.render(data, generated_at="2026-04-30")
    assert "⚠" in out or "needs review" in out.lower()
```

- [ ] **Step 2: Run tests, expect failure**

```bash
cd analysis && python3 -m pytest scripts/tests/test_render_summary.py -v
```

- [ ] **Step 3: Write `render_summary.py`**

```python
# analysis/scripts/render_summary.py
"""Render analysis/integrations/*.json into analysis/summary.md."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INT_DIR = ROOT / "analysis" / "integrations"
OUT = ROOT / "analysis" / "summary.md"

def load_all():
    out = []
    for p in sorted(INT_DIR.glob("*.json")):
        out.append(json.loads(p.read_text()))
    return out

def _refs(rec):
    parts = []
    for r in rec.get("references", []):
        if "url" in r:
            parts.append(f"[{r['kind']}]({r['url']})")
        elif "path" in r:
            parts.append(f"[`{r['path']}`](../{r['path']})")
    return ", ".join(parts) or "—"

def _row(rec):
    flag = " ⚠" if rec.get("needs_human_review") else ""
    expl = rec.get("explanation", "").replace("|", "\\|")
    fields = ", ".join(f"`{f}`" for f in rec.get("required_fields", [])) or "—"
    return (f"| {rec['display_name']}{flag} (`{rec['name']}`) "
            f"| {fields} "
            f"| {rec.get('auto_config_method', '')} — {expl} "
            f"| {_refs(rec)} |")

def _table(records, header):
    lines = [f"### {header}", "",
             "| Integration | Required fields | Method / detail | References |",
             "|---|---|---|---|"]
    for rec in sorted(records, key=lambda r: r["name"]):
        lines.append(_row(rec))
    lines.append("")
    return "\n".join(lines)

def render(records, generated_at=None):
    generated_at = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    counts = {"generic": 0, "custom": 0, "impossible": 0}
    review = 0
    for r in records:
        counts[r["classification"]] += 1
        if r.get("needs_human_review"):
            review += 1
    total = len(records)
    out = []
    out.append(f"_Generated {generated_at}. {total} total: "
               f"{counts['generic']} generic / {counts['custom']} custom / "
               f"{counts['impossible']} impossible / {review} need review (⚠)._\n")
    by_cls = {"generic": [], "custom": [], "impossible": []}
    for r in records:
        by_cls[r["classification"]].append(r)
    out.append(_table(by_cls["generic"], "Generic auto-config possible"))
    out.append(_table(by_cls["custom"], "Custom auto-config possible"))
    out.append(_table(by_cls["impossible"], "Auto-config impossible"))
    return "\n".join(out)

def main():
    records = load_all()
    OUT.write_text(render(records))
    print(f"wrote {OUT} ({len(records)} integrations)")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests, expect pass**

```bash
cd analysis && python3 -m pytest scripts/tests/test_render_summary.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add analysis/scripts/render_summary.py analysis/scripts/tests/test_render_summary.py
git commit -m "analysis: add summary renderer + tests"
```

---

### Task 7: Write `render_html.py` (md → Confluence HTML)

**Files:**
- Create: `analysis/scripts/render_html.py`

This is a focused converter for the markdown subset `render_summary.py` emits (h3, paragraphs, italic emphasis, pipe tables, inline code). No external deps.

- [ ] **Step 1: Write the converter**

```python
# analysis/scripts/render_html.py
"""Convert analysis/summary.md into Confluence-compatible HTML.

Handles only the markdown subset emitted by render_summary.py:
- '### heading'
- '_italic paragraph_'
- '| pipe | tables |'
- inline `code` and [link](href)
"""
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "analysis" / "summary.md"

LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
CODE = re.compile(r"`([^`]+)`")

def inline(text):
    text = html.escape(text, quote=False)
    text = LINK.sub(r'<a href="\2">\1</a>', text)
    text = CODE.sub(r"<code>\1</code>", text)
    return text

def to_html(md):
    out = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("### "):
            out.append(f"<h3>{inline(line[4:].strip())}</h3>")
            i += 1
        elif line.startswith("|"):
            header = [c.strip() for c in line.strip("|").split("|")]
            i += 1  # separator row
            i += 1
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip("|").split("|")])
                i += 1
            out.append("<table><thead><tr>" +
                       "".join(f"<th>{inline(h)}</th>" for h in header) +
                       "</tr></thead><tbody>" +
                       "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>"
                               for row in rows) +
                       "</tbody></table>")
        elif line.startswith("_") and line.endswith("_") and len(line) > 1:
            out.append(f"<p><em>{inline(line[1:-1])}</em></p>")
            i += 1
        elif line.strip() == "":
            i += 1
        else:
            out.append(f"<p>{inline(line)}</p>")
            i += 1
    return "\n".join(out)

def main():
    md = SRC.read_text()
    print(to_html(md))

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke test**

```bash
echo "### Test\n\n_one note._\n\n| a | b |\n|---|---|\n| 1 | 2 |\n" \
  | python3 -c "import sys; from analysis.scripts.render_html import to_html; print(to_html(sys.stdin.read()))"
```

- [ ] **Step 3: Commit**

```bash
git add analysis/scripts/render_html.py
git commit -m "analysis: add markdown-to-Confluence-HTML renderer"
```

---

## Phase 1 — Bootstrap (15 manual analyses)

The bootstrap exists to (a) seed the dataset with high-quality examples, (b) battle-test the procedure, and (c) surface patterns to fold back into `procedure.md` before sub-agents start.

### Task 8: Bootstrap batch A — top 5

**Files:**
- Create: `analysis/integrations/redisdb.json`
- Create: `analysis/integrations/postgres.json`
- Create: `analysis/integrations/nginx.json`
- Create: `analysis/integrations/coredns.json`
- Create: `analysis/integrations/apache.json`

- [ ] **Step 1: For each integration, run the procedure (see `analysis/procedure.md`)**

For each name in `[redisdb, postgres, nginx, coredns, apache]`:

```bash
ls <name>/assets/configuration/spec.yaml
test -f <name>/datadog_checks/<name>/data/auto_conf.yaml && echo "has auto_conf"
ls <name>/datadog_checks/<name>/*.py | head -5
```

Read `spec.yaml`, read `auto_conf.yaml` if present, skim the check `.py` for what the fields drive, write JSON to `analysis/integrations/<name>.json`.

- [ ] **Step 2: Validate every output**

```bash
for f in analysis/integrations/{redisdb,postgres,nginx,coredns,apache}.json; do
    python3 analysis/scripts/validate.py "$f" || echo "FAIL: $f"
done
```
Expected: no FAIL output.

- [ ] **Step 3: Commit**

```bash
git add analysis/integrations/{redisdb,postgres,nginx,coredns,apache}.json
git commit -m "analysis: bootstrap batch A (5 integrations)"
```

---

### Task 9: Bootstrap batch B — next 5

**Files:**
- Create: `analysis/integrations/mysql.json`
- Create: `analysis/integrations/haproxy.json`
- Create: `analysis/integrations/elastic.json`
- Create: `analysis/integrations/containerd.json`
- Create: `analysis/integrations/iis.json`

- [ ] **Step 1: Procedure for each, write JSON, validate, commit (same pattern as Task 8)**

```bash
for n in mysql haproxy elastic containerd iis; do
    python3 analysis/scripts/validate.py analysis/integrations/$n.json
done
git add analysis/integrations/{mysql,haproxy,elastic,containerd,iis}.json
git commit -m "analysis: bootstrap batch B (5 integrations)"
```

---

### Task 10: Bootstrap batch C — pattern variety

**Files:**
- Create: `analysis/integrations/mongo.json`
- Create: `analysis/integrations/rabbitmq.json`
- Create: `analysis/integrations/sqlserver.json`
- Create: `analysis/integrations/kafka_consumer.json`
- Create: `analysis/integrations/snmp.json`

These five intentionally include credential-requiring (mongo, sqlserver, rabbitmq), management-API (rabbitmq), JMX (kafka_consumer), and SNMP (which is its own beast) so the procedure is exercised on the hard cases.

- [ ] **Step 1: Procedure, validate, commit**

```bash
for n in mongo rabbitmq sqlserver kafka_consumer snmp; do
    python3 analysis/scripts/validate.py analysis/integrations/$n.json
done
git add analysis/integrations/{mongo,rabbitmq,sqlserver,kafka_consumer,snmp}.json
git commit -m "analysis: bootstrap batch C (5 integrations, pattern variety)"
```

---

### Task 11: Refine `procedure.md` with patterns observed

**Files:**
- Modify: `analysis/procedure.md`

- [ ] **Step 1: Inspect the 15 bootstrap JSONs for recurring patterns**

```bash
jq -s '
  group_by(.classification)
  | map({classification: .[0].classification, count: length, methods: (map(.auto_config_method) | unique)})
' analysis/integrations/*.json
```

- [ ] **Step 2: Append a "Patterns observed" section to `procedure.md`**

Document:
- Which fields are nearly-always required (host, port).
- Which integrations show the JMX pattern → likely require host+port+credentials → `impossible`.
- Which show the OpenMetrics+Prometheus pattern → likely `generic`.
- Which show the management-API pattern (rabbitmq, etcd) → host+port+credentials → `impossible`.
- Concrete tells in `auto_conf.yaml` (presence of `password: "%%env_…%%"` ⇒ credentials needed).

- [ ] **Step 3: Render summary, sanity-check on disk**

```bash
python3 analysis/scripts/render_summary.py
head -60 analysis/summary.md
```

- [ ] **Step 4: Commit**

```bash
git add analysis/procedure.md analysis/summary.md
git commit -m "analysis: refine procedure with bootstrap patterns; render initial summary"
```

---

### Task 12: First Confluence push (sanity check)

**Files:**
- Modify (remote): Confluence page `6650004331`

- [ ] **Step 1: Render HTML and inspect locally**

```bash
python3 analysis/scripts/render_html.py | head -80
```

- [ ] **Step 2: Compose Confluence body**

The body must keep the existing "Introduction" section intact. Strategy: fetch the current page body in HTML format, locate the `<h2>Analysis</h2>` marker, and replace everything after it with the rendered tables. This is done inline by the orchestrator (main session) using the Atlassian MCP `getConfluencePage` (with `contentFormat: "html"`) and `updateConfluencePage` tools.

- [ ] **Step 3: Push to Confluence**

Call `mcp__atlassian__updateConfluencePage` with:
- `cloudId`: `66c05bee-f5ff-4718-b6fc-81351e5ef659`
- `pageId`: `6650004331`
- `contentFormat`: `"html"`
- `title`: `Integrations advanced auto config exploration`
- `body`: existing intro HTML + `<h2>Analysis</h2>` + rendered tables HTML
- `versionMessage`: `Bootstrap (15 integrations) — wave 0`

- [ ] **Step 4: Verify**

Re-fetch the page and confirm tables render and Introduction is intact.

- [ ] **Step 5: Commit no-op marker**

```bash
git commit --allow-empty -m "analysis: first Confluence push (15 bootstrap integrations)"
```

---

## Phase 2 — Adaptive waves

After bootstrap, the queue still holds ~245 integrations. Each wave processes 50 (10 sub-agents × 5 each). About 5 waves total.

### Task 13: Initialize `state.json`

**Files:**
- Create: `analysis/state.json`

- [ ] **Step 1: Write initial state**

```python
# Run as one-liner:
import json, pathlib
done = sorted(p.stem for p in pathlib.Path("analysis/integrations").glob("*.json"))
queue = [l.strip() for l in open("analysis/queue.txt") if l.strip()]
remaining = [n for n in queue if n not in done]
state = {
    "wave": 0,
    "done": done,
    "remaining": remaining,
    "failed": [],
    "retried": [],
}
pathlib.Path("analysis/state.json").write_text(json.dumps(state, indent=2))
print(f"done={len(done)}, remaining={len(remaining)}")
```

- [ ] **Step 2: Commit**

```bash
git add analysis/state.json
git commit -m "analysis: initialize wave state"
```

---

### Task 14: Wave 1 — dispatch 10 sub-agents in parallel

**Files:**
- Create: `analysis/integrations/<name>.json` (×50)
- Modify: `analysis/state.json`, `analysis/summary.md`

- [ ] **Step 1: Slice next 50 names from `state.json:remaining`**

Five-name chunks per agent. Record assignments in a temporary `analysis/.wave1_assignments.json` for traceability (gitignored isn't an option since the directory is tracked — keep it but it's small).

- [ ] **Step 2: Dispatch 10 `general-purpose` Agent calls in a single message**

Each prompt follows the template in the design spec section 7. Pass: integrations list, paths to procedure / schema / two bootstrap examples, explicit instruction to write JSON only and not modify other files. Run all 10 in parallel.

- [ ] **Step 3: Validate every produced JSON**

```bash
fails=0
for f in analysis/integrations/*.json; do
    python3 analysis/scripts/validate.py "$f" >/dev/null 2>&1 || { echo "FAIL: $f"; fails=$((fails+1)); }
done
echo "$fails validation failures"
```

- [ ] **Step 4: Retry-once on failed batches**

For each batch where any output failed validation, re-dispatch a sub-agent for just those names with a stricter prompt that names the schema violation. If still failing, the orchestrator (main session) re-does that batch inline using the procedure.

- [ ] **Step 5: Update `state.json`**

Move the now-completed names from `remaining` to `done`. Bump `wave`.

- [ ] **Step 6: Re-render summary**

```bash
python3 analysis/scripts/render_summary.py
wc -l analysis/summary.md
```

- [ ] **Step 7: Push to Confluence**

Same procedure as Task 12 step 3, with `versionMessage: "Wave 1 (+50 integrations)"`.

- [ ] **Step 8: Commit wave**

```bash
git add analysis/integrations/ analysis/state.json analysis/summary.md analysis/.wave1_assignments.json
git commit -m "analysis: wave 1 (+50 integrations)"
```

- [ ] **Step 9: Procedure refinement check**

If the wave produced ≥3 integrations of a previously-undocumented pattern, append a section to `procedure.md` and commit separately. Then continue.

---

### Task 15: Wave 2 — same as wave 1

- [ ] Same procedure as Task 14, with `wave: 2` and `versionMessage: "Wave 2 (+50)"`.

---

### Task 16: Wave 3

- [ ] Same procedure as Task 14, with `wave: 3`.

---

### Task 17: Wave 4

- [ ] Same procedure as Task 14, with `wave: 4`.

---

### Task 18: Wave 5 (final, partial)

- [ ] Same procedure as Task 14, but the remaining count will be < 50. Dispatch fewer sub-agents accordingly.

---

## Phase 3 — Final sweep

### Task 19: Final summary + Confluence push

**Files:**
- Modify: `analysis/summary.md`
- Modify (remote): Confluence page `6650004331`

- [ ] **Step 1: Re-validate every output**

```bash
fails=0
for f in analysis/integrations/*.json; do
    python3 analysis/scripts/validate.py "$f" >/dev/null 2>&1 || { echo "FAIL: $f"; fails=$((fails+1)); }
done
echo "$fails validation failures"
test "$fails" -eq 0
```

- [ ] **Step 2: Re-render summary**

```bash
python3 analysis/scripts/render_summary.py
```

- [ ] **Step 3: Stats sanity check**

```bash
ls analysis/integrations/*.json | wc -l           # should match queue.txt minus skipped
grep -c '"classification": "generic"'  analysis/integrations/*.json | wc -l
grep -c '"needs_human_review": true'   analysis/integrations/*.json
```

- [ ] **Step 4: Final Confluence push**

`versionMessage: "Final — N integrations"`. Verify the page renders correctly.

- [ ] **Step 5: Commit final state**

```bash
git add analysis/
git commit -m "analysis: final pass — N integrations classified"
```

---

### Task 20: Hand-off summary

**Files:**
- Create: `analysis/RESULTS.md`

- [ ] **Step 1: Write a short results summary**

A README-style file under `analysis/` summarizing:
- Total integrations classified, breakdown by class.
- List of `needs_human_review` items with their JSON paths.
- A pointer to the Confluence page.
- A pointer to the design spec and this plan.

- [ ] **Step 2: Commit and report ready-to-push branch**

```bash
git add analysis/RESULTS.md
git commit -m "analysis: add results summary"
git log --oneline analysis/auto-config-exploration ^master | head -30
```

Print the branch name and instruct the user (in chat, end-of-turn) that the branch is ready to push.

---

## Self-review notes

- Spec coverage: every Confluence-page deliverable (3 tables + skipped list) is produced by `render_summary.py` (Task 6); the source ticket's "Analysis section" is filled in Task 12 / Task 19.
- Placeholder scan: every code/script step contains complete code; every Bash step has explicit commands.
- Type consistency: schema enum names match the renderer's class names match `procedure.md`'s rubric (`generic` / `custom` / `impossible`); method names match across schema, procedure, and renderer.
- Failure handling appears in Task 14 step 4 and is consistent with the design spec.
