# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable, Dict  # noqa: F401

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.lustre import LustreCheck
from .metrics import LNET_LOCAL_METRICS, LNET_PEER_METRICS, LNET_STATS_METRICS, JOBSTATS_MDS_METRICS, JOBSTATS_OSS_METRICS
from datadog_checks.dev import get_here
import os
import mock
import pytest

HERE = get_here()
FIXTURES_DIR = os.path.join(HERE, 'fixtures')

@pytest.fixture
def disable_subprocess():
    with mock.patch('datadog_checks.lustre.check.subprocess.run'):
        yield

def mock_run_command(command_fixture_mapping):
    def run_command(bin, *args, **kwargs):
        requested_command = f"{bin} {' '.join(args)}"
        for cmd, fixture_file in command_fixture_mapping.items():
            if requested_command.startswith(cmd):
                fixture_file = command_fixture_mapping.get(cmd)
                if fixture_file:
                    with open(os.path.join(FIXTURES_DIR, fixture_file), 'r') as f:
                        return f.read()
        raise ValueError(f"Unexpected command: {requested_command}")
    return run_command


def test_check(dd_run_check, aggregator, instance):
    check = LustreCheck('lustre', {}, [instance])
    dd_run_check(check)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


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
    new_run_command = mock_run_command(mapping)
    with mock.patch.object(LustreCheck, '_run_command', side_effect=new_run_command):
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
    new_run_command = mock_run_command(mapping)
    with mock.patch.object(LustreCheck, '_run_command', side_effect=new_run_command):
        check = LustreCheck('lustre', {}, [instance])
        getattr(check, method)()
    for metric in expected_metrics:
        aggregator.assert_metric(metric)


def test_device_health(aggregator, instance):
    mapping = {
            'lctl get_param -ny version': 'all_version.txt',
            'lctl dl': 'client_dl_yaml.txt',
    }
    new_run_command = mock_run_command(mapping)
    with mock.patch.object(LustreCheck, '_run_command', side_effect=new_run_command):
        check = LustreCheck('lustre', {}, [instance])
        check.submit_device_health(check.devices)
    
    expected_metrics = [
        'lustre.device.health',
        'lustre.device.refcount'
    ]
    
    for metric in expected_metrics:
        aggregator.assert_metric(metric)
    
    # Verify specific device metrics
    aggregator.assert_metric('lustre.device.health', value=1, tags=[
        'device_type:mgc',
        'device_name:MGC172.31.16.218@tcp',
        'device_uuid:7d3988a7-145f-444e-9953-58e3e6d97385',
        'node_type:client',
        'lustre_version:2.16.1'
    ])
    
    aggregator.assert_metric('lustre.device.refcount', value=5, tags=[
        'device_type:mgc',
        'device_name:MGC172.31.16.218@tcp',
        'device_uuid:7d3988a7-145f-444e-9953-58e3e6d97385',
        'node_type:client',
        'lustre_version:2.16.1'
    ])


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
    new_run_command = mock_run_command(mapping)
    with mock.patch.object(LustreCheck, '_run_command', side_effect=new_run_command):
        check = LustreCheck('lustre', {}, [{}])
        node_type = check._find_node_type()
        assert node_type == expected_node_type


def test_submit_changelogs(aggregator, instance):
    mapping = {
        'lctl get_param -ny version': 'all_version.txt',
        'lctl dl': 'client_dl_yaml.txt',
        'lfs changelog': 'client_changelogs.txt',
    }
    new_run_command = mock_run_command(mapping)
    with mock.patch.object(LustreCheck, '_run_command', side_effect=new_run_command):
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
            'message': 't=[0x200000bd1:0x3:0x0] ef=0x13 u=0:0 nid=172.31.38.176@tcp p=[0x200000007:0x1:0x0] bacillus'
        }
        assert first_call[0][0] == expected_data
        assert first_call[0][1] == {'index': '4'}


def test_get_changelog(instance):
    mapping = {
        'lctl get_param -ny version': 'all_version.txt',
        'lctl dl': 'client_dl_yaml.txt',
        'lfs changelog': 'client_changelogs.txt',
    }
    new_run_command = mock_run_command(mapping)
    with mock.patch.object(LustreCheck, '_run_command', side_effect=new_run_command) as mock_run:
        
        check = LustreCheck('lustre', {}, [instance])
        
        # Mock get_log_cursor to return a starting index
        with mock.patch.object(check, 'get_log_cursor', return_value={'index':'100'}):
            result = check._get_changelog('lustre-MDT0000', 1000)
            
            # Verify the command was called with correct arguments
            mock_run.assert_called_with(
                'lfs', 'changelog', 'lustre-MDT0000', '100', '1100', sudo=True
            )
            
            # Verify the result contains changelog data
            assert result is not None
            assert len(result) > 0
        
        # Test with no previous cursor (start from 0)
        with mock.patch.object(check, 'get_log_cursor', return_value=None):
            result = check._get_changelog('lustre-MDT0000', 1000)
            
            mock_run.assert_called_with(
                'lfs', 'changelog', 'lustre-MDT0000', '0', '1000', sudo=True
            )
