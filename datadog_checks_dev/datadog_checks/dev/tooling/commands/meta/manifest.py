# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import click

from ...manifest_validator.v2.migration import TODO_FILL_IN, migrate_manifest
from ...utils import get_valid_integrations
from ..console import CONTEXT_SETTINGS, abort, echo_info, echo_success


@click.group(context_settings=CONTEXT_SETTINGS, short_help='Manifest utilities')
def manifest():
    pass


@manifest.command(context_settings=CONTEXT_SETTINGS, short_help='Migrate a manifest to a newer schema version')
@click.argument('integration', required=True)
@click.argument('to_version', required=True)
@click.pass_context
def migrate(ctx, integration, to_version):
    """
    Helper tool to ease the migration of a manifest to a newer version, auto-filling fields when possible

    Inputs:

    integration: The name of the integration folder to perform the migration on

    to_version: The schema version to upgrade the manifest to
    """
    echo_info(f"Migrating {integration} manifest to {to_version}....", nl=True)

    # Perform input validations
    if integration and integration not in get_valid_integrations():
        abort(f'    Unknown integration `{integration}`, is your repo set properly in `ddev config`?')

    migrate_manifest(ctx.obj['repo_name'], integration, to_version)

    echo_success(
        f"Successfully migrated {integration} manifest to version {to_version}. Please update any needed fields, "
        f"especially those that are marked with `{TODO_FILL_IN}`"
    )
