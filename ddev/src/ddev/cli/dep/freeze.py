# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import click

from ddev.cli.dep.common import (
    read_check_dependencies,
    update_agent_dependencies,
)


@click.command()
@click.pass_obj
def freeze(app):
    """
    Combine all dependencies for the Agent's static environment.

    This reads and merges the dependency specs from individual integrations and writes them to agent_requirements.in
    """
    dependencies, errors = read_check_dependencies(app.repo)

    if errors:
        for error in errors:
            app.display_error(error)

        app.abort()

    app.display_info(f'Writing combined requirements to: {app.repo.agent_requirements}')
    update_agent_dependencies(app.repo, dependencies)
