# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
from datadog_checks.dev.tooling.commands.release.build import build
from datadog_checks.dev.tooling.commands.release.make import make
from datadog_checks.dev.tooling.commands.release.tag import tag
from datadog_checks.dev.tooling.commands.release.trello import trello
from datadog_checks.dev.tooling.commands.release.upload import upload

from ddev.cli.release.agent import agent
from ddev.cli.release.changelog import changelog
from ddev.cli.release.list_versions import list_versions
from ddev.cli.release.show import show
from ddev.cli.release.stats import stats


@click.group(short_help='Manage the release of integrations')
def release():
    """
    Manage the release of integrations.
    """


release.add_command(agent)
release.add_command(build)
release.add_command(changelog)
release.add_command(list_versions)
release.add_command(make)
release.add_command(show)
release.add_command(stats)
release.add_command(tag)
release.add_command(trello)
release.add_command(upload)
