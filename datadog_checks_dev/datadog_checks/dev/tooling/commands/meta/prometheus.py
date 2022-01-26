# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from collections import defaultdict
from itertools import product

import click
import pyperclip
import requests

from ....fs import dir_exists, path_join, write_file_lines
from ...constants import get_root
from ..console import CONTEXT_SETTINGS, abort, echo_info, echo_success, echo_waiting, echo_warning

METRIC_SEPARATORS = ('.', '_')
TYPE_MAP = {'gauge': 'gauge', 'counter': 'count', 'rate': 'gauge', 'histogram': 'gauge', 'summary': 'gauge'}
METADATA_CSV_HEADER = (
    'metric_name,metric_type,interval,unit_name,per_unit_name,description,orientation,integration,short_name'
)


def sanitize_endpoint(endpoint):
    if not endpoint.startswith('http'):
        endpoint = f"http://{'localhost' if endpoint.startswith(':') else ''}{endpoint}"

    return endpoint


def parse_metrics(endpoint):
    metrics = defaultdict(dict)
    response = requests.get(endpoint, stream=True)

    for line in response.iter_lines(decode_unicode=True):
        # Example:
        #
        # # HELP sql_insert_count Number of SQL INSERT statements
        # # TYPE sql_insert_count counter
        if line.startswith('#'):
            try:
                _, info_type, metric, info_value = line.split(' ', 3)
            except ValueError:
                continue

            if info_type == 'HELP':
                metrics[metric]['description'] = info_value.strip()
            elif info_type == 'TYPE':
                metrics[metric]['type'] = info_value.strip()

    return metrics


def get_options_text(options):
    return '\n{}\n' 'q - Quit'.format('\n'.join('{} - {}'.format(n, option) for n, option in enumerate(options, 1)))


@click.group(context_settings=CONTEXT_SETTINGS, short_help='Prometheus utilities')
def prom():
    pass


@prom.command(context_settings=CONTEXT_SETTINGS, short_help='Show metric info from a Prometheus endpoint')
@click.argument('endpoint')
def info(endpoint):
    """Show metric info from a Prometheus endpoint.

    \b
    Example:
    `$ ddev meta prom info :8080/_status/vars`
    """
    endpoint = sanitize_endpoint(endpoint)

    metrics = parse_metrics(endpoint)
    num_metrics = len(metrics)
    num_gauge = 0
    num_counter = 0
    num_histogram = 0

    for data in metrics.values():
        metric_type = data.get('type')

        if metric_type == 'gauge':
            num_gauge += 1
        elif metric_type == 'counter':
            num_counter += 1
        elif metric_type == 'histogram':
            num_histogram += 1

    if num_metrics:
        echo_success(f'Number of metrics: {num_metrics}')
    else:
        echo_warning('No metrics!')
        return

    if num_gauge:
        echo_info(f'Type `gauge`: {num_gauge}')

    if num_counter:
        echo_info(f'Type `counter`: {num_counter}')

    if num_histogram:
        echo_info(f'Type `histogram`: {num_histogram}')


@prom.command(
    context_settings=CONTEXT_SETTINGS,
    short_help='Interactively parse metric info from a Prometheus endpoint and write to metadata.csv',
)
@click.argument('endpoint')
@click.argument('check')
@click.option('--here', '-x', is_flag=True, help='Output to the current location')
@click.pass_context
def parse(ctx, endpoint, check, here):
    """Interactively parse metric info from a Prometheus endpoint and write it to metadata.csv."""
    if here:
        output_dir = os.getcwd()
    else:
        output_dir = path_join(get_root(), check)
        if not dir_exists(output_dir):
            abort(
                'Check `{check}` does not exist; try `ddev create{repo_flag} {check}`.'.format(
                    check=check, repo_flag=' -e' if ctx.obj['repo_choice'] == 'extras' else ''
                )
            )

    endpoint = sanitize_endpoint(endpoint)

    echo_waiting(f'Scraping `{endpoint}`...')
    metrics = parse_metrics(endpoint)
    num_metrics = len(metrics)

    echo_success('\nGlobally available options:')
    echo_info('    t - Append .total to the available options')
    echo_info('    s - Skip')
    echo_info('    q - Quit')

    for i, (metric, data) in enumerate(sorted(metrics.items()), 1):
        metric_parts = metric.split('_')
        metric_template = '{}'.join(metric_parts)
        num_separators = len(metric_parts) - 1

        metric_options = [
            metric_template.format(*possible_separators)
            for possible_separators in product(METRIC_SEPARATORS, repeat=num_separators)
        ]
        num_options = len(metric_options)

        default_option = num_options
        options_prompt = f'Choose an option (default {default_option}, as-is): '
        options_text = get_options_text(metric_options)

        finished = False
        choice_error = ''
        progress_status = f'({i} of {num_metrics}) '
        indent = ' ' * len(progress_status)

        while not finished:
            echo_success(f'\n{progress_status}{metric}')

            echo_success('Type: ', nl=False, indent=indent)
            echo_info(data.get('type', 'None'))

            echo_success('Info: ', nl=False, indent=indent)
            echo_info(data.get('description', 'None'))

            echo_info(options_text)

            if choice_error:
                echo_warning(choice_error)

            echo_waiting(options_prompt, nl=False)

            if num_options >= 9:
                choice = input()
            else:
                # Terminals are odd and sometimes produce an erroneous null byte
                choice = '\x00'
                while choice == '\x00':
                    choice = click.getchar().strip()

            if not choice:
                choice = default_option

            if choice == 't':
                echo_info('Append .total')
                for n in range(num_options):
                    metric_options[n] += '.total'
                options_text = get_options_text(metric_options)
                continue
            elif choice == 's':
                echo_info('Skip')
                echo_info(f'Skipped {metric}')
                break
            elif choice == 'q':
                echo_info('Exit')
                echo_warning(f'Exited at {metric}')
                return

            try:
                choice = int(choice)
            except Exception:
                pass

            if choice not in range(1, num_options + 1):
                echo_info(f'{choice}')
                choice_error = f'`{choice}` is not a valid option.'
                continue
            else:
                choice_error = ''

            option = metric_options[choice - 1]
            echo_info(option)

            data['dd_name'] = option

            finished = True

    metadata_file = path_join(output_dir, 'metadata.csv')
    echo_waiting(f'\nWriting `{metadata_file}`... ', nl=False)

    metric_items = sorted(metrics.items(), key=lambda item: item[1]['dd_name'])
    output_lines = [f'{METADATA_CSV_HEADER}\n']
    for _, data in metric_items:
        metric_name = data['dd_name']
        metric_type = TYPE_MAP.get(data.get('type'), '')
        metric_description = data.get('description', '')
        if ',' in metric_description:
            metric_description = f'"{metric_description}"'

        output_lines.append(
            '{check}.{metric_name},{metric_type},,,,{metric_description},0,{check},\n'.format(
                check=check, metric_name=metric_name, metric_type=metric_type, metric_description=metric_description
            )
        )

    write_file_lines(metadata_file, output_lines)
    echo_success('success!')

    metric_map = (
        'METRIC_MAP = {{\n'
        '{}\n'
        '}}'.format('\n'.join("    '{}': '{}',".format(metric, data['dd_name']) for metric, data in metric_items))
    )

    pyperclip.copy(metric_map)
    echo_success('\nThe metric map has been copied to your clipboard, paste it to any file you want!')
