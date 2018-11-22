# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ..utils import CONTEXT_SETTINGS, echo_info, echo_success
from ...e2e import get_configured_checks, get_configured_envs
from ...test import get_available_tox_envs
from ...utils import get_testable_checks


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help='List active or available environments'
)
@click.argument('checks', nargs=-1)
def ls(checks):
    """List active or available environments."""
    if checks:
        checks = sorted(get_testable_checks() & set(checks))

        for check in checks:
            envs = get_available_tox_envs(check, e2e_only=True)

            if envs:
                echo_success('{}:'.format(check))
                for env in envs:
                    echo_info(env, indent=True)

    else:
        for check in get_configured_checks():
            envs = get_configured_envs(check)

            if envs:
                echo_success('{}:'.format(check))
                for env in envs:
                    echo_info(env, indent=True)
