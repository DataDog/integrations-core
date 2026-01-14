# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Prompt templates for DynamicD LLM interactions."""

from __future__ import annotations

from ddev.cli.meta.scripts.dynamicd.constants import SCENARIOS

# =============================================================================
# STAGE 1: Context Analysis Prompt
# =============================================================================
# This prompt analyzes the integration and produces an enhanced understanding
# that will be used to guide the script generation.

STAGE1_SYSTEM_PROMPT = """You are an expert in observability, monitoring systems, and the operational
characteristics of various software services. Your task is to analyze a Datadog integration and
produce a detailed understanding of:

1. What this service/software does
2. What realistic operational patterns look like
3. What entities exist in this service (clusters, nodes, queues, databases, etc.)
4. How metrics relate to each other
5. What typical failure modes and performance issues look like

You will output a structured analysis that will be used to generate realistic fake telemetry data."""

STAGE1_USER_PROMPT_TEMPLATE = """Analyze the following Datadog integration and provide a detailed understanding
that can be used to generate realistic fake telemetry data.

{integration_context}

---

Please provide your analysis in the following JSON format:

```json
{{
    "service_type": "Brief description of what this service is",
    "typical_deployment": "How this is typically deployed (single node, cluster, etc.)",
    "entities": [
        {{
            "name": "entity name (e.g., queue, node, cluster)",
            "typical_count": "typical count range",
            "naming_pattern": "how these are typically named"
        }}
    ],
    "metric_relationships": [
        {{
            "description": "how metrics relate (e.g., queue depth affects latency)",
            "metrics_involved": ["metric1", "metric2"]
        }}
    ],
    "healthy_patterns": {{
        "description": "what healthy operation looks like",
        "metric_behaviors": [
            {{"metric_pattern": "metric name pattern", "typical_range": "value range", "variation": "how it varies"}}
        ]
    }},
    "degraded_patterns": {{
        "description": "what degraded performance looks like",
        "indicators": ["list of warning signs"]
    }},
    "incident_patterns": {{
        "description": "what an incident looks like",
        "indicators": ["list of critical indicators"]
    }},
    "diurnal_patterns": {{
        "has_diurnal": true/false,
        "description": "how load varies over time of day/week"
    }},
    "realistic_tag_values": {{
        "tag_name": ["list", "of", "realistic", "values"]
    }}
}}
```

Be specific to this integration's domain. Use your knowledge of {display_name} and similar services
to provide realistic operational insights."""


# =============================================================================
# STAGE 2: Script Generation Prompt
# =============================================================================
# This prompt uses the Stage 1 analysis to generate the actual simulator script.

