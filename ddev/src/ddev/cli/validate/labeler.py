# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import copy
from typing import TYPE_CHECKING, cast

import click
import yaml
from rich.markup import escape

if TYPE_CHECKING:
    from ddev.cli.application import Application


def labeler_config_for_check(check: str) -> list[dict[str, list[dict[str, list[str]]]]]:
    return [{"changed-files": [{"any-glob-to-any-file": [f"{check}/**/*"]}]}]


def _extract_directory_from_config(config: list[dict]) -> str | None:
    try:
        return config[0]['changed-files'][0]['any-glob-to-any-file'][0].split('/')[0]
    except (IndexError, KeyError, TypeError, AttributeError):
        return None


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

    include = set(cast(list, app.repo.config.get('/overrides/validate/labeler/include', [])))
    for integration in include:
        valid_integrations[integration] = None

    pr_labels_config_path = app.repo.path / '.github' / 'workflows' / 'config' / 'labeler.yml'
    if not pr_labels_config_path.exists():
        app.abort('Unable to find the PR Labels config file')

    pr_labels_config = yaml.safe_load(pr_labels_config_path.read_text())
    new_pr_labels_config = copy.deepcopy(pr_labels_config)

    tracker = app.create_validation_tracker('labeler')

    # Build mapping from directory (in glob patterns) to label key
    directory_to_label: dict[str, str] = {}
    label_to_directory: dict[str, str] = {}
    for label, config in pr_labels_config.items():
        if not label.startswith('integration'):
            continue
        directory = _extract_directory_from_config(config)
        if directory and directory in valid_integrations:
            directory_to_label[directory] = label
            label_to_directory[label] = directory
        else:
            check_from_label = label.removeprefix('integration/')
            if check_from_label in valid_integrations:
                directory_to_label[check_from_label] = label
                label_to_directory[label] = check_from_label
            elif sync:
                new_pr_labels_config.pop(label)
                app.display_info(f'Removing `{label}` only found in labeler config')
            else:
                message = f'Unknown check label `{label}` found in PR labels config'
                tracker.error((str(pr_labels_config_path),), message=message)

    # Check if valid integration has a label
    for check_name in valid_integrations:
        expected_config = labeler_config_for_check(check_name)

        if check_name not in directory_to_label:
            integration_label = f"integration/{check_name}"
            if sync:
                if len(integration_label) > 50:
                    app.display_warning(
                        f"Integration label `{integration_label}` exceeds the 50 character limit "
                        f"({len(integration_label)} chars)"
                    )
                    max_tag_length = 50 - len("integration/")
                    integration_tag = click.prompt(
                        f'Enter a shorter integration name (max {max_tag_length} chars).'
                        'This tag is only used to label PRs.',
                        type=str,
                    )
                    if integration_tag.startswith('integration/'):
                        integration_tag = integration_tag.removeprefix('integration/')
                    integration_label = f"integration/{integration_tag}"
                    if len(integration_label) > 50:
                        message = (
                            f"Label `{integration_label}` is still too long ({len(integration_label)} chars), skipping"
                        )
                        tracker.error((str(pr_labels_config_path),), message=message)
                        continue
                if integration_label in label_to_directory:
                    existing_dir = label_to_directory[integration_label]
                    app.display_warning(
                        f"Cannot auto-add label `{integration_label}` for `{check_name}` "
                        f"because it is already used for directory `{existing_dir}`"
                    )
                    continue
                new_pr_labels_config[integration_label] = expected_config
                app.display_info(f'Adding config for `{check_name}`')
                continue

            if integration_label in label_to_directory:
                existing_dir = label_to_directory[integration_label]
                message = (
                    f'Check `{check_name}` does not have an integration PR label; '
                    f'label `{integration_label}` is already used for directory `{existing_dir}`'
                )
            else:
                message = f'Check `{check_name}` does not have an integration PR label'
            tracker.error((str(pr_labels_config_path),), message=message)
            continue

        # Check if label config is properly configured
        integration_label = directory_to_label[check_name]
        integration_label_config = pr_labels_config.get(integration_label)
        if integration_label_config != expected_config:
            if sync:
                new_pr_labels_config[integration_label] = expected_config
                app.display_info(f"Fixing label config for `{check_name}`")
                continue
            message = (
                f'Integration PR label `{integration_label}` is not properly configured: `{integration_label_config}`'
            )
            tracker.error((str(pr_labels_config_path),), message=message)

    if sync:
        output = yaml.safe_dump(new_pr_labels_config, default_flow_style=False, sort_keys=True)
        pr_labels_config_path.write_text(output)
        app.display_info(f'Successfully updated {pr_labels_config_path}')

    tracker.display()

    if tracker.errors:  # no cov
        message = (
            'To fix this, you can take one of the following actions based on whether the failure is related to '
            'an Agent check or not:\n'
            '\n'
            '* If it is an Agent check, run `ddev validate labeler --sync`.\n'
            '* If it is not an Agent check, you can mark it as such by adding '
            'it to the `[overrides.is-integration]` table in your `.ddev/config.toml` file.'
        )
        app.display_info(escape(message))
        app.abort()

    app.display_success('Labeler configuration is valid')
