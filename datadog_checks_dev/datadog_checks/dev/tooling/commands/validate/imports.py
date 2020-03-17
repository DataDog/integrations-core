# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import click

from ...constants import get_root
from ...utils import complete_valid_checks, get_valid_integrations
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_warning, echo_debug


# .base - error if not there, insert for fix
DEPRECATED_MODULES = set(
    [
        'datadog_checks.checks',
        'datadog_checks.checks.prometheus_check',
        'datadog_checks.checks.openmetrics',
        'datadog_checks.checks.openmetrics.mixins',
        'datadog_checks.checks.openmetrics.base_check',
        'datadog_checks.checks.win',
        'datadog_checks.checks.win.winpdh',
        'datadog_checks.checks.win.wmi',
        'datadog_checks.checks.win.wmi.counter_type',
        'datadog_checks.checks.win.wmi.sampler',
        'datadog_checks.checks.win.winpdh_base',
        'datadog_checks.checks.win.winpdh_stub',
        'datadog_checks.checks.libs',
        'datadog_checks.checks.libs.wmi',
        'datadog_checks.checks.libs.wmi.sampler',
        'datadog_checks.checks.libs.thread_pool',
        'datadog_checks.checks.libs.timer',
        'datadog_checks.checks.libs.vmware',
        'datadog_checks.checks.libs.vmware.basic_metrics',
        'datadog_checks.checks.libs.vmware.all_metrics',
        'datadog_checks.checks.network',
        'datadog_checks.checks.winwmi_check',
        'datadog_checks.checks.prometheus',
        'datadog_checks.checks.prometheus.mixins',
        'datadog_checks.checks.prometheus.prometheus_base',
        'datadog_checks.checks.prometheus.base_check',
        'datadog_checks.checks.base',
        'datadog_checks.checks.network_checks',
        'datadog_checks.config',
        'datadog_checks.errors',
        'datadog_checks.log',
        'datadog_checks.stubs',
        'datadog_checks.stubs.aggregator',
        'datadog_checks.stubs._util',
        'datadog_checks.stubs.datadog_agent',
        'datadog_checks.utils',
        'datadog_checks.utils.tracing',
        'datadog_checks.utils.proxy',
        'datadog_checks.utils.containers',
        'datadog_checks.utils.timeout',
        'datadog_checks.utils.tailfile',
        'datadog_checks.utils.platform',
        'datadog_checks.utils.common',
        'datadog_checks.utils.subprocess_output',
        'datadog_checks.utils.prometheus',
        'datadog_checks.utils.prometheus.functions',
        'datadog_checks.utils.prometheus.metrics_pb2',
        'datadog_checks.utils.headers',
        'datadog_checks.utils.limiter',
    ]
)


def validate_import(filepath):
    success = True
    lines = []

    with open(filepath) as f:
        for num, line in enumerate(f):
            if 'import' in line:
                # almost every case is of the form `from datadog_checks.. import ..`
                try:
                    parts = line.split('import', 1)[0].split()
                except Exception as e:
                    echo_warning(f'ERROR processing line: {line}')
                    continue

                for part in parts:
                    if 'datadog_checks' in part and part in DEPRECATED_MODULES:
                        success = False
                        lines.append((num, line))
    return success, lines


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate proper base imports')
@click.option('--include-extras', '-i', is_flag=True, help='Include optional fields')
@click.argument('check', autocompletion=complete_valid_checks, required=False)
@click.pass_context
def imports(ctx, check, include_extras):
    """Validate proper imports in checks."""

    integrations_root = get_root()

    validation_results = {}

    echo_info("Validating imports avoiding deprecated modules ...")
    for check_name in sorted(get_valid_integrations()):

        echo_debug(f'Checking {check_name}')
        for root, dirs, files in os.walk(os.path.join(integrations_root, check_name)):
            for i, d in enumerate(dirs):
                if d == '.tox':
                    dirs.pop(i)

            for f in files:
                if f.endswith('.py'):
                    fpath = os.path.join(root, f)
                    success, lines = validate_import(fpath)

                    if not success:
                        validation_results[fpath] = lines

    if validation_results:
        echo_warning(f'Validation failed:')
        for f, lines in validation_results.items():
            for line in lines:
                linenum, linetext = line
                echo_warning(f'{f}: line # {linenum}', indent='  ')
                echo_info(f'{linetext}', indent='    ')

        abort()

    else:
        echo_success('Validation passed!')