STAGE2_SYSTEM_PROMPT = """You are an expert Python developer specializing in observability and monitoring.
Your task is to generate a high-quality, self-contained Python script that simulates realistic
telemetry data for a Datadog integration.

The script must:
1. Be completely self-contained (no external files needed)
2. Use only standard library + requests (for HTTP API calls)
3. Model realistic entities and relationships
4. Support different scenarios (healthy, degraded, incident, etc.)
5. Include realistic variations, patterns, and noise
6. Send BOTH metrics AND logs via Datadog HTTP APIs
7. Run in a continuous loop with configurable duration
8. Have clear, readable code with comments
9. NEVER use emojis anywhere - no emojis in print statements, logs, comments, or strings
10. USE REALISTIC VALUE RANGES - avoid arbitrarily large numbers:
    - Counts/requests: typically 0-100 per batch, not thousands
    - Latencies: milliseconds (10-500ms typical), not seconds unless truly slow
    - Percentages: 0-100
    - Queue depths: 0-50 typical, up to 200 during incidents
    - Token counts: realistic for the service (e.g., 100-2000 per request)
    - Error rates: 0-5% healthy, 5-20% degraded, 20-50% incident
    - Values should look like real production data, not random large numbers

11. SMOOTH TRANSITIONS - values should not jump erratically:
    - Use a base state variable that changes GRADUALLY over time
    - Add small random noise (+-5-10%), not large random jumps
    - For "recovery" scenario: start low, trend upward smoothly
    - For "incident" scenario: start normal, trend downward
    - All entities should follow similar patterns (correlated, not random)
    - Example: base_health = min(1.0, base_health + 0.02) for gradual recovery
    - NEVER generate completely random values each batch - use state that persists

CRITICAL REQUIREMENTS:
1. EVERY BATCH MUST INCLUDE ALL DASHBOARD METRICS (marked as PRIORITY)
   - Do NOT randomly select metrics - generate ALL dashboard metrics every batch
   - The batch should include 1 data point per metric per entity combination

2. METRICS MUST BE MATHEMATICALLY CONSISTENT (Critical!)
   - Related metrics must add up correctly
   - Example: If total_drops=5000, then buffer_drops + threadtable_drops + queue_drops should = 5000
   - Example: If requests_total=1000, then requests_success + requests_failed should = 1000
   - Breakdown metrics should distribute the total, not all be 0
   - Parent/child metrics must have logical relationships

3. MANDATORY TAG - env:dynamicd
   - EVERY metric MUST include the tag "env:dynamicd"
   - This tag allows users to filter out fake/test data in Datadog dashboards
   - Add this tag to EVERY metric's tags list, without exception

4. TAGS ARE MANDATORY (dashboards group by tags - missing tags = "N/A" display):
   - NEVER use empty strings, "N/A", "null", or placeholder values for tags
   - The integration context lists REQUIRED TAGS for each metric - use them ALL
   - Create 2-4 realistic entity instances per tag (e.g., 3 hosts, 2 endpoints)
   - Example tag values:
     - team: "platform-team", "ml-ops", "data-science"
     - api_key_alias: "prod-key-1", "staging-key", "dev-key"
     - model: "gpt-4", "claude-3", "llama-70b"
     - host: "prod-01", "prod-02", "staging-01"
     - worker: "celery-worker-01-5432", "celery-worker-02-8765"
     - endpoint: "/api/v1/chat", "/api/v1/completions", "/health"
     - dir/direction: "inbound", "outbound"
     - api_provider: "openai", "anthropic", "azure"

5. METRIC CORRELATIONS (Very Important):
   - Metrics must tell a COHERENT STORY - related metrics should move together
   - Use shared "state" variables: base_load, error_rate, queue_depth
   - Derive multiple metrics from these shared states
   - Example: if latency increases, throughput should decrease
   - The dashboard should look like a REAL system

6. Use exact metric names from the integration - do not invent new ones
7. Respect metric types (gauge=3, count=1, rate=2)

IMPORTANT - PAYLOAD SIZE LIMITS:
   - Datadog API has payload size limits (~5MB, but aim for <500 metrics per request)
   - If generating many metrics, split into batches of 500 and send multiple requests
   - Keep entity counts reasonable: 2-4 instances per tag type, not dozens
   - Example: 3 hosts x 2 endpoints x 50 metrics = 300 points (good)
   - Avoid: 10 hosts x 10 endpoints x 50 metrics = 5000 points (too many, will fail)

8. LOGS ARE MANDATORY - Generate realistic logs alongside metrics:
   - Send logs via Datadog HTTP Logs API (different endpoint from metrics)
   - Use the integration name as the "source" (e.g., source:celery, source:redis)
   - Include realistic log messages that match the scenario
   - Log levels should correlate with scenario:
     - healthy: mostly INFO, occasional DEBUG
     - degraded: mix of INFO, WARNING, some ERROR
     - incident: many ERROR and CRITICAL logs
     - recovery: WARNING transitioning to INFO
   - Logs must include ddtags with "env:dynamicd" for filtering
   - Include relevant attributes: host, service, worker, task, etc.
   - Generate 5-15 logs per batch depending on scenario severity

9. SERVICE CHECKS (if the integration defines them):
   - Send service checks via Datadog API v1 `/api/v1/check_run`
   - Use exact service check names from the integration context
   - Status values: 0=OK, 1=WARNING, 2=CRITICAL, 3=UNKNOWN
   - Status should correlate with scenario:
     - healthy: status=0 (OK)
     - degraded: status=1 (WARNING)
     - incident: status=2 (CRITICAL)
     - recovery: transition from WARNING to OK
   - Include the "env:dynamicd" tag
   - Send service checks every batch (every 10 seconds)

10. EVENTS (optional, for significant state changes):
    - Send events via Datadog API v1 `/api/v1/events`
    - Only generate events for meaningful state changes, not every batch
    - Event types should match scenario:
      - incident: alert events (alert_type: "error")
      - recovery: recovery events (alert_type: "success")
      - maintenance: info events (alert_type: "info")
    - Include "env:dynamicd" in tags
    - Generate 0-3 events per batch maximum (events are rare)"""

