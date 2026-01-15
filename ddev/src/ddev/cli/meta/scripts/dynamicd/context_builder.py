# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Context builder for gathering integration metadata."""

from __future__ import annotations

import csv
import json
import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ddev.integration.core import Integration

logger = logging.getLogger(__name__)

# Limits to avoid exceeding LLM token limits
MAX_METRICS_IN_PROMPT = 80
MAX_CONFIG_OPTIONS_IN_PROMPT = 30


@dataclass
class IntegrationContext:
    """Contains all context needed to generate realistic fake data."""

    name: str
    display_name: str
    description: str
    categories: list[str]
    metrics: list[dict[str, str]]
    config_options: list[dict[str, str]]
    service_checks: list[dict[str, str]]
    metric_prefix: str
    dashboard_metrics: list[str] = field(default_factory=list)  # Metrics used in dashboards
    dashboard_tags: dict[str, list[str]] = field(default_factory=dict)  # Tags required for each metric
    dashboard_tag_values: dict[str, dict[str, list[str]]] = field(
        default_factory=dict
    )  # CRITICAL: Specific tag values required per metric
    supported_os: list[str] = field(default_factory=list)

    def to_prompt_context(self) -> str:
        """Convert context to a string for LLM prompt."""
        lines = [
            f"# Integration: {self.display_name}",
            f"Internal name: {self.name}",
            f"Description: {self.description}",
            f"Categories: {', '.join(self.categories)}",
            f"Metric prefix: {self.metric_prefix}",
            "",
        ]

        # Collect all unique tags from dashboard for summary
        all_dashboard_tags = set()
        for tags in self.dashboard_tags.values():
            all_dashboard_tags.update(tags)

        # PRIORITY: Dashboard metrics first (these MUST be populated)
        if self.dashboard_metrics:
            lines.extend(
                [
                    "## PRIORITY METRICS (Used in Dashboard - MUST be populated with realistic values)",
                    "",
                    "These metrics appear on the integration's dashboard. They MUST ALL be generated",
                    "with realistic, correlated values so the dashboard looks meaningful.",
                    "",
                    "CRITICAL: Each metric MUST include ALL its required tags with realistic values!",
                    "Dashboard widgets group by these tags - empty/missing tags cause 'N/A' display.",
                    "",
                ]
            )

            for metric_name in self.dashboard_metrics:
                # Find the full metric info
                metric_info = next((m for m in self.metrics if m.get('metric_name') == metric_name), None)
                metric_line = f"- **`{metric_name}`**"
                if metric_info:
                    if metric_info.get('metric_type'):
                        metric_line += f" (type: {metric_info['metric_type']})"
                    if metric_info.get('unit_name'):
                        metric_line += f" [unit: {metric_info['unit_name']}]"

                # Add REQUIRED TAGS for this metric
                metric_tags = self.dashboard_tags.get(metric_name, [])
                if metric_tags:
                    metric_line += f"\n  **REQUIRED TAGS**: `{', '.join(metric_tags)}`"

                # CRITICAL: Add specific TAG VALUES that MUST be generated
                metric_tag_vals = self.dashboard_tag_values.get(metric_name, {})
                if metric_tag_vals:
                    metric_line += "\n  **REQUIRED TAG VALUES (MUST generate metrics with ALL of these):**"
                    for tag_name, values in metric_tag_vals.items():
                        metric_line += f"\n    - `{tag_name}`: {', '.join(values)}"

                if metric_info and metric_info.get('description'):
                    desc = metric_info['description'][:150]
                    metric_line += f"\n  Description: {desc}"

                lines.append(metric_line)
                lines.append("")  # Blank line between metrics

            # Summary of all tags needed
            if all_dashboard_tags:
                lines.extend(
                    [
                        "",
                        "## REQUIRED TAGS (Must have realistic values - NEVER use 'N/A' or empty)",
                        "",
                        "The dashboard groups by these tags. Each MUST have realistic values:",
                        "",
                    ]
                )
                for tag in sorted(all_dashboard_tags):
                    # Provide example values for common tags
                    examples = _get_tag_examples(tag)
                    lines.append(f"- `{tag}`: {examples}")
                lines.append("")

            # CRITICAL: Summarize all required tag VALUES
            # This tells the LLM exactly which tag:value combinations must exist
            all_tag_values: dict[str, set[str]] = {}
            for metric_vals in self.dashboard_tag_values.values():
                for tag_name, values in metric_vals.items():
                    if tag_name not in all_tag_values:
                        all_tag_values[tag_name] = set()
                    all_tag_values[tag_name].update(values)

            if all_tag_values:
                lines.extend(
                    [
                        "",
                        "## CRITICAL: REQUIRED TAG VALUES (Dashboard filters by these exact values!)",
                        "",
                        "The dashboard queries FILTER by these specific tag:value combinations.",
                        "You MUST generate metrics with ALL of these values or widgets will show 'No data':",
                        "",
                    ]
                )
                for tag_name, values in sorted(all_tag_values.items()):
                    values_str = ", ".join(sorted(values))
                    lines.append(f"- **`{tag_name}`**: {values_str}")
                lines.extend(
                    [
                        "",
                        "For each tag listed above, ensure you generate metrics with EVERY value shown.",
                        "Missing even ONE value means a dashboard widget shows 'No data'.",
                        "",
                    ]
                )

            lines.extend(
                [
                    "",
                    "IMPORTANT: The above dashboard metrics should show CORRELATED behavior.",
                    "For example, if queue depth increases, related latency metrics should also increase.",
                    "",
                ]
            )

        # All other metrics
        lines.extend(
            [
                "## All Available Metrics",
                "The following metrics are defined for this integration:",
                "",
            ]
        )

        # Add metrics in a structured format (excluding dashboard metrics already shown)
        dashboard_set = set(self.dashboard_metrics)
        other_metrics = [m for m in self.metrics if m.get('metric_name') not in dashboard_set]

        for metric in other_metrics[:MAX_METRICS_IN_PROMPT]:
            metric_line = f"- `{metric.get('metric_name', 'unknown')}`"
            if metric.get('metric_type'):
                metric_line += f" (type: {metric['metric_type']})"
            if metric.get('unit_name'):
                metric_line += f" [unit: {metric['unit_name']}]"
            if metric.get('description'):
                desc = metric['description'][:200]
                metric_line += f": {desc}"
            lines.append(metric_line)

        if len(other_metrics) > MAX_METRICS_IN_PROMPT:
            lines.append(f"... and {len(other_metrics) - MAX_METRICS_IN_PROMPT} more metrics")

        # Add config options if available
        if self.config_options:
            lines.extend(
                [
                    "",
                    "## Configuration Options (key entities/parameters)",
                    "",
                ]
            )
            for opt in self.config_options[:MAX_CONFIG_OPTIONS_IN_PROMPT]:
                opt_line = f"- `{opt.get('name', 'unknown')}`"
                if opt.get('description'):
                    desc = opt['description'][:150]
                    opt_line += f": {desc}"
                lines.append(opt_line)

        # Add service checks
        if self.service_checks:
            lines.extend(
                [
                    "",
                    "## Service Checks",
                    "",
                ]
            )
            for check in self.service_checks:
                check_line = f"- `{check.get('name', 'unknown')}`"
                if check.get('description'):
                    check_line += f": {check['description'][:100]}"
                lines.append(check_line)

        return "\n".join(lines)


