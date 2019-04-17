# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import json
from collections import OrderedDict

import click
from six import StringIO, iteritems

from .common import get_agent_tags
from ..console import CONTEXT_SETTINGS, abort, echo_info
from ...constants import get_root, get_agent_release_requirements, get_agent_changelog
from ...git import git_show_file
from ...release import get_folder_name, get_package_name, DATADOG_PACKAGE_PREFIX
from ...utils import parse_agent_req_file
from ....utils import write_file, read_file


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help="Provide a list of updated checks on a given Datadog Agent version, in changelog form"
)
@click.option('--since', help="Initial Agent version", default='6.3.0')
@click.option('--to', help="Final Agent version")
@click.option(
    '--write',
    '-w',
    is_flag=True,
    help="Write to the changelog file, if omitted contents will be printed to stdout"
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
    agent_tags = get_agent_tags(since, to)

    # store the changes in a mapping {agent_version --> {check_name --> current_version}}
    changes_per_agent = OrderedDict()

    # to keep indexing easy, we run the loop off-by-one
    for i in range(1, len(agent_tags)):
        req_file_name = os.path.basename(get_agent_release_requirements())
        current_tag = agent_tags[i - 1]
        # Requirements for current tag
        file_contents = git_show_file(req_file_name, current_tag)
        catalog_now = parse_agent_req_file(file_contents)
        # Requirements for previous tag
        file_contents = git_show_file(req_file_name, agent_tags[i])
        catalog_prev = parse_agent_req_file(file_contents)

        changes_per_agent[current_tag] = OrderedDict()

        for name, ver in iteritems(catalog_now):
            # at some point in the git history, the requirements file erroneusly
            # contained the folder name instead of the package name for each check,
            # let's be resilient
            old_ver = catalog_prev.get(name) \
                or catalog_prev.get(get_folder_name(name)) \
                or catalog_prev.get(get_package_name(name))

            # normalize the package name to the check_name
            if name.startswith(DATADOG_PACKAGE_PREFIX):
                name = get_folder_name(name)

            if old_ver and old_ver != ver:
                # determine whether major version changed
                breaking = old_ver.split('.')[0] < ver.split('.')[0]
                changes_per_agent[current_tag][name] = (ver, breaking)
            elif not old_ver:
                # New integration
                changes_per_agent[current_tag][name] = (ver, False)

    # store the changelog in memory
    changelog_contents = StringIO()

    # prepare the links
    agent_changelog_url = 'https://github.com/DataDog/datadog-agent/blob/master/CHANGELOG.rst#{}'
    check_changelog_url = 'https://github.com/DataDog/integrations-core/blob/master/{}/CHANGELOG.md'

    # go through all the agent releases
    for agent, version_changes in iteritems(changes_per_agent):
        url = agent_changelog_url.format(agent.replace('.', ''))  # Github removes dots from the anchor
        changelog_contents.write('## Datadog Agent version [{}]({})\n\n'.format(agent, url))

        if not version_changes:
            changelog_contents.write('* There were no integration updates for this version of the Agent.\n\n')
        else:
            for name, ver in iteritems(version_changes):
                # get the "display name" for the check
                manifest_file = os.path.join(get_root(), name, 'manifest.json')
                if os.path.exists(manifest_file):
                    decoded = json.loads(read_file(manifest_file).strip(), object_pairs_hook=OrderedDict)
                    display_name = decoded.get('display_name')
                else:
                    display_name = name

                breaking_notice = " **BREAKING CHANGE**" if ver[1] else ""
                changelog_url = check_changelog_url.format(name)
                changelog_contents.write(
                    '* {} [{}]({}){}\n'.format(display_name, ver[0], changelog_url, breaking_notice)
                )
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
