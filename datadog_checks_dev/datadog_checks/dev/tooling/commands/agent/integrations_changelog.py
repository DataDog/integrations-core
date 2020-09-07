# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from io import StringIO

import click

from datadog_checks.dev.tooling.testing import complete_active_checks

from ....utils import read_file_lines, write_file
from ...constants import get_integration_changelog
from ...git import git_tag_list
from ...utils import get_valid_checks
from ..console import CONTEXT_SETTINGS, echo_debug, echo_info

EXCLUDED_CHECKS = {
    'datadog_checks_dev',
    'datadog_checks_downloader',
}
INTEGRATION_CHANGELOG_PATTERN = r'^## (\d+\.\d+\.\d+) / \d{4}-\d{2}-\d{2}$'
AGENT_TAG_PATTERN = r'^\d+\.\d+\.\d+$'


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help="Update integration change logs with first Agent version containing each integration release",
)
@click.argument('checks', autocompletion=complete_active_checks, nargs=-1)
@click.option(
    '--write', '-w', is_flag=True, help="Write to the changelog file, if omitted contents will be printed to stdout"
)
def integrations_changelog(checks, write):
    """
    Update integration change logs with first Agent version containing each integration release
    """

    # Process all checks if no check is passed
    if not checks:
        checks = sorted(set(get_valid_checks()) - EXCLUDED_CHECKS)

    for check in checks:
        changelog_contents = StringIO()
        changelog_file = get_integration_changelog(check)

        for line in read_file_lines(changelog_file):
            match = re.search(INTEGRATION_CHANGELOG_PATTERN, line)
            if match:
                version = match.groups()[0]
                release_tag = "{}-{}".format(check, version)
                tags = sorted(git_tag_list(pattern=AGENT_TAG_PATTERN, contains=release_tag))
                if tags:
                    # use the first agent version that include this release tag
                    first_agent_version = tags[0]
                    line = "{} / Agent {}\n".format(line.strip(), first_agent_version)
                else:
                    echo_debug("Agent version not found for integration {} line {}".format(check, line.strip()))
            changelog_contents.write(line)

        # save the changelog on disk if --write was passed
        if write:
            echo_info("Writing to {}".format(changelog_file))
            write_file(changelog_file, changelog_contents.getvalue())
        else:
            echo_info(changelog_contents.getvalue())
