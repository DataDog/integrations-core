# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import csv

import click

from .utils import (
    CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_waiting, echo_warning
)
from ..constants import get_root

from ..utils import load_manifest
from ...utils import file_exists, dir_exists, resolve_path

METADATA_FILE = 'metadata.csv'

CSV_HEADERS = {'metric_name',
               'metric_type',
               'interval',
               'unit_name',
               'per_unit_name',
               'description',
               'orientation',
               'integration',
               'short_name'
               }


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help="Validate metadata files"
)
@click.argument('check', required=False)
@click.pass_context
def validate(ctx, check):
    """Validates metadata.csv files

    If `check` is specified, only the check will be validated, otherwise all matching files in directory.
    """
    check_list = []

    root = get_root()

    if check:
        path = resolve_path(os.path.join(get_root(), check))
        if not dir_exists(path):
            abort(
                'Directory `{}` does not exist. Be sure to `ddev config set {repo} '
                'path/to/integrations-{repo}`.'.format(path, repo=ctx.obj['repo_choice'])
            )
        else:
            check_list = [check]
    else:
        check_list = [x for x in sorted(os.listdir(root))]

    for check in check_list:
        path = resolve_path(os.path.join(get_root(), check, METADATA_FILE))
        if file_exists(path):
            manifest = load_manifest(check)
            try:
                metric_prefix = manifest['metric_prefix']
            except KeyError:
                echo_warning('metric_prefix does not exist in {}'.format(check))
                metric_prefix = None

            if not file_exists(path):
                abort('Missing metadata file at: {}'.format(path))
            else:
                with open(path) as f:
                    reader = csv.DictReader(f, delimiter=',')
                    for row in reader:
                        if set(row.keys()) != CSV_HEADERS:
                            echo_warning('Invalid row in {}'.format(check))
                        if metric_prefix and not row['metric_name'].startswith(metric_prefix):
                            echo_warning('{}: {} does not match metric_prefix defined in the manifest'.format(check, row['metric_name']))

                        for header in CSV_HEADERS:
                            if header != 'metric_name' and not row[header]:
                                echo_warning("{}: {} is empty".format(check, header))