def _get_tag_examples(tag_name: str) -> str:
    """Get example values for common tag names."""
    tag_examples = {
        # Generic tags
        'host': 'e.g., "prod-server-01", "api-node-02", "worker-03"',
        'env': 'e.g., "production", "staging", "development"',
        'service': 'e.g., "api-gateway", "auth-service", "data-pipeline"',
        'team': 'e.g., "platform", "ml-ops", "backend", "data-science"',
        'cluster': 'e.g., "us-east-1-primary", "eu-west-1-replica"',
        'node': 'e.g., "node-01", "node-02", "node-03"',
        'instance': 'e.g., "instance-001", "instance-002"',
        'region': 'e.g., "us-east-1", "eu-west-1", "ap-southeast-1"',
        'zone': 'e.g., "zone-a", "zone-b", "zone-c"',
        'datacenter': 'e.g., "dc1", "dc2", "aws-use1"',
        # Worker/Process tags
        'worker': 'e.g., "worker-01-12345", "celery-web-1-9876"',
        'process': 'e.g., "main", "worker", "scheduler"',
        'pid': 'e.g., "12345", "67890"',
        # Network tags
        'endpoint': 'e.g., "/api/v1/users", "/health", "/metrics"',
        'method': 'e.g., "GET", "POST", "PUT", "DELETE"',
        'status': 'e.g., "200", "404", "500"',
        'status_code': 'e.g., "200", "201", "400", "500"',
        'protocol': 'e.g., "http", "https", "grpc"',
        'port': 'e.g., "8080", "443", "5432"',
        'dir': 'e.g., "inbound", "outbound", "in", "out"',
        'direction': 'e.g., "ingress", "egress"',
        # Database tags
        'db': 'e.g., "users_db", "analytics", "cache"',
        'database': 'e.g., "postgres_main", "mysql_replica"',
        'table': 'e.g., "users", "orders", "events"',
        'query_type': 'e.g., "select", "insert", "update", "delete"',
        # Queue tags
        'queue': 'e.g., "high-priority", "default", "background-jobs"',
        'topic': 'e.g., "user-events", "notifications", "analytics"',
        'exchange': 'e.g., "main", "dead-letter", "events"',
        # AI/ML tags
        'model': 'e.g., "gpt-4", "claude-3", "llama-70b", "mixtral"',
        'api_provider': 'e.g., "openai", "anthropic", "azure", "bedrock"',
        'api_key_alias': 'e.g., "prod-key-1", "dev-key-alpha", "team-ml"',
        'end_user': 'e.g., "user_12345", "service_account", "api_client"',
        'user': 'e.g., "alice@company.com", "bob@company.com"',
        # Drop/Error tags
        'drop': 'e.g., "buffer_full", "timeout", "rate_limited"',
        'reason': 'e.g., "timeout", "connection_reset", "invalid_data"',
        'error_type': 'e.g., "timeout", "auth_failed", "rate_limit"',
        # State tags
        'state': 'e.g., "running", "stopped", "pending"',
        'health_status': 'e.g., "healthy", "degraded", "critical"',
    }

    return tag_examples.get(tag_name, f'Use realistic values appropriate for "{tag_name}"')


