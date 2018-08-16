# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
import mock

from datadog_checks.agent_metrics import AgentMetrics

CHECK_NAME = 'agent_metrics'

MOCK_CONFIG = {
    'process_metrics': [
        {
            'name': 'memory_info',
            'type': 'gauge',
            'active': 'yes'
        },
        {
            'name': 'cpu_times',
            'type': 'rate',
            'active': 'yes'
        },
    ],
    'tags': ['optional:tags']
}

MOCK_CONFIG_2 = {
    'process_metrics': [
        {
            'name': 'memory_info',
            'type': 'gauge',
            'active': 'yes'
        },
        {
            'name': 'get_non_existent_stat',
            'type': 'gauge',
            'active': 'yes'
        },
    ]
}

AGENT_CONFIG_DEV_MODE = {
    'developer_mode': True
}

AGENT_CONFIG_DEFAULT_MODE = {}

MOCK_STATS = {
    'memory_info': dict([('rss', 16814080), ('vms', 74522624)]),
    'cpu_times': dict([('user', 0.041733968), ('system', 0.022306718)])
}

MOCK_NAMES_TO_METRIC_TYPES = {
    'memory_info': 'gauge',
    'cpu_times': 'gauge'
}


@pytest.fixture
def check():
    return AgentMetrics(CHECK_NAME, {}, {})


# Tests for Agent Developer Mode
def test_psutil_config_to_stats(check):
    stats, names_to_metric_types = check._psutil_config_to_stats(MOCK_CONFIG)
    assert 'memory_info' in names_to_metric_types
    assert names_to_metric_types['memory_info'] == 'gauge'

    assert 'cpu_times' in names_to_metric_types
    assert names_to_metric_types['cpu_times'] == 'rate'

    assert 'memory_info' in stats
    assert 'cpu_times' in stats


def test_send_single_metric(check):
    check.gauge = mock.MagicMock()
    check.rate = mock.MagicMock()

    check._send_single_metric('datadog.agent.collector.memory_info.vms', 16814081, 'gauge', tags=['optional:tags'])
    check.gauge.assert_called_with('datadog.agent.collector.memory_info.vms', 16814081, tags=['optional:tags'])

    check._send_single_metric('datadog.agent.collector.memory_info.vms', 16814081, 'rate', tags=['optional:tags'])
    check.rate.assert_called_with('datadog.agent.collector.memory_info.vms', 16814081, tags=['optional:tags'])

    with pytest.raises(Exception):
        check._send_single_metric('datadog.agent.collector.memory_info.vms', 16814081, 'bogus')


def test_register_psutil_metrics(check, aggregator):
    check._register_psutil_metrics(MOCK_STATS, MOCK_NAMES_TO_METRIC_TYPES, tags=['optional:tags'])

    aggregator.assert_metric('datadog.agent.collector.memory_info.rss', value=16814080, tags=['optional:tags'])
    aggregator.assert_metric('datadog.agent.collector.memory_info.vms', value=74522624, tags=['optional:tags'])


def test_bad_process_metric_check(check):
    ''' Tests that a bad configuration option for `process_metrics` gets ignored '''
    stats, names_to_metric_types = check._psutil_config_to_stats(MOCK_CONFIG)

    assert 'memory_info' in names_to_metric_types
    assert names_to_metric_types['memory_info'] == 'gauge'

    assert 'non_existent_stat' not in names_to_metric_types

    assert 'memory_info' in stats
    assert 'non_existent_stat' not in stats


# Tests for Agent Default Mode
def test_no_process_metrics_collected(check):
    ''' Test that additional process metrics are not collected when in default mode '''
    check._register_psutil_metrics = mock.MagicMock(side_effect=AssertionError)
    check._psutil_config_to_stats = mock.MagicMock(side_effect=AssertionError)

    check.check(MOCK_CONFIG)