STAGE2_USER_PROMPT_TEMPLATE = """Generate a Python script that simulates realistic telemetry data for the
{display_name} integration.

## Integration Context
{integration_context}

## Service Analysis
Based on analysis, here's what we know about this service:
{stage1_analysis}

## Selected Scenario: {scenario}
{scenario_description}

## Configuration
- Datadog Site: {dd_site}
- Metrics per batch target: {metrics_per_batch} (but include ALL dashboard metrics regardless)
- Batch interval: 10 seconds (send metrics every 10 seconds, not every second)
- Duration: {duration} seconds (0 = run forever)

## CRITICAL: Tags Must Be Populated
The dashboard widgets GROUP BY tags. If tags are missing:
- Widgets show "N/A" instead of data
- Graphs appear empty or broken
- The dashboard looks unprofessional

For each metric, check the REQUIRED TAGS listed in the context and ALWAYS include them
with realistic values. Create 2-3 "entities" per tag type and emit metrics for each.

## CRITICAL: Metrics Must Be Mathematically Consistent
Related metrics must tell a coherent story:
- If there's a "total" metric and breakdown metrics, they MUST add up
- Example: total_drops = buffer_drops + threadtable_drops + scratch_map_drops + queue_drops
- Example: requests = success + failures + timeouts
- Don't generate total=5000 with all breakdowns=0 - distribute the values logically
- Metrics CAN be 0 if it makes sense (e.g., no errors in healthy scenario)
- But if the parent metric has a value, child metrics should account for it

## MANDATORY: env:dynamicd Tag
EVERY metric MUST include the tag "env:dynamicd" to allow filtering fake data.
Add this to every metric's tags list, e.g.: tags=["env:dynamicd", "host:prod-01", ...]

## Requirements

Generate a Python script with the following structure:

```python
#!/usr/bin/env python3
\"\"\"
{display_name} Telemetry Simulator
Generated by DynamicD

Scenario: {scenario}
\"\"\"

import json
import random
import time
import math
from datetime import datetime, timezone
from typing import Any
import requests

# =============================================================================
# CONFIGURATION
# =============================================================================
DATADOG_API_KEY = "YOUR_API_KEY"  # Will be replaced at runtime
DATADOG_SITE = "{dd_site}"
METRICS_ENDPOINT = f"https://api.{{DATADOG_SITE}}/api/v2/series"
LOGS_ENDPOINT = f"https://http-intake.logs.{{DATADOG_SITE}}/api/v2/logs"

SCENARIO = "{scenario}"
DURATION_SECONDS = {duration}  # 0 = run forever
METRICS_PER_BATCH = {metrics_per_batch}
BATCH_INTERVAL_SECONDS = 10.0  # Send every 10 seconds (realistic monitoring interval)

# Log source should match the integration name for proper filtering
LOG_SOURCE = "{integration_name}"  # Used as ddsource in logs

# =============================================================================
# SIMULATED ENVIRONMENT
# =============================================================================
# Define realistic entities based on the service type
# (clusters, nodes, queues, databases, etc.)

# =============================================================================
# METRIC GENERATORS
# =============================================================================
# Functions that generate realistic values for each metric type

# =============================================================================
# SCENARIO MODIFIERS
# =============================================================================
# Adjust metric values based on the selected scenario

# =============================================================================
# MAIN SIMULATION LOOP
# =============================================================================
def generate_metrics() -> list[dict[str, Any]]:
    \"\"\"Generate a batch of metrics.\"\"\"
    pass

def generate_logs() -> list[dict[str, Any]]:
    \"\"\"Generate a batch of logs correlated with metrics/scenario.\"\"\"
    pass

def send_metrics(metrics: list[dict[str, Any]], api_key: str) -> bool:
    \"\"\"Send metrics to Datadog via HTTP API.\"\"\"
    pass

def send_logs(logs: list[dict[str, Any]], api_key: str, site: str, source: str) -> bool:
    \"\"\"Send logs to Datadog via HTTP Logs API.\"\"\"
    pass

def generate_service_checks() -> list[dict[str, Any]]:
    \"\"\"Generate service checks (only if integration defines them).\"\"\"
    pass

def send_service_checks(checks: list[dict[str, Any]], api_key: str, site: str) -> bool:
    \"\"\"Send service checks to Datadog via API v1.\"\"\"
    pass

def generate_events() -> list[dict[str, Any]]:
    \"\"\"Generate events for significant state changes (optional).\"\"\"
    pass

def send_events(events: list[dict[str, Any]], api_key: str, site: str) -> bool:
    \"\"\"Send events to Datadog via API v1.\"\"\"
    pass

def main():
    \"\"\"Main simulation loop - sends metrics, logs, service checks, and events.\"\"\"
    pass

if __name__ == "__main__":
    main()
```

Make the script:
1. Rich with realistic entity modeling (not just random values)
2. Include time-based patterns (if appropriate for this service)
3. MODEL CORRELATIONS BETWEEN METRICS - this is critical:
   - Create shared "state" variables (e.g., system_load, queue_backlog, error_rate)
   - Derive multiple metrics from these shared states
   - When one metric changes, related metrics should change coherently
   - Example: base_load = 0.7 → cpu from base_load, memory from base_load, latency from base_load
4. Support the selected scenario with appropriate metric modifications
5. Print progress information as it runs
6. Handle the API key being passed via environment variable DATADOG_API_KEY
7. ENSURE ALL DASHBOARD METRICS (marked as PRIORITY) are generated in every batch
8. USE THE CORRECT DATADOG API V2 FORMAT for sending metrics:

```python
def send_metrics(metrics: list, api_key: str) -> bool:
    \"\"\"Send metrics to Datadog using the correct V2 API format.\"\"\"
    headers = {{
        "DD-API-KEY": api_key,
        "Content-Type": "application/json",
    }}

    # Batch metrics to avoid 413 Payload Too Large errors
    BATCH_SIZE = 500
    for i in range(0, len(metrics), BATCH_SIZE):
        batch = metrics[i:i + BATCH_SIZE]

        # V2 API format - series is a list of metric objects
        payload = {{
            "series": [
                {{
                    "metric": m["metric"],
                    "type": m.get("type", 0),  # 0=unspecified, 1=count, 2=rate, 3=gauge
                    "points": [
                        {{
                            "timestamp": m["points"][0]["timestamp"],
                            "value": m["points"][0]["value"]
                        }}
                    ],
                    "tags": m.get("tags", ["env:dynamicd"])  # Always include env:dynamicd
                }}
                for m in batch
            ]
        }}

        response = requests.post(
            f"https://api.{{DATADOG_SITE}}/api/v2/series",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
    return True
```

Example of good correlation modeling:
```python
# Shared state that drives multiple metrics
system_load = 0.3 + 0.2 * math.sin(time.time() / 300)  # Varies over time
if SCENARIO == "incident":
    system_load = min(1.0, system_load + 0.5)

# Derived metrics from shared state
cpu_percent = system_load * 80 + random.uniform(-5, 5)
memory_percent = system_load * 70 + random.uniform(-3, 3)
latency_ms = 10 + (system_load * 200) + random.uniform(-10, 10)
error_rate = 0.01 if system_load < 0.8 else (system_load - 0.8) * 0.5
```

9. SEND LOGS using the Datadog HTTP Logs API:

```python
def send_logs(logs: list, api_key: str, site: str, source: str) -> bool:
    \"\"\"Send logs to Datadog using the HTTP Logs API.\"\"\"
    # Logs intake uses a different endpoint than metrics
    logs_endpoint = f"https://http-intake.logs.{{site}}/api/v2/logs"

    headers = {{
        "DD-API-KEY": api_key,
        "Content-Type": "application/json",
    }}

    # Format logs for the API
    formatted_logs = [
        {{
            "message": log["message"],
            "ddsource": source,  # e.g., "celery", "redis", "postgres"
            "ddtags": f"env:dynamicd,{{log.get('tags', '')}}",
            "hostname": log.get("hostname", "dynamicd-simulator"),
            "service": log.get("service", source),
            "status": log.get("level", "info"),  # debug, info, warning, error, critical
        }}
        for log in logs
    ]

    response = requests.post(logs_endpoint, headers=headers, json=formatted_logs)
    response.raise_for_status()
    return True
```

Example log generation that correlates with scenario:
```python
def generate_logs(scenario: str, source: str) -> list:
    \"\"\"Generate realistic logs based on scenario.\"\"\"
    logs = []
    timestamp = datetime.now(timezone.utc).isoformat()

    if scenario == "healthy":
        logs.append({{"message": f"[{{timestamp}}] Task completed successfully", "level": "info"}})
    elif scenario == "incident":
        logs.append({{"message": f"[{{timestamp}}] ERROR: Connection timeout after 30s", "level": "error"}})
        logs.append({{"message": f"[{{timestamp}}] CRITICAL: Queue backlog exceeded threshold", "level": "critical"}})
    elif scenario == "degraded":
        logs.append({{"message": f"[{{timestamp}}] WARNING: High latency detected (2.5s)", "level": "warning"}})

    return logs
```

10. SEND SERVICE CHECKS using Datadog API v1 (only if the integration defines service checks):

```python
def send_service_checks(checks: list, api_key: str, site: str) -> bool:
    \"\"\"Send service checks to Datadog using API v1.\"\"\"
    check_endpoint = f"https://api.{{site}}/api/v1/check_run"

    headers = {{
        "DD-API-KEY": api_key,
        "Content-Type": "application/json",
    }}

    for check in checks:
        payload = {{
            "check": check["check"],
            "host_name": check.get("host_name", "dynamicd-simulator"),
            "status": check["status"],  # 0=OK, 1=WARNING, 2=CRITICAL, 3=UNKNOWN
            "tags": check.get("tags", ["env:dynamicd"]),
            "message": check.get("message", ""),
        }}
        response = requests.post(check_endpoint, headers=headers, json=payload)
        response.raise_for_status()
    return True
```

Example service check generation:
```python
def generate_service_checks(scenario: str, service_check_names: list) -> list:
    \"\"\"Generate service checks based on scenario. Only call if integration has service checks.\"\"\"
    # Skip if integration has no service checks defined
    if not service_check_names:
        return []

    status_map = {{
        "healthy": 0,      # OK
        "degraded": 1,     # WARNING
        "incident": 2,     # CRITICAL
        "recovery": 1,     # WARNING (transitioning)
        "peak_load": 0,    # OK (high but healthy)
        "maintenance": 3,  # UNKNOWN (expected during maintenance)
    }}

    checks = []
    for check_name in service_check_names:
        checks.append({{
            "check": check_name,
            "status": status_map.get(scenario, 0),
            "tags": ["env:dynamicd"],
            "message": f"DynamicD simulation - scenario: {{scenario}}",
        }})
    return checks
```

11. SEND EVENTS using Datadog API v1 (optional, only for significant state changes):

```python
def send_events(events: list, api_key: str, site: str) -> bool:
    \"\"\"Send events to Datadog using API v1.\"\"\"
    event_endpoint = f"https://api.{{site}}/api/v1/events"

    headers = {{
        "DD-API-KEY": api_key,
        "Content-Type": "application/json",
    }}

    for event in events:
        payload = {{
            "title": event["title"],
            "text": event["text"],
            "alert_type": event.get("alert_type", "info"),  # error, warning, info, success
            "tags": event.get("tags", ["env:dynamicd"]),
            "source_type_name": event.get("source", "dynamicd"),
        }}
        response = requests.post(event_endpoint, headers=headers, json=payload)
        response.raise_for_status()
    return True
```

Example event generation (generate sparingly - events are for significant changes):
```python
def generate_events(scenario: str, prev_scenario: str, integration_name: str) -> list:
    \"\"\"Generate events only when scenario changes or for significant issues.\"\"\"
    events = []

    # Only generate events on state transitions or during incidents
    if scenario == "incident":
        events.append({{
            "title": f"{{integration_name}}: Incident detected",
            "text": "System experiencing failures. Investigating...",
            "alert_type": "error",
            "tags": ["env:dynamicd", f"integration:{{integration_name}}"],
        }})
    elif scenario == "recovery" and prev_scenario == "incident":
        events.append({{
            "title": f"{{integration_name}}: Recovery in progress",
            "text": "System recovering from incident. Metrics returning to normal.",
            "alert_type": "success",
            "tags": ["env:dynamicd", f"integration:{{integration_name}}"],
        }})

    return events
```

Generate the complete, working script now. Output ONLY the Python code, no explanations."""


