# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
import json
from collections.abc import Callable

import mock
import pytest

from datadog_checks.ceph import Ceph
from datadog_checks.dev.utils import get_metadata_metrics

from .common import BASIC_CONFIG, CHECK_NAME, EXPECTED_SERVICE_CHECKS, EXPECTED_SERVICE_TAGS, mock_data
from .common import EXPECTED_METRICS as ALL_METRICS

EXPECTED_METRICS = [
    'ceph.num_mons',
    'ceph.num_mons.active',
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
def test_simple_metrics(_, aggregator, dd_run_check):
    ceph_check = Ceph(CHECK_NAME, {}, [copy.deepcopy(BASIC_CONFIG)])
    dd_run_check(ceph_check)

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(metric, count=1, tags=EXPECTED_TAGS)

    aggregator.assert_service_check('ceph.overall_status', status=Ceph.OK, tags=EXPECTED_SERVICE_TAGS)


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("warn.json"))
def test_warn_health(_, aggregator, dd_run_check):
    ceph_check = Ceph(CHECK_NAME, {}, [copy.deepcopy(BASIC_CONFIG)])
    dd_run_check(ceph_check)

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(metric, count=1, tags=EXPECTED_TAGS)

    aggregator.assert_service_check('ceph.overall_status', status=Ceph.WARNING, tags=EXPECTED_SERVICE_TAGS)


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("ceph_luminous_warn.json"))
def test_luminous_warn_health(_, aggregator, dd_run_check):
    config = copy.deepcopy(BASIC_CONFIG)
    config["collect_service_check_for"] = ['OSD_NEARFULL', 'OSD_FULL']
    ceph_check = Ceph(CHECK_NAME, {}, [config])
    dd_run_check(ceph_check)

    aggregator.assert_service_check('ceph.overall_status', status=Ceph.CRITICAL, tags=EXPECTED_SERVICE_TAGS)
    aggregator.assert_service_check('ceph.osd_nearfull', status=Ceph.WARNING, tags=EXPECTED_SERVICE_TAGS)
    aggregator.assert_service_check('ceph.osd_full', status=Ceph.CRITICAL, tags=EXPECTED_SERVICE_TAGS)


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("ceph_luminous_ok.json"))
def test_luminous_ok_health(_, aggregator, dd_run_check):
    config = copy.deepcopy(BASIC_CONFIG)
    config["collect_service_check_for"] = ['OSD_NEARFULL']
    ceph_check = Ceph(CHECK_NAME, {}, [config])
    dd_run_check(ceph_check)

    aggregator.assert_service_check('ceph.overall_status', status=Ceph.OK)
    aggregator.assert_service_check('ceph.osd_nearfull', status=Ceph.OK)
    aggregator.assert_service_check('ceph.pool_app_not_enabled', count=0)


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("ceph_luminous_warn.json"))
def test_luminous_osd_full_metrics(_, aggregator, dd_run_check):
    ceph_check = Ceph(CHECK_NAME, {}, [copy.deepcopy(BASIC_CONFIG)])
    dd_run_check(ceph_check)

    aggregator.assert_metric('ceph.num_full_osds', value=1)
    aggregator.assert_metric('ceph.num_near_full_osds', value=1)


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("raw.json"))
def test_tagged_metrics(_, aggregator, dd_run_check):
    ceph_check = Ceph(CHECK_NAME, {}, [copy.deepcopy(BASIC_CONFIG)])
    dd_run_check(ceph_check)

    for osd in ['osd0', 'osd1', 'osd2']:
        expected_tags = EXPECTED_TAGS + ['ceph_osd:%s' % osd] + OSD_SPECIFIC_TAGS[osd]

        for metric in ['ceph.commit_latency_ms', 'ceph.apply_latency_ms']:
            aggregator.assert_metric(metric, count=1, tags=expected_tags)

    for pool in ['pool0', 'rbd']:
        expected_tags = EXPECTED_TAGS + ['ceph_pool:%s' % pool]

        for metric in EXPECTED_METRICS_POOL_TAGS:
            aggregator.assert_metric(metric, count=1, tags=expected_tags)


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("raw2.json"))
def test_osd_perf_with_osdstats(_, aggregator, dd_run_check):
    ceph_check = Ceph(CHECK_NAME, {}, [copy.deepcopy(BASIC_CONFIG)])
    dd_run_check(ceph_check)

    for osd in ['osd0', 'osd1', 'osd2']:
        expected_tags = EXPECTED_TAGS + ['ceph_osd:%s' % osd] + OSD_SPECIFIC_TAGS[osd]

        for metric in ['ceph.commit_latency_ms', 'ceph.apply_latency_ms']:
            aggregator.assert_metric(metric, count=1, tags=expected_tags)


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("ceph_10.2.2.json"))
def test_osd_status_metrics(_, aggregator, dd_run_check):
    ceph_check = Ceph(CHECK_NAME, {}, [copy.deepcopy(BASIC_CONFIG)])
    dd_run_check(ceph_check)

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
def test_osd_status_metrics_non_osd_health(_, aggregator, dd_run_check):
    """
    The `detail` key of `health detail` can contain info on the health of non-osd units:
    shouldn't make the check fail
    """

    ceph_check = Ceph(CHECK_NAME, {}, [copy.deepcopy(BASIC_CONFIG)])
    dd_run_check(ceph_check)

    aggregator.assert_metric('ceph.num_full_osds', value=0, count=1, tags=EXPECTED_TAGS)
    aggregator.assert_metric('ceph.num_near_full_osds', value=0, count=1, tags=EXPECTED_TAGS)


@mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=mock_data("ceph_stats_by_class.json"))
def test_stats_by_class_metrics(_, aggregator, dd_run_check):
    """
    Test with populated stats by class field
    """

    ceph_check = Ceph(CHECK_NAME, {}, [copy.deepcopy(BASIC_CONFIG)])
    dd_run_check(ceph_check)

    aggregator.assert_metric('ceph.class_pct_used', count=1, tags=EXPECTED_TAGS + ['ceph_osd_device_class:hdd'])
    aggregator.assert_metric('ceph.class_pct_used', count=0, tags=EXPECTED_TAGS + ['ceph_osd_device_class:nvme'])


# Output of a three-monitor, single-OSD cluster from `tests/compose/micro-cluster.sh`,
# captured with client I/O running. These releases have no `mon_status` command,
# so the fixtures don't include it, as with the real check.
MODERN_RELEASES = [
    pytest.param('ceph_squid.json', 'squid', '19.2.7', id='squid'),
    pytest.param('ceph_tentacle.json', 'tentacle', '20.2.5', id='tentacle'),
    pytest.param('ceph_umbrella.json', 'umbrella', '21.2.0', id='umbrella'),
]


def run_modern_release_check(fixture: str, dd_run_check: Callable) -> list[str]:
    raw = mock_data(fixture)
    with mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=raw):
        dd_run_check(Ceph(CHECK_NAME, {}, [copy.deepcopy(BASIC_CONFIG)]))
    return ['ceph_fsid:%s' % raw['status']['fsid'], 'optional:tag1']


