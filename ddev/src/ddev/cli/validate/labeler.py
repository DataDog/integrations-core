# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import copy
from typing import TYPE_CHECKING

import click
import yaml

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command()
@click.option('--sync', is_flag=True, help='Update the labeler configuration')
@click.pass_obj
def labeler(app: Application, sync: bool):
    """Validate labeler configuration."""

    is_core = app.repo.name == 'core'

    if not is_core:
        app.display_info(
            f"The labeler validation is only enabled for integrations-core, skipping for repo {app.repo.name}"
        )
        return

    valid_integrations = dict.fromkeys(i.name for i in app.repo.integrations.iter("all"))
    # Remove this when we remove the `datadog_checks_tests_helper` package
    valid_integrations['datadog_checks_tests_helper'] = None

    pr_labels_config_path = app.repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml'
    if not pr_labels_config_path.exists():
        app.abort('Unable to find the PR Labels config file')

    pr_labels_config = yaml.safe_load(pr_labels_config_path.read_text())
    new_pr_labels_config = copy.deepcopy(pr_labels_config)

    tracker = app.create_validation_tracker('labeler')

    for label in pr_labels_config:
        if label.startswith('integration'):
            check_name = label.removeprefix('integration/')
            if check_name not in valid_integrations:
                if sync:
                    new_pr_labels_config.pop(label)
                    app.display_info(f'Removing `{label}` only found in labeler config')
                    continue
                message = f'Unknown check label `{label}` found in PR labels config'
                tracker.error((str(pr_labels_config_path),), message=message)

    # Check if valid integration has a label
    for check_name in valid_integrations:
        integration_label = f"integration/{check_name}"

        if integration_label not in pr_labels_config:
            if sync:
                new_pr_labels_config[integration_label] = [f'{check_name}/**/*']
                app.display_info(f'Adding config for `{check_name}`')
                continue

            message = f'Check `{check_name}` does not have an integration PR label'
            tracker.error((str(pr_labels_config_path),), message=message)
            continue

        # Check if label config is properly configured
        integration_label_config = pr_labels_config.get(integration_label)
        if integration_label_config != [f'{check_name}/**/*']:
            if sync:
                new_pr_labels_config[integration_label] = [f'{check_name}/**/*']
                app.display_info(f"Fixing label config for `{check_name}`")
                continue
            message = (
                f'Integration PR label `{integration_label}` is not properly configured: `{integration_label_config}`'
            )
            tracker.error((str(pr_labels_config_path),), message=message)

    if sync:
        output = yaml.safe_dump(new_pr_labels_config, default_flow_style=False, sort_keys=True)
        pr_labels_config_path.write_text(output)
        app.display_info(f'Successfully fixed {pr_labels_config_path}')

    tracker.display()

    if tracker.errors:  # no cov
        message = 'Try running `ddev validate labeler --sync`'
        app.display_info(message)
        app.abort()

    app.display_success('Labeler configuration is valid')
