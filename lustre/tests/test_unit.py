# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from os.path import isfile
from typing import Any, Callable, Dict  # noqa: F401

import mock
import pytest

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev import get_here
from datadog_checks.lustre import LustreCheck
from datadog_checks.lustre.constants import DEFAULT_PARAMS, EXTRA_PARAMS, JOBSTATS_PARAMS

from .metrics import (
    CLIENT_METRICS,
    COMMON_METRICS,
    JOBSTATS_MDS_METRICS,
    JOBSTATS_OSS_METRICS,
    LNET_LOCAL_METRICS,
    LNET_PEER_METRICS,
    LNET_STATS_METRICS,
    MDS_METRICS,
    OSS_METRICS,
)

HERE = get_here()
FIXTURES_DIR = os.path.join(HERE, 'fixtures')


@pytest.fixture
def disable_subprocess():
    with mock.patch('datadog_checks.lustre.check.subprocess.run'):
        yield


def mock_run_command(command_fixture_mapping):
    def run_command(bin, *args, **kwargs):
        requested_command = f"{bin} {' '.join(args)}"
        for cmd, fixture in command_fixture_mapping.items():
            if requested_command.startswith(cmd):
                path = os.path.join(FIXTURES_DIR, fixture)
                if not isfile(path):
                    return fixture
                with open(path, 'r') as f:
                    return f.read()
        raise ValueError(f"Unexpected command: {requested_command}")

    return run_command


@pytest.mark.parametrize(
    'node_type, dl_fixture, expected_metrics',
    [
        pytest.param(
            'client',
            'client_dl_yaml.txt',
            COMMON_METRICS + CLIENT_METRICS,
            id='client',
        ),
        pytest.param(
            'mds',
            'mds_dl_yaml.txt',
            COMMON_METRICS + MDS_METRICS + JOBSTATS_MDS_METRICS,
            id='mds',
        ),
        pytest.param(
            'oss',
            'oss_dl_yaml.txt',
            COMMON_METRICS + OSS_METRICS + JOBSTATS_OSS_METRICS,
            id='oss',
        ),
    ],
)
def test_check(dd_run_check, aggregator, node_type, dl_fixture, expected_metrics):
    instance = {'node_type': node_type, 'enable_extra_params': 'true', 'enable_lnetctl_detailed': 'true'}
    mapping = {
        'lctl get_param -ny version': 'all_version.txt',
        'lctl dl': dl_fixture,
        'lnetctl stats show': 'all_lnet_stats.txt',
        'lnetctl net show': 'all_lnet_net.txt',
        'lnetctl peer show': 'all_lnet_peer.txt',
    }
    for param in DEFAULT_PARAMS + EXTRA_PARAMS + JOBSTATS_PARAMS:
        mapping[f'lctl list_param {param.regex}'] = param.regex
        mapping[f'lctl get_param -ny {param.regex}'] = param.fixture

    with mock.patch.object(LustreCheck, '_run_command', side_effect=mock_run_command(mapping)):
        check = LustreCheck('lustre', {}, [instance])
        dd_run_check(check)

    for metric in expected_metrics:
        aggregator.assert_metric(metric)


@pytest.mark.parametrize(
    'node_type, fixture_file, expected_metrics',
    [
        pytest.param('mds', 'mds_jobstats.txt', JOBSTATS_MDS_METRICS, id='mds'),
        pytest.param('oss', 'oss_jobstats.txt', JOBSTATS_OSS_METRICS, id='oss'),
    ],
)
def test_jobstats(aggregator, disable_subprocess, node_type, fixture_file, expected_metrics):
    instance = {'node_type': node_type}
    mapping = {
        'lctl get_param -ny version': 'all_version.txt',
        'lctl dl': f'{node_type}_dl_yaml.txt',
        'lctl list_param': "all_list_param.txt",
        'lctl get_param': fixture_file,
    }
    with mock.patch.object(LustreCheck, '_run_command', side_effect=mock_run_command(mapping)):
        check = LustreCheck('lustre', {}, [instance])
        check.submit_jobstats_metrics()
    for metric in expected_metrics:
        aggregator.assert_metric(metric)


