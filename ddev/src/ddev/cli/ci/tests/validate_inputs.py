# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application

CONTEXT_PATTERN = re.compile(r'[a-z0-9][a-z0-9_-]*')


@click.command(short_help='Validate the inputs of a called Dispatcher run')
@click.option('--context', required=True, help='What the run is for, such as `nightly` or `test-agent`.')
@click.pass_obj
def validate_inputs(app: Application, context: str):
    """Validate the inputs a caller passed to `test-dispatch.yml`, before the run acquires
    credentials or dispatches anything.

    The context is forwarded as a single `context:VALUE` run tag and names the run's statuses and
    concurrency groups, so it must be one nonempty identifier: lowercase letters, digits, hyphens
    and underscores, starting with a letter or digit.
    """
    if not CONTEXT_PATTERN.fullmatch(context):
        app.abort(
            f'Invalid context {context!r}: use lowercase letters, digits, hyphens and underscores, '
            'starting with a letter or digit.'
        )
