# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help='Stop an environment')
@click.argument('intg_name', metavar='INTEGRATION')
@click.argument('environment')
@click.option('--ignore-state', is_flag=True, hidden=True)
@click.pass_obj
def stop(app: Application, *, intg_name: str, environment: str, ignore_state: bool):
    """
    Stop environments. To stop all the running environments, use `all` as the integration name and the environment.
    """
    from ddev.e2e.agent import get_agent_interface
    from ddev.e2e.config import EnvDataStorage
    from ddev.e2e.constants import DEFAULT_AGENT_TYPE, E2EEnvVars, E2EMetadata
    from ddev.e2e.run import E2EEnvironmentRunner
    from ddev.utils.fs import temp_directory

    env_data_storage = EnvDataStorage(app.data_dir)

    if intg_name == 'all':
        integrations = env_data_storage.get_integrations()
    else:
        integrations = [intg_name]

    for integration_name in integrations:
        if environment == 'all':
            environments = [
                env
                for env in env_data_storage.get_environments(integration_name)
                if env_data_storage.get(integration_name, env).exists()
            ]
        else:
            environments = [environment]

        for env in environments:
            integration = app.repo.integrations.get(integration_name)
            env_data = env_data_storage.get(integration.name, env)
            runner = E2EEnvironmentRunner(env, app.verbosity)

            if not env_data.exists():
                app.abort(f'Environment `{env}` for integration `{integration.name}` is not running')
            elif ignore_state:
                continue

            app.display_header(f'Stopping: {integration_name}:{env}')

            # TODO: remove this required result file indicator once the E2E migration is complete
            with temp_directory() as temp_dir:
                result_file = temp_dir / 'result.json'
                env_vars = {E2EEnvVars.RESULT_FILE: str(result_file)}

                metadata = env_data.read_metadata()
                env_vars.update(metadata.get(E2EMetadata.ENV_VARS, {}))

                agent_type = metadata.get(E2EMetadata.AGENT_TYPE, DEFAULT_AGENT_TYPE)
                agent = get_agent_interface(agent_type)(app.platform, integration, env, metadata, env_data.config_file)

                try:
                    agent.stop()
                finally:
                    env_data.remove()

                    with integration.path.as_cwd(env_vars=env_vars), runner.stop() as command:
                        process = app.platform.run_command(command)
                        if process.returncode:
                            app.abort(code=process.returncode)
