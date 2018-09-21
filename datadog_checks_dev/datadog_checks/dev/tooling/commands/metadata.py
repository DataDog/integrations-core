# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import csv

import click

from .utils import (
    CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_warning
)
from ..constants import get_root

from ..utils import load_manifest, get_valid_checks
from ...utils import file_exists, dir_exists, resolve_path

METADATA_FILE = 'metadata.csv'

REQUIRED_HEADERS = {
    'metric_name',
    'metric_type',
    'description',
    'orientation',
    'integration',
    'short_name'
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
    'rate'
}

VALID_ORIENTATION = {
    '0',
    '1',
    '-1'
}


@click.group(
    context_settings=CONTEXT_SETTINGS,
    short_help="Manage metadata files"
)
def metadata():
    pass


@metadata.command(
    context_settings=CONTEXT_SETTINGS,
    short_help='Validate `metadata.csv` files, takes optional `check` argument'
)
@click.argument('check', required=False)
@click.pass_context
def verify(ctx, check):
    """Validates metadata.csv files

    If `check` is specified, only the check will be validated, otherwise all matching files in directory.
    """
    check_list = []

    root = get_root()

    if check:
        path = resolve_path(os.path.join(root, check))
        if not dir_exists(path):
            abort(
                'Directory `{}` does not exist. Be sure to `ddev config set {repo} '
                'path/to/integrations-{repo}`.'.format(path, repo=ctx.obj['repo_choice'])
            )
        else:
            check_list = [check]
    else:
        check_list = [x for x in sorted(get_valid_checks())]

    for current_check in check_list:
        if current_check.startswith('datadog_checks_'):
            continue

        # get any manifest info needed for validation
        manifest = load_manifest(current_check)
        try:
            metric_prefix = manifest['metric_prefix']
        except KeyError:
            echo_info('{}: metric_prefix does not exist in manifest'.format(current_check))
            metric_prefix = None

        path = resolve_path(os.path.join(root, current_check, METADATA_FILE))
        if not file_exists(path):
            abort('Missing metadata file at: {}'.format(path))

        # To make logging less verbose, common errors are counted for current check
        metric_prefix_count = dict()
        empty_count = dict()
        duplicate_set = set()

        with open(path) as f:
            reader = csv.DictReader(f, delimiter=',')

            for row in reader:
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
                    echo_warning("{}: `{}` is a duplicate metric_name".format(current_check, row['metric_name']))

                # metric_name header
                if metric_prefix and not row['metric_name'].startswith(metric_prefix):
                    prefix = row['metric_name'].rsplit(".")[0]
                    metric_prefix_count[prefix] = metric_prefix_count.get(prefix, 0) + 1

                # metric_type header
                if row['metric_type'] and row['metric_type'] not in VALID_METRIC_TYPE:
                    echo_warning("{}: `{}` is an invalid metric_type.".format(current_check, row['metric_type']))

                # orientation header
                if row['orientation'] and row['orientation'] not in VALID_ORIENTATION:
                    echo_warning("{}: `{}` is an invalid orientation.".format(current_check, row['orientation']))

                # empty required fields
                for header in REQUIRED_HEADERS:
                    if not row[header]:
                        empty_count[header] = empty_count.get(header, 0) + 1

        for header, count in empty_count.items():
            echo_warning("{}: {} is empty in {} rows.".format(current_check, header, count))
        for prefix, count in metric_prefix_count.items():
            echo_warning(
                '{}: `{}` appears {} time(s) and does not match metric_prefix defined in the manifest'.format(
                    current_check, prefix, count))
