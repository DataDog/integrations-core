# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Script to update metadata.csv based on temporal's code and current
# `METRIC_MAP` as defined on metrics.py
# Must be run in an environment that has the integration installed,
# and passed the tag of the temporal version from stdin, e.g.:
# hatch run py3.8-1.19:python ./scripts/generate_metadata.py --tag=v1.19.0

import csv
import re
import sys
import requests
import argparse
from urllib.parse import urljoin

from datadog_checks.temporal.metrics import METRIC_MAP



def main():
    """
    Generates and updates metadata.csv for the Temporal integration by:
    1. Reading existing metadata from metadata.csv
    2. Fetching and processing Temporal's metric definitions from the repository URL (e.g., https://raw.githubusercontent.com/temporalio/temporal/refs/tags/v1.19.0/common/metrics/metric_defs.go)
    3. Merging the data to create updated metadata
    4. Writing the results to metadata.csv

    Metric Converting Rule:
    - Counters: Adds .count suffix (e.g., service.pending_requests.count)
    - Gauges: Preserves original name with gauge type
    - Histograms: Creates three metrics per histogram:
        * .bucket: For histogram buckets
        * .count: For total count
        * .sum: For sum of values (with appropriate units)
    - Timers: Similar to histograms but with millisecond units
    - Native Dynamic Metrics: Added manually & preserved if already present in existing metadata

    Metadata Preservation:
    - Maintains existing metadata for metrics that were present in previous versions
    - Preserves custom configurations (units, descriptions, etc.) from existing metadata
    - Handles metrics that might have been dropped in newer Temporal versions
    - Ensures backward compatibility while incorporating new metric definitions
    """
    parser = argparse.ArgumentParser(description='Generate metadata.csv for Temporal integration')
    parser.add_argument('--tag', required=True, help='Temporal version tag (e.g., v1.19.0)')
    args = parser.parse_args()

    # First, read the existing metadata.csv to keep existing metadata from metrics for later
    with open('metadata.csv', newline='') as metadata_file:
        reader = csv.DictReader(metadata_file)
        metadata_fields = reader.fieldnames
        previous_metadata = {row['metric_name']: row for row in reader}

    # Fetch metrics from temporal's source code
    try:
        temporal_metrics = fetch_temporal_metrics(args.tag)
    except requests.RequestException as e:
        print(f"Error fetching metrics from Temporal repository: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Extract metric definitions from the fetched code
    temporal_metric_types = extract_metric_defs(temporal_metrics)

    # Sanity check: Check whether there are metrics in the temporal code that are not present
    # in the `METRIC_MAP` and warn about them:
    missing_metrics = set(temporal_metric_types) - set(METRIC_MAP)
    if missing_metrics:
        print("WARNING: the input code contains metrics not defined in `METRIC_MAP`:")
        print('\n'.join(f"- {metric}" for metric in missing_metrics))

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

    #  Build the metadata for the metrics that both lives in temporal's code and in the METRIC_MAP
    for temporal_name, name in METRIC_MAP.items():
        if isinstance(name, dict) and name.get('type') == 'native_dynamic':
            # Native dynamic metrics have its type defined at run time, and usually added manually, see https://github.com/DataDog/integrations-core/pull/18050
            existing, exist = check_existing_metric(name.get('name'), previous_metadata)
            if exist:
                print(f"INFO: dynamic metric `{name}` is reserved because it's present in the current metadata.csv file")
                metadata.extend(existing)
            else:
                print(f"WARNING: skipping metric `{name}` because native dynamic type and is not present in the current metadata.csv file")
            continue
            
        try:
            temporal_type = temporal_metric_types[temporal_name]
        except KeyError:
            # If metrics does not exist in this Temporal version, try to search metric in the current metadata file and preserve it if it's already exist
            existing, exist = check_existing_metric(name, previous_metadata)
            if exist:
                metadata.extend(existing)
            else:
                print(f"WARNING: skipping metric `{temporal_name}/{name}` because it's not present in both temporal metric definitions and the current metatada.csv file")
            continue

        # Update the metrics name based on the temporal type
        if temporal_type == 'counter':
            append_metric_metadata(f'{name}.count')
        elif temporal_type == 'gauge':
            append_metric_metadata(name, 'gauge')
        elif temporal_type.endswith('histogram'):
            unit_name = None
            if temporal_type == 'byteshistogram':
                unit_name = "byte"
            append_metric_metadata(f'{name}.bucket')
            append_metric_metadata(f'{name}.count')
            append_metric_metadata(f'{name}.sum', unit_name=unit_name)
        elif temporal_type == 'timer':
            append_metric_metadata(f'{name}.bucket')
            append_metric_metadata(f'{name}.count')
            append_metric_metadata(f'{name}.sum', unit_name='millisecond')
        else:
            print(f"Unrecognized metric type {temporal_type}, skipping.")

    # Write everything back to metadata.csv.
    with open('metadata.csv', 'w', newline='') as metadata_file:
        writer = csv.DictWriter(metadata_file, metadata_fields)
        writer.writeheader()
        writer.writerows(metadata)

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
    pattern = r'(\w+)\s*=\s*(New\w*Def)\s*\(\s*"([^"]+)"'

    # Find all matches in the code
    matches = re.finditer(pattern, go_code)

    for match in matches:
        func_name = match.group(2)
        metric_name = match.group(3)

        # Extract type from function name (everything between New and Def)
        type_name = func_name[3:-3]  # Remove "New" prefix and "Def" suffix

        results[metric_name.lower()] = type_name.lower()

    return results

added_keys = set()

def check_existing_metric(name: str, previous_metadata: dict) -> tuple[list, bool]:
    """
    Check if a metric exists in the previous metadata and add it to the current metadata if found.
    
    Args:
        name: The name of the metric to check, example of a metric name: service.pending_requests
        previous_metadata: Dictionary containing the previous metadata
        
    Returns:
        tuple: (metadata list with any existing metrics added, boolean indicating if metric exists)
    """
    pattern = re.compile(rf"^temporal\.server\.{re.escape(name)}(?:\.[a-z]+)*$")
    exist = False
    result = []
    for key in previous_metadata:
        if pattern.match(key) and key not in added_keys:
            # A metric were supported in the previous temporal version, but dropped in the current temporal version
            result.append(previous_metadata.get(key))
            print(f"INFO: {key} is reserved because it exists in the current metatadata.csv file")
            exist = True
            added_keys.add(key)
    return result, exist

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
    
    response = requests.get(url)
    response.raise_for_status()
    return response.text

if __name__ == '__main__':
    main()
