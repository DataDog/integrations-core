# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from io import StringIO

import click

from ....fs import write_file
from ...constants import get_agent_integrations_file, get_agent_release_requirements
from ...git import git_show_file
from ...utils import parse_agent_req_file
from ..console import CONTEXT_SETTINGS, abort, echo_info
from .common import get_agent_tags


@click.command(
    context_settings=CONTEXT_SETTINGS, short_help="Generate a markdown file of integrations in an Agent release"
)
@click.option('--since', help="Initial Agent version", default='6.3.0')
@click.option('--to', help="Final Agent version")
@click.option('--write', '-w', is_flag=True, help="Write to file, if omitted contents will be printed to stdout")
@click.option('--force', '-f', is_flag=True, default=False, help="Replace an existing file")
def integrations(since, to, write, force):
    """
    Generates a markdown file containing the list of integrations shipped in a
    given Agent release. Agent version numbers are derived inspecting tags on
    `integrations-core` so running this tool might provide unexpected results
    if the repo is not up to date with the Agent release process.

    If neither `--since` or `--to` are passed (the most common use case), the
    tool will generate the list for every Agent since version 6.3.0
    (before that point we don't have enough information to build the log).
    """
    agent_tags = get_agent_tags(since, to)
    # get the list of integrations shipped with the agent from the requirements file
    req_file_name = os.path.basename(get_agent_release_requirements())

    integrations_contents = StringIO()
    for tag in agent_tags:
        integrations_contents.write(f'## Datadog Agent version {tag}\n\n')
        # Requirements for current tag
        file_contents = git_show_file(req_file_name, tag)
        for name, ver in parse_agent_req_file(file_contents).items():
            integrations_contents.write(f'* {name}: {ver}\n')
        integrations_contents.write('\n')

    # save the changelog on disk if --write was passed
    if write:
        dest = get_agent_integrations_file()
        # don't overwrite an existing file
        if os.path.exists(dest) and not force:
            msg = "Output file {} already exists, run the command again with --force to overwrite"
            abort(msg.format(dest))

        write_file(dest, integrations_contents.getvalue())
    else:
        echo_info(integrations_contents.getvalue())
