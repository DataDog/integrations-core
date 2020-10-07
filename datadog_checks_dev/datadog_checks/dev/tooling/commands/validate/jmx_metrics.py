# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import defaultdict

import click
import yaml

from datadog_checks.dev.utils import read_file
from ...utils import get_eula_from_manifest, get_valid_integrations, get_jmx_metrics_file, get_config_file, \
    is_jmx_integration
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_debug


@click.command('jmx-metrics', context_settings=CONTEXT_SETTINGS, short_help='Validate JMX metrics files')
def jmx_metrics():
    """Validate all default JMX metrics definitions."""
    echo_info("Validating all JMX metrics files...")
    saved_errors = defaultdict(list)

    integrations = sorted(get_valid_integrations())
    for check_name in integrations:
        is_jmx = is_jmx_integration(check_name)
        if not is_jmx:
            echo_info("Skip non jmx integration: {}".format(check_name))
            continue

        jmx_metrics_file, file_exists = get_jmx_metrics_file(check_name)

        if not file_exists:
            echo_info(f'{check_name}... ', nl=False)
            saved_errors[check_name].append(f'  {jmx_metrics_file} does not exist')
            continue

        jmx_metrics_data = yaml.safe_load(read_file(jmx_metrics_file)).get('jmx_metrics')

        if jmx_metrics_data is None:
            saved_errors[check_name].append(f'  {jmx_metrics_file} does not have jmx_metrics definition')
            continue
        for rule in jmx_metrics_data:
            include = rule.get('include')
            exclude = rule.get('exclude')
        #     if include and exclude:

    for check_name, errors in saved_errors:
        echo_failure(check_name)
        for err in errors:
            echo_failure(f"    {err}")

    echo_success(f"{len(integrations) - len(saved_errors)} valid files")
    if saved_errors:
        echo_failure(f"{len(saved_errors)} invalid files")
        abort()
