# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""
Unified script to update Temporal integration for new versions.

This script combines the functionality of update_metrics_map.py and generate_metadata.py
to provide a single command for updating both METRIC_MAP and metadata.csv when new
Temporal versions are released.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import pathlib
import re
import sys
from urllib.parse import urljoin

import requests

# We need access to METRIC_MAP and helper functions
# ``scripts`` is **not** a package, so add its parent (repository root) to sys.path
# so that imports work both when the integration is installed and when running from source.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import the existing metrics map
# E402 Module level import not at top of file
# flake8: noqa: E402
from datadog_checks.temporal.metrics import METRIC_MAP

# Paths to files we will modify
METRICS_FILE = REPO_ROOT / "datadog_checks" / "temporal" / "metrics.py"
METADATA_FILE = REPO_ROOT / "metadata.csv"


def fetch_temporal_metrics(tag: str) -> str:
    """
    Fetch the metrics definitions file from Temporal repository for a specific tag.

    Args:
        tag (str): The Temporal version tag (e.g., 'v1.19.0')

    Returns:
        str: The content of the metrics definitions file

    Raises:
        requests.RequestException: If the request fails
        ValueError: If the tag format is invalid
    """
    if not tag.startswith('v'):
        raise ValueError("Tag must start with 'v' (e.g., 'v1.19.0')")

    base_url = "https://raw.githubusercontent.com/temporalio/temporal/refs/tags"
    metrics_path = "common/metrics/metric_defs.go"
    url = urljoin(f"{base_url}/{tag}/", metrics_path)

    print(f"Fetching metrics from {url}")
    response = requests.get(url)
    response.raise_for_status()
    return response.text


def extract_metric_defs(go_code: str) -> dict:
    """
    Extract metric definitions from Go code that are function calls starting with 'New' and containing 'Def'.

    Args:
        go_code (str): The Go source code content

    Returns:
        dict: Dictionary with metric name as key and type as value
    """
    results = {}

    # Regular expression to match variable declarations with New*Def function calls
    # This pattern looks for:
    # 1. Variable name
    # 2. = New*Def(
    # 3. Metric name in quotes
    # 4. Type name between New and Def
    pattern = r'(\w+)\s*=\s*New(\w*)Def\s*\(\s*"([^"]+)"'

    # Find all matches in the code
    matches = re.finditer(pattern, go_code)

    for match in matches:
        type_name = match.group(2)
        metric_name = match.group(3)
        results[metric_name.lower()] = type_name.lower()

    print(f"Extracted {len(results)} metric definitions from Temporal source")
    return results


def build_version_var(tag: str) -> str:
    """Return the variable name for a given Temporal version tag.

    Example: ``v1.29.0`` -> ``TEMPORAL_V1_29_0_METRICS``.
    """
    cleaned = tag.lstrip("vV")  # strip leading 'v'
    var_suffix = cleaned.replace(".", "_")
    return f"TEMPORAL_V{var_suffix}_METRICS"


def update_metrics_map(tag: str, temporal_metrics: set[str]) -> bool:
    """
    Update METRIC_MAP in metrics.py with missing Temporal metrics.

    Args:
        tag: Temporal version tag
        temporal_metrics: Set of metric names from Temporal source

    Returns:
        bool: True if any updates were made, False otherwise
    """
    print("Updating METRIC_MAP...")

    # Compute missing metrics
    missing_metrics = sorted(temporal_metrics - set(METRIC_MAP))

    if not missing_metrics:
        print("No missing metrics – METRIC_MAP is up to date!")
        return False

    var_name = build_version_var(tag)

    # Skip if dictionary already exists – prevents accidental duplication
    with METRICS_FILE.open("r", encoding="utf-8") as fp:
        if var_name in fp.read():
            print(f"WARNING: {var_name} already exists in metrics.py – nothing to do.")
            return False

    # Build the new version dictionary
    header = f"\n{var_name} = {{\n"
    body = [f"    '{m}': '{m}',  # TODO: verify mapping\n" for m in missing_metrics]
    footer = f"}}\n\nMETRIC_MAP.update({var_name})\n"
    block = header + "".join(body) + footer

    # Append to the end of the file
    with METRICS_FILE.open("a", encoding="utf-8") as fp:
        fp.write(block)

    print(f"Appended {len(missing_metrics)} new entries to {var_name} and updated METRIC_MAP.")
    print("Please review the TODO comments and adjust metric names/types where necessary.")
    return True


