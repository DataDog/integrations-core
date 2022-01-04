# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import os
import time
from copy import deepcopy

import mock
import pymysql
import pytest

from datadog_checks.cacti import CactiCheck

from .common import HERE

log = logging.getLogger()

MOCK_INFO = {
    'rra[6].cur_row': 556,
    'rra[5].cdp_prep[0].value': 21262.533333333333,
    'rra[6].pdp_per_row': 24,
    'rra[7].cur_row': 795,
    'ds[mem_buffers].value': 20376.0,
    'rra[4].cdp_prep[0].unknown_datapoints': 0,
    'rra[3].cdp_prep[0].unknown_datapoints': 177,
    'rra[7].pdp_per_row': 288,
    'rra[1].xff': 0.5,
    'rra[3].cur_row': 100,
    'rra[3].cdp_prep[0].value': 83282.52,
    'rra[2].cf': 'AVERAGE',
    'rra[4].cur_row': 454,
    'rra[2].cdp_prep[0].value': 83282.52,
    'ds[mem_buffers].minimal_heartbeat': 600,
    'rra[0].cdp_prep[0].unknown_datapoints': 0,
    'rra[5].cdp_prep[0].unknown_datapoints': 0,
    'ds[mem_buffers].type': 'GAUGE',
    'rra[1].pdp_per_row': 6,
    'rra[1].rows': 700,
    'rra[3].rows': 797,
    'rrd_version': '0003',
    'rra[7].xff': 0.5,
    'rra[6].rows': 775,
    'filename': '/var/lib/cacti/rra/localhost_mem_buffers_3.rrd',
    'rra[1].cf': 'AVERAGE',
    'last_update': 1484061001,
    'rra[5].rows': 700,
    'rra[4].xff': 0.5,
    'rra[0].cf': 'AVERAGE',
    'ds[mem_buffers].index': 0,
    'rra[4].cf': 'MAX',
    'rra[3].pdp_per_row': 288,
    'ds[mem_buffers].last_ds': '20376',
    'rra[7].cdp_prep[0].value': 21262.533333333333,
    'rra[2].xff': 0.5,
    'ds[mem_buffers].unknown_sec': 0,
    'rra[0].pdp_per_row': 1,
    'rra[7].rows': 797,
    'rra[0].cur_row': 42,
    'rra[6].xff': 0.5,
    'rra[4].pdp_per_row': 1,
    'header_size': 2040,
    'rra[5].pdp_per_row': 6,
    'rra[7].cf': 'MAX',
    'step': 300,
    'rra[3].xff': 0.5,
    'ds[mem_buffers].max': None,
    'rra[6].cdp_prep[0].unknown_datapoints': 9,
    'rra[4].cdp_prep[0].value': None,
    'ds[mem_buffers].min': 0.0,
    'rra[0].cdp_prep[0].value': None,
    'rra[1].cdp_prep[0].value': 41644.66666666667,
    'rra[1].cur_row': 234,
    'rra[0].rows': 600,
    'rra[6].cdp_prep[0].value': 21262.533333333333,
    'rra[5].cur_row': 194,
    'rra[4].rows': 600,
    'rra[3].cf': 'AVERAGE',
    'rra[0].xff': 0.5,
    'rra[5].cf': 'MAX',
    'rra[2].cdp_prep[0].unknown_datapoints': 9,
    'rra[5].xff': 0.5,
    'rra[2].cur_row': 742,
    'rra[6].cf': 'MAX',
    'rra[7].cdp_prep[0].unknown_datapoints': 177,
    'rra[1].cdp_prep[0].unknown_datapoints': 0,
    'rra[2].rows': 775,
    'rra[2].pdp_per_row': 24,
}

ts = int(time.time())
MOCK_FETCH = ((ts - 300, ts, 300), ('mem_buffers',), [(2048,), (None,)])

MOCK_RRD_META = [
    ('localhost', None, '/var/lib/cacti/rra/localhost_mem_buffers_3.rrd'),
    ('localhost', None, '/var/lib/cacti/rra/localhost_mem_swap_4.rrd'),
    ('localhost', None, '/var/lib/cacti/rra/localhost_load_1min_5.rrd'),
    ('localhost', None, '/var/lib/cacti/rra/localhost_users_6.rrd'),
    ('localhost', None, '/var/lib/cacti/rra/localhost_proc_7.rrd'),
]


