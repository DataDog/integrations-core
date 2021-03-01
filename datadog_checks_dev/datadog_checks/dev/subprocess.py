# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

import shlex
from collections import namedtuple
from subprocess import Popen
from tempfile import TemporaryFile

from six import string_types

from .errors import SubprocessError
from .utils import NEED_SHELL, ON_WINDOWS, mock_context_manager

SubprocessResult = namedtuple('SubprocessResult', ('stdout', 'stderr', 'code'))


def run_command(command, capture=None, check=False, encoding='utf-8', shell=False, env=None):
    """This function provides a convenient API wrapping subprocess.Popen. Captured output
    is guaranteed not to deadlock, but will still reside in memory in the end.

    :param command: The command to run in a subprocess.
    :type command: ``str`` or ``list`` of ``str``
    :param capture: The method of output capture:
                    stdout => 'stdout' or 'out'
                    stderr => 'stderr' or 'err'
                    both   => ``True`` or 'both'
                    none   => ``False`` or ``None``
    :type capture: ``bool`` or ``str``
    :param check: Whether or not to raise an exception on non-zero exit codes.
    :type check: ``bool``
    :param encoding: Method of decoding output.
    :type encoding: ``str``
    :param shell: Whether to use the shell as the program to execute. Use
                  'detect' to attempt the right thing in a cross-platform
                  manner. You should never need to use this argument.
    :type shell: ``bool`` or ``str``
    :param env: The environment to replace ``os.environ`` with in the subprocess.
    :type env: ``dict``
    """
    if shell == 'detect':
        shell = NEED_SHELL

    if isinstance(command, string_types) and not ON_WINDOWS:
        command = shlex.split(command)

    if capture:
        if capture is True or capture == 'both':
            stdout, stderr = TemporaryFile, TemporaryFile
        elif capture in ('stdout', 'out'):
            stdout, stderr = TemporaryFile, mock_context_manager
        elif capture in ('stderr', 'err'):
            stdout, stderr = mock_context_manager, TemporaryFile
        else:
            raise ValueError('Unknown capture method `{}`'.format(capture))
    else:
        stdout, stderr = mock_context_manager, mock_context_manager

    with stdout() as stdout, stderr() as stderr:
        process = Popen(command, stdout=stdout, stderr=stderr, shell=shell, env=env)
        process.wait()

        if stdout is None:
            stdout = ''
        else:
            stdout.seek(0)
            stdout = stdout.read().decode(encoding)

        if stderr is None:
            stderr = ''
        else:
            stderr.seek(0)
            stderr = stderr.read().decode(encoding)

    if check and process.returncode != 0:
        raise SubprocessError(
            'Command: {}\n' 'Exit code: {}\n' 'Captured Output: {}'.format(command, process.returncode, stdout + stderr)
        )

    return SubprocessResult(stdout, stderr, process.returncode)
