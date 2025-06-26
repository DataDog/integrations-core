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
def mock_client():
    with mock.patch.object(LustreCheck, 'get_node_type', return_value='client'):
        yield

@pytest.fixture
def mock_mds():
    with mock.patch.object(LustreCheck, 'get_node_type', return_value='mds'):
        yield

@pytest.fixture
def mock_oss():
    with mock.patch.object(LustreCheck, 'get_node_type', return_value='oss'):
        yield

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
    def mock_run_command(bin, *args):
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


# TODO: parametrize
@pytest.mark.parametrize(
        'method, fixture_file, expected_metrics',
        [
            pytest.param("submit_lnet_stats_metrics", 'all_lnet_stats.txt', LNET_STATS_METRICS, id='stats'),
            pytest.param("submit_lnet_local_ni_metrics", 'all_lnet_net.txt', LNET_LOCAL_METRICS, id='local'),
            pytest.param("submit_lnet_peer_ni_metrics", 'all_lnet_peer.txt', LNET_PEER_METRICS, id='peer'),
        ],
)
def test_lnet(aggregator, instance, mock_client, method, fixture_file, expected_metrics):
    with mock.patch.object(LustreCheck, 'run_command') as mock_run:
        with open(os.path.join(FIXTURES_DIR, fixture_file), 'r') as f:
            mock_run.return_value = f.read()
        check = LustreCheck('lustre', {}, [instance])
        getattr(check, method)()
    for metric in expected_metrics:
        aggregator.assert_metric(metric)
