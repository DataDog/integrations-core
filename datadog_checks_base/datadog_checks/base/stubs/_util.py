# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import subprocess
import tempfile


class SubprocessOutputEmptyError(Exception):
    pass


def subprocess_output(command, raise_on_empty_output):
    """
    This is a stub to allow a check requiring `Popen` to run without an Agent (e.g. during tests or development),
    it's not supposed to be used anywhere outside the `datadog_checks.utils` package.
    """

    # Use tempfile, allowing a larger amount of memory. The subprocess.Popen
    # docs warn that the data read is buffered in memory. They suggest not to
    # use subprocess.PIPE if the data size is large or unlimited.
    with tempfile.TemporaryFile() as stdout_f, tempfile.TemporaryFile() as stderr_f:
        proc = subprocess.Popen(command, stdout=stdout_f, stderr=stderr_f)
        proc.wait()
        stderr_f.seek(0)
        err = stderr_f.read()
        stdout_f.seek(0)
        output = stdout_f.read()

    if not output and raise_on_empty_output:
        raise SubprocessOutputEmptyError("get_subprocess_output expected output but had none.")

    return output, err, proc.returncode
