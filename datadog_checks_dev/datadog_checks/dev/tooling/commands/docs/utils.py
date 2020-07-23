# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def insert_verbosity_flag(command, verbosity):
    # One level is no tox flag
    if verbosity:
        verbosity -= 1
    # By default hide deps stage and success text
    else:
        verbosity -= 2

    if verbosity < 0:
        command.insert(1, f"-{'q' * abs(verbosity)}")
    elif verbosity > 0:
        command.insert(1, f"-{'v' * abs(verbosity)}")
