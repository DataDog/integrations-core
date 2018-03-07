# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

try:
    # Agent5
    from utils.subprocess_output import get_subprocess_output as subprocess_output
except ImportError:
    try:
        # Agent6
        from _util import get_subprocess_output as subprocess_output
    except ImportError:
        # No agent
        from ..stubs._util import subprocess_output

log = logging.getLogger(__name__)


def get_subprocess_output(command, log, raise_on_empty_output=True):
    """
    Run the given subprocess command and return its output. Raise an Exception
    if an error occurs.
    """

    cmd_args = []
    if isinstance(command, basestring):
        for arg in command.split():
            cmd_args.append(arg)
    elif hasattr(type(command), '__iter__'):
        for arg in command:
            cmd_args.append(arg)
    else:
        raise TypeError("command must be a sequence or string")

    log.debug("Running get_subprocess_output with cmd: %s", cmd_args)
    out, err, returncode = subprocess_output(cmd_args, raise_on_empty_output)
    log.debug("get_subprocess_output with cmd %s returned (len(out): %d ; len(err): %d ; returncode: %d)", cmd_args,
              len(out), len(err), returncode)

    return (out, err, returncode)
