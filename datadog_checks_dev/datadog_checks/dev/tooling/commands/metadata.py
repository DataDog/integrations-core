# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import csv
from collections import defaultdict
from io import open

import click
from six import PY2, iteritems

from .utils import CONTEXT_SETTINGS, abort, echo_failure, echo_warning
from ..utils import get_metadata_file, get_metric_sources, load_manifest

REQUIRED_HEADERS = {
    'metric_name',
    'metric_type',
    'orientation',
    'integration',
}

OPTIONAL_HEADERS = {
    'description',
    'interval',
    'unit_name',
    'per_unit_name',
    'short_name',
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

        # Python 2 csv module does not support unicode
        with open(
            metadata_file,
            'rb' if PY2 else 'r',
            encoding=None if PY2 else 'utf-8',
        ) as f:
            reader = csv.DictReader(f, delimiter=',')

            # Read header
            if PY2:
                reader._fieldnames = [key.decode('utf-8') for key in reader.fieldnames]
            else:
                reader._fieldnames = reader.fieldnames

            for row in reader:
                if PY2:
                    for key, value in iteritems(row):
                        if value is not None:
                            row[key] = value.decode('utf-8')

                # all headers exist, no invalid headers
                all_keys = set(row)
                if all_keys != ALL_HEADERS:
                    invalid_headers = all_keys.difference(ALL_HEADERS)
                    if invalid_headers:
                        errors = True
                        echo_failure('{}: Invalid column {}'.format(current_check, invalid_headers))

                    missing_headers = ALL_HEADERS.difference(all_keys)
                    if missing_headers:
                        errors = True
                        echo_failure('{}: Missing columns {}'.format(current_check, missing_headers))

                    continue

                # duplicate metric_name
                if row['metric_name'] and row['metric_name'] not in duplicate_set:
                    duplicate_set.add(row['metric_name'])
                else:
                    errors = True
                    echo_failure('{}: `{}` is a duplicate metric_name'.format(current_check, row['metric_name']))

                # metric_name header
                if metric_prefix:
                    if not row['metric_name'].startswith(metric_prefix):
                        prefix = row['metric_name'].split('.')[0]
                        metric_prefix_count[prefix] += 1
                else:
                    errors = True
                    if not metric_prefix_error_shown and current_check not in PROVIDER_INTEGRATIONS:
                        metric_prefix_error_shown = True
                        echo_failure('{}: metric_prefix does not exist in manifest'.format(current_check))

                # metric_type header
                if row['metric_type'] and row['metric_type'] not in VALID_METRIC_TYPE:
                    errors = True
                    echo_failure('{}: `{}` is an invalid metric_type.'.format(current_check, row['metric_type']))

                # unit_name header
                if row['unit_name'] and row['unit_name'] not in VALID_UNIT_NAMES:
                    errors = True
                    echo_failure('{}: `{}` is an invalid unit_name.'.format(current_check, row['unit_name']))

                # orientation header
                if row['orientation'] and row['orientation'] not in VALID_ORIENTATION:
                    errors = True
                    echo_failure('{}: `{}` is an invalid orientation.'.format(current_check, row['orientation']))

                # empty required fields
                for header in REQUIRED_HEADERS:
                    if not row[header]:
                        empty_count[header] += 1

                # empty description field, description is recommended
                if not row['description']:
                    empty_warning_count['description'] += 1

        for header, count in iteritems(empty_count):
            errors = True
            echo_failure('{}: {} is empty in {} rows.'.format(current_check, header, count))

        for header, count in iteritems(empty_warning_count):
            echo_warning('{}: {} is empty in {} rows.'.format(current_check, header, count))

        for prefix, count in iteritems(metric_prefix_count):
            # Don't spam this warning when we're validating everything
            if check:
                echo_warning(
                    '{}: `{}` appears {} time(s) and does not match metric_prefix '
                    'defined in the manifest.'.format(current_check, prefix, count)
                )

    if errors:
        abort()
