# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from io import StringIO
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help="Generate a markdown file of integrations in an Agent release")
@click.option('--since', help="Initial Agent version", default='6.3.0')
@click.option('--to', help="Final Agent version")
@click.option('--write', '-w', is_flag=True, help="Write to file, if omitted contents will be printed to stdout")
@click.option('--force', '-f', is_flag=True, default=False, help="Replace an existing file")
@click.pass_obj
def integrations(app: Application, since: str, to: str, write: bool, force: bool):
    """
    Generates a markdown file containing the list of integrations shipped in a
    given Agent release. Agent version numbers are derived by inspecting tags on
    `integrations-core`, so running this tool might provide unexpected results
    if the repo is not up to date with the Agent release process.

    If neither `--since` nor `--to` are passed (the most common use case), the
    tool will generate the list for every Agent since version 6.3.0
    (before that point we don't have enough information to build the log).
    """
    from ddev.cli.release.agent.common import get_agent_tags, parse_agent_req_file

    agent_tags = get_agent_tags(app.repo, since, to)
    # get the list of integrations shipped with the agent from the requirements file
    req_file_name = app.repo.agent_release_requirements.name

    integrations_contents = StringIO()
    for tag in agent_tags:
        integrations_contents.write(f'## Datadog Agent version {tag}\n\n')
        # Requirements for current tag
        file_contents = app.repo.git.show_file(req_file_name, tag)
        for name, ver in parse_agent_req_file(file_contents).items():
            integrations_contents.write(f'* {name}: {ver}\n')
        integrations_contents.write('\n')

    # save the changelog on disk if --write was passed
    if write:
        dest = app.repo.agent_integrations_file
        # don't overwrite an existing file
        if dest.exists() and not force:
            msg = "Output file {} already exists, run the command again with --force to overwrite"
            app.abort(msg.format(dest))

        dest.write_text(integrations_contents.getvalue())
    else:
        app.display(integrations_contents.getvalue())
