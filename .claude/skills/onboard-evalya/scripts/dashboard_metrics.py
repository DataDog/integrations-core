#!/usr/bin/env python3
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Extract the metric coverage target for an integration from its OOTB dashboards
and join it against metadata.csv.

The coverage target is *every* metric referenced in <INTEGRATION>/assets/dashboards/*.json
(the skill's chosen policy). Datadog timeseries queries always name a metric with an
aggregator prefix, e.g. ``avg:redis.stats.keyspace_hits{$scope}``; that ``agg:metric{``
shape is what we extract. Formula queries wrap the same shape, so a single pattern
covers both the legacy ``q`` field and the newer ``requests[].queries[].query`` field.

Usage:
    python dashboard_metrics.py <INTEGRATION_DIR>

Prints JSON to stdout:
    {
      "integration": "redisdb",
      "dashboards": ["assets/dashboards/overview.json"],
      "target": ["redis.mem.used", ...],            # all metrics referenced, sorted, deduped
      "in_metadata": {"redis.mem.used": "gauge", ...},
      "missing_from_metadata": ["redis.foo.bar", ...]  # referenced but not declared -> investigate
    }

Exit code is 0 even when dashboards or metadata are missing; the JSON reports what was found
so the caller can decide. A malformed dashboard JSON is reported on stderr and skipped.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

# A metric reference is a namespaced token immediately followed by its ``{...}`` scope
# filter, which every Datadog dashboard query carries. The aggregator prefix
# (``avg:redis.mem{...}``, legacy ``q`` field) is optional because newer formula widgets
# store the metric bare (``"query": "postgresql.rows_inserted{$scope}"``) with the
# aggregator in a sibling field. Requiring a dot in the token and a trailing ``{`` avoids
# catching template vars (``$scope``), formula operands (``a / b``), and tag keys inside
# braces (``by {host}``). A dot-free metric with no scope filter is not matched; the
# coverage loop is the safety net for such edge cases.
_AGG = r"(?:avg|sum|min|max|count|last|pct|percentile|median|stddev|normalize|weight):"
_METRIC_QUERY = re.compile(rf"(?:{_AGG})?([a-z_][a-z0-9_.]*\.[a-z0-9_.]+)\s*\{{", re.IGNORECASE)

# Query strings live under these keys in a dashboard widget definition.
_QUERY_KEYS = {"q", "query"}


def _walk_query_strings(node: object) -> list[str]:
    """Recursively collect every string value stored under a query key."""
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in _QUERY_KEYS and isinstance(value, str):
                found.append(value)
            else:
                found.extend(_walk_query_strings(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_walk_query_strings(item))
    return found


def extract_metrics(dashboard: dict) -> set[str]:
    metrics: set[str] = set()
    for query in _walk_query_strings(dashboard):
        for match in _METRIC_QUERY.finditer(query):
            metrics.add(match.group(1))
    return metrics


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
    dashboards_dir = integration_dir / "assets" / "dashboards"

    target: set[str] = set()
    dashboards: list[str] = []
    for path in sorted(dashboards_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            print(f"skipping {path}: {exc}", file=sys.stderr)
            continue
        dashboards.append(str(path.relative_to(integration_dir)))
        target |= extract_metrics(data)

    types = load_metadata_types(integration_dir / "metadata.csv")
    in_metadata = {m: types[m] for m in sorted(target) if m in types}
    missing = [m for m in sorted(target) if m not in types]

    json.dump(
        {
            "integration": integration_dir.name,
            "dashboards": dashboards,
            "target": sorted(target),
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
