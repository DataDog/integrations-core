# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import defaultdict

import click
import yaml

from datadog_checks.dev.tooling.annotations import annotate_error
from datadog_checks.dev.utils import file_exists, read_file

from ...testing import process_checks_option
from ...utils import complete_valid_checks, get_default_config_spec, get_jmx_metrics_file, is_jmx_integration
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success


@click.command('jmx-metrics', context_settings=CONTEXT_SETTINGS, short_help='Validate JMX metrics files')
@click.argument('check', autocompletion=complete_valid_checks, required=False)
@click.option('--verbose', '-v', is_flag=True, help='Verbose mode')
def jmx_metrics(check, verbose):
    """Validate all default JMX metrics definitions.

    If `check` is specified, only the check will be validated, if check value is 'changed' will only apply to changed
    checks, an 'all' or empty `check` value will validate all README files.
    """

    checks = process_checks_option(check, source='integrations')
    integrations = sorted(check for check in checks if is_jmx_integration(check))
    echo_info(f"Validating JMX metrics files for {len(integrations)} checks ...")

    saved_errors = defaultdict(list)

    for check_name in integrations:
        validate_jmx_metrics(check_name, saved_errors, verbose)
        validate_config_spec(check_name, saved_errors)

    for key, errors in saved_errors.items():
        if not errors:
            continue
        check_name, filepath = key
        annotate_error(filepath, "\n".join(errors))
        echo_info(f"{check_name}:")
        for err in errors:
            echo_failure(f"    - {err}")

    echo_info(f"{len(integrations)} total JMX integrations")
    echo_success(f"{len(integrations) - len(saved_errors)} valid metrics files")
    if saved_errors:
        echo_failure(f"{len(saved_errors)} invalid metrics files")
        abort()


def validate_jmx_metrics(check_name, saved_errors, verbose):
    jmx_metrics_file, metrics_file_exists = get_jmx_metrics_file(check_name)

    if not metrics_file_exists:
        saved_errors[(check_name, None)].append(f'{jmx_metrics_file} does not exist')
        return

    jmx_metrics_data = yaml.safe_load(read_file(jmx_metrics_file)).get('jmx_metrics')
    if jmx_metrics_data is None:
        saved_errors[(check_name, jmx_metrics_file)].append(f'{jmx_metrics_file} does not have jmx_metrics definition')
        return

    for rule in jmx_metrics_data:
        include = rule.get('include')
        include_str = truncate_message(str(include), verbose)
        rule_str = truncate_message(str(rule), verbose)

        if not include:
            saved_errors[(check_name, jmx_metrics_file)].append(f"missing include: {rule_str}")
            return

        domain = include.get('domain')
        beans = include.get('bean')
        if (not domain) and (not beans):
            # Require `domain` or `bean` to be present,
            # that helps JMXFetch to better scope the beans to retrieve
            saved_errors[(check_name, jmx_metrics_file)].append(
                f"domain or bean attribute is missing for rule: {include_str}"
            )


def validate_config_spec(check_name, saved_errors):
    config_file = get_default_config_spec(check_name)

    if not file_exists(config_file):
        saved_errors[(check_name, None)].append(f"config spec does not exist: {config_file}")
        return

    spec_files = yaml.safe_load(read_file(config_file)).get('files')
    init_config_jmx = False
    instances_jmx = False

    for spec_file in spec_files:
        for base_option in spec_file.get('options', []):
            base_template = base_option.get('template')
            for option in base_option.get("options", []):
                template = option.get('template')
                if template == 'init_config/jmx' and base_template == 'init_config':
                    init_config_jmx = True
                elif template == 'instances/jmx' and base_template == 'instances':
                    instances_jmx = True

    if not init_config_jmx:
        saved_errors[(check_name, config_file)].append("config spec: does not use `init_config/jmx` template")
    if not instances_jmx:
        saved_errors[(check_name, config_file)].append("config spec: does not use `instances/jmx` template")


def truncate_message(s, verbose):
    if not verbose:
        s = (s[:100] + '...') if len(s) > 100 else s
    return s
