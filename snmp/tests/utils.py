# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import contextlib
import errno
import os
from typing import Iterator  # noqa: F401

import mock

from datadog_checks.snmp import utils


@contextlib.contextmanager
def mock_profiles_confd_default_root(root):
    # type: (str) -> Iterator[None]
    with mock.patch.object(utils, '_get_profiles_confd_default_root', return_value=root):
        yield


@contextlib.contextmanager
def mock_profiles_confd_user_root(root):
    # type: (str) -> Iterator[None]
    with mock.patch.object(utils, '_get_profiles_confd_user_root', return_value=root):
        yield


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >= 2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        # possibly handle other errno cases here, otherwise finally:
        else:
            raise
