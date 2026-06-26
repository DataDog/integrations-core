# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
``ddev ai`` command group.

Scaffolds integrations with an AI agent flow.
"""

from __future__ import annotations

import click

from ddev.cli.ai.openmetrics import openmetrics


@click.group(short_help='Build integrations with AI agents')
def ai():
    """Build integrations with AI agents."""


ai.add_command(openmetrics)
