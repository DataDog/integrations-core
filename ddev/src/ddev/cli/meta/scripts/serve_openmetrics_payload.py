# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application

ENVIRONMENT_NAME = "serve-openmetrics-payload"
HERE = os.path.dirname(os.path.abspath(__file__))


@click.command(
    'serve-openmetrics-payload', short_help='Serve and collect metrics from an OpenMetrics file with a real Agent'
)
@click.argument('integration')
@click.argument('payload')
@click.pass_context
def serve_openmetrics_payload(ctx: click.Context, integration: str, payload: str):
    """Serve and collect metrics from an OpenMetrics file with a real Agent

    \b
    `$ ddev meta scripts serve-openmetrics-payload ray payload.txt`
    """

    import time
    from contextlib import suppress

    from ddev.cli.env.start import _get_agent_env_vars
    from ddev.cli.env.stop import stop
    from ddev.e2e.agent.docker import DockerAgent
    from ddev.e2e.config import EnvDataStorage

    app: Application = ctx.obj

    try:
        intg = app.repo.integrations.get(integration)
    except OSError:
        app.abort(f'Unknown target: {intg}')

    env_data = EnvDataStorage(app.data_dir).get(intg.name, ENVIRONMENT_NAME)

    if env_data.exists():
        app.abort(f'Environment `{ENVIRONMENT_NAME}` for integration `{intg.name}` is already running')

    config = {
        "init_config": {},
        'instances': [
            {
                "openmetrics_endpoint": "http://localhost:8080/metrics",
            }
        ],
    }

    metadata = {
        "docker_volumes": [
            f"{HERE}/scripts/serve.py:/tmp/serve.py",
            f"{os.path.join(os.getcwd(), payload)}:/tmp/metrics.txt",
        ]
    }

    env_data.write_config(config)
    env_data.write_metadata(metadata)

    agent = DockerAgent(app.platform, intg, ENVIRONMENT_NAME, metadata, env_data.config_file)
    agent_env_vars = _get_agent_env_vars(app.config.org.config, {}, {}, False)

    try:
        agent.start(agent_build="", local_packages={}, env_vars=agent_env_vars)
        app.display_info('Waiting 10 seconds...')
        time.sleep(10)
    except Exception as e:
        app.display_critical(f'Unable to start the Agent: {e}')
        app.abort()

    app.display_pair('Check status', app.style_info(f'ddev env agent {intg.name} {ENVIRONMENT_NAME} status'))
    app.display_pair('Trigger run', app.style_info(f'ddev env agent {intg.name} {ENVIRONMENT_NAME} check'))
    app.display_pair('Config file', f'[link={env_data.config_file}]{env_data.config_file}[/]')

    try:
        app.display_info('Starting the webserver... Use ctrl+c to stop it.')
        agent.run_command(['python', '/tmp/serve.py'])
    except Exception:
        app.display_info('Server stopped')

        with suppress(Exception):
            ctx.invoke(stop, intg_name=intg.name, environment=ENVIRONMENT_NAME)
