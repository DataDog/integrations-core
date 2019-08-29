# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ...e2e import get_configured_checks, get_configured_envs
from ...testing import get_available_tox_envs
from ...utils import get_testable_checks
from ..console import CONTEXT_SETTINGS, echo_info, echo_success, echo_warning


@click.command(context_settings=CONTEXT_SETTINGS, short_help='List active or available environments')
@click.argument('checks', nargs=-1)
def ls(checks):
    """List active or available environments."""
    if checks:
        testable_checks = get_testable_checks()

        for check in checks:
            if check not in testable_checks:
                echo_warning(
                    '{}: not a testable check. Skipped. Testable checks are: {}'.format(
                        check, ", ".join(testable_checks)
                    )
                )
                continue

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
