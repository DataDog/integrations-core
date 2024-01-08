# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application

INTEGRATION_CHANGELOG_PATTERN = r'^## (\d+\.\d+\.\d+) / \d{4}-\d{2}-\d{2}$'


@click.command(
    short_help="Update integration CHANGELOG.md by adding the Agent version",
)
@click.argument('integrations', nargs=-1)
@click.option('--since', help="Initial Agent version", default='6.3.0')
@click.option('--to', help="Final Agent version")
@click.option(
    '--write', '-w', is_flag=True, help="Write to the changelog file, if omitted contents will be printed to stdout"
)
@click.pass_obj
def integrations_changelog(app: Application, integrations: tuple[str], since: str, to: str, write: bool):
    """
    Update integration CHANGELOG.md by adding the Agent version.

    Agent version is only added to the integration versions released with a specific Agent release.
    """
    import re
    from collections import defaultdict
    from io import StringIO

    from ddev.cli.release.agent.common import get_changes_per_agent

    # Process all checks if no check is passed
    if not integrations:
        integrations = [integration.name for integration in app.repo.integrations.iter_all('all')]

    changes_per_agent = get_changes_per_agent(app.repo, since, to)

    integrations_versions: dict[str, dict[str, str]] = defaultdict(dict)
    for agent_version, version_changes in changes_per_agent.items():
        for name, (ver, _) in version_changes.items():
            if name not in integrations:
                continue
            integrations_versions[name][ver] = agent_version

    for integration, versions in integrations_versions.items():
        changelog_contents = StringIO()
        changelog_file = app.repo.integrations.get(integration).path / 'CHANGELOG.md'

        if not changelog_file.exists():
            continue

        for line in changelog_file.read_text().splitlines(keepends=True):
            match = re.search(INTEGRATION_CHANGELOG_PATTERN, line)
            if match:
                version = match.groups()[0]
                if version in versions:
                    agent_version = versions[version]
                    line = "{} / Agent {}\n".format(line.strip(), agent_version)
                else:
                    app.display_debug(
                        "Agent version not found for integration {} line {}".format(integration, line.strip())
                    )
            changelog_contents.write(line)

        # Save the changelog on disk if --write was passed
        if write:
            app.display_info("Writing to {}".format(changelog_file))
            changelog_file.write_text(changelog_contents.getvalue())
        else:
            print(changelog_contents.getvalue())
