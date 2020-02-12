# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

import click

from ....utils import running_on_ci
from ...e2e import create_interface, get_configured_checks, get_configured_envs, stop_environment
from ...e2e.agent import DEFAULT_SAMPLING_WAIT_TIME
from ...testing import complete_active_checks, complete_configured_envs
from ..console import CONTEXT_SETTINGS, DEFAULT_INDENT, abort, echo_failure, echo_info, echo_success, echo_waiting


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Stop environments.')
@click.argument('check', autocompletion=complete_active_checks)
@click.argument('env', autocompletion=complete_configured_envs, required=False)
def stop(check, env):
    """Stop environments, use "all" as check argument to stop everything."""
    all_checks = check == 'all'
    checks = get_configured_checks() if all_checks else [check]
    on_ci = running_on_ci()

    if all_checks:
        env_indent = DEFAULT_INDENT
        status_indent = DEFAULT_INDENT * 2
    else:
        env_indent = None
        status_indent = DEFAULT_INDENT

    for check in checks:
        if all_checks:
            envs = get_configured_envs(check)
            if envs:
                echo_success(f'{check}:')
        else:
            envs = [env] if env else get_configured_envs(check)

        for env in envs:
            echo_info(f'{env}:', indent=env_indent)
            environment = create_interface(check, env)

            if on_ci and 'sampling_start_time' in environment.metadata:
                start_time = environment.metadata['sampling_start_time']
                wait_time = environment.metadata.get('sampling_wait_time', DEFAULT_SAMPLING_WAIT_TIME)

                notice_displayed = False
                while time.time() - start_time < wait_time:
                    if not notice_displayed:
                        echo_waiting('Collecting samples... ', nl=False, indent=status_indent)
                        notice_displayed = True

                    time.sleep(1)

                if notice_displayed:
                    echo_success('success!')

            echo_waiting('Stopping the Agent... ', nl=False, indent=status_indent)
            environment.stop_agent()
            echo_success('success!')

            echo_waiting('Removing configuration files... ', nl=False, indent=status_indent)
            environment.remove_config()
            echo_success('success!')

            echo_waiting('Stopping the environment... ', nl=False, indent=status_indent)
            _, _, error = stop_environment(check, env, metadata=environment.metadata)
            if error:
                echo_failure('failed!')
                abort(error)
            echo_success('success!')
