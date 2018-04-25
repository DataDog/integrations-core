# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.ceph import Ceph

import os
import copy
import mock
import pytest
import simplejson as json

# Constants
CHECK_NAME = 'ceph'
HERE = os.path.abspath(os.path.dirname(__file__))
FIXTURE_DIR = os.path.join(HERE, 'fixtures')

BASIC_CONFIG = {
    'host': 'foo',
    'tags': ['optional:tag1'],
}

EXPECTED_TAGS = [
    'ceph_fsid:e0efcf84-e8ed-4916-8ce1-9c70242d390a',
    'ceph_mon_state:peon',
    'optional:tag1'
]
EXPECTED_METRICS = [
    'ceph.num_mons',
    'ceph.total_objects',
    'ceph.pgstate.active_clean'
]
EXPECTED_SERVICE_TAGS = ['optional:tag1']


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


def mock_data(file):
    filepath = os.path.join(FIXTURE_DIR, file)
    with open(filepath, "r") as f:
        data = f.read()
    return json.loads(data)


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("raw.json"))
def test_simple_metrics(_, aggregator):
    ceph_check = Ceph(CHECK_NAME, {}, {})
    ceph_check.check(copy.deepcopy(BASIC_CONFIG))

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(metric, count=1, tags=EXPECTED_TAGS)

    aggregator.assert_service_check('ceph.overall_status', status=Ceph.OK, tags=EXPECTED_SERVICE_TAGS)


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("warn.json"))
def test_warn_health(_, aggregator):
    ceph_check = Ceph(CHECK_NAME, {}, {})
    ceph_check.check(copy.deepcopy(BASIC_CONFIG))

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(metric, count=1, tags=EXPECTED_TAGS)

    aggregator.assert_service_check('ceph.overall_status', status=Ceph.WARNING, tags=EXPECTED_SERVICE_TAGS)


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("ceph_luminous_warn.json"))
def test_luminous_warn_health(_, aggregator):
    ceph_check = Ceph(CHECK_NAME, {}, {})
    config = copy.deepcopy(BASIC_CONFIG)
    config["collect_service_check_for"] = ['OSD_NEARFULL', 'OSD_FULL']
    ceph_check.check(config)

    aggregator.assert_service_check('ceph.overall_status', status=Ceph.CRITICAL, tags=EXPECTED_SERVICE_TAGS)
    aggregator.assert_service_check('ceph.osd_nearfull', status=Ceph.WARNING, tags=EXPECTED_SERVICE_TAGS)
    aggregator.assert_service_check('ceph.osd_full', status=Ceph.CRITICAL, tags=EXPECTED_SERVICE_TAGS)


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("ceph_luminous_ok.json"))
def test_luminous_ok_health(_, aggregator):

    ceph_check = Ceph(CHECK_NAME, {}, {})
    config = copy.deepcopy(BASIC_CONFIG)
    config["collect_service_check_for"] = ['OSD_NEARFULL']
    ceph_check.check(config)

    aggregator.assert_service_check('ceph.overall_status', status=Ceph.OK)
    aggregator.assert_service_check('ceph.osd_nearfull', status=Ceph.OK)
    aggregator.assert_service_check('ceph.pool_app_not_enabled', count=0)


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("ceph_luminous_warn.json"))
def test_luminous_osd_full_metrics(_, aggregator):

    ceph_check = Ceph(CHECK_NAME, {}, {})
    ceph_check.check(copy.deepcopy(BASIC_CONFIG))

    aggregator.assert_metric('ceph.num_full_osds', value=1)
    aggregator.assert_metric('ceph.num_near_full_osds', value=1)


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("raw.json"))
def test_tagged_metrics(_, aggregator):

    ceph_check = Ceph(CHECK_NAME, {}, {})
    ceph_check.check(copy.deepcopy(BASIC_CONFIG))

    for osd in ['osd0', 'osd1', 'osd2']:
        expected_tags = EXPECTED_TAGS + ['ceph_osd:%s' % osd]

        for metric in ['ceph.commit_latency_ms', 'ceph.apply_latency_ms']:
            aggregator.assert_metric(metric, count=1, tags=expected_tags)

    for pool in ['pool0', 'rbd']:
        expected_tags = EXPECTED_TAGS + ['ceph_pool:%s' % pool]

        for metric in ['ceph.read_bytes', 'ceph.write_bytes', 'ceph.pct_used', 'ceph.num_objects']:
            aggregator.assert_metric(metric, count=1, tags=expected_tags)


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("ceph_10.2.2.json"))
def test_osd_status_metrics(_, aggregator):

    ceph_check = Ceph(CHECK_NAME, {}, {})
    ceph_check.check(copy.deepcopy(BASIC_CONFIG))

    expected_metrics = [
        'ceph.read_op_per_sec',
        'ceph.write_op_per_sec',
        'ceph.op_per_sec'
    ]

    for osd, pct_used in [('osd1', 94), ('osd2', 95)]:
        expected_tags = EXPECTED_TAGS + ['ceph_osd:%s' % osd]
        aggregator.assert_metric('ceph.osd.pct_used', value=pct_used, count=1, tags=expected_tags)

    aggregator.assert_metric('ceph.num_full_osds', value=1, count=1, tags=EXPECTED_TAGS)
    aggregator.assert_metric('ceph.num_near_full_osds', value=1, count=1, tags=EXPECTED_TAGS)

    for pool in ['rbd', 'scbench']:
        expected_tags = EXPECTED_TAGS + ['ceph_pool:%s' % pool]
        for metric in expected_metrics:
            aggregator.assert_metric(metric, count=1, tags=expected_tags)


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("ceph_10.2.2_mon_health.json"))
def test_osd_status_metrics_non_osd_health(_, aggregator):
    """
    The `detail` key of `health detail` can contain info on the health of non-osd units:
    shouldn't make the check fail
    """

    ceph_check = Ceph(CHECK_NAME, {}, {})
    ceph_check.check(copy.deepcopy(BASIC_CONFIG))

    aggregator.assert_metric('ceph.num_full_osds', value=0, count=1, tags=EXPECTED_TAGS)
    aggregator.assert_metric('ceph.num_near_full_osds', value=0, count=1, tags=EXPECTED_TAGS)