@pytest.mark.parametrize(
    'method, fixture_file, expected_metrics',
    [
        pytest.param("submit_lnet_stats_metrics", 'all_lnet_stats.txt', LNET_STATS_METRICS, id='stats'),
        pytest.param("submit_lnet_local_ni_metrics", 'all_lnet_net.txt', LNET_LOCAL_METRICS, id='local'),
        pytest.param("submit_lnet_peer_ni_metrics", 'all_lnet_peer.txt', LNET_PEER_METRICS, id='peer'),
    ],
)
def test_lnet(aggregator, instance, method, fixture_file, expected_metrics):
    mapping = {
        'lctl get_param -ny version': 'all_version.txt',
        'lctl dl': 'client_dl_yaml.txt',
        'lnetctl': fixture_file,
    }
    with mock.patch.object(LustreCheck, '_run_command', side_effect=mock_run_command(mapping)):
        check = LustreCheck('lustre', {}, [instance])
        getattr(check, method)()
    for metric in expected_metrics:
        aggregator.assert_metric(metric)


def test_device_health(aggregator, instance):
    mapping = {
        'lctl get_param -ny version': 'all_version.txt',
        'lctl dl': 'client_dl_yaml.txt',
    }
    with mock.patch.object(LustreCheck, '_run_command', side_effect=mock_run_command(mapping)):
        check = LustreCheck('lustre', {}, [instance])
        check.submit_device_health(check.devices)

    expected_metrics = ['lustre.device.health', 'lustre.device.refcount']

    for metric in expected_metrics:
        aggregator.assert_metric(metric)

    # Verify specific device metrics
    aggregator.assert_metric(
        'lustre.device.health',
        value=1,
        tags=[
            'device_type:mgc',
            'device_name:MGC172.31.16.218@tcp',
            'device_uuid:7d3988a7-145f-444e-9953-58e3e6d97385',
            'node_type:client',
            'lustre_version:2.16.1',
        ],
    )

    aggregator.assert_metric(
        'lustre.device.refcount',
        value=5,
        tags=[
            'device_type:mgc',
            'device_name:MGC172.31.16.218@tcp',
            'device_uuid:7d3988a7-145f-444e-9953-58e3e6d97385',
            'node_type:client',
            'lustre_version:2.16.1',
        ],
    )


@pytest.mark.parametrize(
    'fixture_file, expected_node_type',
    [
        pytest.param('client_dl_yaml.txt', 'client', id='client'),
        pytest.param('mds_dl_yaml.txt', 'mds', id='mds'),
        pytest.param('oss_dl_yaml.txt', 'oss', id='oss'),
    ],
)
def test_node_type(fixture_file, expected_node_type):
    mapping = {
        'lctl get_param -ny version': 'all_version.txt',
        'lctl dl': fixture_file,
    }
    with mock.patch.object(LustreCheck, '_run_command', side_effect=mock_run_command(mapping)):
        check = LustreCheck('lustre', {}, [{}])
        node_type = check._find_node_type()
        assert node_type == expected_node_type


def test_submit_changelogs(aggregator, instance):
    mapping = {
        'lctl get_param -ny version': 'all_version.txt',
        'lctl dl': 'client_dl_yaml.txt',
        'lfs changelog': 'client_changelogs.txt',
    }
    with mock.patch.object(LustreCheck, '_run_command', side_effect=mock_run_command(mapping)):
        check = LustreCheck('lustre', {}, [instance])
        check._update_changelog_targets(check.devices, ["lustre"])

        with mock.patch.object(check, 'send_log') as mock_send_log:
            check.submit_changelogs(1000)

        # Verify send_log was called for each changelog entry
        assert mock_send_log.call_count == 304

        # Verify the first call arguments
        first_call = mock_send_log.call_args_list[0]
        expected_data = {
            'operation_type': '07RMDIR',
            'timestamp': 1748861252.0,
            'flags': '0x1',
            'message': 't=[0x200000bd1:0x3:0x0] ef=0x13 u=0:0 nid=172.31.38.176@tcp p=[0x200000007:0x1:0x0] bacillus',
        }
        assert first_call[0][0] == expected_data
        assert first_call[0][1] == {'index': '4'}


