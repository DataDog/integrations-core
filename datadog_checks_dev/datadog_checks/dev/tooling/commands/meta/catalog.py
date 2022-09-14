# (C) Datadog, Inc. 2020-present

import csv
import io
import os
import tempfile

import click

from ...utils import (
    complete_valid_checks,
    get_check_file,
    get_data_directory,
    get_testable_checks,
    get_valid_integrations,
    has_dashboard,
    has_e2e,
    has_logs,
    is_tile_only,
)
from ..console import CONTEXT_SETTINGS, abort, echo_info

CSV_COLUMNS = [
    'name',
    'has_dashboard',
    'has_logs',
    'is_jmx',
    'is_prometheus',
    'is_http',
    'has_e2e',
    'tile_only',
    'has_tests',
    'has_metadata',
]


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Create a catalog with information about integrations')
@click.argument('checks', nargs=-1, shell_complete=complete_valid_checks, required=True)
@click.option(
    '-f',
    '--file',
    'out_file',
    required=False,
    help='Output to file (it will be overwritten), you can pass "tmp" to generate a temporary file',
)
@click.option('--markdown', '-m', is_flag=True, help='Output to markdown instead of CSV')
def catalog(checks, out_file, markdown):
    if not out_file:
        fd = io.StringIO()
    elif out_file == 'tmp':
        # Default w+b mode does not work with CSV writer in python 3
        suffix = '.md' if markdown else '.csv'
        tmp = tempfile.NamedTemporaryFile(prefix='integration_catalog', suffix=suffix, delete=False, mode='w')
        fd = tmp.file
        echo_info(f"Catalog is being saved to `{tmp.name}`")
    else:
        fd = open(out_file, mode='w+')
        echo_info(f"Catalog is being saved to `{out_file}`")

    checking_all = 'all' in checks
    valid_checks = get_valid_integrations()
    testable_checks = get_testable_checks()

    if not checking_all:
        for check in checks:
            if check not in valid_checks:
                abort(f'Check `{check}` is not an Agent-based Integration')
    else:
        checks = valid_checks

    integration_catalog = []

    for check in sorted(checks):
        is_prometheus = False
        is_http = False
        has_metadata = False
        tile_only = is_tile_only(check)

        check_file = get_check_file(check)
        if os.path.exists(check_file):
            with open(check_file) as f:
                contents = f.read()
                if '(OpenMetricsBaseCheck):' in contents:
                    is_prometheus = True
                if 'self.http.' in contents:
                    is_http = True
                if 'self.set_metadata' in contents:
                    has_metadata = True

        entry = {
            'name': check,
            'has_dashboard': has_dashboard(check),
            'has_logs': has_logs(check),
            'is_jmx': os.path.exists(os.path.join(get_data_directory(check), 'metrics.yaml')),
            'is_prometheus': is_prometheus,
            'is_http': is_http,
            'has_e2e': has_e2e(check),
            'tile_only': tile_only,
            'has_tests': not tile_only and check in testable_checks,
            'has_metadata': has_metadata,
        }
        integration_catalog.append(entry)

    if markdown:
        dict_to_markdown(fd, integration_catalog)
    else:
        dict_to_csv(fd, integration_catalog)

    if not out_file:
        print(fd.getvalue())

    fd.close()


def dict_to_csv(buffer, contents: list):
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    for entry in contents:
        writer.writerow(entry)


def dict_to_markdown(buffer, contents: list):
    def write_line(row: list):
        return '| {} |\n'.format(' | '.join(row))

    buffer.write(write_line(CSV_COLUMNS))
    border = ['-' * len(name) for name in CSV_COLUMNS]
    buffer.write(write_line(border))

    for row in contents:
        ordered = [str(row.get(elem, '')) for elem in CSV_COLUMNS]
        buffer.write(write_line(ordered))
