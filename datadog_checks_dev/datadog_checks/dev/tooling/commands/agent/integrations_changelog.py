# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from collections import defaultdict
from io import StringIO

import click
from six import iteritems

from ....utils import read_file_lines, write_file
from ...constants import get_integration_changelog
from ...testing import complete_active_checks
from ...utils import get_valid_checks
from ..console import CONTEXT_SETTINGS, echo_debug, echo_info
from .common import get_changes_per_agent

INTEGRATION_CHANGELOG_PATTERN = r'^## (\d+\.\d+\.\d+) / \d{4}-\d{2}-\d{2}$'


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help="Update integration CHANGELOG.md by adding the Agent version",
)
@click.argument('checks', autocompletion=complete_active_checks, nargs=-1)
@click.option('--since', help="Initial Agent version", default='6.3.0')
@click.option('--to', help="Final Agent version")
@click.option(
    '--write', '-w', is_flag=True, help="Write to the changelog file, if omitted contents will be printed to stdout"
)
def integrations_changelog(checks, since, to, write):
    """
    Update integration CHANGELOG.md by adding the Agent version.

    Agent version is only added to the integration versions released with a specific Agent release.
    """

    # Process all checks if no check is passed
    if not checks:
        checks = get_valid_checks()

    changes_per_agent = get_changes_per_agent(since, to)

    integrations_versions = defaultdict(dict)
    for agent_version, version_changes in changes_per_agent.items():
        for name, (ver, _) in version_changes.items():
            if name not in checks:
                continue
            integrations_versions[name][ver] = agent_version

    for check, versions in iteritems(integrations_versions):
        changelog_contents = StringIO()
        changelog_file = get_integration_changelog(check)

        for line in read_file_lines(changelog_file):
            match = re.search(INTEGRATION_CHANGELOG_PATTERN, line)
            if match:
                version = match.groups()[0]
                if version in versions:
                    agent_version = versions[version]
                    line = "{} / Agent {}\n".format(line.strip(), agent_version)
                else:
                    echo_debug("Agent version not found for integration {} line {}".format(check, line.strip()))
            changelog_contents.write(line)

        # Save the changelog on disk if --write was passed
        if write:
            echo_info("Writing to {}".format(changelog_file))
            write_file(changelog_file, changelog_contents.getvalue())
        else:
            echo_info(changelog_contents.getvalue())
