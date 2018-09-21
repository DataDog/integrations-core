# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import six


if six.PY3:
    from json import JSONDecodeError

    FileNotFoundError = FileNotFoundError
    PermissionError = PermissionError
else:
    JSONDecodeError = ValueError
    FileNotFoundError = IOError
    PermissionError = IOError
