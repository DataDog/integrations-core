# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from __future__ import annotations

import argparse
import pathlib
import sys
from typing import List

# We need access to METRIC_MAP and to helper functions from generate_metadata.py
# ``scripts`` is **not** a package, so add its parent (repository root) to sys.path
# so that ``import generate_metadata`` works both when the integration is installed
# and when running from source.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from scripts.generate_metadata import extract_metric_defs, fetch_temporal_metrics  # type: ignore
except ImportError as exc:  # pragma: no cover – should never happen inside repo
    raise SystemExit(f"Could not import helpers from generate_metadata.py: {exc}")

# Import the existing metrics map
# E402 Module level import not at top of file
# flake8: noqa: E402
from datadog_checks.temporal.metrics import METRIC_MAP

METRICS_FILE = REPO_ROOT / "datadog_checks" / "temporal" / "metrics.py"


def locate_insertion_index(lines: List[str]) -> int:
    """Return the index *before* the closing brace of METRIC_MAP."""
    end_index = None
    brace_level = 0
    inside_map = False

    for idx, line in enumerate(lines):
        if not inside_map and line.lstrip().startswith("METRIC_MAP") and "{" in line:
            inside_map = True
            brace_level = line.count("{") - line.count("}")
            continue

        if inside_map:
            brace_level += line.count("{") - line.count("}")
            if brace_level == 0:
                # `idx` points to the line containing the closing brace '}'
                end_index = idx
                break

    if end_index is None:
        raise RuntimeError("Could not locate end of METRIC_MAP in metrics.py")
    return end_index


def append_missing_metrics(missing: List[str]) -> None:
    """Append mapping placeholders for *missing* metrics to metrics.py."""
    with METRICS_FILE.open("r", encoding="utf-8") as fp:
        lines = fp.readlines()

    insert_at = locate_insertion_index(lines)

    # Prepare new lines – 4-space indentation to match existing file style.
    # We also record the Temporal version we pulled these from to aid future audits.
    version_comment = f"added in temporal version {ARGS_TAG}" if ARGS_TAG else "added automatically"
    new_lines = [f"    '{m}': '{m}',  # TODO: verify mapping, {version_comment}\n" for m in sorted(missing)]

    # Insert before the closing brace
    updated_lines = lines[:insert_at] + new_lines + lines[insert_at:]

    with METRICS_FILE.open("w", encoding="utf-8") as fp:
        fp.writelines(updated_lines)

    print("Appended", len(new_lines), "new entries to METRIC_MAP.")


def main() -> None:
    """
    Compares Temporal's metric definitions for a specific release tag
    with our local ``METRIC_MAP`` and appends placeholder mappings for any **missing**
    metrics.

    1. Download ``common/metrics/metric_defs.go`` for the requested tag from the
    Temporal OSS repository.
    2. Extract all metric identifiers defined in that file.
    3. Compute the set difference between those identifiers and the keys already
    present in ``METRIC_MAP``.
    4. Append entries for the missing metrics to ``datadog_checks/temporal/metrics.py``
    right before the closing "}" of the dictionary.

    For every newly-added metric we default the Datadog metric name to be identical to
    Temporal's.
    """
    parser = argparse.ArgumentParser(
        description="Update metrics.py with missing Temporal metrics.",
        epilog="Example: hatch run py3.8-1.19:python ./scripts/update_metrics_map.py --tag=v1.19.0",
    )
    parser.add_argument("--tag", required=True, help="Temporal version tag to compare against, e.g. v1.19.0")
    args = parser.parse_args()

    global ARGS_TAG  # expose to append_missing_metrics
    ARGS_TAG = args.tag

    # fetch & extract metrics from Temporal source
    source_go = fetch_temporal_metrics(args.tag)
    temporal_metric_types = extract_metric_defs(source_go)
    temporal_metrics = set(temporal_metric_types)

    # compute missing
    missing_metrics = sorted(temporal_metrics - set(METRIC_MAP))

    if not missing_metrics:
        print("✅ No missing metrics – METRIC_MAP is up to date!")
        return

    # update metrics.py
    append_missing_metrics(missing_metrics)

    print("💡 Please review the TODO comments and adjust metric names/types where necessary.")


if __name__ == "__main__":
    main()
