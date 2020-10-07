# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import defaultdict

import click
import yaml

from datadog_checks.dev.utils import read_file

from ...utils import get_jmx_metrics_file, get_valid_integrations, is_jmx_integration
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success


@click.command('jmx-metrics', context_settings=CONTEXT_SETTINGS, short_help='Validate JMX metrics files')
@click.option('--verbose', '-v', is_flag=True, help='Verbose mode')
def jmx_metrics(verbose):
    """Validate all default JMX metrics definitions."""

    echo_info("Validating all JMX metrics files...")

    saved_errors = defaultdict(list)
    integrations = sorted(check for check in get_valid_integrations() if is_jmx_integration(check))
    for check_name in integrations:
        jmx_metrics_file, file_exists = get_jmx_metrics_file(check_name)

        if not file_exists:
            saved_errors[check_name].append(f'{jmx_metrics_file} does not exist')
            continue

        jmx_metrics_data = yaml.safe_load(read_file(jmx_metrics_file)).get('jmx_metrics')

        if jmx_metrics_data is None:
            saved_errors[check_name].append(f'{jmx_metrics_file} does not have jmx_metrics definition')
            continue
        for rule in jmx_metrics_data:
            include = rule.get('include')
            include_str = truncate_message(str(include), verbose)
            rule_str = truncate_message(str(rule), verbose)

            if not include:
                saved_errors[check_name].append(f"missing include: {rule_str}")
                continue

            domain = include.get('domain')
            beans = include.get('bean')
            if (not domain) and (not beans):
                # Require `domain` or `bean` to be present,
                # that helps JMXFetch to better scope the beans to retrieve
                saved_errors[check_name].append(f"domain or bean attribute is missing for rule: {include_str}")

    for check_name, errors in saved_errors.items():
        if not errors:
            continue
        echo_info(f"{check_name}:")
        for err in errors:
            echo_failure(f"    - {err}")

    echo_info(f"{len(integrations)} total JMX integrations")
    echo_success(f"{len(integrations) - len(saved_errors)} valid metrics files")
    if saved_errors:
        echo_failure(f"{len(saved_errors)} invalid metrics files")
        abort()


def truncate_message(s, verbose):
    if not verbose:
        s = (s[:100] + '...') if len(s) > 100 else s
    return s
