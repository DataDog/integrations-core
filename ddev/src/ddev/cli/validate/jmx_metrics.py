# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from ast import literal_eval
from collections import defaultdict
from typing import TYPE_CHECKING, Any

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.integration.core import Integration


@click.command('jmx-metrics', short_help='Validate JMX metrics files')
@click.argument('check', required=False)
@click.option('--verbose', '-v', is_flag=True, help='Verbose mode')
@click.pass_obj
def jmx_metrics(app: Application, check: str | None, verbose: bool):
    """Validate all default JMX metrics definitions.

    If `check` is specified, only the check will be validated, if check value is 'changed' will only apply to changed
    checks, an 'all' or empty `check` value will validate all README files.
    """
    if check and check.lower() == 'changed':
        candidates = app.repo.integrations.iter_changed_code()
    else:
        selection: tuple[str, ...] = (check,) if check and check.lower() != 'all' else ()
        candidates = app.repo.integrations.iter(selection)
    integrations = sorted(
        (i for i in candidates if _is_jmx_integration(i)),
        key=lambda i: i.name,
    )
    app.display_info(f"Validating JMX metrics files for {len(integrations)} checks ...")

    saved_errors: dict[tuple[str, str | None], list[str]] = defaultdict(list)

    for integration in integrations:
        _validate_jmx_metrics(integration, saved_errors, verbose)
        _validate_config_spec(integration, saved_errors)

    for key, errors in saved_errors.items():
        if not errors:
            continue
        check_name, _ = key
        app.display_info(f"{check_name}:")
        for err in errors:
            app.display_error(f"    - {err}")

    app.display_info(f"{len(integrations)} total JMX integrations")
    app.display_success(f"{len(integrations) - len(saved_errors)} valid metrics files")
    if saved_errors:
        app.display_error(f"{len(saved_errors)} invalid metrics files")
        app.abort()


def _is_jmx_integration(integration: Integration) -> bool:
    import yaml

    config_file = (
        integration.path / 'datadog_checks' / integration.package_directory_name / 'data' / 'conf.yaml.example'
    )
    if not config_file.is_file():
        return False
    config_content = yaml.safe_load(config_file.read_text())
    if not config_content:
        return False
    init_config = config_content.get('init_config', None)
    if not init_config:
        return False
    return init_config.get('is_jmx', False)


def _validate_jmx_metrics(
    integration: Integration, saved_errors: dict[tuple[str, str | None], list[str]], verbose: bool
):
    import yaml

    check_name = integration.name
    jmx_metrics_file = str(integration.jmx_metrics_file)

    if not integration.jmx_metrics_file.is_file():
        saved_errors[(check_name, None)].append(f'{jmx_metrics_file} does not exist')
        return

    contents = integration.jmx_metrics_file.read_text()
    try:
        # Load yaml config with custom constructor. The default loader overwrites duplicate keys:
        # https://github.com/yaml/pyyaml/issues/165
        yaml.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicates_constructor)
        yaml.load(contents, Loader=yaml.FullLoader).get('jmx_metrics')
    except Exception as errors:
        saved_errors[(check_name, jmx_metrics_file)].append("The config contains the following duplicates entries:")
        # Convert Exception -> String -> List
        parsed = literal_eval(str(errors))
        for e in parsed:
            saved_errors[(check_name, jmx_metrics_file)].append(f"{e[0]} on line {e[-1]}")

    jmx_metrics_data = yaml.safe_load(contents).get('jmx_metrics')
    if jmx_metrics_data is None:
        saved_errors[(check_name, jmx_metrics_file)].append(f'{jmx_metrics_file} does not have jmx_metrics definition')
        return

    for rule in jmx_metrics_data:
        include = rule.get('include')
        include_str = _truncate_message(str(include), verbose)
        rule_str = _truncate_message(str(rule), verbose)

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

    duplicates = _duplicate_bean_check(jmx_metrics_data)
    if duplicates:
        saved_errors[(check_name, jmx_metrics_file)].append(
            "The following bean and attribute combination is a duplicate:"
        )
        for k, v in duplicates.items():
            saved_errors[(check_name, jmx_metrics_file)].append(f"{k}: {v}")


def _duplicate_bean_check(bean_list: list[dict[str, Any]]) -> dict[str, list[str]]:
    bean_dict: dict[str, list[str]] = defaultdict(list)
    duplicate_bean: dict[str, list[str]] = defaultdict(list)
    for beans in bean_list:
        bean = beans.get("include").get("bean")
        if isinstance(bean, list):
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


def _validate_config_spec(integration: Integration, saved_errors: dict[tuple[str, str | None], list[str]]):
    import yaml

    check_name = integration.name
    config_file = integration.config_spec
    config_file_str = str(config_file)

    if not config_file.is_file():
        saved_errors[(check_name, None)].append(f"config spec does not exist: {config_file_str}")
        return

    spec_files = yaml.safe_load(config_file.read_text()).get('files')
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
        saved_errors[(check_name, config_file_str)].append("config spec: does not use `init_config/jmx` template")
    if not instances_jmx:
        saved_errors[(check_name, config_file_str)].append("config spec: does not use `instances/jmx` template")


def _truncate_message(s: str, verbose: bool) -> str:
    if not verbose:
        s = (s[:100] + '...') if len(s) > 100 else s
    return s


# Modified version of:
# https://gist.github.com/pypt/94d747fe5180851196eb
def _no_duplicates_constructor(loader, node, deep: bool = False):
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
