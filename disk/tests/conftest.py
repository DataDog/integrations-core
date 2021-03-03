# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest

from datadog_checks.dev.utils import ON_WINDOWS, mock_context_manager

from .metrics import CORE_COUNTS, CORE_GAUGES, CORE_RATES, UNIX_GAUGES
from .mocks import (
    MockDiskIOMetrics,
    MockDiskMetrics,
    MockInodesMetrics,
    MockPart,
    mock_blkid_cache_file,
    mock_blkid_cache_file_no_label,
)


@pytest.fixture
def psutil_mocks():
    if ON_WINDOWS:
        mock_statvfs = mock_context_manager()
    else:
        mock_statvfs = mock.patch('os.statvfs', return_value=MockInodesMetrics(), __name__='statvfs')

    with mock.patch('psutil.disk_partitions', return_value=[MockPart()], __name__='disk_partitions'), mock.patch(
        'psutil.disk_usage', return_value=MockDiskMetrics(), __name__='disk_usage'
    ), mock.patch('psutil.disk_io_counters', return_value=MockDiskIOMetrics()), mock_statvfs:
        yield


@pytest.fixture(scope='session')
def dd_environment(instance_basic_volume):
    yield instance_basic_volume


@pytest.fixture(scope='session')
def instance_basic_volume():
    return {'use_mount': 'false', 'tag_by_label': False}


@pytest.fixture(scope='session')
def instance_basic_mount():
    return {'use_mount': 'true', 'tag_by_label': False}


@pytest.fixture(scope='session')
def instance_blkid_cache_file():
    return {'blkid_cache_file': mock_blkid_cache_file()}


@pytest.fixture(scope='session')
def instance_blkid_cache_file_no_label():
    return {'blkid_cache_file': mock_blkid_cache_file_no_label()}


@pytest.fixture(scope='session')
def gauge_metrics():
    if ON_WINDOWS:
        return CORE_GAUGES
    else:
        return UNIX_GAUGES


@pytest.fixture(scope='session')
def rate_metrics():
    return CORE_RATES


@pytest.fixture(scope='session')
def count_metrics():
    return CORE_COUNTS
