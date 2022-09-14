# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from io import StringIO

import click

from ....fs import write_file
from ...constants import get_agent_changelog
from ...manifest_utils import Manifest
from ..console import CONTEXT_SETTINGS, abort, echo_info
from .common import get_changes_per_agent

# Extra entries in the agent changelog
CHANGELOG_MANUAL_ENTRIES = {
    '7.30.1': [
        '* Revert requests bump back to 2.22.0 [#9912](https://github.com/DataDog/integrations-core/pull/9912)',
    ]
}

DISPLAY_NAME_MAPPING = {
    # `Mesos` tile was migrated into `Mesos Slave`, so the display name must be manually changed
    'Mesos': 'Mesos Slave'
}


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help="Provide a list of updated checks on a given Datadog Agent version, in changelog form",
)
@click.option('--since', help="Initial Agent version", default='6.3.0')
@click.option('--to', help="Final Agent version")
@click.option(
    '--write', '-w', is_flag=True, help="Write to the changelog file, if omitted contents will be printed to stdout"
)
@click.option('--force', '-f', is_flag=True, default=False, help="Replace an existing file")
def changelog(since, to, write, force):
    """
    Generates a markdown file containing the list of checks that changed for a
    given Agent release. Agent version numbers are derived inspecting tags on
    `integrations-core` so running this tool might provide unexpected results
    if the repo is not up to date with the Agent release process.

    If neither `--since` or `--to` are passed (the most common use case), the
    tool will generate the whole changelog since Agent version 6.3.0
    (before that point we don't have enough information to build the log).
    """
    changes_per_agent = get_changes_per_agent(since, to)

    # store the changelog in memory
    changelog_contents = StringIO()

    # prepare the links
    agent_changelog_url = 'https://github.com/DataDog/datadog-agent/blob/master/CHANGELOG.rst#{}'
    check_changelog_url = 'https://github.com/DataDog/integrations-core/blob/master/{}/CHANGELOG.md'

    # go through all the agent releases
    for agent, version_changes in changes_per_agent.items():
        url = agent_changelog_url.format(agent.replace('.', ''))  # Github removes dots from the anchor
        changelog_contents.write(f'## Datadog Agent version [{agent}]({url})\n\n')

        if not version_changes and not CHANGELOG_MANUAL_ENTRIES.get(agent):
            changelog_contents.write('* There were no integration updates for this version of the Agent.\n\n')
        else:
            for entry in CHANGELOG_MANUAL_ENTRIES.get(agent, []):
                changelog_contents.write(f'{entry}\n')
            for name, ver in version_changes.items():
                manifest = Manifest.load_manifest(name)
                if manifest is None:
                    display_name = name
                else:
                    display_name = manifest.get_display_name()
                display_name = DISPLAY_NAME_MAPPING.get(display_name, display_name)

                breaking_notice = " **BREAKING CHANGE**" if ver[1] else ""
                changelog_url = check_changelog_url.format(name)
                changelog_contents.write(f'* {display_name} [{ver[0]}]({changelog_url}){breaking_notice}\n')
            # add an extra line to separate the release block
            changelog_contents.write('\n')

    # save the changelog on disk if --write was passed
    if write:
        dest = get_agent_changelog()
        # don't overwrite an existing file
        if os.path.exists(dest) and not force:
            msg = "Output file {} already exists, run the command again with --force to overwrite"
            abort(msg.format(dest))

        write_file(dest, changelog_contents.getvalue())
    else:
        echo_info(changelog_contents.getvalue())
