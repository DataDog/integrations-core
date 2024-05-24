# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import click

from ddev.cli.dep.common import (
    read_check_dependencies,
    update_agent_dependencies,
)


@click.command(short_help="Combine all dependencies for the Agent's static environment")
@click.pass_obj
def freeze(app):
    """Combine all dependencies for the Agent's static environment."""
    dependencies, errors = read_check_dependencies(app.repo)

    if errors:
        for error in errors:
            app.display_error(error)

        app.abort()

    app.display_info(f'Static file: {app.repo.agent_requirements}')
    update_agent_dependencies(app.repo, dependencies)
