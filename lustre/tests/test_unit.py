# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable, Dict  # noqa: F401

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.lustre import LustreCheck
from datadog_checks.lustre.metrics import LNET_LOCAL_METRICS, LNET_PEER_METRICS, LNET_STATS_METRICS
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


def test_jobstats(aggregator, instance, mock_oss, disable_subprocess):
    with mock.patch.object(LustreCheck, 'lctl_list_param') as mock_list_param:
        with mock.patch.object(LustreCheck, 'lctl_get_param') as mock_get_param:
            mock_list_param.return_value = ['obdfilter.lustre-OST0001.job_stats']
            with open(os.path.join(FIXTURES_DIR, 'oss_jobstats.txt'), 'r') as f:
                mock_get_param.return_value = f.read()
                check = LustreCheck('lustre', {}, [instance])
                check.submit_jobstats_metrics()
    # TODO: Add assertions to verify the job stats metrics

def test_lnet_stats(aggregator, instance, mock_client):
    with mock.patch.object(LustreCheck, 'lnet_get_stats') as mock_get:
        with open(os.path.join(FIXTURES_DIR, 'all_lnet_stats.txt'), 'r') as f:
            mock_get.return_value = f.read()
            check = LustreCheck('lustre', {}, [instance])
            check.submit_lnet_stats_metrics()
    for metric in LNET_STATS_METRICS:
        aggregator.assert_metric(metric)

def test_lnet_local(aggregator, instance, mock_client):
    with mock.patch.object(LustreCheck, 'lnet_get_stats') as mock_get:
        with open(os.path.join(FIXTURES_DIR, 'all_lnet_net.txt'), 'r') as f:
            mock_get.return_value = f.read()
            check = LustreCheck('lustre', {}, [instance])
            check.submit_lnet_local_ni_metrics()
    for metric in LNET_LOCAL_METRICS:
        aggregator.assert_metric(metric)

def test_lnet_peer(aggregator, instance, mock_client):
    with mock.patch.object(LustreCheck, 'lnet_get_stats') as mock_get:
        with open(os.path.join(FIXTURES_DIR, 'all_lnet_peer.txt'), 'r') as f:
            mock_get.return_value = f.read()
            check = LustreCheck('lustre', {}, [instance])
            check.submit_lnet_peer_ni_metrics()
    for metric in LNET_PEER_METRICS:
        aggregator.assert_metric(metric)