def check_existing_metric(name: str, previous_metadata: dict, added_dd_metrics: set) -> list:
    """
    Check if a metric exists in the previous metadata and add it to the current metadata if found.

    Args:
        name: The name of the metric to check, example: service.pending_requests
        previous_metadata: Dictionary containing the previous metadata
        added_dd_metrics: Set of already processed metrics

    Returns:
        List of metadata entries for existing metrics
    """
    # Match metric names like:
    #   temporal.server.<metric_name>
    #   temporal.server.<metric_name>.count
    #   temporal.server.<metric_name>.sum
    #   temporal.server.<metric_name>.bucket
    pattern = re.compile(rf"^temporal\.server\.{re.escape(name)}(?:\.(?:count|sum|bucket))?$")
    result = []
    for dd_metric in previous_metadata:
        if pattern.match(dd_metric) and dd_metric not in added_dd_metrics:
            # A metric was supported in the previous temporal version, but dropped in the current version
            result.append(previous_metadata.get(dd_metric))
            print(f"INFO: {dd_metric} is reserved because it exists in the current metadata.csv file")
            added_dd_metrics.add(dd_metric)
    return result


def update_metadata_csv(tag: str, temporal_metric_types: dict) -> None:
    """
    Update metadata.csv with current metrics information.

    Args:
        tag: Temporal version tag
        temporal_metric_types: Dictionary mapping metric names to types
    """
    print("Updating metadata.csv...")

    # Preserve existing metadata.csv entries
    with METADATA_FILE.open(newline='') as metadata_file:
        reader = csv.DictReader(metadata_file)
        metadata_fields = reader.fieldnames
        previous_metadata = {row['metric_name']: row for row in reader}

    # Sanity check: Check whether there are metrics in the temporal code that are not present
    # in the `METRIC_MAP` and warn about them:
    missing_metrics = set(temporal_metric_types) - set(METRIC_MAP)
    if missing_metrics:
        print("WARNING: the input code contains metrics not defined in `METRIC_MAP`:")
        for metric in sorted(missing_metrics):
            print(f"   - {metric}")

    # Merge all the data
    metadata = []

    def append_metric_metadata(metric_name, metric_type='count', unit_name=None):
        qualified_metric_name = f'temporal.server.{metric_name}'
        metric_meta = dict.fromkeys(metadata_fields, '')
        metric_meta['orientation'] = 0
        metric_meta.update(previous_metadata.get(qualified_metric_name, {}))
        metric_meta['integration'] = 'temporal'
        metric_meta['metric_name'] = qualified_metric_name
        metric_meta['metric_type'] = metric_type
        metric_meta['short_name'] = metric_name.replace('.', ' ').replace('_', ' ')
        # Only override unit_name explicitly
        if unit_name is not None:
            metric_meta['unit_name'] = unit_name
        metadata.append(metric_meta)

    # Handling metrics that might have multiple variations (like histograms that generate
    # .bucket, .count, and .sum metrics)
    added_dd_metrics = set()

    # Build the metadata for the metrics that both live in temporal's code and in the METRIC_MAP
    for temporal_name, dd_metric in METRIC_MAP.items():
        metric_name = dd_metric.get('name') if isinstance(dd_metric, dict) else dd_metric
        is_native_dynamic = isinstance(dd_metric, dict) and dd_metric.get('type') == 'native_dynamic'

        # Check if metric exists in previous metadata
        existing_dd_metric = check_existing_metric(metric_name, previous_metadata, added_dd_metrics)

        if existing_dd_metric:
            print(f"INFO: metric `{metric_name}` is reserved because it's present in the current metadata.csv file")
            metadata.extend(existing_dd_metric)
            continue

        if is_native_dynamic:
            print(
                f"WARNING: skipping metric `{dd_metric}` because native dynamic type "
                "and is not present in the current metadata.csv file"
            )
            continue

        temporal_type = temporal_metric_types.get(temporal_name)
        if temporal_type is None:
            print(
                f"WARNING: skipping metric `{temporal_name}/{dd_metric}` because it's "
                "not present in both temporal metric definitions and the current "
                "metadata.csv file"
            )
            continue

        # Update the metrics name based on the temporal type
        if temporal_type == 'counter':
            append_metric_metadata(f'{metric_name}.count')
        elif temporal_type == 'gauge':
            append_metric_metadata(metric_name, 'gauge')
        elif temporal_type.endswith('histogram'):
            unit_name = None
            if temporal_type == 'byteshistogram':
                unit_name = "byte"
            append_metric_metadata(f'{metric_name}.bucket')
            append_metric_metadata(f'{metric_name}.count')
            append_metric_metadata(f'{metric_name}.sum', unit_name=unit_name)
        elif temporal_type == 'timer':
            append_metric_metadata(f'{metric_name}.bucket')
            append_metric_metadata(f'{metric_name}.count')
            append_metric_metadata(f'{metric_name}.sum', unit_name='millisecond')
        else:
            print(f"Unrecognized metric type {temporal_type}, skipping.")

    # Write everything back to metadata.csv
    with METADATA_FILE.open('w', newline='') as metadata_file:
        writer = csv.DictWriter(metadata_file, metadata_fields)
        writer.writeheader()
        writer.writerows(metadata)

    print(f"Updated metadata.csv with {len(metadata)} metric entries")


