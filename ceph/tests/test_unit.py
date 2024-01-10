# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy

import mock
import pytest

from datadog_checks.ceph import Ceph

from .common import BASIC_CONFIG, CHECK_NAME, EXPECTED_SERVICE_TAGS, mock_data

EXPECTED_METRICS = [
    'ceph.num_mons',
    'ceph.total_objects',
    'ceph.pgstate.active_clean',
]

EXPECTED_METRICS_POOL_TAGS = [
    'ceph.read_bytes',
    'ceph.write_bytes',
    'ceph.pct_used',
    'ceph.num_objects',
    'ceph.misplaced_objects',
    'ceph.misplaced_total',
    'ceph.recovering_objects_per_sec',
    'ceph.recovering_bytes_per_sec',
    'ceph.recovering_keys_per_sec',
]

EXPECTED_TAGS = ['ceph_fsid:e0efcf84-e8ed-4916-8ce1-9c70242d390a', 'ceph_mon_state:peon', 'optional:tag1']

OSD_SPECIFIC_TAGS = {
    'osd0': [
        'ceph_osd_device:/dev/sda',
        'ceph_osd_device_class:hdd',
        'ceph_osd_device_id:disk0',
        'ceph_osd_objectstore:bluestore',
        'ceph_release:octopus',
        'ceph_version:15.2.8',
    ],
    'osd1': [
        'ceph_osd_device:/dev/sdb',
        'ceph_osd_device_class:hdd',
        'ceph_osd_device_id:disk1',
        'ceph_osd_objectstore:bluestore',
        'ceph_release:octopus',
        'ceph_version:15.2.8',
    ],
    'osd2': [
        'ceph_osd_device:/dev/sdc',
        'ceph_osd_device_class:hdd',
        'ceph_osd_device_id:disk2',
        'ceph_osd_objectstore:bluestore',
        'ceph_release:octopus',
        'ceph_version:15.2.8',
    ],
}

pytestmark = pytest.mark.unit


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("raw.json"))
def test_simple_metrics(_, aggregator):
    ceph_check = Ceph(CHECK_NAME, {}, [copy.deepcopy(BASIC_CONFIG)])
    ceph_check.check({})

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(metric, count=1, tags=EXPECTED_TAGS)

    aggregator.assert_service_check('ceph.overall_status', status=Ceph.OK, tags=EXPECTED_SERVICE_TAGS)


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("warn.json"))
def test_warn_health(_, aggregator):
    ceph_check = Ceph(CHECK_NAME, {}, [copy.deepcopy(BASIC_CONFIG)])
    ceph_check.check({})

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(metric, count=1, tags=EXPECTED_TAGS)

    aggregator.assert_service_check('ceph.overall_status', status=Ceph.WARNING, tags=EXPECTED_SERVICE_TAGS)


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("ceph_luminous_warn.json"))
def test_luminous_warn_health(_, aggregator):
    config = copy.deepcopy(BASIC_CONFIG)
    config["collect_service_check_for"] = ['OSD_NEARFULL', 'OSD_FULL']
    ceph_check = Ceph(CHECK_NAME, {}, [config])
    ceph_check.check({})

    aggregator.assert_service_check('ceph.overall_status', status=Ceph.CRITICAL, tags=EXPECTED_SERVICE_TAGS)
    aggregator.assert_service_check('ceph.osd_nearfull', status=Ceph.WARNING, tags=EXPECTED_SERVICE_TAGS)
    aggregator.assert_service_check('ceph.osd_full', status=Ceph.CRITICAL, tags=EXPECTED_SERVICE_TAGS)


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("ceph_luminous_ok.json"))
def test_luminous_ok_health(_, aggregator):
    config = copy.deepcopy(BASIC_CONFIG)
    config["collect_service_check_for"] = ['OSD_NEARFULL']
    ceph_check = Ceph(CHECK_NAME, {}, [config])
    ceph_check.check({})

    aggregator.assert_service_check('ceph.overall_status', status=Ceph.OK)
    aggregator.assert_service_check('ceph.osd_nearfull', status=Ceph.OK)
    aggregator.assert_service_check('ceph.pool_app_not_enabled', count=0)


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("ceph_luminous_warn.json"))
def test_luminous_osd_full_metrics(_, aggregator):
    ceph_check = Ceph(CHECK_NAME, {}, [copy.deepcopy(BASIC_CONFIG)])
    ceph_check.check({})

    aggregator.assert_metric('ceph.num_full_osds', value=1)
    aggregator.assert_metric('ceph.num_near_full_osds', value=1)


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("raw.json"))
def test_tagged_metrics(_, aggregator):

    ceph_check = Ceph(CHECK_NAME, {}, [copy.deepcopy(BASIC_CONFIG)])
    ceph_check.check({})

    for osd in ['osd0', 'osd1', 'osd2']:
        expected_tags = EXPECTED_TAGS + ['ceph_osd:%s' % osd] + OSD_SPECIFIC_TAGS[osd]

        for metric in ['ceph.commit_latency_ms', 'ceph.apply_latency_ms']:
            aggregator.assert_metric(metric, count=1, tags=expected_tags)

    for pool in ['pool0', 'rbd']:
        expected_tags = EXPECTED_TAGS + ['ceph_pool:%s' % pool]

        for metric in EXPECTED_METRICS_POOL_TAGS:
            aggregator.assert_metric(metric, count=1, tags=expected_tags)


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("raw2.json"))
def test_osd_perf_with_osdstats(_, aggregator):

    ceph_check = Ceph(CHECK_NAME, {}, [copy.deepcopy(BASIC_CONFIG)])
    ceph_check.check({})

    for osd in ['osd0', 'osd1', 'osd2']:
        expected_tags = EXPECTED_TAGS + ['ceph_osd:%s' % osd] + OSD_SPECIFIC_TAGS[osd]

        for metric in ['ceph.commit_latency_ms', 'ceph.apply_latency_ms']:
            aggregator.assert_metric(metric, count=1, tags=expected_tags)


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("ceph_10.2.2.json"))
def test_osd_status_metrics(_, aggregator):

    ceph_check = Ceph(CHECK_NAME, {}, [copy.deepcopy(BASIC_CONFIG)])
    ceph_check.check({})

    expected_metrics = ['ceph.read_op_per_sec', 'ceph.write_op_per_sec', 'ceph.op_per_sec']

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

    ceph_check = Ceph(CHECK_NAME, {}, [copy.deepcopy(BASIC_CONFIG)])
    ceph_check.check({})

    aggregator.assert_metric('ceph.num_full_osds', value=0, count=1, tags=EXPECTED_TAGS)
    aggregator.assert_metric('ceph.num_near_full_osds', value=0, count=1, tags=EXPECTED_TAGS)
