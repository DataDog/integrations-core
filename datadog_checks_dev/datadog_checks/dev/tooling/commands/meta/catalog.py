import click
from ..console import CONTEXT_SETTINGS, abort, echo_info
from ...utils import get_data_directory, get_config_file, get_assets_directory, get_check_file, \
    has_e2e, get_valid_integrations
import tempfile
import os
import csv

csv_columns = ['name', 'has_dashboard', 'has_logs', 'is_jmx', 'is_prometheus', 'is_http', 'has_e2e', 'tile_only']


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Create a catalog with information about integrations')
@click.argument('checks', nargs=-1, required=True)
@click.option('-f', '--file', 'out_file', required=False,
              help='Output to file, you can pass "tmp" to generate a temporary file')
def catalog(checks, out_file):
    if not out_file:
        fp = None
    elif out_file == 'tmp':
        tmp = tempfile.NamedTemporaryFile(prefix='integration_catalog', suffix='.csv', delete=False, mode='w')
        fp = tmp.file
        echo_info(f"Catalog is being saved to `{tmp.name}`")
    else:
        fp = open(out_file)
        echo_info(f"Catalog is being saved to `{out_file}`")

    checking_all = 'all' in checks
    valid_checks = get_valid_integrations()

    if not checking_all:
        for check in checks:
            if check not in valid_checks:
                abort(f'Check `{check}` is not an Agent-based Integration')
    else:
        checks = valid_checks

    catalog = []
    for check in checks:
        has_logs = False
        is_prometheus = False
        is_http = False
        tile_only = False

        config_file = get_config_file(check)
        if not os.path.exists(config_file):
            tile_only = True
        else:
            with open(config_file) as f:
                if '# logs:' in f.read():
                    has_logs = True

        check_file = get_check_file(check)
        if os.path.exists(check_file):
            with open(check_file) as f:
                contents = f.read()
                if '(OpenMetricsBaseCheck):' in contents:
                    is_prometheus = True
                if 'self.http.' in contents:
                    is_http = True

        entry = {
            'name': check,
            'has_dashboard': os.path.exists(os.path.join(get_assets_directory(check), 'dashboards')),
            'has_logs': has_logs,
            'is_jmx': os.path.exists(os.path.join(get_data_directory(check), 'metrics.yaml')),
            'is_prometheus': is_prometheus,
            'is_http': is_http,
            'has_e2e': has_e2e(check),
            'tile_only': tile_only
        }
        catalog.append(entry)

    if not fp:
        for entry in catalog:
            echo_info(str(entry))
    else:
        dict_to_csv(fp, catalog)


def dict_to_csv(csvfile, catalog: list):
    try:
        writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
        writer.writeheader()
        for entry in catalog:
            writer.writerow(entry)
        csvfile.close()
    except IOError:
        print("I/O error")