def build_context(integration: Integration) -> IntegrationContext:
    """Build context from an integration."""
    # Get basic info from manifest
    manifest = integration.manifest

    display_name = manifest.get("/display_name", "") or manifest.get("/tile/title", integration.name)

    # Read description from README.md (much richer than manifest)
    description = _read_readme(integration)
    if not description:
        # Fallback to manifest description
        description = manifest.get("/tile/description", "") or ""

    # Extract categories from classifier_tags
    classifier_tags = manifest.get("/tile/classifier_tags", []) or []
    categories = [tag.replace("Category::", "") for tag in classifier_tags if tag.startswith("Category::")]

    # Extract supported OS
    supported_os = [tag.replace("Supported OS::", "") for tag in classifier_tags if tag.startswith("Supported OS::")]

    # Get metric prefix
    metric_prefix = manifest.get("/assets/integration/metrics/prefix", "") or f"{integration.name}."

    # Read metrics from metadata.csv
    metrics = _read_metrics(integration)

    # Read config options from spec.yaml
    config_options = _read_config_options(integration)

    # Read service checks
    service_checks = _read_service_checks(integration)

    # Read dashboard metrics (PRIORITY - these must be populated)
    dashboard_metrics = _read_dashboard_metrics(integration, metric_prefix)

    # Read dashboard tags (tells us which tags each metric needs)
    dashboard_tags = _read_dashboard_tags(integration)

    # CRITICAL: Read specific tag VALUES required by dashboard queries
    # This tells us exactly what tag:value combinations must exist
    dashboard_tag_values = _read_dashboard_tag_values(integration)

    return IntegrationContext(
        name=integration.name,
        display_name=display_name,
        description=description,
        categories=categories,
        metrics=metrics,
        config_options=config_options,
        service_checks=service_checks,
        metric_prefix=metric_prefix,
        dashboard_metrics=dashboard_metrics,
        dashboard_tags=dashboard_tags,
        dashboard_tag_values=dashboard_tag_values,
        supported_os=supported_os,
    )