def test_get_changelog(instance):
    mapping = {
        'lctl get_param -ny version': 'all_version.txt',
        'lctl dl': 'client_dl_yaml.txt',
        'lfs changelog': 'client_changelogs.txt',
    }
    with mock.patch.object(LustreCheck, '_run_command', side_effect=mock_run_command(mapping)) as mock_run:

        check = LustreCheck('lustre', {}, [instance])

        # Mock get_log_cursor to return a starting index
        with mock.patch.object(check, 'get_log_cursor', return_value={'index': '100'}):
            result = check._get_changelog('lustre-MDT0000', 1000)

            # Verify the command was called with correct arguments
            mock_run.assert_called_with('lfs', 'changelog', 'lustre-MDT0000', '100', '1100', sudo=True)

            # Verify the result contains changelog data
            assert result is not None
            assert len(result) > 0

        # Test with no previous cursor (start from 0)
        with mock.patch.object(check, 'get_log_cursor', return_value=None):
            result = check._get_changelog('lustre-MDT0000', 1000)

            mock_run.assert_called_with('lfs', 'changelog', 'lustre-MDT0000', '0', '1000', sudo=True)


def test_submit_general_stats(aggregator, instance):
    mapping = {
        'lctl get_param -ny version': 'all_version.txt',
        'lctl dl': 'client_dl_yaml.txt',
        'lctl list_param llite.*.stats': 'llite',
        'lctl get_param -ny llite': 'client_llite_stats.txt',
    }
    with mock.patch.object(LustreCheck, '_run_command', side_effect=mock_run_command(mapping)):
        check = LustreCheck('lustre', {}, [instance])
        check.submit_general_stats(DEFAULT_PARAMS)

    # Verify some general stats metrics are submitted
    expected_metrics = [
        'lustre.filesystem.read_bytes.count',
        'lustre.filesystem.write_bytes.count',
        'lustre.filesystem.read.count',
        'lustre.filesystem.write.count',
    ]
    for metric in expected_metrics:
        aggregator.assert_metric(metric)


def test_extract_tags_from_param():
    mapping = {
        'lctl get_param -ny version': 'all_version.txt',
        'lctl dl': 'client_dl_yaml.txt',
    }
    with mock.patch.object(LustreCheck, '_run_command', side_effect=mock_run_command(mapping)):
        check = LustreCheck('lustre', {}, [{}])
        
        # Test with wildcards
        tags = check._extract_tags_from_param(
            'mdc.*.stats',
            'mdc.lustre-MDT0000-mdc-ffff8803f0d41000.stats',
            ('device_uuid',)
        )
        assert tags == ['device_uuid:lustre-MDT0000-mdc-ffff8803f0d41000']
        
        # Test with multiple wildcards
        tags = check._extract_tags_from_param(
            'mdt.*.exports.*.stats',
            'mdt.lustre-MDT0000.exports.172.31.16.218@tcp.stats',
            ('device_name', 'nid')
        )
        assert tags == ['device_name:lustre-MDT0000', 'nid:172.31.16.218@tcp']
        
        # Test with no wildcards
        tags = check._extract_tags_from_param(
            'mds.MDS.mdt.stats',
            'mds.MDS.mdt.stats',
            ()
        )
        assert tags == []
        
        # Test with mismatched parts
        tags = check._extract_tags_from_param(
            'mdc.*.stats',
            'mdc.too.many.parts.stats',
            ('device_uuid',)
        )
        assert tags == []


def test_parse_stats():
    mapping = {
        'lctl get_param -ny version': 'all_version.txt',
        'lctl dl': 'client_dl_yaml.txt',
    }
    with mock.patch.object(LustreCheck, '_run_command', side_effect=mock_run_command(mapping)):
        check = LustreCheck('lustre', {}, [{}])
        
        # Test valid stats parsing
        raw_stats = '''req_waittime              83 samples [usecs] 11 40 1493 32135
req_qdepth                83 samples [reqs] 0 0 0 0
cancel                    253 samples [locks] 1 1 253
'''
        
        parsed = check._parse_stats(raw_stats)
        
        assert 'req_waittime' in parsed
        assert parsed['req_waittime']['count'] == 83
        assert parsed['req_waittime']['unit'] == 'usecs'
        assert parsed['req_waittime']['min'] == 11
        assert parsed['req_waittime']['max'] == 40
        assert parsed['req_waittime']['sum'] == 1493
        assert parsed['req_waittime']['sumsq'] == 32135
        
        # Test ignored stats
        raw_stats_with_ignored = '''elapsed_time              2068792.478877751 secs.nsecs
req_waittime              83 samples [usecs] 11 40 1493 32135
'''
        
        parsed = check._parse_stats(raw_stats_with_ignored)
        assert 'elapsed_time' not in parsed
        assert 'req_waittime' in parsed
        
        # Test malformed lines
        raw_stats_malformed = '''invalid_line
req_waittime              83 samples [usecs] 11 40 1493 32135
short_line 1
'''
        
        parsed = check._parse_stats(raw_stats_malformed)
        assert len(parsed) == 1
        assert 'req_waittime' in parsed


