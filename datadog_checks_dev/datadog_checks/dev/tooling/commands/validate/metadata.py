# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re
from collections import defaultdict

import click

from ...utils import (
    complete_valid_checks,
    get_metadata_file,
    get_metric_sources,
    load_manifest,
    normalize_display_name,
    read_metadata_rows,
)
from ..console import CONTEXT_SETTINGS, abort, echo_debug, echo_failure, echo_success, echo_warning

REQUIRED_HEADERS = {'metric_name', 'metric_type', 'orientation', 'integration'}

OPTIONAL_HEADERS = {'description', 'interval', 'unit_name', 'per_unit_name', 'short_name'}

ALL_HEADERS = REQUIRED_HEADERS | OPTIONAL_HEADERS

VALID_METRIC_TYPE = {'count', 'gauge', 'rate'}

VALID_ORIENTATION = {'0', '1', '-1'}

EXCLUDE_INTEGRATIONS = [
    'disk',
    'go-expvar',  # This has a special case externally
    'go-metro',
    'hdfs_datanode',
    'hdfs_namenode',
    'http',
    'kafka_consumer',
    'kubelet',
    'kubernetes',
    'kubernetes_api_server_metrics',
    'kubernetes_state',
    'mesos_master',
    'mesos_slave',
    'network',
    'ntp',
    'process',
    'riak_cs',
    'system_core',
    'system_swap',
    'tcp',
]

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
    'heap',
    'volume',
    'watt',
    'kilowatt',
    'megawatt',
    'gigawatt',
    'terawatt',
    'view',
    'microdollar',
    'euro',
    'pound',
    'penny',
    'yen',
    'milliwatt',
    'microwatt',
    'nanowatt',
    'ampere',
    'milliampere',
    'volt',
    'millivolt',
    'deciwatt',
    'decidegree celsius',
    'span',
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


def check_duplicate_values(current_check, line, row, header_name, duplicates, fail=None):
    """Check if the given column value has been seen before.
    Output a warning and return True if so.
    """
    if row[header_name] and row[header_name] not in duplicates:
        duplicates.add(row[header_name])
    elif row[header_name] != '':
        message = f"{current_check}:{line} `{row[header_name]}` is a duplicate {header_name}"
        if fail:
            echo_failure(message)
            return True
        else:
            echo_warning(message)
    return False


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate `metadata.csv` files')
@click.option(
    '--check-duplicates', is_flag=True, help='Output warnings if there are duplicate short names and descriptions'
)
@click.option('--show-warnings', '-w', is_flag=True, help='Show warnings in addition to failures')
@click.argument('check', autocompletion=complete_valid_checks, required=False)
def metadata(check, check_duplicates, show_warnings):
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

        display_name = manifest['display_name']

        metadata_file = get_metadata_file(current_check)
        echo_debug(f"Checking {metadata_file}")

        # To make logging less verbose, common errors are counted for current check
        metric_prefix_count = defaultdict(int)
        empty_count = defaultdict(int)
        empty_warning_count = defaultdict(int)
        duplicate_name_set = set()
        duplicate_short_name_set = set()
        duplicate_description_set = set()

        metric_prefix_error_shown = False
        if os.stat(metadata_file).st_size == 0:
            errors = True
            echo_failure(f"{current_check} metadata file is empty. This file needs the header row at minimum")

        for line, row in read_metadata_rows(metadata_file):
            # determine if number of columns is complete by checking for None values (DictReader populates missing columns with None https://docs.python.org/3.8/library/csv.html#csv.DictReader) # noqa
            if None in row.values():
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

            errors = errors or check_duplicate_values(
                current_check, line, row, 'metric_name', duplicate_name_set, fail=True
            )

            if check_duplicates:
                check_duplicate_values(current_check, line, row, 'short_name', duplicate_short_name_set)
                check_duplicate_values(current_check, line, row, 'description', duplicate_description_set)

            normalized_metric_name = normalize_metric_name(row['metric_name'])
            if row['metric_name'] != normalized_metric_name:
                errors = True
                echo_failure(
                    f"{current_check}:{line} Metric name '{row['metric_name']}' is not valid, "
                    f"it should be normalized as {normalized_metric_name}"
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

            # per_unit_name header
            if row['per_unit_name'] and row['per_unit_name'] not in VALID_UNIT_NAMES:
                errors = True
                echo_failure(f"{current_check}:{line} `{row['per_unit_name']}` is an invalid per_unit_name.")

            # integration header
            integration = row['integration']
            normalized_integration = normalize_display_name(display_name)
            if integration != normalized_integration and normalized_integration not in EXCLUDE_INTEGRATIONS:
                errors = True
                echo_failure(
                    f"{current_check}:{line} integration: `{row['integration']}` should be: {normalized_integration}"
                )

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

            elif "|" in row['description']:
                errors = True
                echo_failure(f"{current_check}:{line} `{row['metric_name']}` contains a `|`.")

            # check if there is unicode
            elif not (row['description'].isascii() and row['metric_name'].isascii() and row['metric_type'].isascii()):
                errors = True
                echo_failure(f"{current_check}:{line} `{row['metric_name']}` contains unicode characters.")

            # exceeds max allowed length of description
            elif len(row['description']) > MAX_DESCRIPTION_LENGTH:
                errors = True
                echo_failure(
                    f"{current_check}:{line} `{row['metric_name']}` exceeds the max length: "
                    f"{MAX_DESCRIPTION_LENGTH} for descriptions."
                )
            if row['interval'] and not row['interval'].isdigit():
                errors = True
                echo_failure(f"{current_check}:{line} interval should be an int, found '{row['interval']}'.")

        for header, count in empty_count.items():
            errors = True
            echo_failure(f'{current_check}: {header} is empty in {count} rows.')

        if show_warnings:
            for header, count in empty_warning_count.items():
                echo_warning(f'{current_check}: {header} is empty in {count} rows.')

            for prefix, count in metric_prefix_count.items():
                # Don't spam this warning when we're validating everything
                if check:
                    echo_warning(
                        f"{current_check}: `{prefix}` appears {count} time(s) and does not match metric_prefix "
                        "defined in the manifest."
                    )

    if errors:
        abort()

    echo_success('Validated!')
