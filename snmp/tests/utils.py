# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import contextlib
from typing import Iterator

import mock

from datadog_checks.snmp import utils


@contextlib.contextmanager
def mock_profiles_confd_root(root):
    # type: (str) -> Iterator[None]
    with mock.patch.object(utils, '_get_profiles_confd_root', return_value=root):
        yield
