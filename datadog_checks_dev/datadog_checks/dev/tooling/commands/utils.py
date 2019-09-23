# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import functools

from datadog_checks.dev.tooling.commands.console import abort, echo_failure, echo_warning


def retry_command(func):
    """ Make command retryable

    Usage with click:

        @click.option('--retry', '-r', help='Number of retries on failure')
        @retryable
        def command():
            ...

    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        retry = kwargs.pop('retry')
        retry = 1 if retry is None else int(retry)
        if retry < 1:
            abort('\nRetry must be >= 1.', code=2)
        n = 1
        while True:
            try:
                return func(*args, **kwargs)
            except SystemExit as e:
                if n < retry:
                    echo_warning(
                        "\n[RETRY] Command \"{}\" failed. Start attempt {}/{} ...\n".format(func.__name__, n + 1, retry)
                    )
                else:
                    echo_failure("\n[RETRY] Command \"{}\" failed after {} attempts.\n".format(func.__name__, retry))
                    raise e
            n += 1

    return wrapper
