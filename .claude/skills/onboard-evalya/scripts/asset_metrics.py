#!/usr/bin/env python3
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Extract the metric coverage target for an integration from the metrics its shipped
assets put in front of users, and join it against metadata.csv.

The coverage target is *every* metric referenced in the integration's OOTB dashboards
(``assets/dashboards/*.json``) and its recommended monitors (``assets/monitors/*.json``).
These are the metrics a user actually sees, so they are the fixture's first-class input.
Datadog queries name a metric with an aggregator prefix, e.g. ``avg:redis.stats.keyspace_hits{$scope}``
(dashboards) or ``avg(last_5m):avg:redis.mem.used{*}`` (monitors); that ``agg:metric{`` shape is
what we extract. Formula queries and newer widgets store the metric bare, so the aggregator is
optional. A single pattern covers dashboard ``q``/``queries[].query`` fields and monitor
``definition.query`` alike. Only *metric* queries are read: a query's sibling ``data_source`` must
be ``metrics`` (dashboards) and a monitor's ``type`` must be a metric alert, so log/APM/RUM/DSM
widgets sharing the same ``query`` key do not leak non-metric tokens into the target.

Usage:
    python asset_metrics.py <INTEGRATION_DIR>

Prints JSON to stdout:
    {
      "integration": "redisdb",
      "dashboards": ["assets/dashboards/overview.json"],
      "monitors": ["assets/monitors/high_mem.json"],
      "target": ["redis.mem.used", ...],            # union across dashboards + monitors, sorted
      "by_source": {"dashboards": [...], "monitors": [...]},
      "in_metadata": {"redis.mem.used": "gauge", ...},
      "missing_from_metadata": ["redis.foo.bar", ...]  # referenced but not declared -> investigate
    }

Exit code is 0 even when assets or metadata are missing; the JSON reports what was found so the
caller can decide. A malformed asset JSON is reported on stderr and skipped.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

# A metric reference is a namespaced token immediately followed by its ``{...}`` scope
# filter, which every Datadog query carries. The aggregator prefix (``avg:redis.mem{...}``)
# is optional because newer formula widgets store the metric bare
# (``"query": "postgresql.rows_inserted{$scope}"``) with the aggregator in a sibling field.
# Requiring a dot in the token and a trailing ``{`` avoids catching template vars (``$scope``),
# formula operands (``a / b``), monitor window functions (``avg(last_5m)``), and tag keys inside
# braces (``by {host}``). A dot-free metric with no scope filter is not matched; the coverage
# loop is the safety net for such edge cases.
_AGG = r"(?:avg|sum|min|max|count|last|pct|percentile|median|stddev|normalize|weight):"
_METRIC_QUERY = re.compile(rf"(?:{_AGG})?([a-z_][a-z0-9_.]*\.[a-z0-9_.]+)\s*\{{", re.IGNORECASE)

# Query strings live under these keys in dashboard widgets and monitor definitions.
_QUERY_KEYS = ("q", "query")

# We only care about metric queries. A dashboard widget query object carries a `data_source`
# (`metrics`, `logs`, `rum`, `data_streams`, …); keep only `metrics`. A monitor's `definition`
# carries a `type` instead; keep only metric-based alert types. Without this, log/APM/DSM queries
# stored under the same `query` key leak metric-shaped tokens into the coverage target.
_METRIC_MONITOR_TYPES = {"query alert", "metric alert"}


def _is_metric_query(container: dict, key: str) -> bool:
    """Whether the `q`/`query` string on this dict is a metrics query.

    Decided by the sibling `data_source` (dashboard formula/timeseries queries) or `type` (monitor
    definitions). Legacy `q` and any query with neither sibling are assumed to be metrics — those
    shapes only ever carried metric queries.
    """
    data_source = container.get("data_source")
    if data_source is not None:
        return data_source == "metrics"
    monitor_type = container.get("type")
    if monitor_type is not None and key == "query":
        return monitor_type in _METRIC_MONITOR_TYPES
    return True


def _walk_query_strings(node: object) -> list[str]:
    """Recursively collect metric query strings; skip non-metric (logs/APM/DSM) queries."""
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in _QUERY_KEYS and isinstance(value, str):
                if _is_metric_query(node, key):
                    found.append(value)
            else:
                found.extend(_walk_query_strings(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_walk_query_strings(item))
    return found


def extract_metrics(asset: dict) -> set[str]:
    metrics: set[str] = set()
    for query in _walk_query_strings(asset):
        for match in _METRIC_QUERY.finditer(query):
            metrics.add(match.group(1))
    return metrics


def scan_assets(assets_dir: Path, integration_dir: Path) -> tuple[list[str], set[str]]:
    """Return (relative file paths scanned, union of metrics) for one asset directory."""
    files: list[str] = []
    metrics: set[str] = set()
    for path in sorted(assets_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            print(f"skipping {path}: {exc}", file=sys.stderr)
            continue
        files.append(str(path.relative_to(integration_dir)))
        metrics |= extract_metrics(data)
    return files, metrics


def load_metadata_types(metadata_csv: Path) -> dict[str, str]:
    """Map metric_name -> metric_type from metadata.csv (empty dict if absent)."""
    types: dict[str, str] = {}
    if not metadata_csv.is_file():
        return types
    with metadata_csv.open(newline="") as handle:
        for row in csv.DictReader(handle):
            name = (row.get("metric_name") or "").strip()
            if name:
                types[name] = (row.get("metric_type") or "").strip()
    return types


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2

    integration_dir = Path(argv[1]).resolve()

    dashboards, dashboard_metrics = scan_assets(integration_dir / "assets" / "dashboards", integration_dir)
    monitors, monitor_metrics = scan_assets(integration_dir / "assets" / "monitors", integration_dir)
    target = dashboard_metrics | monitor_metrics

    types = load_metadata_types(integration_dir / "metadata.csv")
    in_metadata = {m: types[m] for m in sorted(target) if m in types}
    missing = [m for m in sorted(target) if m not in types]

    json.dump(
        {
            "integration": integration_dir.name,
            "dashboards": dashboards,
            "monitors": monitors,
            "target": sorted(target),
            "by_source": {
                "dashboards": sorted(dashboard_metrics),
                "monitors": sorted(monitor_metrics),
            },
            "in_metadata": in_metadata,
            "missing_from_metadata": missing,
        },
        sys.stdout,
        indent=2,
    )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
