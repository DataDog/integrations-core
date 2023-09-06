# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ddev.cli.release.agent.changelog import changelog
from ddev.cli.release.agent.integrations import integrations
from ddev.cli.release.agent.integrations_changelog import integrations_changelog


@click.group(short_help='A collection of tasks related to the Datadog Agent')
def agent():
    """
    A collection of tasks related to the Datadog Agent.
    """


agent.add_command(changelog)
agent.add_command(integrations)
agent.add_command(integrations_changelog)
