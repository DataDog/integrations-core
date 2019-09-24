# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

from ...subprocess import run_command
from .console import abort, echo_failure, echo_success, echo_waiting


def run_command_with_retry(retry, command, *args, **kwargs):
    """ Wrap run_command with retry.

        If retry is None, we just forward the call to run_command.
        Otherwise, retry run_command until success or retry limit.
    """
    if retry is None:
        return run_command(command, *args, **kwargs)

    if retry < 1:
        abort('\nRetry must be >= 1.', code=2)

    result = None
    for i in range(retry):
        echo_prefix = "[RETRY] {}/{} - Command \"{}\": ".format(i + 1, retry, command)
        if i > 0:  # do not print on first attempt
            echo_waiting(echo_prefix + "Start...")

        result = run_command(command, *args, **kwargs)
        if result.code == 0:
            if i > 0:  # do not print on first attempt
                echo_success(echo_prefix + "Passed.")
            break

        echo_failure(echo_prefix + "Failed.")
        time.sleep(1)

    return result
