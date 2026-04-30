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

## Patterns observed

(Section appended after Phase 1 bootstrap — see Task 11 of the plan.)
