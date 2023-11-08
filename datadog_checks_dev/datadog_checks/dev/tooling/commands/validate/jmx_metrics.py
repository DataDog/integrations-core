# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ast import literal_eval
from collections import defaultdict

import click
import yaml

from ...testing import process_checks_option
from ...utils import (
    complete_valid_checks,
    file_exists,
    get_default_config_spec,
    get_jmx_metrics_file,
    is_jmx_integration,
    read_file,
)
from ..console import CONTEXT_SETTINGS, abort, annotate_error, echo_failure, echo_info, echo_success


@click.command('jmx-metrics', context_settings=CONTEXT_SETTINGS, short_help='Validate JMX metrics files')
@click.argument('check', shell_complete=complete_valid_checks, required=False)
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
    try:
        # Load yaml config with custom constructor. The default loader overwrites duplicate keys:
        # https://github.com/yaml/pyyaml/issues/165
        yaml.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, no_duplicates_constructor)
        yaml.load(read_file(jmx_metrics_file), Loader=yaml.FullLoader).get('jmx_metrics')
    except Exception as errors:
        saved_errors[(check_name, jmx_metrics_file)].append("The config contains the following duplicates entries:")
        # Convert Exception -> String -> List
        errors = literal_eval(str(errors))
        for e in errors:
            saved_errors[(check_name, jmx_metrics_file)].append(f"{e[0]} on line {e[-1]}")

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
        domain_regex = include.get('domain_regex')
        beans = include.get('bean')
        if (not domain) and (not domain_regex) and (not beans):
            # Require `domain`, `domain_regex`, or `bean` to be present,
            # that helps JMXFetch to better scope the beans to retrieve
            saved_errors[(check_name, jmx_metrics_file)].append(
                f"domain, domain_regex or bean attribute is missing for rule: {include_str}"
            )

    duplicates = duplicate_bean_check(jmx_metrics_data)
    if duplicates:
        saved_errors[(check_name, jmx_metrics_file)].append(
            "The following bean and attribute combination is a duplicate:"
        )
        for k, v in duplicates.items():
            saved_errors[(check_name, jmx_metrics_file)].append(f"{k}: {v}")


def duplicate_bean_check(bean_list):
    bean_dict = defaultdict(list)
    duplicate_bean = defaultdict(list)
    for beans in bean_list:
        bean = beans.get("include").get("bean")
        if type(bean) == list:
            for b in bean:
                for attr in beans.get("include").get("attribute", {}).keys():
                    if attr in bean_dict[b]:
                        duplicate_bean[b].append(attr)
                    else:
                        bean_dict[b].append(attr)
        elif bean:
            for attr in beans.get("include").get("attribute", {}).keys():
                if attr in bean_dict[bean]:
                    duplicate_bean[bean].append(attr)
                else:
                    bean_dict[bean].append(attr)
    return dict(duplicate_bean)


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


# Modified version of:
# https://gist.github.com/pypt/94d747fe5180851196eb
def no_duplicates_constructor(loader, node, deep=False):
    """Check for duplicate keys."""

    mapping = {}
    errors = []
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        value = loader.construct_object(value_node, deep=deep)
        if key in mapping:
            errors.append([key, key_node.start_mark.line])
        mapping[key] = value
    if len(errors) > 0:
        raise Exception(errors)
    return loader.construct_mapping(node, deep)
