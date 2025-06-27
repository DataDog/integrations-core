# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable, Dict  # noqa: F401

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.lustre import LustreCheck
from datadog_checks.lustre.metrics import LNET_LOCAL_METRICS, LNET_PEER_METRICS, LNET_STATS_METRICS, JOBSTATS_MDS_METRICS, JOBSTATS_OSS_METRICS
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
    def mock_run_command(bin, *args, **kwargs):
        if args[0] == 'list_param':
            return 'some.job_stats.param'
        elif args[0] == 'get_param':
            with open(os.path.join(FIXTURES_DIR, fixture_file), 'r') as f:
                return f.read()
    with mock.patch.object(LustreCheck, 'run_command', side_effect=mock_run_command) as mock_run:
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
    with mock.patch.object(LustreCheck, 'run_command') as mock_run:
        with open(os.path.join(FIXTURES_DIR, fixture_file), 'r') as f:
            mock_run.return_value = f.read()
        check = LustreCheck('lustre', {}, [instance])
        getattr(check, method)()
    for metric in expected_metrics:
        aggregator.assert_metric(metric)


def test_device_health(aggregator, instance):
    with mock.patch.object(LustreCheck, 'run_command') as mock_run:
        with open(os.path.join(FIXTURES_DIR, 'client_dl_yaml.txt'), 'r') as f:
            mock_run.return_value = f.read()
        check = LustreCheck('lustre', {}, [instance])
        check.submit_device_health()
    
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
        'node_type:client'
    ])
    
    aggregator.assert_metric('lustre.device.refcount', value=5, tags=[
        'device_type:mgc',
        'device_name:MGC172.31.16.218@tcp',
        'device_uuid:7d3988a7-145f-444e-9953-58e3e6d97385',
        'node_type:client'
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
    with mock.patch.object(LustreCheck, 'run_command') as mock_run:
        with open(os.path.join(FIXTURES_DIR, fixture_file), 'r') as f:
            mock_run.return_value = f.read()
        check = LustreCheck('lustre', {}, [{}])
        node_type = check._find_node_type()
        assert node_type == expected_node_type


def test_submit_changelogs(aggregator, instance):
    with mock.patch.object(LustreCheck, 'run_command') as mock_run:
        with open(os.path.join(FIXTURES_DIR, 'client_dl_yaml.txt'), 'r') as f:
            mock_run.return_value = f.read()
        check = LustreCheck('lustre', {}, [instance])
        check.filesystems = ['lustre']
        check._update_changelog_targets()
        
        # Mock the get_changelog method to return test data
        test_changelog_data = (
            "4 07RMDIR 12:47:32.913242547 2025.06.02 0x1 t=[0x200000bd1:0x3:0x0] bacillus\n"
            "5 02MKDIR 12:48:25.401684027 2025.06.02 0x0 t=[0x200000bd1:0x4:0x0] bacillus\n" 
            "6 01CREAT 12:50:50.996256280 2025.06.02 0x0 t=[0x200000bd1:0x5:0x0] bulgaricus.txt\n"
        )
        with mock.patch.object(check, 'get_changelog', return_value=test_changelog_data):
            with mock.patch.object(check, 'send_log') as mock_send_log:
                check.submit_changelogs()
        
        # Verify send_log was called for each changelog entry
        assert mock_send_log.call_count == 3
        
        # Verify the first call arguments
        first_call = mock_send_log.call_args_list[0]
        expected_data = {
            'operation_type': '07RMDIR',
            'timestamp': '12:47:32.913242547',
            'datestamp': '2025.06.02',
            'flags': '0x1',
            'message': 't=[0x200000bd1:0x3:0x0] bacillus'
        }
        assert first_call[0][0] == expected_data
        assert first_call[0][1] == {'index': '4'}


def test_get_changelog(instance):
    with mock.patch.object(LustreCheck, 'run_command') as mock_run_command:
        with open(os.path.join(FIXTURES_DIR, 'client_changelogs.txt'), 'r') as f:
            mock_run_command.return_value = f.read()
        
        check = LustreCheck('lustre', {}, [instance])
        
        # Mock get_log_cursor to return a starting index
        with mock.patch.object(check, 'get_log_cursor', return_value='100'):
            result = check.get_changelog('lustre-MDT0000')
            
            # Verify the command was called with correct arguments
            mock_run_command.assert_called_with(
                '/usr/bin/lfs', 'changelog', 'lustre-MDT0000', '100', '1100', sudo=True
            )
            
            # Verify the result contains changelog data
            assert result is not None
            assert len(result) > 0
        
        # Test with no previous cursor (start from 0)
        with mock.patch.object(check, 'get_log_cursor', return_value=None):
            result = check.get_changelog('lustre-MDT0000')
            
            mock_run_command.assert_called_with(
                '/usr/bin/lfs', 'changelog', 'lustre-MDT0000', '0', '1000', sudo=True
            )