def build_stage1_prompt(integration_context: str, display_name: str) -> tuple[str, str]:
    """Build the Stage 1 (analysis) prompt."""
    user_prompt = STAGE1_USER_PROMPT_TEMPLATE.format(
        integration_context=integration_context,
        display_name=display_name,
    )
    return STAGE1_SYSTEM_PROMPT, user_prompt


def build_stage2_prompt(
    integration_context: str,
    display_name: str,
    integration_name: str,
    stage1_analysis: str,
    scenario: str,
    dd_site: str,
    metrics_per_batch: int,
    duration: int,
) -> tuple[str, str]:
    """Build the Stage 2 (script generation) prompt."""
    scenario_description = SCENARIOS.get(scenario, SCENARIOS["healthy"])

    user_prompt = STAGE2_USER_PROMPT_TEMPLATE.format(
        integration_context=integration_context,
        display_name=display_name,
        integration_name=integration_name,
        stage1_analysis=stage1_analysis,
        scenario=scenario,
        scenario_description=scenario_description,
        dd_site=dd_site,
        metrics_per_batch=metrics_per_batch,
        duration=duration,
    )
    return STAGE2_SYSTEM_PROMPT, user_prompt


def build_error_correction_prompt(
    original_script: str,
    error_message: str,
    attempt: int,
) -> tuple[str, str]:
    """Build a prompt to fix errors in the generated script."""
    system_prompt = """You are an expert Python developer. A script you generated has an error.
Fix the error and return the complete corrected script. Output ONLY the Python code."""

    user_prompt = f"""The following script has an error. Please fix it and return the complete corrected script.

## Original Script
```python
{original_script}
```

## Error (Attempt {attempt}/3)
```
{error_message}
```

Return ONLY the corrected Python code, no explanations. Make sure to fix the specific error mentioned."""

    return system_prompt, user_prompt
