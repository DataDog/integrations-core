# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import click

from ...utils import get_valid_integrations, has_legacy_signature
from ..console import CONTEXT_SETTINGS, echo_failure, echo_success


@click.command(
    'legacy-signature',
    context_settings=CONTEXT_SETTINGS,
    short_help='Validate that no integration uses the legacy signature',
)
def legacy_signature():
    """Validate that no integration uses the legacy signature."""
    integrations = get_valid_integrations()
    has_failed = False
    for integration in integrations:
        if has_legacy_signature(integration):
            echo_failure(f'Integration {integration} uses legacy agent signature.')
    if not has_failed:
        echo_success(f'All integrations use the new agent signature.')
    return
