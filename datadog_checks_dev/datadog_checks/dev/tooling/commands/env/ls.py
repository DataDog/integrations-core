# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ...e2e import get_configured_checks, get_configured_envs
from ...testing import get_available_tox_envs
from ...utils import complete_testable_checks, get_testable_checks
from ..console import CONTEXT_SETTINGS, echo_info, echo_success, echo_warning


@click.command(context_settings=CONTEXT_SETTINGS, short_help='List active or available environments')
@click.argument('checks', nargs=-1, autocompletion=complete_testable_checks)
def ls(checks):
    """List active or available environments."""
    if checks:
        testable_checks = sorted(get_testable_checks() & set(checks))

        if not testable_checks:
            echo_warning(f"No testable checks found for: {', '.join(checks)}")

        for check in testable_checks:
            envs = get_available_tox_envs(check, e2e_only=True)

            if envs:
                echo_success(f'{check}:')
                for env in envs:
                    echo_info(env, indent=True)
            else:
                echo_warning(f'No envs found for check: {check}')

    else:
        found = False
        for check in get_configured_checks():
            envs = get_configured_envs(check)

            if envs:
                found = True
                echo_success(f'{check}:')
                for env in envs:
                    echo_info(env, indent=True)

        if not found:
            echo_warning('No envs found for configured checks')