def test_update_filesystems():
    mapping = {
        'lctl get_param -ny version': 'all_version.txt',
        'lctl dl': 'mds_dl_yaml.txt',
        'lctl list_param mdt.*.job_stats': 'mdt.lustre-MDT0000.job_stats\nmdt.lustre2-MDT0000.job_stats',
    }
    with mock.patch.object(LustreCheck, '_run_command', side_effect=mock_run_command(mapping)):
        check = LustreCheck('lustre', {}, [{'node_type': 'mds'}])
        check._update_filesystems()
        
        # Should extract filesystems from the parameter names
        assert 'lustre' in check.filesystems
        assert 'lustre2' in check.filesystems


def test_update_changelog_targets():
    mapping = {
        'lctl get_param -ny version': 'all_version.txt',
        'lctl dl': 'client_dl_yaml.txt',
    }
    with mock.patch.object(LustreCheck, '_run_command', side_effect=mock_run_command(mapping)):
        check = LustreCheck('lustre', {}, [{}])
        
        devices = [
            {'name': 'lustre-MDT0000', 'type': 'mdt'},
            {'name': 'lustre-MDT0001', 'type': 'mdt'},
            {'name': 'lustre2-MDT0000', 'type': 'mdt'},
            {'name': 'lustre-OST0000', 'type': 'ost'},
        ]
        filesystems = ['lustre', 'lustre2']
        
        check._update_changelog_targets(devices, filesystems)
        
        expected_targets = ['lustre-MDT0000', 'lustre-MDT0001', 'lustre2-MDT0000']
        assert set(check.changelog_targets) == set(expected_targets)


def test_lnet_group_filtering(aggregator, instance):
    mapping = {
        'lctl get_param -ny version': 'all_version.txt',
        'lctl dl': 'client_dl_yaml.txt',
        'lnetctl net show': 'all_lnet_net.txt',
    }
    with mock.patch.object(LustreCheck, '_run_command', side_effect=mock_run_command(mapping)):
        check = LustreCheck('lustre', {}, [instance])
        
        # Test that ignored groups are not submitted
        test_group = {'test_metric': 123}
        tags = ['test_tag:value']
        
        check._submit_lnet_metric_group('local', 'statistics', test_group, tags)
        
        aggregator.assert_metric('lustre.net.local.statistics.test_metric')
        aggregator.assert_metric_has_tag('lustre.net.local.statistics.test_metric', 'test_tag:value')


def test_metric_type_assignment(aggregator, instance):
    mapping = {
        'lctl get_param -ny version': 'all_version.txt',
        'lctl dl': 'client_dl_yaml.txt',
    }
    with mock.patch.object(LustreCheck, '_run_command', side_effect=mock_run_command(mapping)):
        check = LustreCheck('lustre', {}, [instance])
        
        # Test gauge metric
        check._submit('test.gauge', 100, 'gauge', tags=[])
        aggregator.assert_metric('lustre.test.gauge', value=100, metric_type=aggregator.GAUGE)
        
        # Test count metric
        check._submit('test.count', 50, 'count', tags=[])
        aggregator.assert_metric('lustre.test.count', value=50, metric_type=aggregator.COUNT)
        
        # Test rate metric
        check._submit('test.rate', 25, 'rate', tags=[])
        aggregator.assert_metric('lustre.test.rate', value=25, metric_type=aggregator.RATE)


def test_empty_command_outputs(instance):
    mapping = {
        'lctl get_param -ny version': 'all_version.txt',
        'lctl get_param -ny mdt': '',
        'lctl dl': 'client_dl_yaml.txt',
    }
    with mock.patch.object(LustreCheck, '_run_command', side_effect=mock_run_command(mapping)):
        check = LustreCheck('lustre', {}, [instance])
        
        # Should handle empty outputs gracefully
        result = check._parse_stats('')
        assert result == {}
        
        result = check._get_jobstats_metrics('mdt.lustre-MDT0000.job_stats')
        assert result == {}