CHECK_NAME = 'cacti'

CUSTOM_TAGS = ['optional:tag1']

CACTI_CONFIG = {'mysql_host': 'nohost', 'mysql_user': 'mocked', 'rrd_path': '/rrdtool/is/mocked', 'tags': CUSTOM_TAGS}


@pytest.fixture
def check():
    return CactiCheck(CHECK_NAME, {}, [CACTI_CONFIG])


pytestmark = pytest.mark.unit


def test_check(aggregator, check, dd_run_check):
    mocks = _setup_mocks()

    # Run the check twice to set the timestamps and capture metrics on the second run
    dd_run_check(check)
    dd_run_check(check)

    for mock_func in mocks:
        mock_func.stop()

    # We are mocking the MySQL call so we won't have cacti.rrd.count or cacti.hosts.count metrics,
    # check for metrics that are returned from our mock data.
    aggregator.assert_metric('cacti.metrics.count', value=10, tags=CUSTOM_TAGS)
    aggregator.assert_metric('system.mem.buffered.max', value=2, tags=CUSTOM_TAGS)
    aggregator.assert_metric('system.mem.buffered', value=2, tags=CUSTOM_TAGS)
    aggregator.assert_metric('cacti.rrd.count', value=5, tags=CUSTOM_TAGS)
    aggregator.assert_metric('cacti.hosts.count', value=1, tags=CUSTOM_TAGS)
    aggregator.assert_all_metrics_covered()


def test_whitelist(aggregator, dd_run_check):
    config = deepcopy(CACTI_CONFIG)
    config['rrd_whitelist'] = os.path.join(HERE, 'whitelist.txt')
    check = CactiCheck('cacti', {}, [config])

    mocks = _setup_mocks()

    # Run the check twice to set the timestamps and capture metrics on the second run
    dd_run_check(check)
    dd_run_check(check)

    for mock_func in mocks:
        mock_func.stop()

    # We are mocking the MySQL call so we won't have cacti.rrd.count or cacti.hosts.count metrics,
    # check for metrics that are returned from our mock data.
    aggregator.assert_metric('cacti.metrics.count', value=2, tags=CUSTOM_TAGS)
    aggregator.assert_metric('system.mem.buffered.max', value=2, tags=CUSTOM_TAGS)
    aggregator.assert_metric('system.mem.buffered', value=2, tags=CUSTOM_TAGS)
    aggregator.assert_metric('cacti.rrd.count', value=1, tags=CUSTOM_TAGS)
    aggregator.assert_metric('cacti.hosts.count', value=1, tags=CUSTOM_TAGS)
    aggregator.assert_all_metrics_covered()


@mock.patch.object(pymysql.connections.Connection, 'connect')
def test_default_port_config(mock_connect):
    config = deepcopy(CACTI_CONFIG)

    cacti = CactiCheck('cacti', {}, [config])
    connection = cacti._get_connection()

    assert connection.port == 3306


@mock.patch.object(pymysql.connections.Connection, 'connect')
def test_port_config_custom(mock_connect):
    config = deepcopy(CACTI_CONFIG)
    config['mysql_port'] = 3308

    cacti = CactiCheck('cacti', {}, [config])
    connection = cacti._get_connection()

    assert connection.port == 3308


def _setup_mocks():
    mock_conn = mock.MagicMock()
    mock_cursor = mock.MagicMock()

    mock_cursor.fetchall.return_value = MOCK_RRD_META
    mock_conn.cursor.return_value = mock_cursor

    mocks = [
        mock.patch('datadog_checks.cacti.cacti.rrdtool'),
        mock.patch('datadog_checks.cacti.cacti.pymysql.connect', return_value=mock_conn),
        mock.patch('datadog_checks.cacti.CactiCheck._get_rrd_info', return_value=MOCK_INFO),
        mock.patch('datadog_checks.cacti.CactiCheck._get_rrd_fetch', return_value=MOCK_FETCH),
    ]

    for mock_func in mocks:
        mock_func.start()
    return mocks
