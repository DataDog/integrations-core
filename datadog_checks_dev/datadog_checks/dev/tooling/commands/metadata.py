# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import csv
from io import open

import click
from six import PY2, iteritems

from .utils import (
    CONTEXT_SETTINGS, abort, echo_failure, echo_warning
)
from ..utils import get_metadata_file, get_metric_sources, load_manifest

REQUIRED_HEADERS = {
    'metric_name',
    'metric_type',
    'description',
    'orientation',
    'integration',
    'short_name',
}

OPTIONAL_HEADERS = {
    'interval',
    'unit_name',
    'per_unit_name',
}

ALL_HEADERS = REQUIRED_HEADERS | OPTIONAL_HEADERS

VALID_METRIC_TYPE = {
    'count',
    'counter',
    'distribution',
    'gauge',
    'rate',
}

VALID_ORIENTATION = {
    '0',
    '1',
    '-1'
}

PROVIDER_INTEGRATIONS = {
    'openmetrics',
    'prometheus',
}


@click.group(
    context_settings=CONTEXT_SETTINGS,
    short_help='Manage metadata files'
)
def metadata():
    pass


@metadata.command(
    context_settings=CONTEXT_SETTINGS,
    short_help='Validate `metadata.csv` files'
)
@click.argument('check', required=False)
def verify(check):
    """Validates metadata.csv files

    If `check` is specified, only the check will be validated,
    otherwise all metadata files in the repo will be.
    """
    metric_sources = get_metric_sources()

    if check:
        if check not in metric_sources:
            abort(
                'Metadata file `{}` does not exist.'.format(get_metadata_file(check))
            )
        metric_sources = [check]
    else:
        metric_sources = sorted(metric_sources)

    for current_check in metric_sources:
        if current_check.startswith('datadog_checks_'):
            continue

        # get any manifest info needed for validation
        manifest = load_manifest(current_check)
        try:
            metric_prefix = manifest['metric_prefix']
        except KeyError:
            if current_check not in PROVIDER_INTEGRATIONS:
                echo_warning('{}: metric_prefix does not exist in manifest'.format(current_check))
            metric_prefix = None

        metadata_file = get_metadata_file(current_check)

        # To make logging less verbose, common errors are counted for current check
        metric_prefix_count = {}
        empty_count = {}
        duplicate_set = set()

        # Python 2 csv module does not support unicode
        with open(
            metadata_file,
            'rb' if PY2 else 'r',
            encoding=None if PY2 else 'utf-8',
        ) as f:
            reader = csv.DictReader(f, delimiter=',')

            if PY2:
                reader.fieldnames = [key.decode('utf-8') for key in reader.fieldnames]

            for row in reader:
                if PY2:
                    for key, value in iteritems(row):
                        if value is not None:
                            row[key] = value.decode('utf-8')

                # all headers exist, no invalid headers
                if set(row.keys()) != ALL_HEADERS:
                    invalid_headers = set(row.keys()).difference(ALL_HEADERS)
                    if invalid_headers:
                        echo_failure('{}: Invalid column {}'.format(current_check, invalid_headers))

                    missing_headers = ALL_HEADERS.difference(set(row.keys()))
                    if missing_headers:
                        echo_failure('{}: Missing columns {}'.format(current_check, missing_headers))

                    continue

                # duplicate metric_name
                if row['metric_name'] and row['metric_name'] not in duplicate_set:
                    duplicate_set.add(row['metric_name'])
                else:
                    echo_warning('{}: `{}` is a duplicate metric_name'.format(current_check, row['metric_name']))

                # metric_name header
                if metric_prefix and not row['metric_name'].startswith(metric_prefix):
                    prefix = row['metric_name'].rsplit('.')[0]
                    metric_prefix_count[prefix] = metric_prefix_count.get(prefix, 0) + 1

                # metric_type header
                if row['metric_type'] and row['metric_type'] not in VALID_METRIC_TYPE:
                    echo_warning('{}: `{}` is an invalid metric_type.'.format(current_check, row['metric_type']))

                # orientation header
                if row['orientation'] and row['orientation'] not in VALID_ORIENTATION:
                    echo_warning('{}: `{}` is an invalid orientation.'.format(current_check, row['orientation']))

                # empty required fields
                for header in REQUIRED_HEADERS:
                    if not row[header]:
                        empty_count[header] = empty_count.get(header, 0) + 1

        for header, count in empty_count.items():
            echo_warning('{}: {} is empty in {} rows.'.format(current_check, header, count))
        for prefix, count in metric_prefix_count.items():
            echo_warning(
                '{}: `{}` appears {} time(s) and does not match metric_prefix defined in the manifest'.format(
                    current_check, prefix, count))
