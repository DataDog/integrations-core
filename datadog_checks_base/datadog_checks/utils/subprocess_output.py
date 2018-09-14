# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

from six import string_types

try:
    # Agent6
    from _util import get_subprocess_output as subprocess_output
    from _util import SubprocessOutputEmptyError  # noqa
except ImportError:
    try:
        # Agent5 (these paths may also exist in Agent6, so import them only if Agent6-specific ones aren't found)
        from utils.subprocess_output import subprocess_output
        from utils.subprocess_output import SubprocessOutputEmptyError  # noqa
    except ImportError:
        # No agent
        from ..stubs._util import subprocess_output
        from ..stubs._util import SubprocessOutputEmptyError  # noqa

log = logging.getLogger(__name__)


def get_subprocess_output(command, log, raise_on_empty_output=True):
    """
    Run the given subprocess command and return its output. Raise an Exception
    if an error occurs.

    :param command: The command to run. Using a list of strings is recommended. The command
                    will be run in a subprocess without using a shell, as such shell features like
                    shell pipes, wildcard expansion, environment variable expansion, etc., are
                    not supported.
    :type command: list(str) or str
    :param logging.Logger log: The log object to use
    :param bool raise_on_empty_output: Whether to raise a SubprocessOutputEmptyError exception when
                                       the subprocess doesn't output anything to its stdout.
    :returns: The stdout contents, stderr contents and status code of the command
    :rtype: tuple(str, str, int)
    """

    cmd_args = []
    if isinstance(command, string_types):
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
