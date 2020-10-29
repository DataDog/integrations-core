# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

from six import string_types

from .. import ensure_unicode

try:
    from _util import SubprocessOutputEmptyError  # noqa
    from _util import get_subprocess_output as subprocess_output
except ImportError:
    # No agent
    from ..stubs._util import SubprocessOutputEmptyError  # noqa
    from ..stubs._util import subprocess_output


log = logging.getLogger(__name__)


def get_subprocess_output(command, log, raise_on_empty_output=True, log_debug=True, env=None):
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
    :param bool log_debug: Whether to enable debug logging of full command.
    :param env: The environment variables to run the command with. If this parameter is set to None
                then, the environment variables of the agent are used. The default value is None.
    :type env: dict(str, str) or None
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
        raise TypeError('command must be a sequence or string')

    if log_debug:
        log.debug('Running get_subprocess_output with cmd: %s', cmd_args)

    out, err, returncode = subprocess_output(cmd_args, raise_on_empty_output, env=env)

    log.debug(
        'get_subprocess_output returned (len(out): %s ; len(err): %s ; returncode: %s)', len(out), len(err), returncode
    )

    out = ensure_unicode(out) if out is not None else None
    err = ensure_unicode(err) if err is not None else None

    return out, err, returncode
