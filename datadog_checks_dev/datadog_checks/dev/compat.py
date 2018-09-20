# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import six


if six.PY3:
    from json import JSONDecodeError
    from shutil import which

    FileNotFoundError = FileNotFoundError
    PermissionError = PermissionError
else:
    from distutils.spawn import find_executable as which

    JSONDecodeError = ValueError
    FileNotFoundError = IOError
    PermissionError = IOError