def main() -> None:
    """
    Update Temporal integration for a new version by:
    1. Fetching metric definitions from Temporal repository
    2. Updating METRIC_MAP with any missing metrics
    3. Regenerating metadata.csv with current metric information

    This combines the functionality of update_metrics_map.py and generate_metadata.py
    into a single convenient command.
    """
    parser = argparse.ArgumentParser(
        description="Update Temporal integration for a new version",
        epilog=(
            "Examples:\n"
            "  # Update both METRIC_MAP and metadata.csv:\n"
            "  python ./scripts/update_temporal_integration.py --tag=v1.19.0\n\n"
            "  # Update only METRIC_MAP:\n"
            "  python ./scripts/update_temporal_integration.py --tag=v1.19.0 --metrics-only\n\n"
            "  # Update only metadata.csv:\n"
            "  python ./scripts/update_temporal_integration.py --tag=v1.19.0 --metadata-only"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--tag", required=True, help="Temporal version tag to process (e.g., v1.19.0)")
    parser.add_argument(
        "--metrics-only", action="store_true", help="Only update METRIC_MAP, skip metadata.csv generation"
    )
    parser.add_argument(
        "--metadata-only", action="store_true", help="Only update metadata.csv, skip METRIC_MAP updates"
    )

    args = parser.parse_args()

    if args.metrics_only and args.metadata_only:
        args.metrics_only = False
        args.metadata_only = False
        print("INFO: Both --metrics-only and --metadata-only specified, updating both METRIC_MAP and metadata.csv")

    print(f"Updating Temporal integration for {args.tag}")

    try:
        # Fetch temporal metrics once (shared by both operations)
        source_go = fetch_temporal_metrics(args.tag)
        temporal_metric_types = extract_metric_defs(source_go)
        temporal_metrics = set(temporal_metric_types)

        metrics_updated = False

        # Update METRIC_MAP unless --metadata-only is specified
        if not args.metadata_only:
            metrics_updated = update_metrics_map(args.tag, temporal_metrics)

        # Update metadata.csv unless --metrics-only is specified
        if not args.metrics_only:
            # If we just updated METRIC_MAP, we need to reload it for metadata generation
            if metrics_updated:
                print("Reloading METRIC_MAP after updates...")
                try:
                    # Reload the metrics module to get the updated METRIC_MAP
                    import datadog_checks.temporal.metrics

                    importlib.reload(datadog_checks.temporal.metrics)

                    # Re-import the updated METRIC_MAP
                    from datadog_checks.temporal.metrics import METRIC_MAP as UPDATED_METRIC_MAP

                    # Update the global METRIC_MAP reference
                    global METRIC_MAP
                    METRIC_MAP = UPDATED_METRIC_MAP

                    print("Successfully reloaded METRIC_MAP with new metrics")
                    update_metadata_csv(args.tag, temporal_metric_types)

                except Exception as reload_error:
                    print(f"WARNING: Failed to reload METRIC_MAP: {reload_error}")
                    print("WARNING: Note: You may need to run the metadata update in a separate command")
                    print("   after reviewing and adjusting the new metric mappings.")
            else:
                update_metadata_csv(args.tag, temporal_metric_types)

        print(f"Successfully updated Temporal integration for {args.tag}")

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
