# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from .common import (
    MOCK_DEVICE,
    MOCK_IB_COUNTER_DATA,
    MOCK_PORT,
    MOCK_RDMA_COUNTER_DATA,
)


@pytest.fixture
def instance():
    return {
        'tags': ['custom:tag'],
    }


def _is_valid_directory(path):
    return any(x in path for x in ['infiniband', 'ports', 'counters', 'hw_counters'])


def _get_directory_contents(path):
    if path.endswith('infiniband'):
        return [MOCK_DEVICE]
    elif 'ports' in path and not path.endswith(('counters', 'hw_counters')):
        return [MOCK_PORT]
    elif path.endswith('counters'):
        return list(MOCK_IB_COUNTER_DATA.keys())
    elif path.endswith('hw_counters'):
        return list(MOCK_RDMA_COUNTER_DATA.keys())
    return []


def _get_glob_matches(pattern):
    base_dir = os.path.dirname(pattern)
    if 'counters/*' in pattern and 'hw_counters' not in pattern:
        return [os.path.join(base_dir, f) for f in MOCK_IB_COUNTER_DATA.keys()]
    elif 'hw_counters/*' in pattern:
        return [os.path.join(base_dir, f) for f in MOCK_RDMA_COUNTER_DATA.keys()]
    return []


def _get_file_content(filename):
    counter = os.path.basename(filename)
    if counter in MOCK_IB_COUNTER_DATA:
        return MOCK_IB_COUNTER_DATA[counter]
    elif counter in MOCK_RDMA_COUNTER_DATA:
        return MOCK_RDMA_COUNTER_DATA[counter]
    return '0'


@pytest.fixture
def mock_fs():
    with mock.patch('os.path.exists') as mock_exists, mock.patch('os.path.isdir') as mock_isdir, mock.patch(
        'os.listdir'
    ) as mock_listdir, mock.patch('glob.glob') as mock_glob, mock.patch('builtins.open') as mock_open:

        mock_exists.return_value = True
        mock_isdir.side_effect = _is_valid_directory
        mock_listdir.side_effect = _get_directory_contents
        mock_glob.side_effect = _get_glob_matches
        mock_open.side_effect = lambda f, *args, **kwargs: mock.mock_open(read_data=_get_file_content(f))()

        yield


@pytest.fixture
def caplog(caplog):
    caplog.set_level("DEBUG")
    return caplog
