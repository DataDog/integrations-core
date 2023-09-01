# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
from datadog_checks.dev.tooling.commands.release.show.changes import changes
from datadog_checks.dev.tooling.commands.release.show.ready import ready


@click.group(short_help='Show components of to-be released integrations')
def show():
    """To avoid GitHub's public API rate limits, you need to set
    `github.user`/`github.token` in your config file or use the
    `DD_GITHUB_USER`/`DD_GITHUB_TOKEN` environment variables.
    """


show.add_command(changes)
show.add_command(ready)
