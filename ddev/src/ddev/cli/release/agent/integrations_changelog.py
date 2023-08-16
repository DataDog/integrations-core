# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from collections import defaultdict
from io import StringIO

import click
from datadog_checks.dev.tooling.testing import complete_active_checks
from datadog_checks.dev.tooling.utils import get_valid_checks
from six import iteritems

from ddev.cli.release.agent.common import get_changes_per_agent

INTEGRATION_CHANGELOG_PATTERN = r'^## (\d+\.\d+\.\d+) / \d{4}-\d{2}-\d{2}$'


@click.command(
    short_help="Update integration CHANGELOG.md by adding the Agent version",
)
@click.argument('checks', shell_complete=complete_active_checks, nargs=-1)
@click.option('--since', help="Initial Agent version", default='6.3.0')
@click.option('--to', help="Final Agent version")
@click.option(
    '--write', '-w', is_flag=True, help="Write to the changelog file, if omitted contents will be printed to stdout"
)
@click.pass_obj
def integrations_changelog(app, checks, since, to, write):
    """
    Update integration CHANGELOG.md by adding the Agent version.

    Agent version is only added to the integration versions released with a specific Agent release.
    """

    # Process all checks if no check is passed
    if not checks:
        checks = get_valid_checks()

    changes_per_agent = get_changes_per_agent(app.repo, since, to)

    integrations_versions = defaultdict(dict)
    for agent_version, version_changes in changes_per_agent.items():
        for name, (ver, _) in version_changes.items():
            if name not in checks:
                continue
            integrations_versions[name][ver] = agent_version

    for check, versions in iteritems(integrations_versions):
        changelog_contents = StringIO()
        changelog_file = app.repo.integrations.get(check).path / 'CHANGELOG.md'

        for line in changelog_file.read_text().splitlines(keepends=True):
            match = re.search(INTEGRATION_CHANGELOG_PATTERN, line)
            if match:
                version = match.groups()[0]
                if version in versions:
                    agent_version = versions[version]
                    line = "{} / Agent {}\n".format(line.strip(), agent_version)
                else:
                    app.display_debug("Agent version not found for integration {} line {}".format(check, line.strip()))
            changelog_contents.write(line)

        # Save the changelog on disk if --write was passed
        if write:
            app.display_info("Writing to {}".format(changelog_file))
            (app.repo.integrations.get(check).path / changelog_file).write_text(changelog_contents.getvalue())
        else:
            print(changelog_contents.getvalue())
