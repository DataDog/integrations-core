# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from ...subprocess import run_command
from .console import abort, echo_failure, echo_info, echo_success


def run_command_with_retry(retry, command, *args, **kwargs):
    """ Wrap run_command with retry.
        If retry is None. Will call transparently run_command.
    """
    if retry is None:
        return run_command(command, *args, **kwargs)

    if retry < 1:
        abort('\nRetry must be >= 1.', code=2)

    attempt = 1
    result = None
    while attempt <= retry:
        echo_info("[RETRY] Start attempt {}/{} ...".format(attempt, retry))

        result = run_command(command, *args, **kwargs)
        if result.code == 0:
            echo_success("[RETRY] Command \"{}\" succeeded.".format(command))
            break

        echo_failure("[RETRY] Command \"{}\" failed attempt {}/{}.".format(command, attempt, retry))
        attempt += 1

    return result