def _read_metrics(integration: Integration) -> list[dict[str, str]]:
    """Read metrics from metadata.csv."""
    metrics_file = integration.metrics_file
    if not metrics_file.exists():
        return []

    metrics = []
    with metrics_file.open(encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            metrics.append(dict(row))

    return metrics


def _read_config_options(integration: Integration) -> list[dict[str, str]]:
    """Read configuration options from spec.yaml."""
    spec_file = integration.path / "assets" / "configuration" / "spec.yaml"
    if not spec_file.exists():
        return []

    try:
        import yaml

        with spec_file.open(encoding='utf-8') as f:
            spec = yaml.safe_load(f)

        options: list[dict[str, str]] = []
        _extract_options(spec, options)
        return options
    except Exception:
        logger.debug("Failed to read config options from %s", spec_file, exc_info=True)
        return []


def _extract_options(spec: dict | list, options: list[dict[str, str]], depth: int = 0) -> None:
    """Recursively extract options from spec.yaml structure."""
    if depth > 5:  # Prevent infinite recursion
        return

    if isinstance(spec, dict):
        if 'name' in spec and 'description' in spec:
            options.append(
                {
                    'name': spec.get('name', ''),
                    'description': spec.get('description', ''),
                    'required': str(spec.get('required', False)),
                }
            )
        for value in spec.values():
            _extract_options(value, options, depth + 1)
    elif isinstance(spec, list):
        for item in spec:
            _extract_options(item, options, depth + 1)


def _read_readme(integration: Integration) -> str:
    """
    Read the README.md file and extract the Overview section.

    The README contains much richer context about what the integration does
    than the manifest.json description.
    """
    readme_file = integration.path / "README.md"
    if not readme_file.exists():
        return ""

    try:
        content = readme_file.read_text(encoding='utf-8')

        # Extract the Overview section (most useful for understanding the integration)
        # README format is typically: ## Overview\n\n<content>\n\n## Setup
        # Try to find Overview section
        overview_match = re.search(r'##\s*Overview\s*\n+(.*?)(?=\n##|\Z)', content, re.DOTALL | re.IGNORECASE)

        if overview_match:
            overview = overview_match.group(1).strip()
            # Limit to first 2000 chars to avoid token bloat
            if len(overview) > 2000:
                overview = overview[:2000] + "..."
            return overview

        # Fallback: return first 1500 chars of README
        return content[:1500] + "..." if len(content) > 1500 else content

    except Exception:
        logger.debug("Failed to read README from %s", readme_file, exc_info=True)
        return ""


def _read_service_checks(integration: Integration) -> list[dict[str, str]]:
    """Read service checks from service_checks.json."""
    service_checks_file = integration.path / "assets" / "service_checks.json"
    if not service_checks_file.exists():
        return []

    try:
        with service_checks_file.open(encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        logger.debug("Failed to read service checks from %s", service_checks_file, exc_info=True)
        return []


def _read_dashboard_metrics(integration: Integration, metric_prefix: str) -> list[str]:
    """
    Extract metrics used in dashboard widgets.

    These are the PRIORITY metrics that must be populated for the dashboard to look good.
    """
    dashboards_dir = integration.path / "assets" / "dashboards"
    if not dashboards_dir.exists():
        return []

    metrics = set()

    # Pattern to extract metric names from dashboard queries
    # Matches patterns like: avg:ibm_mq.queue.depth_current{...}
    metric_pattern = re.compile(
        r'(?:avg|sum|max|min|count|rate|diff|derivative|integral|cumsum|top|anomalies|forecast|outliers|ewma|median|percentile|stddev|timeshift):([a-zA-Z0-9_\.]+)\{'
    )

    # Also match simple metric references without aggregation
    simple_pattern = re.compile(rf'{re.escape(metric_prefix)}[a-zA-Z0-9_\.]+')

    for dashboard_file in dashboards_dir.glob("*.json"):
        try:
            with dashboard_file.open(encoding='utf-8') as f:
                dashboard_content = f.read()

            # Find all metric names using the aggregation pattern
            for match in metric_pattern.finditer(dashboard_content):
                metric_name = match.group(1)
                if metric_name.startswith(metric_prefix):
                    metrics.add(metric_name)

            # Also find simple metric references
            for match in simple_pattern.finditer(dashboard_content):
                metrics.add(match.group(0))

        except Exception:
            logger.debug("Failed to read dashboard metrics from %s", dashboard_file, exc_info=True)
            continue

    # Return sorted list for consistent ordering
    return sorted(metrics)


def _read_dashboard_tags(integration: Integration) -> dict[str, list[str]]:
    """
    Extract tags used for grouping in dashboard widgets.

    This tells us WHICH TAGS must be populated for dashboards to display properly.
    Returns: dict mapping metric names to list of required tags.
    """
    dashboards_dir = integration.path / "assets" / "dashboards"
    if not dashboards_dir.exists():
        return {}

    metric_tags: dict[str, set[str]] = {}

    # Pattern to extract "by {tag1, tag2}" groupings
    # e.g., "sum:litellm.request.total{*} by {team,api_key_alias}"
    by_pattern = re.compile(r'([a-zA-Z0-9_\.]+)\{[^}]*\}\s*(?:by\s*\{([^}]+)\})?')

    # Pattern to extract tags from filter expressions like {tag:value}
    filter_tag_pattern = re.compile(r'\{([^}:,\s]+):[^}]+\}')

    for dashboard_file in dashboards_dir.glob("*.json"):
        try:
            with dashboard_file.open(encoding='utf-8') as f:
                content = f.read()

            # Find all metrics and their "by {tags}" groupings
            for match in by_pattern.finditer(content):
                metric_name = match.group(1)
                # Initialize metric even without "by {}" so filter tags get captured
                if metric_name not in metric_tags:
                    metric_tags[metric_name] = set()
                if match.group(2):  # Has "by {tags}"
                    tags = [t.strip() for t in match.group(2).split(',')]
                    metric_tags[metric_name].update(tags)

            # Find tags used in filters
            for match in filter_tag_pattern.finditer(content):
                tag_name = match.group(1)
                # Add to all metrics as a common tag
                for metric in metric_tags:
                    metric_tags[metric].add(tag_name)

            # Parse JSON to find template variables (these indicate important tags)
            try:
                dashboard_json = json.loads(content)
                template_vars = dashboard_json.get('template_variables', [])
                for var in template_vars:
                    tag_name = var.get('name') or var.get('default')
                    if tag_name:
                        # This tag is used for filtering across the dashboard
                        for metric in metric_tags:
                            metric_tags[metric].add(tag_name)
            except json.JSONDecodeError:
                logger.debug("Failed to parse JSON from %s", dashboard_file)

        except Exception:
            logger.debug("Failed to read dashboard tags from %s", dashboard_file, exc_info=True)
            continue

    # Convert sets to sorted lists
    return {k: sorted(v) for k, v in metric_tags.items()}


def _read_dashboard_tag_values(integration: Integration) -> dict[str, dict[str, list[str]]]:
    """
    CRITICAL: Extract specific tag:value pairs used in dashboard queries.

    This is essential for ensuring all required data combinations are generated.
    For example, if a dashboard queries:
        sum:kuma.resources_count{resource_type:zone}
        sum:kuma.resources_count{resource_type:mesh}
        sum:kuma.resources_count{resource_type:dataplane}

    We need to tell the LLM to generate metrics with ALL these resource_type values.

    Returns: dict mapping metric names to dict of {tag_name: [list of required values]}
    Example: {
        "kuma.resources_count": {
            "resource_type": ["zone", "mesh", "dataplane", "healthcheck"]
        }
    }
    """
    dashboards_dir = integration.path / "assets" / "dashboards"
    if not dashboards_dir.exists():
        return {}

    # Structure: metric_name -> tag_name -> set of values
    metric_tag_values: dict[str, dict[str, set[str]]] = {}

    # Pattern to match metric queries with tag filters
    # Matches: sum:metric.name{tag1:value1,tag2:value2,...}
    # Also matches: sum:metric.name{$var AND tag:value AND $var2}
    query_pattern = re.compile(
        r'(?:avg|sum|max|min|count|rate|diff|derivative|integral|cumsum|top|anomalies|forecast|outliers|ewma|median|percentile|stddev|timeshift):([a-zA-Z0-9_\.]+)\{([^}]*)\}'
    )

    # Pattern to extract individual tag:value pairs (not template variables like $zone)
    tag_value_pattern = re.compile(r'([a-zA-Z0-9_]+):([a-zA-Z0-9_\-\.\/]+)')

    # Pattern for IN clauses like: code_class IN (1xx,2xx,3xx)
    in_clause_pattern = re.compile(r'([a-zA-Z0-9_]+)\s+IN\s+\(([^)]+)\)', re.IGNORECASE)

    for dashboard_file in dashboards_dir.glob("*.json"):
        try:
            with dashboard_file.open(encoding='utf-8') as f:
                content = f.read()

            # Find all metric queries
            for match in query_pattern.finditer(content):
                metric_name = match.group(1)
                filter_str = match.group(2)

                if metric_name not in metric_tag_values:
                    metric_tag_values[metric_name] = {}

                # Extract tag:value pairs from the filter
                for tag_match in tag_value_pattern.finditer(filter_str):
                    tag_name = tag_match.group(1)
                    tag_value = tag_match.group(2)

                    # Skip template variables (start with $) and wildcards
                    if tag_value.startswith('$') or tag_value == '*':
                        continue

                    if tag_name not in metric_tag_values[metric_name]:
                        metric_tag_values[metric_name][tag_name] = set()
                    metric_tag_values[metric_name][tag_name].add(tag_value)

                # Extract values from IN clauses
                for in_match in in_clause_pattern.finditer(filter_str):
                    tag_name = in_match.group(1)
                    values_str = in_match.group(2)
                    values = [v.strip() for v in values_str.split(',')]

                    if tag_name not in metric_tag_values[metric_name]:
                        metric_tag_values[metric_name][tag_name] = set()
                    metric_tag_values[metric_name][tag_name].update(values)

        except Exception:
            logger.debug("Failed to read dashboard tag values from %s", dashboard_file, exc_info=True)
            continue

    # Convert sets to sorted lists for consistent output
    result: dict[str, dict[str, list[str]]] = {}
    for metric, tags in metric_tag_values.items():
        if tags:  # Only include metrics that have specific tag values
            result[metric] = {tag: sorted(values) for tag, values in tags.items() if values}

    return result
