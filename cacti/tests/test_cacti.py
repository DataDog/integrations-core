# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
import time

import mock
import pytest

from datadog_checks.cacti import Cacti

log = logging.getLogger()

MOCK_INFO = {
    'rra[6].cur_row': 556L,
    'rra[5].cdp_prep[0].value': 21262.533333333333,
    'rra[6].pdp_per_row': 24L,
    'rra[7].cur_row': 795L,
    'ds[mem_buffers].value': 20376.0,
    'rra[4].cdp_prep[0].unknown_datapoints': 0L,
    'rra[3].cdp_prep[0].unknown_datapoints': 177L,
    'rra[7].pdp_per_row': 288L,
    'rra[1].xff': 0.5,
    'rra[3].cur_row': 100L,
    'rra[3].cdp_prep[0].value': 83282.52,
    'rra[2].cf': 'AVERAGE',
    'rra[4].cur_row': 454L,
    'rra[2].cdp_prep[0].value': 83282.52,
    'ds[mem_buffers].minimal_heartbeat': 600L,
    'rra[0].cdp_prep[0].unknown_datapoints': 0L,
    'rra[5].cdp_prep[0].unknown_datapoints': 0L,
    'ds[mem_buffers].type': 'GAUGE',
    'rra[1].pdp_per_row': 6L,
    'rra[1].rows': 700L,
    'rra[3].rows': 797L,
    'rrd_version': '0003',
    'rra[7].xff': 0.5,
    'rra[6].rows': 775L,
    'filename': '/var/lib/cacti/rra/localhost_mem_buffers_3.rrd',
    'rra[1].cf': 'AVERAGE',
    'last_update': 1484061001L,
    'rra[5].rows': 700L,
    'rra[4].xff': 0.5,
    'rra[0].cf': 'AVERAGE',
    'ds[mem_buffers].index': 0L,
    'rra[4].cf': 'MAX',
    'rra[3].pdp_per_row': 288L,
    'ds[mem_buffers].last_ds': '20376',
    'rra[7].cdp_prep[0].value': 21262.533333333333,
    'rra[2].xff': 0.5,
    'ds[mem_buffers].unknown_sec': 0L,
    'rra[0].pdp_per_row': 1L,
    'rra[7].rows': 797L,
    'rra[0].cur_row': 42L,
    'rra[6].xff': 0.5,
    'rra[4].pdp_per_row': 1L,
    'header_size': 2040L,
    'rra[5].pdp_per_row': 6L,
    'rra[7].cf': 'MAX',
    'step': 300L,
    'rra[3].xff': 0.5,
    'ds[mem_buffers].max': None,
    'rra[6].cdp_prep[0].unknown_datapoints': 9L,
    'rra[4].cdp_prep[0].value': None,
    'ds[mem_buffers].min': 0.0,
    'rra[0].cdp_prep[0].value': None,
    'rra[1].cdp_prep[0].value': 41644.66666666667,
    'rra[1].cur_row': 234L,
    'rra[0].rows': 600L,
    'rra[6].cdp_prep[0].value': 21262.533333333333,
    'rra[5].cur_row': 194L,
    'rra[4].rows': 600L,
    'rra[3].cf': 'AVERAGE',
    'rra[0].xff': 0.5,
    'rra[5].cf': 'MAX',
    'rra[2].cdp_prep[0].unknown_datapoints': 9L,
    'rra[5].xff': 0.5,
    'rra[2].cur_row': 742L,
    'rra[6].cf': 'MAX',
    'rra[7].cdp_prep[0].unknown_datapoints': 177L,
    'rra[1].cdp_prep[0].unknown_datapoints': 0L,
    'rra[2].rows': 775L,
    'rra[2].pdp_per_row': 24L,
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

CACTI_CONFIG = {
    'mysql_host': 'nohost',
    'mysql_user': 'mocked',
    'rrd_path': '/rrdtool/is/mocked',
    'tags': CUSTOM_TAGS,
}


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture
def check():
    return Cacti(CHECK_NAME, {}, {})


def test_check(aggregator, check):
    mock_conn = mock.MagicMock()
    mock_cursor = mock.MagicMock()

    mock_cursor.fetchall.return_value = MOCK_RRD_META
    mock_conn.cursor.return_value = mock_cursor

    mocks = [
        mock.patch('datadog_checks.cacti.cacti.rrdtool'),
        mock.patch('datadog_checks.cacti.cacti.pymysql.connect', return_value=mock_conn),
        mock.patch('datadog_checks.cacti.Cacti._get_rrd_info', return_value=MOCK_INFO),
        mock.patch('datadog_checks.cacti.Cacti._get_rrd_fetch', return_value=MOCK_FETCH),
    ]

    for mock_func in mocks:
        mock_func.start()

    # Run the check twice to set the timestamps and capture metrics on the second run
    check.check(CACTI_CONFIG)
    check.check(CACTI_CONFIG)

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