@pytest.mark.parametrize('fixture, release, version', MODERN_RELEASES)
def test_modern_release_metrics(aggregator, dd_run_check, fixture, release, version):
    tags = run_modern_release_check(fixture, dd_run_check)

    for metric in ALL_METRICS:
        aggregator.assert_metric(metric, at_least=1)
        for tag in tags:
            aggregator.assert_metric_has_tag(metric, tag)

    aggregator.assert_metric('ceph.num_mons', value=3, count=1, tags=tags)
    aggregator.assert_metric('ceph.num_mons.active', value=3, count=1, tags=tags)
    aggregator.assert_metric('ceph.num_osds', value=1, count=1, tags=tags)
    aggregator.assert_metric('ceph.num_up_osds', value=1, count=1, tags=tags)
    aggregator.assert_metric('ceph.num_in_osds', value=1, count=1, tags=tags)
    aggregator.assert_metric('ceph.num_pools', value=2, count=1, tags=tags)
    aggregator.assert_metric('ceph.num_pgs', value=9, count=1, tags=tags)
    # `ceph.osd.pct_used` needs a full OSD, and `ceph.total_objects` only exists before Nautilus.
    metadata = {
        name: row
        for name, row in get_metadata_metrics().items()
        if name not in ('ceph.osd.pct_used', 'ceph.total_objects')
    }
    aggregator.assert_metrics_using_metadata(metadata, check_submission_type=True, check_symmetric_inclusion=True)
    aggregator.assert_metric('ceph.pgstate.active_clean', value=9, count=1, tags=tags)

    for metric in ['ceph.commit_latency_ms', 'ceph.apply_latency_ms']:
        aggregator.assert_metric_has_tag(metric, 'ceph_osd:osd0')
        aggregator.assert_metric_has_tag(metric, 'ceph_release:%s' % release)
        aggregator.assert_metric_has_tag(metric, 'ceph_version:%s' % version)

    for metric in ['ceph.write_bytes_sec', 'ceph.write_op_per_sec']:
        aggregator.assert_metric_has_tag(metric, 'ceph_pool:demo')

    for sc in EXPECTED_SERVICE_CHECKS + ['ceph.overall_status']:
        aggregator.assert_service_check(sc, status=Ceph.OK, tags=EXPECTED_SERVICE_TAGS)


def test_num_mons_active_pacific_issue_11896(aggregator, dd_run_check):
    raw = {
        'status': {
            'fsid': '3b9bd3ca-ff4d-11eb-ada4-566fa99c0024',
            'health': {'status': 'HEALTH_OK', 'checks': {}, 'mutes': []},
            'election_epoch': 106590,
            'quorum': [0, 1, 2],
            'quorum_names': ['ceph-mon-1', 'ceph-mon-0', 'ceph-mon-2'],
            'quorum_age': 2652,
            'monmap': {'epoch': 57, 'min_mon_release_name': 'pacific', 'num_mons': 3},
        }
    }
    with mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=raw):
        dd_run_check(Ceph(CHECK_NAME, {}, [copy.deepcopy(BASIC_CONFIG)]))

    tags = ['ceph_fsid:3b9bd3ca-ff4d-11eb-ada4-566fa99c0024', 'optional:tag1']
    aggregator.assert_metric('ceph.num_mons', value=3, count=1, tags=tags)
    aggregator.assert_metric('ceph.num_mons.active', value=3, count=1, tags=tags)


def test_num_mons_active_leader_down(aggregator, dd_run_check):
    raw = mock_data('ceph_umbrella_mon_down.json')
    with mock.patch("datadog_checks.ceph.Ceph._collect_raw", return_value=raw):
        dd_run_check(Ceph(CHECK_NAME, {}, [copy.deepcopy(BASIC_CONFIG)]))

    aggregator.assert_metric('ceph.num_mons', value=3, count=1)
    aggregator.assert_metric('ceph.num_mons.active', value=2, count=1)


@pytest.mark.parametrize(
    'monmap, runs_mon_status',
    [
        pytest.param({'mons': []}, True, id='luminous'),
        # Before 14.2.17, `status` returns the full monmap, which names the release and has no `num_mons`.
        pytest.param({'min_mon_release_name': 'nautilus', 'mons': []}, True, id='nautilus-before-14.2.17'),
        pytest.param({'num_mons': 3, 'min_mon_release_name': '14'}, True, id='nautilus'),
        pytest.param({'num_mons': 3, 'min_mon_release_name': 'octopus'}, False, id='octopus'),
        pytest.param({'num_mons': 3, 'min_mon_release_name': 'umbrella'}, False, id='umbrella'),
    ],
)
def test_mon_status_only_runs_before_octopus(monmap, runs_mon_status):
    commands = []

    def run_ceph(args, log):
        cmd = ' '.join(args[3:-1])
        commands.append(cmd)
        return json.dumps({'monmap': monmap} if cmd == 'status' else {}), '', 0

    with mock.patch('datadog_checks.ceph.ceph.get_subprocess_output', side_effect=run_ceph):
        Ceph(CHECK_NAME, {}, [copy.deepcopy(BASIC_CONFIG)])._collect_raw('ceph', 'ceph', {})

    assert commands[0] == 'status'
    assert ('mon_status' in commands) is runs_mon_status
