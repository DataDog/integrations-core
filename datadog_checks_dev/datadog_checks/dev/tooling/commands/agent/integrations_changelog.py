# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import re
from io import StringIO

import click

from ....utils import read_file, write_file, read_file_lines
from ...constants import get_agent_changelog, get_agent_release_requirements, get_root
from ...git import git_show_file, git_tag_list
from ...release import DATADOG_PACKAGE_PREFIX, get_folder_name, get_package_name
from ...utils import parse_agent_req_file, get_valid_checks
from ..console import CONTEXT_SETTINGS, abort, echo_info
from .common import get_agent_tags


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help="Update integration change logs with first Agent version containing each integration release",
)
@click.option(
    '--write', '-w', is_flag=True, help="Write to the changelog file, if omitted contents will be printed to stdout"
)
def integrations_changelog(write):
    """
    Update integration change logs with first Agent version containing each integration release
    """
    checks = sorted(get_valid_checks())
    # store the changelog in memory
    changelog_contents = StringIO()

    for check in checks:
        changelog_file = get_integration_changelog(check)
        for line in read_file_lines(changelog_file):
            match = re.search(r'## (\d\.\d\.\d) / \d{4}-\d{2}-\d{2}', line)
            if match:
                version = match.groups()[0]
                tag = "{}-{}".format(check, version)
                tag_list = sorted(git_tag_list(pattern=r"^\d+\.\d+\.\d+$", contains=tag))
                if tag_list:
                    first_agent_version = tag_list[0]
                    line = "{} / first included in Agent {}\n".format(line.strip(), first_agent_version)
            changelog_contents.write(line)

        # save the changelog on disk if --write was passed
        if write:
            write_file(changelog_file, changelog_contents.getvalue())
        else:
            echo_info(changelog_contents.getvalue())

        break  # TODO: remove me


def get_integration_changelog(check):
    return os.path.join(get_root(), check, 'CHANGELOG.md')
