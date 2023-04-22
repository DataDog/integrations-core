# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Script to update metadata.csv based on temporal's code and current
# `METRIC_MAP` as defined on metrics.py
# Must be run in an environment that has the integration installed,
# and passed the go code from temporal's codebase where metrics are defined via stdin, e.g.:
# cat ${path_to_temporal}/common/metrics/metric_defs.go | hatch run py3.8-1.19:python ./scripts/generate_metadata.py

import csv
import re
import sys

from datadog_checks.temporal.metrics import METRIC_MAP

temporal_metric_matcher = re.compile(r'New(?P<type>\w+)Def\("(?P<name>\w+)"\)')


def main():
    # First, read the existing metadata.csv to keep existing metadata from metrics for later
    with open('metadata.csv', newline='') as metadata_file:
        reader = csv.DictReader(metadata_file)
        metadata_fields = reader.fieldnames
        previous_metadata = {row['metric_name']: row for row in reader}

    # Then, read metrics from temporal's source code, fed through stdin
    # This file lives in /common/metrics/metric_defs.go inside temporal's repo
    parsed_metrics = (parse_temporal_metric(line) for line in sys.stdin.readlines())
    temporal_metric_types = {metric['name']: metric['type'] for metric in parsed_metrics if metric}

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
        metric_meta = {k: '' for k in metadata_fields}
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

    for temporal_name, name in METRIC_MAP.items():
        try:
            temporal_type = temporal_metric_types[temporal_name]
        except KeyError:
            print(f"WARNING: skipping metric `{temporal_name}/{name}` as it's not present in input data")
            continue

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


def parse_temporal_metric(line):
    match = temporal_metric_matcher.search(line)
    if match:
        return {k: v.lower() for k, v in match.groupdict().items()}


if __name__ == '__main__':
    main()
