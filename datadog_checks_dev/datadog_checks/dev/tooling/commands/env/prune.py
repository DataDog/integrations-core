# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ...e2e.config import get_configured_checks, get_configured_envs, remove_env_data, remove_env_root
from ..console import CONTEXT_SETTINGS, abort, echo_info, echo_success, echo_waiting, echo_warning


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Remove all configuration for environments')
@click.option('--force', '-f', is_flag=True)
def prune(force):
    """Remove all configuration for environments."""
    if not force:
        echo_warning(
            'Removing configuration of environments that may be in use will leave '
            'them in a potentially unusable state. If you wish to proceed (e.g. you '
            'have just restarted your machine), you may use the -f / --force flag.'
        )
        abort(code=2)

    checks = get_configured_checks()
    for check in checks:
        envs = get_configured_envs(check)

        if envs:
            echo_info(f'{check}:')
            for env in envs:
                echo_waiting(f'Removing `{env}`... ', nl=False, indent=True)
                remove_env_data(check, env)
                echo_success('success!')

        remove_env_root(check)
