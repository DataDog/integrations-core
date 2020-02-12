# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import csv
import re
from collections import defaultdict
from io import open

import click

from ...utils import complete_valid_checks, get_metadata_file, get_metric_sources, load_manifest
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_success, echo_warning

REQUIRED_HEADERS = {'metric_name', 'metric_type', 'orientation', 'integration'}

OPTIONAL_HEADERS = {'description', 'interval', 'unit_name', 'per_unit_name', 'short_name'}

ALL_HEADERS = REQUIRED_HEADERS | OPTIONAL_HEADERS

VALID_METRIC_TYPE = {'count', 'gauge', 'rate'}

VALID_ORIENTATION = {'0', '1', '-1'}

# To easily derive these again in future, copy the contents of `integration/system/units_catalog.csv` then run:
#
# pyperclip.copy('\n'.join("    '{}',".format(line.split(',')[2]) for line in pyperclip.paste().splitlines()))
VALID_UNIT_NAMES = {
    'name',
    'bit',
    'byte',
    'kibibyte',
    'mebibyte',
    'gibibyte',
    'tebibyte',
    'pebibyte',
    'exbibyte',
    'microsecond',
    'millisecond',
    'second',
    'minute',
    'hour',
    'day',
    'week',
    'fraction',
    'percent',
    'connection',
    'request',
    'process',
    'file',
    'buffer',
    'inode',
    'sector',
    'block',
    'packet',
    'segment',
    'response',
    'message',
    'payload',
    'core',
    'thread',
    'table',
    'index',
    'lock',
    'transaction',
    'query',
    'row',
    'hit',
    'miss',
    'eviction',
    'dollar',
    'cent',
    'error',
    'host',
    'node',
    'key',
    'command',
    'offset',
    'page',
    'read',
    'write',
    'occurrence',
    'event',
    'time',
    'unit',
    'operation',
    'item',
    'record',
    'object',
    'cursor',
    'assertion',
    'fault',
    'percent_nano',
    'get',
    'set',
    'scan',
    'nanosecond',
    'service',
    'task',
    'worker',
    'resource',
    'document',
    'shard',
    'flush',
    'merge',
    'refresh',
    'fetch',
    'garbage collection',
    'timeout',
    'hertz',
    'kilohertz',
    'megahertz',
    'gigahertz',
    'email',
    'datagram',
    'column',
    'apdex',
    'instance',
    'sample',
    'commit',
    'wait',
    'ticket',
    'split',
    'stage',
    'monitor',
    'location',
    'check',
    'question',
    'route',
    'session',
    'entry',
    'attempt',
    'cpu',
    'device',
    'update',
    'method',
    'job',
    'container',
    'execution',
    'throttle',
    'invocation',
    'user',
    'degree celsius',
    'degree fahrenheit',
    'success',
    'nanocore',
    'microcore',
    'millicore',
    'kilocore',
    'megacore',
    'gigacore',
    'teracore',
    'petacore',
    'exacore',
    'build',
    'prediction',
    'watt',
    'kilowatt',
    'megawatt',
    'gigawatt',
    'terawatt',
    'heap',
    'volume',
}

PROVIDER_INTEGRATIONS = {'openmetrics', 'prometheus'}

MAX_DESCRIPTION_LENGTH = 400

METRIC_REPLACEMENT = re.compile(r"([^a-zA-Z0-9_.]+)|(^[^a-zA-Z]+)")
METRIC_DOTUNDERSCORE_CLEANUP = re.compile(r"_*\._*")


