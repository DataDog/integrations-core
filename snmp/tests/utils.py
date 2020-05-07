# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import contextlib
from typing import Iterator

import mock
import os

from .common import HERE
from datadog_checks.snmp import utils


@contextlib.contextmanager
def mock_profiles_confd_root(root):
    # type: (str) -> Iterator[None]
    with mock.patch.object(utils, '_get_profiles_confd_root', return_value=root):
        yield


def get_all_profiles():
    check_dir = os.path.dirname(HERE)
    profile_dir = os.path.join(check_dir, 'datadog_checks', 'snmp', 'data', 'profiles')
    print(profile_dir)
    profiles = []
    for filename in os.listdir(profile_dir):
        # This file is a testable profile
        if not filename.startswith('_'):
            profiles.append(filename.replace('.yaml', ''))
    print(profiles)
    return profiles