def normalize_metric_name(metric_name):
    """Copy pasted from the backend normalization code.
    Extracted from dogweb/datalayer/metrics/query/metadata.py:normalize_metric_name
    Metrics in metadata.csv need to be formatted this way otherwise, syncing metadata will fail.
    Function not exported as a util, as this is different than AgentCheck.normalize. This function just makes sure
    that whatever is in the metadata.csv is understandable by the backend.
    """
    if not isinstance(metric_name, str):
        metric_name = str(metric_name)
    metric_name = METRIC_REPLACEMENT.sub("_", metric_name)
    return METRIC_DOTUNDERSCORE_CLEANUP.sub(".", metric_name).strip("_")


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate `metadata.csv` files')
@click.argument('check', autocompletion=complete_valid_checks, required=False)
def metadata(check):
    """Validates metadata.csv files

    If `check` is specified, only the check will be validated,
    otherwise all metadata files in the repo will be.
    """
    metric_sources = get_metric_sources()

    if check:
        if check not in metric_sources:
            abort(f'Metadata file `{get_metadata_file(check)}` does not exist.')
        metric_sources = [check]
    else:
        metric_sources = sorted(metric_sources)

    errors = False

    for current_check in metric_sources:
        if current_check.startswith('datadog_checks_'):
            continue

        # get any manifest info needed for validation
        manifest = load_manifest(current_check)
        try:
            metric_prefix = manifest['metric_prefix'].rstrip('.')
        except KeyError:
            metric_prefix = None

        metadata_file = get_metadata_file(current_check)

        # To make logging less verbose, common errors are counted for current check
        metric_prefix_count = defaultdict(int)
        empty_count = defaultdict(int)
        empty_warning_count = defaultdict(int)
        duplicate_set = set()
        metric_prefix_error_shown = False

        with open(metadata_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=',')

            # Read header
            reader._fieldnames = reader.fieldnames

            for line, row in enumerate(reader, 2):
                # Number of rows is correct. Since metric is first in the list, should be safe to access
                if len(row) != len(ALL_HEADERS):
                    errors = True
                    echo_failure(f"{current_check}:{line} {row['metric_name']} Has the wrong amount of columns")
                    continue

                # all headers exist, no invalid headers
                all_keys = set(row)
                if all_keys != ALL_HEADERS:
                    invalid_headers = all_keys.difference(ALL_HEADERS)
                    if invalid_headers:
                        errors = True
                        echo_failure(f'{current_check}:{line} Invalid column {invalid_headers}')

                    missing_headers = ALL_HEADERS.difference(all_keys)
                    if missing_headers:
                        errors = True
                        echo_failure(f'{current_check}:{line} Missing columns {missing_headers}')

                    continue

                # duplicate metric_name
                if row['metric_name'] and row['metric_name'] not in duplicate_set:
                    duplicate_set.add(row['metric_name'])
                else:
                    errors = True
                    echo_failure(f"{current_check}:{line} `{row['metric_name']}` is a duplicate metric_name")

                normalized_metric_name = normalize_metric_name(row['metric_name'])
                if row['metric_name'] != normalized_metric_name:
                    errors = True
                    echo_failure(
                        "Metric name '{}' is not valid, it should be normalized as {}".format(
                            row['metric_name'], normalized_metric_name
                        )
                    )

                # metric_name header
                if metric_prefix:
                    if not row['metric_name'].startswith(metric_prefix):
                        prefix = row['metric_name'].split('.')[0]
                        metric_prefix_count[prefix] += 1
                else:
                    errors = True
                    if not metric_prefix_error_shown and current_check not in PROVIDER_INTEGRATIONS:
                        metric_prefix_error_shown = True
                        echo_failure(f'{current_check}:{line} metric_prefix does not exist in manifest')

                # metric_type header
                if row['metric_type'] and row['metric_type'] not in VALID_METRIC_TYPE:
                    errors = True
                    echo_failure(f"{current_check}:{line} `{row['metric_type']}` is an invalid metric_type.")

                # unit_name header
                if row['unit_name'] and row['unit_name'] not in VALID_UNIT_NAMES:
                    errors = True
                    echo_failure(f"{current_check}:{line} `{row['unit_name']}` is an invalid unit_name.")

                # orientation header
                if row['orientation'] and row['orientation'] not in VALID_ORIENTATION:
                    errors = True
                    echo_failure(f"{current_check}:{line} `{row['orientation']}` is an invalid orientation.")

                # empty required fields
                for header in REQUIRED_HEADERS:
                    if not row[header]:
                        empty_count[header] += 1

                # empty description field, description is recommended
                if not row['description']:
                    empty_warning_count['description'] += 1
                # exceeds max allowed length of description
                elif len(row['description']) > MAX_DESCRIPTION_LENGTH:
                    errors = True
                    echo_failure(
                        '{}:{} `{}` exceeds the max length: {} for descriptions.'.format(
                            current_check, line, row['metric_name'], MAX_DESCRIPTION_LENGTH
                        )
                    )
                if row['interval'] and not row['interval'].isdigit():
                    errors = True
                    echo_failure('{}: interval should be an int, found "{}"'.format(current_check, row['interval']))

        for header, count in empty_count.items():
            errors = True
            echo_failure(f'{current_check}: {header} is empty in {count} rows.')

        for header, count in empty_warning_count.items():
            echo_warning(f'{current_check}: {header} is empty in {count} rows.')

        for prefix, count in metric_prefix_count.items():
            # Don't spam this warning when we're validating everything
            if check:
                echo_warning(
                    '{}: `{}` appears {} time(s) and does not match metric_prefix '
                    'defined in the manifest.'.format(current_check, prefix, count)
                )

    if errors:
        abort()

    echo_success('Validated!')
